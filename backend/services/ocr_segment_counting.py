#!/usr/bin/env python3
"""
Seven-segment OCR using segment detection instead of template matching.
This is lighting-invariant because it detects which segments are ON, not pixel intensity.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Seven-segment patterns for each digit
# Index: [top, top-right, bottom-right, bottom, bottom-left, top-left, middle]
SEGMENT_PATTERNS = {
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


class SegmentCountingOCR:
    """OCR using seven-segment analysis"""

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract meter reading from image"""
        try:
            # Preprocess
            preprocessed = self._preprocess(image_path)

            # Segment digits using fixed-width (we know there are 8 digits)
            h, w = preprocessed.shape
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

                digit_img = preprocessed[y:y+digit_h, x:x+digit_width]

                # Detect which segments are lit
                digit, conf = self._recognize_digit_by_segments(digit_img)
                digits.append(str(digit))
                confidences.append(conf)

                logger.info(f"Digit {i}: {digit} (confidence: {conf:.1f}%)")

            result_str = ''.join(digits)
            logger.info(f"Recognized: {result_str}")

            if len(result_str) == 8:
                reading = float(result_str[:7] + '.' + result_str[7])
                avg_conf = sum(confidences) / len(confidences)
                return reading, avg_conf

            return None, 0.0

        except Exception as e:
            logger.error(f"Segment counting OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _preprocess(self, image_path: str) -> np.ndarray:
        """Preprocess image"""
        img = Image.open(image_path)
        if img.format == 'MPO':
            img = img.convert('RGB')
        elif img.mode not in ['RGB', 'L']:
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

        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=21,
            C=10
        )

        # Clean
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def _recognize_digit_by_segments(self, digit_img: np.ndarray) -> Tuple[int, float]:
        """
        Recognize digit by detecting which seven segments are lit.
        Returns (digit, confidence)
        """
        h, w = digit_img.shape

        # Define segment regions (as fractions of digit bounds)
        # Each segment is (y1, y2, x1, x2) as fractions
        segment_regions = {
            'top':         (0.0, 0.2, 0.2, 0.8),
            'top_right':   (0.1, 0.45, 0.7, 1.0),
            'bottom_right': (0.55, 0.9, 0.7, 1.0),
            'bottom':      (0.8, 1.0, 0.2, 0.8),
            'bottom_left': (0.55, 0.9, 0.0, 0.3),
            'top_left':    (0.1, 0.45, 0.0, 0.3),
            'middle':      (0.45, 0.55, 0.2, 0.8),
        }

        # Detect which segments are ON
        detected_segments = []
        segment_order = ['top', 'top_right', 'bottom_right', 'bottom', 'bottom_left', 'top_left', 'middle']

        for seg_name in segment_order:
            y1, y2, x1, x2 = segment_regions[seg_name]
            y1_px, y2_px = int(h * y1), int(h * y2)
            x1_px, x2_px = int(w * x1), int(w * x2)

            region = digit_img[y1_px:y2_px, x1_px:x2_px]

            if region.size == 0:
                detected_segments.append(0)
                continue

            # Segment is ON if more than 30% of pixels are white
            white_ratio = np.sum(region > 128) / region.size
            detected_segments.append(1 if white_ratio > 0.3 else 0)

        # Match against patterns
        best_digit = 0
        best_score = -1

        for digit_str, pattern in SEGMENT_PATTERNS.items():
            # Calculate similarity (how many segments match)
            matches = sum(1 for i in range(7) if detected_segments[i] == pattern[i])
            score = matches / 7.0

            if score > best_score:
                best_score = score
                best_digit = int(digit_str)

        confidence = best_score * 100

        return best_digit, confidence


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_segment_counting.py <image_path>")
        sys.exit(1)

    ocr = SegmentCountingOCR()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print("\n" + "="*70)
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print("✗ Failed to extract reading")
    print("="*70)
