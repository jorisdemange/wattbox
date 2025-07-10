from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timedelta
from typing import List, Optional
from db import models
from models.reading import ReadingCreate
from models.device import DeviceUpdate

def get_device(db: Session, device_id: str) -> Optional[models.Device]:
    return db.query(models.Device).filter(models.Device.id == device_id).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100) -> List[models.Device]:
    return db.query(models.Device).offset(skip).limit(limit).all()

def create_device(db: Session, device_id: str, name: Optional[str] = None) -> models.Device:
    db_device = models.Device(id=device_id, name=name)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def update_device(db: Session, device_id: str, device_update: DeviceUpdate) -> Optional[models.Device]:
    db_device = get_device(db, device_id)
    if db_device:
        update_data = device_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_device, field, value)
        db.commit()
        db.refresh(db_device)
    return db_device

def create_reading(db: Session, reading: ReadingCreate) -> models.Reading:
    db_reading = models.Reading(**reading.model_dump())
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading

def get_readings(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    device_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[models.Reading]:
    query = db.query(models.Reading)
    
    if device_id:
        query = query.filter(models.Reading.device_id == device_id)
    if start_date:
        query = query.filter(models.Reading.timestamp >= start_date)
    if end_date:
        query = query.filter(models.Reading.timestamp <= end_date)
    
    return query.order_by(desc(models.Reading.timestamp)).offset(skip).limit(limit).all()

def get_latest_reading(db: Session, device_id: Optional[str] = None) -> Optional[models.Reading]:
    query = db.query(models.Reading)
    if device_id:
        query = query.filter(models.Reading.device_id == device_id)
    return query.order_by(desc(models.Reading.timestamp)).first()

def get_readings_by_date_range(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    device_id: Optional[str] = None
) -> List[models.Reading]:
    query = db.query(models.Reading).filter(
        models.Reading.timestamp >= start_date,
        models.Reading.timestamp <= end_date
    )
    if device_id:
        query = query.filter(models.Reading.device_id == device_id)
    return query.order_by(models.Reading.timestamp).all()