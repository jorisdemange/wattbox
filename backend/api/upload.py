from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
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
from services.ocr_advanced import AdvancedOCRService
from services.storage import StorageService
from services.validation import ValidationService
from services.pricing import PricingService
from meter_config.meter_types import detect_meter_type, METER_TYPES
from config import get_settings

router = APIRouter(prefix="/upload", tags=["upload"])
logger = logging.getLogger(__name__)

settings = get_settings()
ocr_service = OCRService(settings.TESSERACT_PATH)
advanced_ocr_service = AdvancedOCRService(settings.TESSERACT_PATH)
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
            logger.info(f"Processing image at path: {full_path}")
            logger.info(f"File exists: {os.path.exists(full_path)}")
            
            # First, do a basic OCR scan to detect meter type
            from PIL import Image
            import pytesseract
            
            try:
                img = Image.open(full_path)
                logger.info(f"Image opened successfully: {img.format}, {img.size}, {img.mode}")
                
                # Convert MPO or other formats to standard RGB/L format
                if img.format in ['MPO', 'HEIF', 'HEIC'] or img.mode not in ['RGB', 'L']:
                    logger.info(f"Converting image from {img.format}/{img.mode} to RGB")
                    img = img.convert('RGB')
                    
            except Exception as img_error:
                logger.error(f"Failed to open image: {str(img_error)}")
                raise
                
            initial_text = pytesseract.image_to_string(img)
            meter_type = detect_meter_type(initial_text)
            logger.info(f"Detected meter type: {meter_type}")
            
            # Use appropriate OCR service based on meter type
            meter_config = METER_TYPES.get(meter_type)
            if meter_config and meter_config.use_advanced_ocr:
                logger.info("Using advanced OCR service")
                reading_kwh, confidence = advanced_ocr_service.extract_reading(full_path)
            else:
                logger.info("Using basic OCR service")
                reading_kwh, confidence = ocr_service.extract_reading(full_path)
            
            if reading_kwh is None:
                storage_service.move_to_failed(photo_path)
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Could not extract reading from image. Please provide manual reading."
                )
            
            # Save processed image
            if meter_config and meter_config.use_advanced_ocr:
                # For advanced OCR, save the detected region if available
                import cv2
                display_region = advanced_ocr_service.detect_display_region(full_path)
                if display_region is not None:
                    img_buffer = BytesIO()
                    Image.fromarray(cv2.cvtColor(display_region, cv2.COLOR_BGR2RGB)).save(img_buffer, format='PNG')
                else:
                    processed_img = ocr_service.preprocess_image(full_path)
                    img_buffer = BytesIO()
                    processed_img.save(img_buffer, format='PNG')
            else:
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