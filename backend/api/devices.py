from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db import crud
from models.device import DeviceResponse, DeviceListResponse, DeviceCreate, DeviceUpdate

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get("", response_model=DeviceListResponse)
async def get_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Get list of all known devices"""
    
    query = db.query(crud.models.Device)
    
    if not include_inactive:
        query = query.filter(crud.models.Device.is_active == True)
    
    total = query.count()
    devices = query.offset(skip).limit(limit).all()
    
    # Convert to response model with status calculation
    device_responses = []
    for device in devices:
        device_dict = {
            "id": device.id,
            "name": device.name,
            "is_active": device.is_active,
            "last_ping": device.last_ping,
            "battery_percent": device.battery_percent,
            "created_at": device.created_at,
            "updated_at": device.updated_at
        }
        device_responses.append(DeviceResponse(**device_dict))
    
    return DeviceListResponse(
        devices=device_responses,
        total=total
    )

@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific device"""
    
    device = crud.get_device(db, device_id)
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found"
        )
    
    device_dict = {
        "id": device.id,
        "name": device.name,
        "is_active": device.is_active,
        "last_ping": device.last_ping,
        "battery_percent": device.battery_percent,
        "created_at": device.created_at,
        "updated_at": device.updated_at
    }
    
    return DeviceResponse(**device_dict)

@router.post("", response_model=DeviceResponse)
async def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db)
):
    """Register a new device"""
    
    # Check if device already exists
    existing = crud.get_device(db, device.id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Device {device.id} already exists"
        )
    
    new_device = crud.create_device(db, device.id, device.name)
    
    device_dict = {
        "id": new_device.id,
        "name": new_device.name,
        "is_active": new_device.is_active,
        "last_ping": new_device.last_ping,
        "battery_percent": new_device.battery_percent,
        "created_at": new_device.created_at,
        "updated_at": new_device.updated_at
    }
    
    return DeviceResponse(**device_dict)

@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_update: DeviceUpdate,
    db: Session = Depends(get_db)
):
    """Update device information"""
    
    device = crud.update_device(db, device_id, device_update)
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found"
        )
    
    device_dict = {
        "id": device.id,
        "name": device.name,
        "is_active": device.is_active,
        "last_ping": device.last_ping,
        "battery_percent": device.battery_percent,
        "created_at": device.created_at,
        "updated_at": device.updated_at
    }
    
    return DeviceResponse(**device_dict)

@router.get("/{device_id}/health", response_model=dict)
async def get_device_health(
    device_id: str,
    db: Session = Depends(get_db)
):
    """Get device health and statistics"""
    
    device = crud.get_device(db, device_id)
    
    if not device:
        raise HTTPException(
            status_code=404,
            detail=f"Device {device_id} not found"
        )
    
    # Get last reading for this device
    last_reading = crud.get_latest_reading(db, device_id)
    
    # Calculate uptime percentage (last 7 days)
    from datetime import datetime, timedelta
    week_ago = datetime.utcnow() - timedelta(days=7)
    
    readings_last_week = crud.get_readings(
        db,
        device_id=device_id,
        start_date=week_ago,
        limit=1000
    )
    
    # Expected readings (1 per day minimum)
    expected_readings = 7
    actual_readings = len(readings_last_week)
    uptime_percentage = min(100, (actual_readings / expected_readings) * 100)
    
    # Device status
    if not device.last_ping:
        status = "never_connected"
        health_score = 0
    else:
        time_since_ping = datetime.utcnow() - device.last_ping
        
        if time_since_ping.total_seconds() > 86400:  # More than 24 hours
            status = "offline"
            health_score = 0
        elif device.battery_percent and device.battery_percent < 10:
            status = "critical_battery"
            health_score = 25
        elif device.battery_percent and device.battery_percent < 20:
            status = "low_battery"
            health_score = 50
        elif time_since_ping.total_seconds() > 3600:  # More than 1 hour
            status = "delayed"
            health_score = 75
        else:
            status = "healthy"
            health_score = 100
    
    return {
        "device_id": device_id,
        "status": status,
        "health_score": health_score,
        "battery_percent": device.battery_percent,
        "last_ping": device.last_ping,
        "last_reading": {
            "timestamp": last_reading.timestamp if last_reading else None,
            "kwh": last_reading.reading_kwh if last_reading else None
        },
        "uptime_percentage_7d": round(uptime_percentage, 1),
        "readings_last_7d": actual_readings
    }