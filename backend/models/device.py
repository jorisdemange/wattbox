from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DeviceBase(BaseModel):
    name: Optional[str] = None
    is_active: bool = True

class DeviceCreate(DeviceBase):
    id: str = Field(..., description="Unique device identifier")

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    last_ping: Optional[datetime] = None
    battery_percent: Optional[float] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None

class DeviceResponse(DeviceBase):
    id: str
    last_ping: Optional[datetime] = None
    battery_percent: Optional[float] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    status: str = Field(..., description="Device status: online, offline, or low_battery")
    
    class Config:
        from_attributes = True
    
    def __init__(self, **data):
        # Calculate status before validation
        if 'last_ping' in data and data['last_ping']:
            time_diff = datetime.now() - data['last_ping'].replace(tzinfo=None)
            if time_diff.total_seconds() > 3600:  # More than 1 hour
                data['status'] = "offline"
            elif 'battery_percent' in data and data['battery_percent'] and data['battery_percent'] < 20:
                data['status'] = "low_battery"
            else:
                data['status'] = "online"
        else:
            data['status'] = "offline"
        super().__init__(**data)

class DeviceListResponse(BaseModel):
    devices: list[DeviceResponse]
    total: int