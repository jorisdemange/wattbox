#!/usr/bin/env python3
"""
Python implementation of ssocr-style seven-segment digit recognition.
Based on https://pyimagesearch.com/2017/02/13/recognizing-digits-with-opencv-and-python/
and ssocr logic: robust segment detection without ML.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

# Seven-segment lookup table
SEGMENTS = {
    (1, 1, 1, 0, 1, 1, 1): '0',
    (0, 0, 1, 0, 0, 1, 0): '1',
    (1, 0, 1, 1, 1, 0, 1): '2',
    (1, 0, 1, 1, 0, 1, 1): '3',
    (0, 1, 1, 1, 0, 1, 0): '4',
    (1, 1, 0, 1, 0, 1, 1): '5',
    (1, 1, 0, 1, 1, 1, 1): '6',
    (1, 0, 1, 0, 0, 1, 0): '7',
    (1, 1, 1, 1, 1, 1, 1): '8',
    (1, 1, 1, 1, 0, 1, 1): '9',
}


class SSOcrPython:
    """Seven-segment OCR using ssocr-style segment detection"""

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract meter reading from image"""
        try:
            # Aggressive preprocessing for robust binarization
            binary = self._preprocess_aggressive(image_path)

            # Find digit contours
            digit_rois = self._find_digits(binary)

            if len(digit_rois) < 7:  # Need at least 7 digits for reading
                logger.warning(f"Only found {len(digit_rois)} digits, need 7-8")
                return None, 0.0

            # Take first 8 digits (or pad if less than 8)
            digit_rois = digit_rois[:8]

            digits = []
            confidences = []

            for i, (digit_roi, x) in enumerate(digit_rois):
                digit_char, conf = self._recognize_segment_digit(digit_roi)
                digits.append(digit_char)
                confidences.append(conf)
                logger.info(f"Digit {i} at x={x}: {digit_char} ({conf:.1f}%)")

            # Pad with zeros if we have less than 8 digits
            while len(digits) < 8:
                digits.insert(0, '0')
                confidences.insert(0, 50.0)

            result_str = ''.join(digits[:8])
            logger.info(f"Recognized: {result_str}")

            reading = float(result_str[:7] + '.' + result_str[7])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return reading, avg_conf

        except Exception as e:
            logger.error(f"SSOcr failed: {e}", exc_info=True)
            return None, 0.0

    def _preprocess_aggressive(self, image_path: str) -> np.ndarray:
        """
        Aggressive preprocessing for robust binarization across lighting conditions.
        Following ssocr best practices.
        """
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

        # 1. Strong denoising
        denoised = cv2.fastNlMeansDenoising(gray, None, h=20, templateWindowSize=7, searchWindowSize=21)

        # 2. CLAHE for extreme contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)

        # 3. Morphological gradient to enhance edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gradient = cv2.morphologyEx(enhanced, cv2.MORPH_GRADIENT, kernel)
        enhanced = cv2.add(enhanced, gradient)

        # 4. Otsu's thresholding (automatically finds best threshold)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 5. Morphological close to connect broken segments
        kernel_close = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close, iterations=2)

        # 6. Remove small noise
        kernel_open = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)

        return binary

    def _find_digits(self, binary: np.ndarray) -> List[Tuple[np.ndarray, int]]:
        """Find digit contours and extract ROIs"""
        contours, _ = cv2.findContours(binary.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height, width = binary.shape
        digit_rois = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Seven-segment digits have specific aspect ratio and size
            aspect_ratio = h / float(w) if w > 0 else 0

            # Filter by size and aspect ratio
            # LCD digits are taller than wide (typically 2-3:1)
            if (1.5 < aspect_ratio < 4.5 and
                w >= width * 0.03 and w <= width * 0.15 and
                h >= height * 0.25 and h <= height * 0.95):

                # Extract ROI with padding
                padding = 5
                x1 = max(0, x - padding)
                y1 = max(0, y - padding)
                x2 = min(width, x + w + padding)
                y2 = min(height, y + h + padding)

                digit_roi = binary[y1:y2, x1:x2]
                digit_rois.append((digit_roi, x))

        # Sort by x-coordinate (left to right)
        digit_rois.sort(key=lambda item: item[1])

        return digit_rois

    def _recognize_segment_digit(self, digit_roi: np.ndarray) -> Tuple[str, float]:
        """
        Recognize digit by analyzing seven segments.
        Segments: (top, top-right, bottom-right, middle, bottom-left, top-left, bottom)
        """
        h, w = digit_roi.shape

        # Define the seven segment regions as percentage of bounding box
        # Format: (y_start, y_end, x_start, x_end) as ratios
        segments_map = [
            ('top', 0.0, 0.15, 0.15, 0.85),           # Top horizontal
            ('top_right', 0.1, 0.45, 0.6, 1.0),       # Top right vertical
            ('bottom_right', 0.55, 0.9, 0.6, 1.0),    # Bottom right vertical
            ('middle', 0.45, 0.55, 0.15, 0.85),       # Middle horizontal
            ('bottom_left', 0.55, 0.9, 0.0, 0.4),     # Bottom left vertical
            ('top_left', 0.1, 0.45, 0.0, 0.4),        # Top left vertical
            ('bottom', 0.85, 1.0, 0.15, 0.85),        # Bottom horizontal
        ]

        # Detect which segments are ON
        on_segments = []

        for seg_name, y1_ratio, y2_ratio, x1_ratio, x2_ratio in segments_map:
            y1 = int(h * y1_ratio)
            y2 = int(h * y2_ratio)
            x1 = int(w * x1_ratio)
            x2 = int(w * x2_ratio)

            # Ensure valid region
            if y2 <= y1 or x2 <= x1:
                on_segments.append(0)
                continue

            segment_roi = digit_roi[y1:y2, x1:x2]

            if segment_roi.size == 0:
                on_segments.append(0)
                continue

            # Calculate percentage of "ON" pixels (white pixels)
            total_pixels = segment_roi.size
            on_pixels = np.count_nonzero(segment_roi)
            on_ratio = on_pixels / float(total_pixels)

            # Threshold: segment is ON if >25% of pixels are white
            on_segments.append(1 if on_ratio > 0.25 else 0)

        # Convert to tuple for lookup
        segments_tuple = tuple(on_segments)

        # Find best match in segments table
        best_digit = None
        best_score = 0

        for pattern, digit in SEGMENTS.items():
            # Calculate Hamming distance (how many segments match)
            matches = sum(1 for i in range(7) if pattern[i] == segments_tuple[i])
            score = matches / 7.0

            if score > best_score:
                best_score = score
                best_digit = digit

        # If no good match, default to '8' (most segments)
        if best_digit is None or best_score < 0.4:
            best_digit = '8'
            best_score = 0.4

        confidence = best_score * 100

        return best_digit, confidence


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_ssocr.py <image_path>")
        sys.exit(1)

    ocr = SSOcrPython()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print("\n" + "="*70)
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print("✗ Failed to extract reading")
    print("="*70)
