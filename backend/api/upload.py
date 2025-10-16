from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
import os
from io import BytesIO

from db.database import get_db
from db import crud
from models.reading import ReadingCreate, ReadingResponse, SourceType
from models.device import DeviceUpdate
from services.ocr import OCRService
from services.ocr_orchestrator import OCROrchestrator, OCRStrategy
from services.storage import StorageService
from services.validation import ValidationService
from services.pricing import PricingService
from config import get_settings

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

settings = get_settings()
ocr_orchestrator = OCROrchestrator(settings.TESSERACT_PATH)
ocr_service = OCRService(settings.TESSERACT_PATH)  # Keep for backward compatibility
storage_service = StorageService(settings.UPLOAD_DIRECTORY, settings.S3_BUCKET_NAME, settings.AWS_REGION)
validation_service = ValidationService(settings.ALLOWED_DEVICE_IDS.split(','))
pricing_service = PricingService(settings.PRICE_PER_KWH)

@router.post("/device", response_model=ReadingResponse)
async def upload_from_device(
    device_id: str = Form(...),
    file: UploadFile = File(...),
    battery_percent: Optional[float] = Form(None),
    timestamp: Optional[datetime] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload image from ESP32 device"""
    
    # Validate device ID
    if not validation_service.validate_device_id(device_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device ID {device_id} not allowed"
        )
    
    # Validate file
    is_valid, error_msg = validation_service.validate_image_file(
        file.filename, file.content_type, file.size
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Update device info
    device = crud.get_device(db, device_id)
    if not device:
        device = crud.create_device(db, device_id)
    
    device_update = DeviceUpdate(
        last_ping=datetime.utcnow(),
        battery_percent=battery_percent
    )
    crud.update_device(db, device_id, device_update)
    
    # Save raw image
    try:
        file_content = await file.read()
        sanitized_filename = validation_service.sanitize_filename(file.filename)
        photo_path = storage_service.save_raw_image(
            file_content, sanitized_filename, device_id
        )
    except Exception as e:
        logger.error(f"Failed to save image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image"
        )
    
    # Perform OCR using orchestrator
    try:
        full_path = storage_service.get_full_path(photo_path)

        # Use orchestrator with fallback if enabled
        if settings.OCR_ENABLE_FALLBACK:
            ocr_result = ocr_orchestrator.process_with_fallback(
                full_path,
                primary_strategy=OCRStrategy(settings.OCR_DEFAULT_STRATEGY),
                confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD
            )
        else:
            ocr_result = ocr_orchestrator.extract_reading(
                full_path,
                strategy=OCRStrategy(settings.OCR_DEFAULT_STRATEGY)
            )

        reading_value = ocr_result.reading_kwh
        confidence = ocr_result.confidence

        if reading_value is None:
            # Move to failed directory
            storage_service.move_to_failed(photo_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract reading from image. Strategy: {ocr_result.strategy_used}"
            )

        # Validate reading value
        last_reading = crud.get_latest_reading(db, device_id)
        if last_reading:
            time_diff = datetime.utcnow() - last_reading.timestamp
            is_valid, error_msg = validation_service.validate_reading_value(
                reading_value, last_reading.reading_kwh, time_diff
            )
            if not is_valid:
                logger.warning(f"Reading validation failed: {error_msg}")
                # Optionally still save with a flag

        # Save processed image
        processed_img = ocr_service.preprocess_image(full_path)
        img_buffer = BytesIO()
        processed_img.save(img_buffer, format='PNG')
        processed_path = storage_service.save_processed_image(
            photo_path, img_buffer.getvalue()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR processing failed"
        )
    
    # Create reading record
    reading_data = ReadingCreate(
        timestamp=timestamp or datetime.utcnow(),
        reading_kwh=reading_value,
        photo_path=photo_path,
        processed_photo_path=processed_path,
        source=SourceType.DEVICE,
        device_id=device_id,
        battery_percent=battery_percent,
        ocr_confidence=confidence,
        price_per_kwh=pricing_service.get_current_price(timestamp)
    )
    
    reading = crud.create_reading(db, reading_data)
    return reading

@router.post("/manual/extract")
async def extract_reading_from_photo(
    file: UploadFile = File(...),
):
    """Extract reading from photo without saving it (for manual confirmation)"""

    # Validate file
    is_valid, error_msg = validation_service.validate_image_file(
        file.filename, file.content_type, file.size
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    try:
        # Read file content into memory
        file_content = await file.read()

        # Process OCR directly from memory without saving
        from PIL import Image
        image = Image.open(BytesIO(file_content))

        # Save temporarily for OCR processing
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name

        try:
            # Use orchestrator with fallback for best results
            if settings.OCR_ENABLE_FALLBACK:
                ocr_result = ocr_orchestrator.process_with_fallback(
                    tmp_path,
                    primary_strategy=OCRStrategy(settings.OCR_DEFAULT_STRATEGY),
                    confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD
                )
            else:
                ocr_result = ocr_orchestrator.extract_reading(
                    tmp_path,
                    strategy=OCRStrategy(settings.OCR_DEFAULT_STRATEGY)
                )

            # Clean up temp file
            os.unlink(tmp_path)

            if ocr_result.reading_kwh is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Could not extract reading from image. Strategy used: {ocr_result.strategy_used}"
                )

            return {
                "reading_kwh": ocr_result.reading_kwh,
                "confidence": ocr_result.confidence,
                "strategy_used": ocr_result.strategy_used.value,
                "meter_type": ocr_result.meter_type
            }
        except HTTPException:
            raise
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR extraction failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OCR extraction failed"
        )

@router.post("/manual", response_model=ReadingResponse)
async def upload_manual(
    reading_kwh: float = Form(...),
    timestamp: Optional[datetime] = Form(None),
    notes: Optional[str] = Form(None),
    device_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Save manual reading (no photo storage)"""

    # Validate reading value
    is_valid, error_msg = validation_service.validate_reading_value(reading_kwh)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reading: {error_msg}"
        )

    # Create reading record without photo
    reading_data = ReadingCreate(
        timestamp=timestamp or datetime.utcnow(),
        reading_kwh=reading_kwh,
        photo_path=None,  # No photo saved for manual entries
        processed_photo_path=None,
        source=SourceType.DEVICE if device_id else SourceType.MANUAL,
        device_id=device_id,
        ocr_confidence=100.0,  # Manual entry = 100% confidence
        price_per_kwh=pricing_service.get_current_price(timestamp),
        manual_override=True,
        notes=notes
    )

    reading = crud.create_reading(db, reading_data)
    return reading