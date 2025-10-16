"""
Custom Seven-Segment OCR
Uses contour-based digit recognition for LCD displays
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class CustomSevenSegmentOCR:
    """Custom seven-segment digit recognizer using contour analysis"""

    def __init__(self):
        # Seven-segment digit patterns (which segments are ON for each digit)
        # Segments: top, top-right, bottom-right, bottom, bottom-left, top-left, middle
        self.digit_patterns = {
            '0': [1, 1, 1, 1, 1, 1, 0],
            '1': [0, 1, 1, 0, 0, 0, 0],
            '2': [1, 1, 0, 1, 1, 0, 1],
            '3': [1, 1, 1, 1, 0, 0, 1],
            '4': [0, 1, 1, 0, 0, 1, 1],
            '5': [1, 0, 1, 1, 0, 1, 1],
            '6': [1, 0, 1, 1, 1, 1, 1],
            '7': [1, 1, 1, 0, 0, 0, 0],
            '8': [1, 1, 1, 1, 1, 1, 1],
            '9': [1, 1, 1, 1, 0, 1, 1],
        }

    def preprocess(self, image_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """Preprocess image for seven-segment recognition"""
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            from PIL import Image
            pil_img = Image.open(image_path)
            if pil_img.mode == 'RGBA':
                pil_img = pil_img.convert('RGB')
            img = np.array(pil_img)
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Invert (we want white digits on black background)
        inverted = cv2.bitwise_not(gray)

        # Threshold to get clean binary image
        _, binary = cv2.threshold(inverted, 127, 255, cv2.THRESH_BINARY)

        # Denoise
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        return gray, cleaned

    def find_digit_regions(self, binary: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Find bounding boxes of individual digits"""
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Get bounding boxes
        boxes = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter by size - digits should have certain aspect ratio
            aspect_ratio = h / w if w > 0 else 0
            area = w * h

            # Seven-segment digits are roughly 1.5-2.5 times taller than wide
            if 1.2 < aspect_ratio < 3.5 and area > 100:
                boxes.append((x, y, w, h))

        # Sort by x coordinate (left to right)
        boxes.sort(key=lambda b: b[0])

        return boxes

    def recognize_digit_simple(self, digit_img: np.ndarray) -> str:
        """Simple digit recognition by counting segments"""
        h, w = digit_img.shape

        # Divide into 7 regions for seven-segment check
        # Top horizontal
        top = digit_img[0:h//4, w//4:3*w//4]
        # Top right vertical
        tr = digit_img[0:h//2, 2*w//3:w]
        # Bottom right vertical
        br = digit_img[h//2:h, 2*w//3:w]
        # Bottom horizontal
        bottom = digit_img[3*h//4:h, w//4:3*w//4]
        # Bottom left vertical
        bl = digit_img[h//2:h, 0:w//3]
        # Top left vertical
        tl = digit_img[0:h//2, 0:w//3]
        # Middle horizontal
        middle = digit_img[2*h//5:3*h//5, w//4:3*w//4]

        # Check if each segment is ON (has white pixels)
        threshold = 0.3  # Segment is ON if >30% of region is white

        segments = [
            np.mean(top) / 255 > threshold,      # top
            np.mean(tr) / 255 > threshold,       # top-right
            np.mean(br) / 255 > threshold,       # bottom-right
            np.mean(bottom) / 255 > threshold,   # bottom
            np.mean(bl) / 255 > threshold,       # bottom-left
            np.mean(tl) / 255 > threshold,       # top-left
            np.mean(middle) / 255 > threshold,   # middle
        ]

        # Convert to int pattern
        pattern = [1 if s else 0 for s in segments]

        # Match against known patterns
        best_match = None
        best_score = 0

        for digit, digit_pattern in self.digit_patterns.items():
            # Count matching segments
            matches = sum(p == d for p, d in zip(pattern, digit_pattern))
            if matches > best_score:
                best_score = matches
                best_match = digit

        # Need at least 5/7 segments matching
        if best_score >= 5:
            return best_match
        else:
            return '?'

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract reading from seven-segment display

        Returns:
            (reading_kwh, confidence)
        """
        try:
            logger.info(f"Custom seven-segment OCR processing: {image_path}")

            # Preprocess
            gray, binary = self.preprocess(image_path)

            # Save debug image
            cv2.imwrite('/tmp/custom_ssd_binary.jpg', binary)

            # Find digit regions
            boxes = self.find_digit_regions(binary)

            if len(boxes) < 6:
                logger.warning(f"Found only {len(boxes)} digits, expected 8")

            logger.info(f"Found {len(boxes)} potential digit regions")

            # Extract and recognize each digit
            digits = []
            for i, (x, y, w, h) in enumerate(boxes):
                # Extract digit
                digit_img = binary[y:y+h, x:x+w]

                # Save for debugging
                cv2.imwrite(f'/tmp/digit_{i}.jpg', digit_img)

                # Recognize
                digit = self.recognize_digit_simple(digit_img)
                digits.append(digit)
                logger.debug(f"Digit {i}: '{digit}' at ({x},{y},{w},{h})")

            # Build reading string
            reading_str = ''.join(digits)
            logger.info(f"Recognized digits: '{reading_str}'")

            # Check for unknowns
            if '?' in reading_str:
                logger.warning(f"Could not recognize all digits: {reading_str}")
                return None, 0.0

            # Parse the reading
            # Iskra meter shows 8 digits: 0007783.2
            # Format: XXXXXXX.X
            if len(reading_str) == 8:
                # Insert decimal point before last digit
                reading_with_decimal = reading_str[:7] + '.' + reading_str[7]
                value = float(reading_with_decimal)

                # Confidence is based on how many digits we found
                confidence = (len(boxes) / 8.0) * 100.0

                logger.info(f"Parsed reading: {value} kWh (confidence: {confidence:.1f}%)")
                return value, confidence
            elif len(reading_str) >= 6:
                # Try without leading zeros
                value = float(reading_str[:-1] + '.' + reading_str[-1])
                confidence = 75.0
                logger.info(f"Parsed reading (trimmed): {value} kWh")
                return value, confidence
            else:
                logger.warning(f"Unexpected digit count: {len(reading_str)}")
                return None, 0.0

        except Exception as e:
            logger.error(f"Custom seven-segment OCR failed: {e}", exc_info=True)
            return None, 0.0


# Test function
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ocr_seven_segment_custom.py <image_path>")
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG)

    ocr = CustomSevenSegmentOCR()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print(f"\nResult: {reading} kWh (confidence: {confidence:.1f}%)")
    print(f"Preprocessed images saved to /tmp/")
