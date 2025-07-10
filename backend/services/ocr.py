import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import re
import os
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image for better OCR results"""
        img = Image.open(image_path)
        
        # Convert to grayscale
        img = img.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)
        
        # Apply sharpening filter
        img = img.filter(ImageFilter.SHARPEN)
        
        # Resize image if too small
        width, height = img.size
        if width < 800:
            scale = 800 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return img
    
    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract kWh reading from image
        Returns: (reading_value, confidence_score)
        """
        try:
            # Preprocess image
            img = self.preprocess_image(image_path)
            
            # Perform OCR with confidence scores
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            # Extract text and confidence
            text = pytesseract.image_to_string(img)
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            logger.info(f"OCR raw text: {text}")
            logger.info(f"OCR confidence: {avg_confidence}")
            
            # Look for number patterns (supporting various formats)
            patterns = [
                r'(\d{1,6}[.,]\d{1,2})',  # 1234.56 or 1234,56
                r'(\d{1,6}\s*[.,]\s*\d{1,2})',  # 1234 . 56 (with spaces)
                r'(\d{4,6})',  # 123456 (no decimal)
            ]
            
            reading = None
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    # Take the first valid match
                    for match in matches:
                        try:
                            # Clean and convert the match
                            cleaned = match.replace(' ', '').replace(',', '.')
                            value = float(cleaned)
                            
                            # Sanity check - meter readings should be reasonable
                            if 0 < value < 999999:
                                reading = value
                                break
                        except ValueError:
                            continue
                
                if reading:
                    break
            
            return reading, avg_confidence
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return None, 0.0
    
    def save_processed_image(self, image_path: str, output_path: str) -> bool:
        """Save preprocessed image for debugging"""
        try:
            img = self.preprocess_image(image_path)
            img.save(output_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save processed image: {str(e)}")
            return False