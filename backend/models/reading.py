from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class SourceType(str, Enum):
    DEVICE = "device"
    MANUAL = "manual"

class ReadingBase(BaseModel):
    reading_kwh: float = Field(..., description="Electricity reading in kWh")
    source: SourceType
    device_id: Optional[str] = None
    battery_percent: Optional[float] = Field(None, ge=0, le=100)
    ocr_confidence: Optional[float] = Field(None, ge=0, le=100)
    price_per_kwh: float = Field(..., gt=0)
    manual_override: bool = False

class ReadingCreate(ReadingBase):
    timestamp: Optional[datetime] = None
    photo_path: str
    processed_photo_path: Optional[str] = None

class ReadingUpdate(BaseModel):
    reading_kwh: Optional[float] = None
    ocr_confidence: Optional[float] = None
    processed_photo_path: Optional[str] = None

class ReadingResponse(ReadingBase):
    id: int
    timestamp: datetime
    photo_path: str
    processed_photo_path: Optional[str] = None
    created_at: datetime
    cost: float
    
    class Config:
        from_attributes = True

class ReadingListResponse(BaseModel):
    readings: list[ReadingResponse]
    total: int
    skip: int
    limit: int