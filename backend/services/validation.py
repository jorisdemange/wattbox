from typing import List, Optional, Tuple
import re
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class ValidationService:
    def __init__(self, allowed_device_ids: List[str], max_reading_jump: float = 100.0):
        self.allowed_device_ids = allowed_device_ids
        self.max_reading_jump = max_reading_jump
    
    def validate_device_id(self, device_id: str) -> bool:
        """Check if device ID is in allowlist"""
        return device_id in self.allowed_device_ids
    
    def validate_image_file(self, filename: str, content_type: str, 
                          file_size: int) -> Tuple[bool, Optional[str]]:
        """Validate uploaded image file"""
        # Check file extension
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        ext = filename.lower().split('.')[-1]
        if f'.{ext}' not in allowed_extensions:
            return False, f"Invalid file extension: {ext}"
        
        # Check content type
        allowed_content_types = {
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/bmp', 'image/tiff'
        }
        if content_type not in allowed_content_types:
            return False, f"Invalid content type: {content_type}"
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return False, f"File too large: {file_size} bytes (max {max_size})"
        
        return True, None
    
    def validate_reading_value(self, reading: float, 
                             previous_reading: Optional[float] = None,
                             time_since_last: Optional[timedelta] = None) -> Tuple[bool, Optional[str]]:
        """Validate meter reading value"""
        # Basic range check
        if reading < 0:
            return False, "Reading cannot be negative"
        
        if reading > 999999:
            return False, "Reading too large (max 999999)"
        
        # Check against previous reading if available
        if previous_reading is not None:
            if reading < previous_reading:
                return False, f"Reading {reading} is less than previous {previous_reading}"
            
            # Check for abnormal jump
            jump = reading - previous_reading
            if jump > self.max_reading_jump:
                # Calculate expected daily usage if we have time info
                if time_since_last:
                    days = time_since_last.total_seconds() / 86400
                    daily_jump = jump / days if days > 0 else jump
                    
                    # Allow higher jumps over longer periods
                    if daily_jump > self.max_reading_jump:
                        return False, f"Abnormal jump detected: {jump} kWh in {days:.1f} days"
                else:
                    return False, f"Abnormal jump detected: {jump} kWh"
        
        return True, None
    
    def validate_battery_level(self, battery_percent: float) -> Tuple[bool, Optional[str]]:
        """Validate battery percentage"""
        if battery_percent < 0 or battery_percent > 100:
            return False, f"Invalid battery percentage: {battery_percent}"
        return True, None
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Replace special characters
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Ensure it has an extension
        if '.' not in filename:
            filename += '.jpg'
        
        return filename[:255]  # Max filename length