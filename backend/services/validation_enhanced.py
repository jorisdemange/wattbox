from typing import Tuple, Dict, List
import logging

logger = logging.getLogger(__name__)

class EnhancedValidationService:
    """Enhanced validation with confidence-based rules and heuristics"""
    
    def __init__(self):
        # Confidence thresholds for different scenarios
        self.confidence_thresholds = {
            'high_confidence': 0.85,     # Very confident, accept without question
            'medium_confidence': 0.70,    # Reasonably confident, apply basic validation
            'low_confidence': 0.50,       # Low confidence, apply strict validation
            'reject_threshold': 0.30      # Too low, always reject
        }
        
        # Historical reading validation parameters
        self.max_daily_increase = 100.0  # Max kWh increase per day (reasonable for most homes)
        self.max_daily_decrease = 0.0    # Readings should never decrease
        self.typical_daily_usage = 30.0   # Typical household usage
        
    def validate_reading_with_confidence(
        self, 
        reading: float, 
        confidence: float,
        previous_reading: float = None,
        days_since_last: float = None
    ) -> Tuple[bool, str, Dict]:
        """
        Validate a reading based on confidence score and historical data
        Returns: (is_valid, error_message, validation_details)
        """
        validation_details = {
            'confidence_level': self._get_confidence_level(confidence),
            'checks_performed': [],
            'warnings': []
        }
        
        # Check 1: Confidence threshold
        if confidence < self.confidence_thresholds['reject_threshold']:
            return False, "OCR confidence too low", validation_details
        
        # Check 2: Basic range validation
        if reading < 0 or reading > 999999:
            return False, "Reading out of valid range", validation_details
        
        validation_details['checks_performed'].append('basic_range')
        
        # Check 3: Historical validation (if previous reading available)
        if previous_reading is not None and days_since_last is not None:
            increase = reading - previous_reading
            daily_increase = increase / max(days_since_last, 0.1)
            
            validation_details['checks_performed'].append('historical_comparison')
            validation_details['daily_increase'] = daily_increase
            
            # Reading decreased (meter rollback?)
            if increase < self.max_daily_decrease:
                return False, f"Reading decreased from {previous_reading} to {reading}", validation_details
            
            # Suspiciously high increase
            if daily_increase > self.max_daily_increase:
                if confidence >= self.confidence_thresholds['high_confidence']:
                    # High confidence, just warn
                    validation_details['warnings'].append(
                        f"Unusually high usage: {daily_increase:.1f} kWh/day"
                    )
                else:
                    # Low confidence + suspicious reading = reject
                    return False, f"Suspicious daily increase: {daily_increase:.1f} kWh/day", validation_details
            
            # Check if increase is reasonable
            if 0 < daily_increase < self.typical_daily_usage * 3:
                validation_details['reading_quality'] = 'normal'
            elif daily_increase > self.typical_daily_usage * 5:
                validation_details['reading_quality'] = 'suspicious'
            else:
                validation_details['reading_quality'] = 'acceptable'
        
        # Check 4: Confidence-based additional validation
        if confidence < self.confidence_thresholds['medium_confidence']:
            # For low confidence, check if reading has reasonable number of digits
            reading_str = str(int(reading))
            if len(reading_str) < 4:
                validation_details['warnings'].append("Unusually low reading value")
            
            # Check for common OCR errors
            if self._has_common_ocr_errors(reading):
                validation_details['warnings'].append("Potential OCR misread detected")
        
        # All checks passed
        return True, "", validation_details
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Categorize confidence score"""
        if confidence >= self.confidence_thresholds['high_confidence']:
            return 'high'
        elif confidence >= self.confidence_thresholds['medium_confidence']:
            return 'medium'
        elif confidence >= self.confidence_thresholds['low_confidence']:
            return 'low'
        else:
            return 'very_low'
    
    def _has_common_ocr_errors(self, reading: float) -> bool:
        """Check for common OCR misreads"""
        reading_str = str(reading)
        
        # Common OCR errors:
        # - Reading all 1s, 7s, or 0s (111111, 777777)
        # - Repeated patterns (121212, 123123)
        
        # Check for all same digit
        if len(set(reading_str.replace('.', ''))) == 1:
            return True
        
        # Check for simple repeated patterns
        if len(reading_str) >= 4:
            half = len(reading_str) // 2
            if reading_str[:half] == reading_str[half:2*half]:
                return True
        
        return False
    
    def suggest_manual_review(self, confidence: float, validation_details: Dict) -> bool:
        """Determine if manual review should be suggested"""
        if confidence < self.confidence_thresholds['medium_confidence']:
            return True
        
        if validation_details.get('warnings'):
            return True
        
        if validation_details.get('reading_quality') == 'suspicious':
            return True
        
        return False