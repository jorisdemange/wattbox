"""Simple OCR approach for Iskra meter - focus on getting ANY numbers"""

import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class SimpleOCR:
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Simple approach: try multiple preprocessing methods and OCR configs"""
        
        # Load image
        img = cv2.imread(image_path)
        if img is None:
            pil_img = Image.open(image_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            img = np.array(pil_img)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        height, width = img.shape[:2]
        
        # Crop to display area (rough estimate for Iskra meter)
        y1 = int(height * 0.22)
        y2 = int(height * 0.42)
        x1 = int(width * 0.38)
        x2 = int(width * 0.82)
        display_area = img[y1:y2, x1:x2]
        
        # Save cropped area for debugging
        cv2.imwrite('/tmp/meter_display_crop.jpg', display_area)
        
        best_reading = None
        best_confidence = 0
        
        # Try different preprocessing methods
        preprocessing_methods = [
            ('original', display_area),
            ('grayscale', cv2.cvtColor(display_area, cv2.COLOR_BGR2GRAY)),
            ('threshold_binary', self.apply_threshold(display_area, cv2.THRESH_BINARY)),
            ('threshold_binary_inv', self.apply_threshold(display_area, cv2.THRESH_BINARY_INV)),
            ('adaptive_mean', self.apply_adaptive_threshold(display_area, cv2.ADAPTIVE_THRESH_MEAN_C)),
            ('adaptive_gaussian', self.apply_adaptive_threshold(display_area, cv2.ADAPTIVE_THRESH_GAUSSIAN_C)),
        ]
        
        # OCR configurations to try
        ocr_configs = [
            '',  # Default
            '--psm 6',  # Uniform block
            '--psm 7',  # Single line
            '--psm 8',  # Single word
            '--psm 11',  # Sparse text
            '--psm 13',  # Raw line
            '-c tessedit_char_whitelist=0123456789.',
            '--psm 7 -c tessedit_char_whitelist=0123456789.',
            '--psm 8 -c tessedit_char_whitelist=0123456789.',
        ]
        
        for prep_name, processed_img in preprocessing_methods:
            # Skip if image is too dark or too bright
            if len(processed_img.shape) == 2:  # Grayscale
                mean_val = np.mean(processed_img)
                if mean_val < 10 or mean_val > 245:
                    continue
            
            # Save for debugging
            if prep_name != 'original':
                cv2.imwrite(f'/tmp/meter_{prep_name}.jpg', processed_img)
            
            # Convert to PIL for OCR
            if len(processed_img.shape) == 3:  # Color
                pil_img = Image.fromarray(cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB))
            else:  # Grayscale
                pil_img = Image.fromarray(processed_img)
            
            for config in ocr_configs:
                try:
                    # Run OCR
                    text = pytesseract.image_to_string(pil_img, config=config)
                    text = text.strip()
                    
                    if text:
                        logger.info(f"OCR [{prep_name}][{config}]: {text}")
                        
                        # Extract numbers
                        numbers = re.findall(r'[\d.]+', text)
                        for num_str in numbers:
                            try:
                                # Skip if just a dot
                                if num_str == '.':
                                    continue
                                
                                # Remove multiple dots
                                if num_str.count('.') > 1:
                                    num_str = num_str.replace('.', '', num_str.count('.') - 1)
                                
                                value = float(num_str)
                                
                                # Iskra meter format: 0007510.3
                                # Could be read as 7510.3 or 75103 or 00075103
                                if value > 100000:  # Probably missing decimal
                                    value = value / 10
                                
                                # Sanity check for meter reading
                                if 0 < value < 99999:
                                    # Get confidence
                                    data = pytesseract.image_to_data(pil_img, config=config, output_type=pytesseract.Output.DICT)
                                    confidences = [int(c) for c in data['conf'] if int(c) > 0]
                                    confidence = sum(confidences) / len(confidences) if confidences else 50
                                    
                                    if confidence > best_confidence or (confidence == best_confidence and value > best_reading):
                                        best_reading = value
                                        best_confidence = confidence
                                        logger.info(f"Found potential reading: {value} kWh (confidence: {confidence})")
                            except ValueError:
                                continue
                except Exception as e:
                    logger.debug(f"OCR failed [{prep_name}][{config}]: {e}")
                    continue
        
        return best_reading, best_confidence
    
    def apply_threshold(self, img, threshold_type):
        """Apply threshold to image"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        _, thresh = cv2.threshold(gray, 0, 255, threshold_type + cv2.THRESH_OTSU)
        return thresh
    
    def apply_adaptive_threshold(self, img, method):
        """Apply adaptive threshold"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        return cv2.adaptiveThreshold(gray, 255, method, cv2.THRESH_BINARY, 11, 2)