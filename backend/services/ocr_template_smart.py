"""
Smart Template OCR - Tries multiple detection regions and picks best result
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from PIL import Image
import logging

try:
    from services.ocr_template import TemplateOCR
except ImportError:
    from ocr_template import TemplateOCR

logger = logging.getLogger(__name__)


class SmartTemplateOCR:
    """Smart template OCR that tries multiple regions"""

    def __init__(self, tesseract_path: Optional[str] = None):
        self.base_ocr = TemplateOCR(tesseract_path)

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Try multiple detection regions and return the best result based on confidence
        """
        # Load image
        img = Image.open(image_path)
        if img.format == 'MPO':
            img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img_cv = np.array(img)
        img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
        height, width = img_cv.shape[:2]

        # Check if already cropped
        aspect_ratio = width / height if height > 0 else 0
        if 2.5 < aspect_ratio < 8:
            # Already cropped, use directly
            return self.base_ocr.extract_reading(image_path)

        # Generate multiple candidate regions to test
        regions = self._generate_candidate_regions(img_cv)

        logger.info(f"Testing {len(regions)} candidate regions")

        best_reading = None
        best_confidence = 0.0
        best_region_desc = None

        for region_desc, region_img in regions:
            # Save region temporarily
            temp_path = f'/tmp/region_{region_desc}.png'
            cv2.imwrite(temp_path, region_img)

            # Try OCR on this region
            reading, confidence = self.base_ocr.extract_reading(temp_path)

            logger.info(f"Region {region_desc}: reading={reading}, confidence={confidence:.1f}%")

            if confidence > best_confidence:
                best_reading = reading
                best_confidence = confidence
                best_region_desc = region_desc

        if best_reading is not None:
            logger.info(f"Best result from region {best_region_desc}: {best_reading} kWh ({best_confidence:.1f}%)")

        return best_reading, best_confidence

    def _generate_candidate_regions(self, img_cv: np.ndarray) -> list:
        """
        Generate multiple candidate regions covering different parts of the image
        """
        height, width = img_cv.shape[:2]
        regions = []

        # Strategy 1: Grid of regions (3x3 covering the image)
        for row in range(3):
            for col in range(3):
                y1 = int(height * (row * 0.33))
                y2 = int(height * min(1.0, (row + 1) * 0.33 + 0.15))  # Overlap
                x1 = int(width * (col * 0.33))
                x2 = int(width * min(1.0, (col + 1) * 0.33 + 0.15))  # Overlap

                region = img_cv[y1:y2, x1:x2]
                regions.append((f"grid_r{row}_c{col}", region))

        # Strategy 2: Common locations based on analysis
        # These are real locations found in the example photos
        common_locations = [
            # From template matching analysis (IMG_7751)
            ("known_location_1", 0.704, 0.891, 0.892, 0.983),
            # From contour detection analysis
            ("known_location_2", 0.950, 1.000, 0.026, 0.038),
            ("known_location_3", 0.943, 1.000, 0.130, 0.144),
            ("known_location_4", 0.247, 0.309, 0.015, 0.027),
            ("known_location_5", 0.889, 0.965, 0.000, 0.014),
            # Grid-based common areas
            ("top_right", 0.70, 0.95, 0.00, 0.15),
            ("center_right", 0.70, 0.95, 0.30, 0.50),
            ("bottom_right", 0.65, 0.99, 0.80, 0.99),
            ("center_left", 0.20, 0.40, 0.30, 0.50),
            ("top_left", 0.10, 0.35, 0.00, 0.15),
        ]

        for name, x1_pct, x2_pct, y1_pct, y2_pct in common_locations:
            x1 = int(width * x1_pct)
            x2 = int(width * x2_pct)
            y1 = int(height * y1_pct)
            y2 = int(height * y2_pct)

            region = img_cv[y1:y2, x1:x2]
            regions.append((name, region))

        # Strategy 3: Contour detection candidates
        try:
            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 11, 2)
            kernel_h = np.ones((3, 15), np.uint8)
            dilated = cv2.dilate(binary, kernel_h, iterations=2)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            candidates = []
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                width_ratio = w / width
                height_ratio = h / height

                if (2.5 < aspect_ratio < 8 and
                    0.04 < width_ratio < 0.40 and
                    0.01 < height_ratio < 0.15):
                    candidates.append({
                        'box': (x, y, w, h),
                        'score': aspect_ratio * width_ratio
                    })

            candidates.sort(key=lambda c: c['score'], reverse=True)

            for i, cand in enumerate(candidates[:5]):  # Top 5 contour candidates
                x, y, w, h = cand['box']
                region = img_cv[y:y+h, x:x+w]
                regions.append((f"contour_{i+1}", region))

        except Exception as e:
            logger.debug(f"Contour detection failed: {e}")

        logger.info(f"Generated {len(regions)} candidate regions")
        return regions


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python ocr_template_smart.py <image_path>")
        sys.exit(1)

    ocr = SmartTemplateOCR()
    reading, confidence = ocr.extract_reading(sys.argv[1])

    print(f"\n{'='*70}")
    if reading:
        print(f"✓ Result: {reading} kWh (confidence: {confidence:.1f}%)")
    else:
        print(f"✗ Failed to extract reading")
    print(f"{'='*70}")
