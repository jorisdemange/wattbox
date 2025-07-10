from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from db.database import get_db
from db import crud
from models.reading import ReadingResponse, ReadingListResponse
from services.pricing import PricingService
from config import get_settings

router = APIRouter(prefix="/readings", tags=["readings"])

settings = get_settings()
pricing_service = PricingService(settings.PRICE_PER_KWH)

@router.get("", response_model=ReadingListResponse)
async def get_readings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all readings with optional filters"""
    
    readings = crud.get_readings(
        db, 
        skip=skip, 
        limit=limit,
        device_id=device_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Get total count for pagination
    total_query = db.query(crud.models.Reading)
    if device_id:
        total_query = total_query.filter(crud.models.Reading.device_id == device_id)
    if start_date:
        total_query = total_query.filter(crud.models.Reading.timestamp >= start_date)
    if end_date:
        total_query = total_query.filter(crud.models.Reading.timestamp <= end_date)
    
    total = total_query.count()
    
    return ReadingListResponse(
        readings=readings,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/last", response_model=ReadingResponse)
async def get_last_reading(
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get the latest reading for a device or overall"""
    
    reading = crud.get_latest_reading(db, device_id)
    
    if not reading:
        raise HTTPException(
            status_code=404,
            detail="No readings found"
        )
    
    return reading

@router.get("/daily", response_model=dict)
async def get_daily_usage(
    days: int = Query(7, ge=1, le=90),
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get daily usage statistics for the last N days"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    readings = crud.get_readings_by_date_range(db, start_date, end_date, device_id)
    
    if len(readings) < 2:
        return {
            "days": days,
            "total_kwh": 0,
            "total_cost": 0,
            "daily_average_kwh": 0,
            "daily_average_cost": 0,
            "readings_count": len(readings)
        }
    
    # Calculate usage
    first_reading = readings[0]
    last_reading = readings[-1]
    total_kwh = last_reading.reading_kwh - first_reading.reading_kwh
    
    # Calculate cost
    total_cost = pricing_service.calculate_cost(total_kwh)
    
    # Calculate daily averages
    actual_days = (last_reading.timestamp - first_reading.timestamp).days or 1
    daily_avg_kwh = total_kwh / actual_days
    daily_avg_cost = total_cost / actual_days
    
    return {
        "days": days,
        "actual_days": actual_days,
        "total_kwh": round(total_kwh, 2),
        "total_cost": round(total_cost, 2),
        "daily_average_kwh": round(daily_avg_kwh, 2),
        "daily_average_cost": round(daily_avg_cost, 2),
        "readings_count": len(readings),
        "first_reading": {
            "timestamp": first_reading.timestamp,
            "kwh": first_reading.reading_kwh
        },
        "last_reading": {
            "timestamp": last_reading.timestamp,
            "kwh": last_reading.reading_kwh
        }
    }

@router.get("/monthly-estimate", response_model=dict)
async def get_monthly_estimate(
    device_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get estimated monthly usage and cost based on recent data"""
    
    # Get last 30 days of readings
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    readings = crud.get_readings_by_date_range(db, start_date, end_date, device_id)
    
    if len(readings) < 2:
        return {
            "estimated_monthly_kwh": 0,
            "estimated_monthly_cost": 0,
            "average_daily_kwh": 0,
            "average_daily_cost": 0,
            "based_on_days": 0,
            "confidence": "low"
        }
    
    # Group by day and calculate daily usage
    daily_usage = []
    for i in range(1, len(readings)):
        prev = readings[i-1]
        curr = readings[i]
        
        # Only include if readings are from different days
        if curr.timestamp.date() != prev.timestamp.date():
            days_diff = (curr.timestamp - prev.timestamp).days
            if days_diff > 0:
                kwh_diff = curr.reading_kwh - prev.reading_kwh
                daily_kwh = kwh_diff / days_diff
                if daily_kwh > 0:  # Sanity check
                    daily_usage.append(daily_kwh)
    
    if not daily_usage:
        # Fall back to total period calculation
        total_kwh = readings[-1].reading_kwh - readings[0].reading_kwh
        total_days = (readings[-1].timestamp - readings[0].timestamp).days or 1
        daily_usage = [total_kwh / total_days]
    
    # Calculate estimates
    estimate = pricing_service.estimate_monthly_cost(daily_usage)
    
    # Determine confidence based on data points
    if len(daily_usage) >= 20:
        confidence = "high"
    elif len(daily_usage) >= 10:
        confidence = "medium"
    else:
        confidence = "low"
    
    return {
        **estimate,
        "based_on_days": len(daily_usage),
        "confidence": confidence
    }

@router.get("/{reading_id}", response_model=ReadingResponse)
async def get_reading(
    reading_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific reading by ID"""
    
    reading = db.query(crud.models.Reading).filter(
        crud.models.Reading.id == reading_id
    ).first()
    
    if not reading:
        raise HTTPException(
            status_code=404,
            detail="Reading not found"
        )
    
    return reading