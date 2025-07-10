from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

Base = declarative_base()

class SourceType(enum.Enum):
    DEVICE = "device"
    MANUAL = "manual"

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    last_ping = Column(DateTime(timezone=True), nullable=True)
    battery_percent = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Reading(Base):
    __tablename__ = "readings"
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    reading_kwh = Column(Float, nullable=False)
    photo_path = Column(String, nullable=False)
    processed_photo_path = Column(String, nullable=True)
    source = Column(Enum(SourceType), nullable=False)
    device_id = Column(String, nullable=True)
    battery_percent = Column(Float, nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    price_per_kwh = Column(Float, nullable=False)
    manual_override = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    @property
    def cost(self):
        return self.reading_kwh * self.price_per_kwh if self.price_per_kwh else 0