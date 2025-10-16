"""
Shotgun OCR Approach - Read everything, filter for meter reading pattern
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class ShotgunOCR:
    """
    Shotgun approach: OCR the entire image, extract all numbers,
    find the one that matches meter reading pattern (7-8 digits)
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract reading by OCRing everything and filtering for meter pattern
        """
        try:
            # Load image
            img = Image.open(image_path)
            if img.format == 'MPO':
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img_cv = np.array(img)
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

            # Downscale large images for speed (OCR works better on ~1000px width)
            height, width = img_cv.shape[:2]
            if width > 2000:
                scale = 2000 / width
                new_width = 2000
                new_height = int(height * scale)
                img_cv = cv2.resize(img_cv, (new_width, new_height), interpolation=cv2.INTER_AREA)
                logger.info(f"Downscaled image from {width}x{height} to {new_width}x{new_height}")

            # Try multiple preprocessing strategies and collect all text
            all_text = []

            # Strategy 1: Direct PSM 11 (sparse text - best for meters)
            text = pytesseract.image_to_string(img_cv, config='--psm 11')
            all_text.append(text)

            # Strategy 2: PSM 6 (uniform block)
            text = pytesseract.image_to_string(img_cv, config='--psm 6 digits')
            all_text.append(text)

            # Strategy 3: Grayscale + threshold
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(binary, config='--psm 11')
            all_text.append(text)

            # Combine all text
            combined_text = '\n'.join(all_text)
            logger.info(f"Total text extracted: {len(combined_text)} chars")

            # Find meter reading pattern
            reading, confidence = self._extract_meter_reading(combined_text)

            if reading:
                logger.info(f"✓ Found meter reading: {reading} kWh (confidence: {confidence:.1f}%)")
            else:
                logger.warning("✗ No valid meter reading found in extracted text")

            return reading, confidence

        except Exception as e:
            logger.error(f"Shotgun OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _ocr_image(self, img, strategy_name: str) -> str:
        """OCR an image and return text"""
        try:
            # Try multiple Tesseract configs
            configs = [
                '--psm 11',  # Sparse text
                '--psm 12',  # Sparse text with OSD
                '--psm 3',   # Fully automatic
                'digits',    # Only digits
            ]

            all_text = []
            for config in configs:
                try:
                    text = pytesseract.image_to_string(img, config=config)
                    all_text.append(text)
                except:
                    pass

            combined = '\n'.join(all_text)
            logger.debug(f"Strategy {strategy_name}: {len(combined)} chars")
            return combined

        except Exception as e:
            logger.debug(f"OCR failed for {strategy_name}: {e}")
            return ""

    def _extract_meter_reading(self, text: str) -> Tuple[Optional[float], float]:
        """
        Extract meter reading from text using pattern matching.
        Meter readings are 7-8 consecutive digits (with last digit after decimal point)
        """
        # Remove all whitespace and special characters
        cleaned = re.sub(r'[^0-9]', '', text)

        logger.info(f"Cleaned text (digits only): {cleaned}")

        # Find all sequences of 7-8 digits
        patterns = [
            r'(\d{8})',  # 8 digits (e.g., 00077832 -> 7783.2)
            r'(\d{7})',  # 7 digits (e.g., 0077832 -> 7783.2)
        ]

        candidates = []

        for pattern in patterns:
            matches = re.finditer(pattern, cleaned)
            for match in matches:
                digit_str = match.group(1)

                # Convert to reading (last digit is decimal)
                if len(digit_str) == 8:
                    reading = float(digit_str[:7] + '.' + digit_str[7])
                elif len(digit_str) == 7:
                    reading = float(digit_str[:6] + '.' + digit_str[6])
                else:
                    continue

                # Sanity checks
                if 0 < reading < 100000:  # Reasonable meter reading range
                    confidence = 80.0  # Base confidence for pattern match
                    candidates.append((reading, confidence))
                    logger.info(f"  Candidate: {reading} kWh from digits '{digit_str}'")

        if not candidates:
            # Try finding any 6+ digit sequences
            long_sequences = re.findall(r'\d{6,}', cleaned)
            logger.info(f"Found {len(long_sequences)} sequences of 6+ digits: {long_sequences}")

            for seq in long_sequences:
                # Try different interpretations
                for length in [8, 7, 6]:
                    if len(seq) >= length:
                        digit_str = seq[:length]
                        if length == 8:
                            reading = float(digit_str[:7] + '.' + digit_str[7])
                        elif length == 7:
                            reading = float(digit_str[:6] + '.' + digit_str[6])
                        elif length == 6:
                            reading = float(digit_str[:5] + '.' + digit_str[5])

                        if 0 < reading < 100000:
                            candidates.append((reading, 50.0))  # Lower confidence
                            logger.info(f"  Candidate (alt): {reading} kWh from '{digit_str}'")

        if candidates:
            # Sort by confidence and return best
            candidates.sort(key=lambda x: x[1], reverse=True)
            best = candidates[0]

            # Log all candidates for debugging
            logger.info(f"Total candidates found: {len(candidates)}")
            for i, (reading, conf) in enumerate(candidates[:5], 1):
                logger.info(f"  #{i}: {reading} kWh ({conf:.1f}%)")

            return best
        else:
            logger.warning("No candidates found matching meter reading pattern")
            return None, 0.0


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_shotgun.py <image_path>")
        sys.exit(1)

    ocr = ShotgunOCR()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print(f"\n{'='*70}")
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print(f"✗ Failed to extract reading")
    print(f"{'='*70}")
