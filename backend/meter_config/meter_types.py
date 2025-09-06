from typing import Dict, List, Any
from pydantic import BaseModel

class MeterTypeConfig(BaseModel):
    """Configuration for different meter types"""
    name: str
    manufacturer: str
    keywords: List[str]  # Keywords to identify this meter type in OCR results
    use_advanced_ocr: bool
    display_characteristics: Dict[str, Any]

# Predefined meter configurations
METER_TYPES = {
    "iskra_digital": MeterTypeConfig(
        name="ISKRA Digital",
        manufacturer="ISKRA",
        keywords=["iskra", "slovenia", "me162"],
        use_advanced_ocr=True,
        display_characteristics={
            "display_type": "lcd",
            "digits": 8,
            "decimal_places": 1,
            "expected_patterns": [r'\d{8}[.,]\d{1}', r'\d{5,8}']
        }
    ),
    "generic_digital": MeterTypeConfig(
        name="Generic Digital",
        manufacturer="Generic",
        keywords=["kwh", "digital"],
        use_advanced_ocr=True,
        display_characteristics={
            "display_type": "lcd",
            "digits": 6,
            "decimal_places": 2,
            "expected_patterns": [r'\d{4,6}[.,]\d{1,2}', r'\d{4,6}']
        }
    ),
    "analog_mechanical": MeterTypeConfig(
        name="Analog Mechanical",
        manufacturer="Generic",
        keywords=["mechanical", "analog"],
        use_advanced_ocr=False,  # Basic OCR works better for clear mechanical digits
        display_characteristics={
            "display_type": "mechanical",
            "digits": 5,
            "decimal_places": 1,
            "expected_patterns": [r'\d{5}[.,]\d{1}', r'\d{5}']
        }
    )
}

def detect_meter_type(ocr_text: str) -> str:
    """Detect meter type based on OCR text"""
    text_lower = ocr_text.lower()
    
    for meter_id, config in METER_TYPES.items():
        for keyword in config.keywords:
            if keyword in text_lower:
                return meter_id
    
    return "generic_digital"  # Default fallback