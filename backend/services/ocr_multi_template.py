#!/usr/bin/env python3
"""
Multi-template OCR: Match against ALL extracted templates from all images.
This handles lighting variations because we have templates from all lighting conditions.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Dict, List
import logging
import os
import glob

logger = logging.getLogger(__name__)


class MultiTemplateOCR:
    """OCR using multiple templates per digit from different images"""

    def __init__(self):
        self.templates = self._load_all_templates()

    def _load_all_templates(self) -> Dict[str, List[np.ndarray]]:
        """Load all templates, grouped by digit"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(os.path.dirname(script_dir), 'templates_multi')

        templates = {str(i): [] for i in range(10)}

        for digit in range(10):
            pattern = os.path.join(templates_dir, f'template_{digit}_*.png')
            template_files = sorted(glob.glob(pattern))

            for tpl_file in template_files:
                tpl = cv2.imread(tpl_file, cv2.IMREAD_GRAYSCALE)
                if tpl is not None:
                    templates[str(digit)].append(tpl)

        total = sum(len(v) for v in templates.values())
        logger.info(f"Loaded {total} templates across all digits")
        for digit, tpls in templates.items():
            logger.info(f"  Digit {digit}: {len(tpls)} templates")

        return templates

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract reading using multi-template matching"""
        try:
            binary = self._preprocess(image_path)

            # Fixed-width segmentation
            h, w = binary.shape
            margin_x = int(w * 0.05)
            digit_width = (w - 2 * margin_x) // 8

            digits = []
            confidences = []

            for i in range(8):
                x = margin_x + i * digit_width
                y = int(h * 0.1)
                digit_h = int(h * 0.8)

                digit_roi = binary[y:y+digit_h, x:x+digit_width]

                # Match against ALL templates
                digit_char, conf = self._match_multi_template(digit_roi)
                digits.append(digit_char)
                confidences.append(conf)
                logger.info(f"Digit {i}: {digit_char} ({conf:.1f}%)")

            result_str = ''.join(digits)
            logger.info(f"Recognized: {result_str}")

            reading = float(result_str[:7] + '.' + result_str[7])
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return reading, avg_conf

        except Exception as e:
            logger.error(f"Multi-template OCR failed: {e}", exc_info=True)
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

        denoised = cv2.fastNlMeansDenoising(gray, None, h=15)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

        return cleaned

    def _match_multi_template(self, digit_roi: np.ndarray) -> Tuple[str, float]:
        """Match digit against ALL templates for all digits, return best"""
        best_digit = '0'
        best_score = -1.0

        for digit_str, template_list in self.templates.items():
            for template in template_list:
                # Resize digit to match template size
                template_h, template_w = template.shape
                resized = cv2.resize(digit_roi, (template_w, template_h), interpolation=cv2.INTER_AREA)

                # Normalized cross-correlation
                result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
                score = result[0, 0]

                if score > best_score:
                    best_score = score
                    best_digit = digit_str

        confidence = min(100, max(0, best_score * 100))
        return best_digit, confidence


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_multi_template.py <image_path>")
        sys.exit(1)

    ocr = MultiTemplateOCR()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print("\n" + "="*70)
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print("✗ Failed to extract reading")
    print("="*70)
