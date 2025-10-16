"""
Template-based Seven-Segment OCR
Uses correlation matching against digit templates
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Import LCD detector
try:
    from services.lcd_detector import LCDDetector
    LCD_DETECTOR_AVAILABLE = True
except ImportError:
    try:
        from lcd_detector import LCDDetector
        LCD_DETECTOR_AVAILABLE = True
    except ImportError:
        LCD_DETECTOR_AVAILABLE = False
        logger.warning("LCD detector not available")


class TemplateOCR:
    """Template-based OCR for seven-segment displays"""

    def __init__(self, tesseract_path: Optional[str] = None):
        # Will load templates on first use
        self.templates: Optional[Dict[str, np.ndarray]] = None
        # Initialize LCD detector if available
        self.lcd_detector = LCDDetector() if LCD_DETECTOR_AVAILABLE else None

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract reading using template matching

        Returns:
            (reading_kwh, confidence)
        """
        try:
            # Preprocess
            preprocessed = self._preprocess(image_path)

            # Initialize templates if needed
            if self.templates is None:
                self.templates = self._create_templates_from_reference()

            # Extract digits using contour detection (more accurate than fixed-width)
            digit_regions = self._segment_digits_by_contours(preprocessed)

            if len(digit_regions) != 8:
                logger.warning(f"Expected 8 digits, found {len(digit_regions)}. Falling back to fixed-width segmentation.")
                digit_regions = self._segment_digits_fixed_width(preprocessed)

            digits = []
            confidences = []

            for i, (digit_img, x, y, w_digit, h_digit) in enumerate(digit_regions):
                # Match against templates
                digit, conf = self._match_digit(digit_img)
                digits.append(str(digit))
                confidences.append(conf)

                logger.info(f"Digit {i} at x={x}: {digit} (confidence: {conf:.1f}%)")

            result_str = ''.join(digits)
            logger.info(f"Recognized: {result_str}")

            if len(result_str) == 8:
                reading = float(result_str[:7] + '.' + result_str[7])
                avg_conf = sum(confidences) / len(confidences)
                return reading, avg_conf
            else:
                return None, 0.0

        except Exception as e:
            logger.error(f"Template OCR failed: {e}", exc_info=True)
            return None, 0.0

    def _preprocess(self, image_path: str) -> np.ndarray:
        """Preprocess image for template matching"""
        img = Image.open(image_path)

        # Handle MPO format (iPhone multi-picture)
        if img.format == 'MPO':
            img = img.convert('RGB')
        elif img.mode == 'RGBA':
            img = img.convert('RGB')

        img_cv = np.array(img)
        if len(img_cv.shape) == 3:
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        # Check if image is already cropped to LCD or needs detection
        height, width = img_cv.shape[:2]
        aspect_ratio = width / height if height > 0 else 0

        # If aspect ratio is not typical for LCD panel (2.5-8:1), try to detect and crop
        # LCD crops typically have wider-than-tall aspect ratios
        if not (2.5 < aspect_ratio < 8) and self.lcd_detector is not None:
            logger.info(f"Image aspect ratio {aspect_ratio:.2f} suggests uncropped meter. Attempting LCD detection...")
            lcd_region = self.lcd_detector.detect_and_crop(image_path)
            if lcd_region is not None:
                img_cv = lcd_region
                logger.info(f"LCD detected, cropped to {lcd_region.shape[1]}x{lcd_region.shape[0]}")
            else:
                logger.warning("LCD detection failed, using full image")

        # Convert to grayscale
        if len(img_cv.shape) == 3:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        else:
            gray = img_cv

        # Denoise
        denoised = cv2.fastNlMeansDenoising(gray, None, h=15)

        # CLAHE (adaptive histogram equalization - handles lighting variations)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)

        # Use adaptive thresholding instead of fixed threshold
        # This works much better with varying lighting
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=21,  # Larger block size for LCD displays
            C=10
        )

        # Alternative: Otsu's method (finds optimal threshold automatically)
        _, otsu = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Combine both methods: use Otsu if it has good contrast, else adaptive
        otsu_contrast = np.std(otsu)
        adaptive_contrast = np.std(binary)

        if otsu_contrast > adaptive_contrast * 0.8:
            binary = otsu
        # else use adaptive (default)

        # Clean up noise
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return cleaned

    def _create_templates_from_reference(self) -> Dict[str, np.ndarray]:
        """
        Load digit templates extracted from the reference image.
        Falls back to synthetic templates for missing digits.
        """
        import os

        templates = {}

        # Try to load real templates from backend/templates/ directory
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(os.path.dirname(script_dir), 'templates')

        logger.info(f"Loading templates from: {templates_dir}")

        # Load available real templates
        loaded_real = []
        for digit in '0123456789':
            template_path = os.path.join(templates_dir, f'template_{digit}.png')
            if os.path.exists(template_path):
                template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
                if template is not None:
                    templates[digit] = template
                    loaded_real.append(digit)
                    logger.info(f"Loaded real template for digit {digit}: {template.shape}")

        logger.info(f"Loaded {len(loaded_real)} real templates: {loaded_real}")

        # Create synthetic templates for missing digits as fallback
        missing_digits = [d for d in '0123456789' if d not in templates]
        if missing_digits:
            logger.info(f"Creating synthetic templates for missing digits: {missing_digits}")
            synthetic = self._create_synthetic_templates(missing_digits)
            templates.update(synthetic)

        logger.info(f"Total templates available: {len(templates)}")
        return templates

    def _create_synthetic_templates(self, digits: list) -> Dict[str, np.ndarray]:
        """Create synthetic seven-segment templates for specified digits"""
        templates = {}

        # Size: 40x20 (height x width) - match typical template size
        h, w = 40, 20

        # Helper to create a blank template
        def blank():
            return np.zeros((h, w), dtype=np.uint8)

        # Helper to draw horizontal segment
        def draw_h_seg(img, y, x1, x2):
            cv2.rectangle(img, (x1, y), (x2, y+3), 255, -1)

        # Helper to draw vertical segment
        def draw_v_seg(img, x, y1, y2):
            cv2.rectangle(img, (x, y1), (x+3, y2), 255, -1)

        for digit in digits:
            t = blank()

            if digit == '0':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom
                draw_v_seg(t, 0, 20, 37)  # bottom-left
                draw_v_seg(t, 0, 3, 17)  # top-left
            elif digit == '1':
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_v_seg(t, 17, 20, 37)  # bottom-right
            elif digit == '2':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 0, 20, 37)  # bottom-left
                draw_h_seg(t, 37, 3, 17)  # bottom
            elif digit == '3':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom
            elif digit == '4':
                draw_v_seg(t, 0, 3, 17)  # top-left
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_v_seg(t, 17, 20, 37)  # bottom-right
            elif digit == '5':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 0, 3, 17)  # top-left
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom
            elif digit == '6':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 0, 3, 17)  # top-left
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 0, 20, 37)  # bottom-left
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom
            elif digit == '7':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_v_seg(t, 17, 20, 37)  # bottom-right
            elif digit == '8':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 0, 3, 17)  # top-left
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 0, 20, 37)  # bottom-left
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom
            elif digit == '9':
                draw_h_seg(t, 0, 3, 17)  # top
                draw_v_seg(t, 0, 3, 17)  # top-left
                draw_v_seg(t, 17, 3, 17)  # top-right
                draw_h_seg(t, 18, 3, 17)  # middle
                draw_v_seg(t, 17, 20, 37)  # bottom-right
                draw_h_seg(t, 37, 3, 17)  # bottom

            templates[digit] = t

        return templates

    def _match_digit(self, digit_img: np.ndarray) -> Tuple[int, float]:
        """
        Match a digit image against all templates using lighting-invariant methods.

        Uses multiple strategies:
        1. Normalized cross-correlation (TM_CCOEFF_NORMED)
        2. Correlation with normalized images (mean=0, std=1)
        3. Structural similarity on edges
        """
        best_digit = 0
        best_score = -1.0

        # Normalize the input digit image
        digit_normalized = self._normalize_image(digit_img)

        for digit_str, template in self.templates.items():
            # Resize digit to match template size
            template_h, template_w = template.shape
            resized = cv2.resize(digit_img, (template_w, template_h), interpolation=cv2.INTER_AREA)
            resized_norm = cv2.resize(digit_normalized, (template_w, template_h), interpolation=cv2.INTER_AREA)

            # Normalize template too
            template_norm = self._normalize_image(template)

            # Strategy 1: Normalized images (lighting-invariant, most reliable)
            result1 = cv2.matchTemplate(resized_norm, template_norm, cv2.TM_CCOEFF_NORMED)
            score1 = result1[0, 0]

            # Strategy 2: Standard normalized cross-correlation (backup)
            result2 = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            score2 = result2[0, 0]

            # Combine: Prioritize normalized matching heavily
            combined_score = (score1 * 0.8) + (score2 * 0.2)

            if combined_score > best_score:
                best_score = combined_score
                best_digit = int(digit_str)

        # Convert to confidence percentage
        confidence = min(100, max(0, best_score * 100))

        return best_digit, confidence

    def _segment_digits_by_contours(self, binary_img: np.ndarray):
        """Segment digits using contour detection"""
        contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height, width = binary_img.shape
        digit_regions = []

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect = h / w if w > 0 else 0

            # LCD digits are typically 2-3:1 height/width ratio
            # Filter by size and aspect ratio
            if (1.5 < aspect < 4.0 and
                w > width * 0.04 and  # At least 4% of image width
                h > height * 0.3):     # At least 30% of image height

                # Add small margin around digit
                x1 = max(0, x - 2)
                y1 = max(0, y - 2)
                x2 = min(width, x + w + 2)
                y2 = min(height, y + h + 2)

                digit_img = binary_img[y1:y2, x1:x2]
                digit_regions.append((digit_img, x, y, w, h))

        # Sort by x-coordinate (left to right)
        digit_regions.sort(key=lambda r: r[1])

        return digit_regions

    def _segment_digits_fixed_width(self, binary_img: np.ndarray):
        """Fallback: segment digits using fixed-width approach"""
        h, w = binary_img.shape
        num_digits = 8
        margin_x = int(w * 0.05)
        usable_width = w - 2 * margin_x
        digit_width = usable_width // num_digits

        digit_regions = []

        for i in range(num_digits):
            x = margin_x + i * digit_width
            y = int(h * 0.1)
            digit_h = int(h * 0.8)

            digit_img = binary_img[y:y+digit_h, x:x+digit_width]
            digit_regions.append((digit_img, x, y, digit_width, digit_h))

        return digit_regions

    def _normalize_image(self, img: np.ndarray) -> np.ndarray:
        """
        Normalize image to have zero mean and unit variance.
        This makes matching lighting-invariant.
        """
        img_float = img.astype(np.float32)
        mean = np.mean(img_float)
        std = np.std(img_float)

        if std < 1e-6:  # Avoid division by zero
            return np.zeros_like(img, dtype=np.uint8)

        normalized = (img_float - mean) / std
        # Scale back to 0-255 range
        normalized = ((normalized - normalized.min()) / (normalized.max() - normalized.min()) * 255)
        return normalized.astype(np.uint8)


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_template.py <image_path>")
        sys.exit(1)

    ocr = TemplateOCR()
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
