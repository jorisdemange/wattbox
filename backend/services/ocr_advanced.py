import cv2
import numpy as np
import pytesseract
from PIL import Image
import re
from typing import Tuple, Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class AdvancedOCRService:
    """Advanced OCR service with region detection and meter-specific logic"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
        # Common meter patterns and their priorities
        self.meter_patterns = {
            'lcd_display': {
                'pattern': r'\d{5,8}[.,]\d{1,3}',  # LCD displays often show 5-8 digits with decimals
                'priority': 10,
                'validation': lambda x: 0 <= float(x.replace(',', '.')) <= 999999.999
            },
            'digital_reading': {
                'pattern': r'\d{8}',  # Some meters show 8 digits without decimals
                'priority': 8,
                'validation': lambda x: len(x) == 8
            },
            'standard_reading': {
                'pattern': r'\d{4,6}',  # Standard 4-6 digit readings
                'priority': 5,
                'validation': lambda x: 1000 <= int(x) <= 999999
            }
        }
    
    def detect_display_region(self, image_path: str) -> Optional[np.ndarray]:
        """Detect the LCD/display region in the meter image"""
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Failed to read image with cv2: {image_path}")
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Detect edges
        edges = cv2.Canny(denoised, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find rectangular regions that could be displays
        display_candidates = []
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            
            if len(approx) == 4:  # Rectangle
                x, y, w, h = cv2.boundingRect(approx)
                aspect_ratio = w / h
                
                # LCD displays typically have aspect ratio between 2:1 and 5:1
                if 2.0 <= aspect_ratio <= 5.0 and w > 100 and h > 30:
                    display_candidates.append((x, y, w, h, w * h))
        
        if display_candidates:
            # Sort by area and take the largest
            display_candidates.sort(key=lambda x: x[4], reverse=True)
            x, y, w, h, _ = display_candidates[0]
            
            # Add some padding
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img.shape[1] - x, w + 2 * padding)
            h = min(img.shape[0] - y, h + 2 * padding)
            
            return img[y:y+h, x:x+w]
        
        return None
    
    def enhance_lcd_region(self, image: np.ndarray) -> Image.Image:
        """Enhance LCD region for better OCR"""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply adaptive thresholding for LCD displays
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 11, 2)
        
        # Invert if necessary (dark digits on light background)
        if np.mean(thresh) > 127:
            thresh = cv2.bitwise_not(thresh)
        
        # Convert to PIL Image
        return Image.fromarray(thresh)
    
    def extract_text_regions(self, image_path: str) -> List[Dict]:
        """Extract all text regions with their locations and confidence"""
        img = Image.open(image_path)
        
        # Convert to RGB if needed (for MPO, HEIF, etc.)
        if img.mode not in ['RGB', 'L']:
            img = img.convert('RGB')
        
        # Get OCR data with positions
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        text_regions = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 30:  # Confidence threshold
                text = data['text'][i].strip()
                if text:
                    text_regions.append({
                        'text': text,
                        'conf': data['conf'][i],
                        'x': data['left'][i],
                        'y': data['top'][i],
                        'w': data['width'][i],
                        'h': data['height'][i]
                    })
        
        return text_regions
    
    def find_reading_value(self, text_regions: List[Dict]) -> Tuple[Optional[float], float]:
        """Find the most likely reading value from text regions"""
        candidates = []
        
        for region in text_regions:
            text = region['text']
            
            # Check against each pattern type
            for pattern_name, pattern_info in self.meter_patterns.items():
                matches = re.findall(pattern_info['pattern'], text)
                
                for match in matches:
                    try:
                        # Normalize the number (replace comma with dot)
                        normalized = match.replace(',', '.')
                        value = float(normalized)
                        
                        # Validate the value
                        if pattern_info['validation'](match):
                            candidates.append({
                                'value': value,
                                'confidence': region['conf'] / 100.0,
                                'priority': pattern_info['priority'],
                                'pattern': pattern_name,
                                'y_position': region['y']
                            })
                    except ValueError:
                        continue
        
        if not candidates:
            return None, 0.0
        
        # Score candidates based on:
        # 1. Pattern priority (LCD patterns are preferred)
        # 2. Confidence score
        # 3. Y position (readings are usually in upper half of meter)
        
        image_height = max(r['y'] + r['h'] for r in text_regions)
        
        for candidate in candidates:
            # Normalize y position (0 = top, 1 = bottom)
            y_norm = candidate['y_position'] / image_height
            
            # Prefer readings in upper 60% of image
            position_score = 1.0 if y_norm < 0.6 else 0.7
            
            # Calculate final score
            candidate['score'] = (
                candidate['priority'] * 0.5 +
                candidate['confidence'] * 0.3 +
                position_score * 0.2
            )
        
        # Sort by score and return best candidate
        candidates.sort(key=lambda x: x['score'], reverse=True)
        best = candidates[0]
        
        return best['value'], best['confidence']
    
    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract kWh reading from image with advanced techniques
        Returns: (reading_value, confidence_score)
        """
        try:
            # First, try to detect and extract LCD region
            display_region = self.detect_display_region(image_path)
            
            if display_region is not None:
                logger.info("LCD region detected, processing...")
                # Enhance and OCR the LCD region
                enhanced = self.enhance_lcd_region(display_region)
                
                # Save enhanced region for debugging
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    enhanced.save(tmp.name)
                    region_texts = self.extract_text_regions(tmp.name)
                
                reading, confidence = self.find_reading_value(region_texts)
                if reading is not None:
                    logger.info(f"Found reading in LCD region: {reading} kWh (confidence: {confidence:.2f})")
                    return reading, confidence
            
            # Fallback: process entire image
            logger.info("Processing entire image...")
            all_texts = self.extract_text_regions(image_path)
            reading, confidence = self.find_reading_value(all_texts)
            
            if reading is not None:
                logger.info(f"Found reading: {reading} kWh (confidence: {confidence:.2f})")
                return reading, confidence
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return None, 0.0