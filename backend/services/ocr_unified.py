#!/usr/bin/env python3
"""
Unified OCR system with multiple detection and recognition strategies
Uses the best available method automatically
"""

import os
import sys
import logging
from pathlib import Path
from typing import Tuple, Optional
import cv2
import numpy as np
from PIL import Image

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)

# Import our OCR implementations
try:
    from services.ocr_template import TemplateOCR
    from services.lcd_detector import LCDDetector
except ImportError:
    from ocr_template import TemplateOCR
    from lcd_detector import LCDDetector


class UnifiedOCR:
    """
    Unified OCR with multiple strategies:
    1. If image is pre-cropped LCD -> Direct template OCR
    2. If full meter image -> Detect LCD region -> Template OCR
    3. Multiple detection methods with confidence scoring
    """

    def __init__(self):
        self.template_ocr = TemplateOCR()
        self.lcd_detector = LCDDetector()

    def extract_reading(self, image_path: str) -> dict:
        """
        Extract reading with automatic strategy selection

        Returns dict with:
          - reading_kwh: float or None
          - confidence: float (0-100)
          - strategy: str describing method used
          - crop_path: path to detected/used crop (if any)
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
        aspect_ratio = width / height

        # Strategy 1: Already cropped LCD
        if 2.5 < aspect_ratio < 8 and width < 2000:
            logger.info("Image appears pre-cropped, using direct template OCR")
            reading, conf = self.template_ocr.extract_reading(image_path)
            return {
                'reading_kwh': reading,
                'confidence': conf,
                'strategy': 'direct_template',
                'crop_path': None
            }

        # Strategy 2: Full image - try multiple detection methods
        logger.info("Full meter image detected, trying multi-strategy detection...")

        candidates = []

        # Method A: Contour-based detection
        try:
            contour_crop = self._detect_contour_based(img_cv)
            if contour_crop is not None:
                temp_path = '/tmp/contour_crop.jpg'
                cv2.imwrite(temp_path, contour_crop)
                reading, conf = self.template_ocr.extract_reading(temp_path)
                if reading is not None and conf > 0:
                    candidates.append({
                        'reading_kwh': reading,
                        'confidence': conf * 0.8,  # Slightly penalize contour detection
                        'strategy': 'contour_detection',
                        'crop_path': temp_path
                    })
                    logger.info(f"Contour detection: {reading} kWh ({conf:.1f}%)")
        except Exception as e:
            logger.warning(f"Contour detection failed: {e}")

        # Method B: Grid search
        try:
            grid_results = self._detect_grid_search(img_cv)
            for i, (crop, region_name) in enumerate(grid_results[:5]):
                temp_path = f'/tmp/grid_crop_{i}.jpg'
                cv2.imwrite(temp_path, crop)
                reading, conf = self.template_ocr.extract_reading(temp_path)
                if reading is not None and conf > 0:
                    candidates.append({
                        'reading_kwh': reading,
                        'confidence': conf * 0.7,  # Penalize grid search more
                        'strategy': f'grid_search_{region_name}',
                        'crop_path': temp_path
                    })
                    logger.info(f"Grid {region_name}: {reading} kWh ({conf:.1f}%)")
        except Exception as e:
            logger.warning(f"Grid search failed: {e}")

        # Method C: Known heuristic locations
        try:
            heuristic_crops = self._detect_heuristic(img_cv)
            for i, (crop, loc_name) in enumerate(heuristic_crops):
                temp_path = f'/tmp/heuristic_crop_{i}.jpg'
                cv2.imwrite(temp_path, crop)
                reading, conf = self.template_ocr.extract_reading(temp_path)
                if reading is not None and conf > 0:
                    candidates.append({
                        'reading_kwh': reading,
                        'confidence': conf * 0.9,  # Heuristics are pretty good
                        'strategy': f'heuristic_{loc_name}',
                        'crop_path': temp_path
                    })
                    logger.info(f"Heuristic {loc_name}: {reading} kWh ({conf:.1f}%)")
        except Exception as e:
            logger.warning(f"Heuristic detection failed: {e}")

        # Pick best candidate
        if candidates:
            best = max(candidates, key=lambda x: x['confidence'])
            logger.info(f"✓ Best result: {best['reading_kwh']} kWh ({best['confidence']:.1f}%) via {best['strategy']}")
            return best

        # No candidates found
        logger.warning("✗ No valid LCD regions detected")
        return {
            'reading_kwh': None,
            'confidence': 0.0,
            'strategy': 'failed',
            'crop_path': None
        }

    def _detect_contour_based(self, img_cv: np.ndarray) -> Optional[np.ndarray]:
        """Contour-based LCD detection"""
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 11, 2)
        kernel_h = np.ones((3, 15), np.uint8)
        dilated = cv2.dilate(binary, kernel_h, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height, width = img_cv.shape[:2]
        best_candidate = None
        best_score = 0

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            width_ratio = w / width
            height_ratio = h / height

            if (2.5 < aspect_ratio < 8 and
                0.04 < width_ratio < 0.40 and
                0.01 < height_ratio < 0.15):

                score = aspect_ratio * width_ratio
                if score > best_score:
                    best_score = score
                    # Add margin
                    x1 = max(0, x - 10)
                    y1 = max(0, y - 10)
                    x2 = min(width, x + w + 10)
                    y2 = min(height, y + h + 10)
                    best_candidate = img_cv[y1:y2, x1:x2]

        return best_candidate

    def _detect_grid_search(self, img_cv: np.ndarray) -> list:
        """Grid-based search for LCD"""
        height, width = img_cv.shape[:2]
        results = []

        # Search grid positions
        positions = [
            ('bottom_right', 0.7, 0.9, 0.85, 1.0),
            ('center_right', 0.6, 0.8, 0.4, 0.6),
            ('top_right', 0.7, 0.9, 0.0, 0.15),
            ('center', 0.3, 0.7, 0.3, 0.5),
        ]

        for name, x1_ratio, x2_ratio, y1_ratio, y2_ratio in positions:
            x1 = int(width * x1_ratio)
            x2 = int(width * x2_ratio)
            y1 = int(height * y1_ratio)
            y2 = int(height * y2_ratio)

            crop = img_cv[y1:y2, x1:x2]
            if crop.size > 0:
                results.append((crop, name))

        return results

    def _detect_heuristic(self, img_cv: np.ndarray) -> list:
        """Known heuristic locations from analysis"""
        height, width = img_cv.shape[:2]
        results = []

        # Location from template matching analysis
        locations = [
            ('bottom_right_known', 0.704, 0.891, 0.892, 0.983),
            ('top_right_known', 0.950, 1.000, 0.026, 0.038),
        ]

        for name, x1_ratio, x2_ratio, y1_ratio, y2_ratio in locations:
            x1 = int(width * x1_ratio)
            x2 = int(width * x2_ratio)
            y1 = int(height * y1_ratio)
            y2 = int(height * y2_ratio)

            crop = img_cv[y1:y2, x1:x2]
            if crop.size > 0:
                results.append((crop, name))

        return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python ocr_unified.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)

    ocr = UnifiedOCR()
    result = ocr.extract_reading(image_path)

    print("\n" + "="*70)
    if result['reading_kwh'] is not None:
        print(f"✓ Result: {result['reading_kwh']} kWh (confidence: {result['confidence']:.1f}%)")
        print(f"Strategy: {result['strategy']}")
        if result['crop_path']:
            print(f"Crop saved: {result['crop_path']}")
    else:
        print("✗ Failed to extract reading")
    print("="*70)


if __name__ == "__main__":
    main()
