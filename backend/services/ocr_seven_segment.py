"""OCR service optimized for seven-segment displays on electricity meters"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class SevenSegmentOCR:
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # Try to use seven-segment trained data if available
        self.use_ssd = self.check_ssd_available()
        
    def check_ssd_available(self) -> bool:
        """Check if seven-segment display trained data is available"""
        try:
            # Test if ssd (seven segment display) or letsgodigital trained data exists
            test_img = np.ones((100, 100), dtype=np.uint8) * 255
            pytesseract.image_to_string(test_img, lang='ssd', config='--psm 8')
            logger.info("Seven-segment OCR model (ssd) is available")
            return True
        except:
            logger.info("Seven-segment OCR model not available, using standard OCR")
            return False
    
    def preprocess_for_seven_segment(self, image_path: str) -> np.ndarray:
        """Preprocess image specifically for seven-segment display reading"""
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            # Try with PIL for different formats
            pil_img = Image.open(image_path)
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            img = np.array(pil_img)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        height, width = img.shape[:2]
        
        # For Iskra meter: crop to display area
        # Display is typically in upper-middle portion
        display_y1 = int(height * 0.20)  # Start a bit higher
        display_y2 = int(height * 0.50)  # Go a bit lower
        display_x1 = int(width * 0.30)   # Start a bit more left
        display_x2 = int(width * 0.90)   # Go a bit more right
        
        cropped = img[display_y1:display_y2, display_x1:display_x2]
        
        # Convert to grayscale
        gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
        
        # Apply bilateral filter to reduce noise while keeping edges sharp
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Use OTSU thresholding for better binarization
        _, thresh = cv2.threshold(filtered, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find the display area more precisely using contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the largest rectangular contour (likely the display)
        display_contour = None
        max_area = 0
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area and area > 1000:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h
                # Seven-segment displays are typically wide
                if 2.0 < aspect_ratio < 6.0:
                    max_area = area
                    display_contour = (x, y, w, h)
        
        if display_contour:
            x, y, w, h = display_contour
            # Crop to detected display with small padding
            pad = 5
            display_region = thresh[max(0, y-pad):min(thresh.shape[0], y+h+pad),
                                   max(0, x-pad):min(thresh.shape[1], x+w+pad)]
        else:
            display_region = thresh
        
        # Invert if necessary (white digits on black background)
        mean_val = np.mean(display_region)
        if mean_val > 127:  # Mostly white, so invert
            display_region = cv2.bitwise_not(display_region)
        
        # Morphological operations to clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        display_region = cv2.morphologyEx(display_region, cv2.MORPH_CLOSE, kernel)
        
        # Scale up for better OCR
        scale_factor = 3
        width = int(display_region.shape[1] * scale_factor)
        height = int(display_region.shape[0] * scale_factor)
        display_region = cv2.resize(display_region, (width, height), interpolation=cv2.INTER_CUBIC)
        
        return display_region
    
    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract meter reading from seven-segment display"""
        try:
            # Preprocess image
            processed = self.preprocess_for_seven_segment(image_path)
            
            # Save processed image for debugging
            debug_path = '/tmp/processed_seven_segment.jpg'
            cv2.imwrite(debug_path, processed)
            logger.info(f"Saved processed image to {debug_path}")
            
            # Try multiple OCR configurations
            configs = [
                '--psm 7 -c tessedit_char_whitelist=0123456789.',  # Single line
                '--psm 8 -c tessedit_char_whitelist=0123456789.',  # Single word
                '--psm 13 -c tessedit_char_whitelist=0123456789.', # Raw line
                '--psm 6',  # Uniform block
            ]
            
            # If seven-segment model available, try it first
            if self.use_ssd:
                configs.insert(0, '--psm 8 -l ssd')
                configs.insert(1, '--psm 7 -l ssd')
            
            best_reading = None
            best_confidence = 0
            
            for config in configs:
                try:
                    # Get text with confidence
                    data = pytesseract.image_to_data(processed, config=config, output_type=pytesseract.Output.DICT)
                    
                    # Extract text and confidence
                    text_parts = []
                    confidences = []
                    for i, conf in enumerate(data['conf']):
                        if int(conf) > 0:
                            text_parts.append(data['text'][i])
                            confidences.append(int(conf))
                    
                    text = ''.join(text_parts)
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    logger.info(f"Config '{config}': text='{text}', confidence={avg_confidence}")
                    
                    # Parse reading
                    if text:
                        # Remove spaces and normalize
                        text = text.replace(' ', '').replace(',', '.')
                        
                        # Look for number pattern
                        match = re.search(r'(\d+\.?\d*)', text)
                        if match:
                            value = float(match.group(1))
                            
                            # Iskra meter shows readings like 0007510.3 (7510.3 kWh)
                            # Format: 7 digits before decimal, 1 after
                            # If we get a large number without decimal, add decimal point
                            if value > 100000 and '.' not in match.group(1):
                                # Assume last digit is decimal
                                value = value / 10
                            elif value > 10000000 and '.' not in match.group(1):
                                # If we somehow read all 8 digits as one number
                                value = value / 10
                            
                            # Sanity check
                            if 0 < value < 999999:
                                if avg_confidence > best_confidence:
                                    best_reading = value
                                    best_confidence = avg_confidence
                
                except Exception as e:
                    logger.debug(f"Config {config} failed: {e}")
                    continue
            
            if best_reading:
                logger.info(f"Best reading: {best_reading} kWh, confidence: {best_confidence}")
                return best_reading, best_confidence
            
            # Fallback: try to extract any numbers from the processed image
            text = pytesseract.image_to_string(processed)
            logger.info(f"Fallback OCR text: {text}")
            
            # Look for any number sequence
            numbers = re.findall(r'\d+', text)
            if numbers:
                # Take the longest number (likely the reading)
                longest = max(numbers, key=len)
                if len(longest) >= 4:  # At least 4 digits
                    value = float(longest)
                    if value > 10000:
                        value = value / 100
                    if 0 < value < 999999:
                        return value, 50.0  # Lower confidence for fallback
            
            return None, 0.0
            
        except Exception as e:
            logger.error(f"Seven-segment OCR failed: {str(e)}")
            return None, 0.0