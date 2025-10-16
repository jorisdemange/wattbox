#!/usr/bin/env python3
"""
Seven-segment OCR using ssocr segment detection logic with fixed-width segmentation.
Combines: fixed-width (works) + segment counting (lighting-invariant)
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Seven-segment lookup (order matters!)
SEGMENTS = {
    (1, 1, 1, 0, 1, 1, 1): '0',
    (0, 0, 1, 0, 0, 1, 0): '1',
    (1, 0, 1, 1, 1, 0, 1): '2',
    (1, 0, 1, 1, 0, 1, 1): '3',
    (0, 1, 1, 1, 0, 1, 0): '4',
    (1, 1, 0, 1, 0, 1, 1): '5',
    (1, 1, 0, 1, 1, 1, 1): '6',
    (1, 0, 1, 0, 0, 1, 0): '7',  # Note: 7 is same as 1 in some LCDs!
    (1, 1, 1, 1, 1, 1, 1): '8',
    (1, 1, 1, 1, 0, 1, 1): '9',
}


class SSOcrFixed:
    """Seven-segment OCR: ssocr logic + fixed-width segmentation"""

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract meter reading"""
        try:
            binary = self._preprocess(image_path)

            # Fixed-width segmentation (8 digits)
            h, w = binary.shape
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

                digit_roi = binary[y:y+digit_h, x:x+digit_width]
                digit_char, conf = self._recognize_segment_digit(digit_roi)
                digits.append(digit_char)
                confidences.append(conf)
                logger.info(f"Digit {i}: {digit_char} ({conf:.1f}%)")

            result_str = ''.join(digits)
            logger.info(f"Recognized: {result_str}")

            reading = float(result_str[:7] + '.' + result_str[7])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return reading, avg_conf

        except Exception as e:
            logger.error(f"OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _preprocess(self, image_path: str) -> np.ndarray:
        """Aggressive preprocessing"""
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

        # Strong denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, h=20)

        # CLAHE
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # Otsu threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Morphological operations
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return binary

    def _recognize_segment_digit(self, digit_roi: np.ndarray) -> Tuple[str, float]:
        """Recognize digit by segment pattern"""
        h, w = digit_roi.shape

        # Seven segments: top, top-right, bottom-right, middle, bottom-left, top-left, bottom
        segments_map = [
            (0.0, 0.15, 0.15, 0.85),    # top
            (0.1, 0.45, 0.6, 1.0),      # top-right
            (0.55, 0.9, 0.6, 1.0),      # bottom-right
            (0.45, 0.55, 0.15, 0.85),   # middle
            (0.55, 0.9, 0.0, 0.4),      # bottom-left
            (0.1, 0.45, 0.0, 0.4),      # top-left
            (0.85, 1.0, 0.15, 0.85),    # bottom
        ]

        on_segments = []

        for y1_r, y2_r, x1_r, x2_r in segments_map:
            y1, y2 = int(h * y1_r), int(h * y2_r)
            x1, x2 = int(w * x1_r), int(w * x2_r)

            if y2 <= y1 or x2 <= x1:
                on_segments.append(0)
                continue

            segment_roi = digit_roi[y1:y2, x1:x2]

            if segment_roi.size == 0:
                on_segments.append(0)
                continue

            # ON if >20% pixels are white (lowered threshold for robustness)
            on_ratio = np.count_nonzero(segment_roi) / float(segment_roi.size)
            on_segments.append(1 if on_ratio > 0.20 else 0)

        segments_tuple = tuple(on_segments)

        # Find best match
        best_digit = '8'
        best_score = 0

        for pattern, digit in SEGMENTS.items():
            matches = sum(1 for i in range(7) if pattern[i] == segments_tuple[i])
            score = matches / 7.0

            if score > best_score:
                best_score = score
                best_digit = digit

        confidence = best_score * 100
        return best_digit, confidence


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_ssocr_fixed.py <image_path>")
        sys.exit(1)

    ocr = SSOcrFixed()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print("\n" + "="*70)
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print("✗ Failed to extract reading")
    print("="*70)
