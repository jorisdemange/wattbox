from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import logging
from io import BytesIO

from db.database import get_db
from db import crud
from models.reading import ReadingCreate, ReadingResponse, SourceType
from models.device import DeviceUpdate
from services.ocr import OCRService
from services.storage import StorageService
from services.validation import ValidationService
from services.pricing import PricingService
from config import get_settings

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

settings = get_settings()
ocr_service = OCRService(settings.TESSERACT_PATH)
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
    
    # Perform OCR
    try:
        full_path = storage_service.get_full_path(photo_path)
        reading_value, confidence = ocr_service.extract_reading(full_path)
        
        if reading_value is None:
            # Move to failed directory
            storage_service.move_to_failed(photo_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not extract reading from image"
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

@router.post("/manual", response_model=ReadingResponse)
async def upload_manual(
    file: UploadFile = File(...),
    reading_kwh: Optional[float] = Form(None),
    timestamp: Optional[datetime] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload image manually (from web or iPhone)"""
    
    # Validate file
    is_valid, error_msg = validation_service.validate_image_file(
        file.filename, file.content_type, file.size
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Save raw image
    try:
        file_content = await file.read()
        sanitized_filename = validation_service.sanitize_filename(file.filename)
        photo_path = storage_service.save_raw_image(
            file_content, sanitized_filename
        )
    except Exception as e:
        logger.error(f"Failed to save image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image"
        )
    
    # Use manual reading or perform OCR
    confidence = 100.0
    manual_override = False
    
    if reading_kwh is None:
        try:
            full_path = storage_service.get_full_path(photo_path)
            reading_kwh, confidence = ocr_service.extract_reading(full_path)
            
            if reading_kwh is None:
                storage_service.move_to_failed(photo_path)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract reading from image. Please provide manual reading."
                )
            
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
    else:
        manual_override = True
        processed_path = None
        
        # Validate manual reading
        is_valid, error_msg = validation_service.validate_reading_value(reading_kwh)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    
    # Create reading record
    reading_data = ReadingCreate(
        timestamp=timestamp or datetime.utcnow(),
        reading_kwh=reading_kwh,
        photo_path=photo_path,
        processed_photo_path=processed_path,
        source=SourceType.MANUAL,
        ocr_confidence=confidence,
        price_per_kwh=pricing_service.get_current_price(timestamp),
        manual_override=manual_override
    )
    
    reading = crud.create_reading(db, reading_data)
    return reading