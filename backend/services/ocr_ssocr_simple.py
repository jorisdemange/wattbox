"""
Simple Seven-Segment OCR - Use Tesseract on individual digits
"""

import logging
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image
import pytesseract

logger = logging.getLogger(__name__)


class SimpleSSOCR:
    """Simple seven-segment OCR using Tesseract on individual digits"""

    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract reading from seven-segment display by OCR-ing each digit separately

        Returns:
            (reading_kwh, confidence)
        """
        try:
            # Preprocess
            preprocessed = self._preprocess(image_path)
            cv2.imwrite('/tmp/ssocr_simple_prep.png', preprocessed)

            h, w = preprocessed.shape

            # Divide into 8 equal slices
            num_digits = 8
            margin_x = int(w * 0.05)
            usable_width = w - 2 * margin_x
            digit_width = usable_width // num_digits

            digits = []
            confidences = []

            for i in range(num_digits):
                x = margin_x + i * digit_width
                y = int(h * 0.1)
                digit_h = int(h * 0.8)

                # Extract single digit
                digit_img = preprocessed[y:y+digit_h, x:x+digit_width]

                # Scale up significantly for this single digit
                scaled = cv2.resize(digit_img, (digit_img.shape[1]*15, digit_img.shape[0]*15),
                                  interpolation=cv2.INTER_CUBIC)

                cv2.imwrite(f'/tmp/digit_simple_{i}.png', scaled)

                # OCR this single digit with PSM 10 (single character)
                pil_digit = Image.fromarray(scaled)

                best_digit = None
                best_conf = 0

                # Try different configurations
                configs = [
                    '--psm 10 -c tessedit_char_whitelist=0123456789',
                    '--psm 8 -c tessedit_char_whitelist=0123456789',
                    '--psm 7 -c tessedit_char_whitelist=0123456789',
                ]

                for config in configs:
                    try:
                        text = pytesseract.image_to_string(pil_digit, config=config).strip()
                        # Clean
                        text = ''.join(c for c in text if c.isdigit())

                        if text and len(text) == 1:
                            # Got a single digit, get confidence
                            try:
                                data = pytesseract.image_to_data(pil_digit, config=config, output_type=pytesseract.Output.DICT)
                                # Get highest confidence
                                confs = [c for c in data['conf'] if c != -1]
                                conf = max(confs) if confs else 50
                            except:
                                conf = 50

                            if conf > best_conf:
                                best_digit = text
                                best_conf = conf
                            break
                    except:
                        pass

                if best_digit:
                    digits.append(best_digit)
                    confidences.append(best_conf)
                    logger.info(f"Digit {i}: {best_digit} (conf: {best_conf:.1f}%)")
                else:
                    logger.warning(f"Digit {i}: FAILED")
                    digits.append('?')
                    confidences.append(0)

            # Build result
            result_str = ''.join(digits)
            logger.info(f"Recognized: {result_str}")

            if '?' in result_str:
                logger.warning(f"Could not recognize all digits: {result_str}")
                return None, 0.0

            if len(result_str) == 8:
                # Format: XXXXXXX.X
                reading = float(result_str[:7] + '.' + result_str[7])
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                logger.info(f"Final reading: {reading} kWh (avg conf: {avg_conf:.1f}%)")
                return reading, avg_conf
            else:
                logger.warning(f"Wrong number of digits: {len(result_str)}")
                return None, 0.0

        except Exception as e:
            logger.error(f"Simple seven-segment OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _preprocess(self, image_path: str) -> np.ndarray:
        """Preprocess image"""
        img = Image.open(image_path)
        if img.mode == 'RGBA':
            img = img.convert('RGB')

        img_cv = np.array(img)
        if len(img_cv.shape) == 3:
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_cv

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=15)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)

        # Threshold (white on black for Tesseract)
        _, binary = cv2.threshold(enhanced, 120, 255, cv2.THRESH_BINARY_INV)

        # Clean
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return cleaned


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

    if len(sys.argv) < 2:
        print("Usage: python ocr_ssocr_simple.py <image_path>")
        sys.exit(1)

    ocr = SimpleSSOCR('/opt/homebrew/bin/tesseract')
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print(f"\n{'='*70}")
    print(f"Result: {reading} kWh (confidence: {confidence:.1f}%)")
    print(f"Expected: 7783.2 kWh")

    if reading:
        diff = abs(reading - 7783.2)
        if diff < 0.1:
            print(f"\n✓✓✓ SUCCESS! Perfect match! ✓✓✓")
        elif diff < 10:
            print(f"\nClose - off by {diff:.1f} kWh")
        else:
            print(f"\nOff by {diff:.1f} kWh")
    print(f"{'='*70}")
