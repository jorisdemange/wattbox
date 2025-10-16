from fastapi import APIRouter, Request, Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from io import BytesIO
import logging

from db.database import get_db
from db import crud
from models.reading import ReadingCreate, SourceType
from models.device import DeviceUpdate
from services.ocr import OCRService
from services.ocr_orchestrator import OCROrchestrator, OCRStrategy
from services.storage import StorageService
from services.pricing import PricingService
from config import get_settings

router = APIRouter(prefix="/api", tags=["esp32"])
logger = logging.getLogger(__name__)

settings = get_settings()
ocr_orchestrator = OCROrchestrator(settings.TESSERACT_PATH)
ocr_service = OCRService(settings.TESSERACT_PATH)  # Keep for backward compatibility
storage_service = StorageService(settings.UPLOAD_DIRECTORY, settings.S3_BUCKET_NAME, settings.AWS_REGION)
pricing_service = PricingService(settings.PRICE_PER_KWH)

@router.post("/upload")
async def upload_from_esp32(
    request: Request,
    device_id: str = Header(None, alias="X-Device-ID"),
    device_name: str = Header(None, alias="X-Device-Name"),
    db: Session = Depends(get_db)
):
    """ESP32-CAM upload endpoint matching embedded/esp32-cam/API.md spec"""
    
    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID header required"
        )
    
    # Get image data
    image_data = await request.body()
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image data received"
        )
    
    # Update device info
    device = crud.get_device(db, device_id)
    if not device:
        device = crud.create_device(db, device_id, device_name)
    
    device_update = DeviceUpdate(
        last_ping=datetime.utcnow(),
        name=device_name
    )
    crud.update_device(db, device_id, device_update)
    
    # Save raw image
    try:
        filename = f"esp32_{device_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
        photo_path = storage_service.save_raw_image(
            image_data, filename, device_id
        )
    except Exception as e:
        logger.error(f"Failed to save ESP32 image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save image"
        )
    
    # Perform OCR using orchestrator with fallback
    try:
        full_path = storage_service.get_full_path(photo_path)

        # Use orchestrator with fallback for ESP32 images
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

        logger.info(f"ESP32 OCR result: reading={reading_value}, confidence={confidence:.2f}, "
                   f"strategy={ocr_result.strategy_used}")

        if reading_value is None:
            storage_service.move_to_failed(photo_path)
            return {
                "status": "received",
                "device": device_id,
                "ocr_failed": True,
                "message": f"Image saved but OCR failed. Strategy: {ocr_result.strategy_used}"
            }

        # Save processed image
        processed_img = ocr_service.preprocess_image(full_path)
        img_buffer = BytesIO()
        processed_img.save(img_buffer, format='PNG')
        processed_path = storage_service.save_processed_image(
            photo_path, img_buffer.getvalue()
        )

    except Exception as e:
        logger.error(f"OCR processing failed: {str(e)}")
        return {
            "status": "received",
            "device": device_id,
            "ocr_failed": True,
            "error": str(e)
        }
    
    # Create reading record
    reading_data = ReadingCreate(
        timestamp=datetime.utcnow(),
        reading_kwh=reading_value,
        photo_path=photo_path,
        processed_photo_path=processed_path,
        source=SourceType.DEVICE,
        device_id=device_id,
        ocr_confidence=confidence,
        price_per_kwh=pricing_service.get_current_price(datetime.utcnow())
    )
    
    reading = crud.create_reading(db, reading_data)
    
    return {
        "status": "received",
        "device": device_id,
        "reading": reading_value,
        "confidence": confidence,
        "reading_id": reading.id
    }