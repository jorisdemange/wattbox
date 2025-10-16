#!/usr/bin/env python3
"""
Multi-template OCR with integrated LCD detection.
Works on both cropped LCD images and full meter photos.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Dict, List
import logging
import os
import glob
import tempfile

logger = logging.getLogger(__name__)


class MultiTemplateOCRFull:
    """OCR using multiple templates per digit with LCD detection for full images"""

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
        """Extract reading from either cropped LCD or full meter image"""
        try:
            # First try to detect if this is a full image or already cropped
            img = Image.open(image_path)
            if img.format == 'MPO':
                img = img.convert('RGB')
            elif img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')

            img_cv = np.array(img)
            if len(img_cv.shape) == 3:
                img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

            height, width = img_cv.shape[:2]
            aspect_ratio = width / height if height > 0 else 0

            # If aspect ratio suggests this is already a cropped LCD (wide strip ~4-8:1),
            # process directly
            if 3.5 < aspect_ratio < 9:
                logger.info("Image appears to be pre-cropped LCD, processing directly")
                return self._extract_from_lcd(image_path)
            else:
                # Full meter image, need LCD detection
                logger.info("Image appears to be full meter photo, detecting LCD region")
                lcd_region = self._detect_lcd(img_cv)

                if lcd_region is None:
                    logger.warning("LCD detection failed")
                    return None, 0.0

                # Save LCD region to temp file and process
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name
                    cv2.imwrite(tmp_path, lcd_region)

                try:
                    result = self._extract_from_lcd(tmp_path)
                    return result
                finally:
                    # Clean up temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        except Exception as e:
            logger.error(f"Multi-template OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _detect_lcd(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Detect LCD region in full meter image"""
        # Try template matching first (most robust across different orientations/zoom)
        lcd_region = self._detect_by_template_matching(img)
        if lcd_region is not None:
            logger.info("LCD detected using template matching")
            return lcd_region

        # Fallback to contour detection
        lcd_region = self._detect_by_contours(img)
        if lcd_region is not None:
            logger.info("LCD detected using contour method")
            return lcd_region

        # Last resort: heuristic (only works for specific orientation/zoom)
        lcd_region = self._heuristic_crop(img)
        if lcd_region is not None:
            logger.info("LCD detected using heuristic crop (fallback)")
            return lcd_region

        return None

    def _detect_by_template_matching(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect LCD using template matching against a known cropped LCD image.
        This works across different zoom levels and orientations.
        """
        try:
            # Load one of the cropped LCD templates as reference
            # Path: /Users/joris/dev/wattbox/data/examples_cropped/IMG_7751.jpeg
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(script_dir))
            template_path = os.path.join(project_root, 'data', 'examples_cropped', 'IMG_7751.jpeg')

            if not os.path.exists(template_path):
                logger.debug(f"Template file not found: {template_path}")
                return None

            template_img = Image.open(template_path)
            if template_img.format == 'MPO':
                template_img = template_img.convert('RGB')
            template_cv = np.array(template_img)
            template_cv = cv2.cvtColor(template_cv, cv2.COLOR_RGB2BGR)
            template_gray = cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)

            # Convert full image to grayscale
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Try multiple scales since LCD might be at different zoom levels
            best_match = None
            best_score = 0.3  # Minimum threshold

            for scale in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.4]:
                # Resize template
                new_w = int(template_gray.shape[1] * scale)
                new_h = int(template_gray.shape[0] * scale)

                # Skip if template would be larger than image
                if new_w > img_gray.shape[1] or new_h > img_gray.shape[0]:
                    continue

                scaled_template = cv2.resize(template_gray, (new_w, new_h))

                # Template matching
                result = cv2.matchTemplate(img_gray, scaled_template, cv2.TM_CCOEFF_NORMED)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                if max_val > best_score:
                    best_score = max_val
                    best_match = {
                        'score': max_val,
                        'location': max_loc,
                        'size': (new_w, new_h),
                        'scale': scale
                    }

            if best_match:
                x, y = best_match['location']
                w, h = best_match['size']

                # Add small margin
                height, width = img.shape[:2]
                margin_x = int(w * 0.02)
                margin_y = int(h * 0.05)
                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(width, x + w + margin_x)
                y2 = min(height, y + h + margin_y)

                lcd_region = img[y1:y2, x1:x2]
                logger.info(f"Template matching: score={best_match['score']:.3f}, "
                           f"scale={best_match['scale']:.1f}, box=({x1},{y1},{x2},{y2})")
                return lcd_region

            logger.debug("Template matching failed to find good match")
            return None

        except Exception as e:
            logger.debug(f"Template matching detection failed: {e}")
            return None

    def _heuristic_crop(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Heuristic crop based on typical Iskra meter layout"""
        try:
            height, width = img.shape[:2]

            # Based on template matching from IMG_7751.jpeg (4032x3024):
            # LCD found at x: 34.5% to 53.9%, y: 90.1% to 99.4%
            x1 = int(width * 0.345)
            x2 = int(width * 0.539)
            y1 = int(height * 0.901)
            y2 = int(height * 0.994)

            lcd_region = img[y1:y2, x1:x2]
            logger.info(f"Heuristic crop: ({x1}, {y1}, {x2}, {y2})")
            return lcd_region

        except Exception as e:
            logger.debug(f"Heuristic crop failed: {e}")
            return None

    def _detect_by_contours(self, img: np.ndarray) -> Optional[np.ndarray]:
        """Detect LCD by finding rectangular contours"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 11, 2)

            kernel_h = np.ones((3, 15), np.uint8)
            dilated = cv2.dilate(binary, kernel_h, iterations=2)

            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            height, width = img.shape[:2]
            candidates = []

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                width_ratio = w / width
                height_ratio = h / height

                if (4 < aspect_ratio < 12 and
                    0.04 < width_ratio < 0.30 and
                    0.01 < height_ratio < 0.10):

                    candidates.append({
                        'box': (x, y, w, h),
                        'score': aspect_ratio * width_ratio
                    })

            if candidates:
                candidates.sort(key=lambda c: c['score'], reverse=True)
                x, y, w, h = candidates[0]['box']

                margin_x = int(w * 0.02)
                margin_y = int(h * 0.15)
                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(width, x + w + margin_x)
                y2 = min(height, y + h + margin_y)

                lcd_region = img[y1:y2, x1:x2]
                logger.info(f"Contour detection found LCD at ({x1}, {y1}, {x2}, {y2})")
                return lcd_region

            return None

        except Exception as e:
            logger.debug(f"Contour detection failed: {e}")
            return None

    def _extract_from_lcd(self, image_path: str) -> Tuple[Optional[float], float]:
        """Extract reading from cropped LCD image"""
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
        print("Usage: python ocr_multi_template_full.py <image_path>")
        sys.exit(1)

    ocr = MultiTemplateOCRFull()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print("\n" + "="*70)
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print("✗ Failed to extract reading")
    print("="*70)
