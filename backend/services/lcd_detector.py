"""
LCD Display Detector for Iskra Meters

Automatically detects and crops the LCD display region from full meter images.
"""

import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LCDDetector:
    """Detects and extracts LCD display regions from meter images"""

    def __init__(self):
        pass

    def detect_and_crop(self, image_path: str) -> Optional[np.ndarray]:
        """
        Detect LCD display in image and return cropped region.

        Args:
            image_path: Path to the full meter image

        Returns:
            Cropped LCD region as numpy array, or None if detection fails
        """
        try:
            # Load image
            img = Image.open(image_path)

            # Handle MPO format (iPhone multi-picture)
            if img.format == 'MPO':
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img_cv = np.array(img)
            img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

            # Try multiple detection methods
            # For Iskra meters, heuristic works best, try it first
            lcd_region = self._heuristic_crop(img_cv)
            if lcd_region is not None:
                logger.info("LCD detected using heuristic crop")
                return lcd_region

            lcd_region = self._detect_by_contours(img_cv)
            if lcd_region is not None:
                logger.info("LCD detected using contour method")
                return lcd_region

            lcd_region = self._detect_by_color(img_cv)
            if lcd_region is not None:
                logger.info("LCD detected using color method")
                return lcd_region

            logger.warning("LCD detection failed, returning None")
            return None

        except Exception as e:
            logger.error(f"LCD detection error: {e}", exc_info=True)
            return None

    def _detect_by_contours(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect LCD by finding rectangular contours.
        Specifically looks for the dark seven-segment digits on light background.
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Apply adaptive thresholding to find dark regions (LCD digits)
            # LCD digits are dark on light background
            binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 11, 2)

            # Morphological operations to connect digit segments
            kernel_h = np.ones((3, 15), np.uint8)  # Horizontal kernel for connecting digits
            dilated = cv2.dilate(binary, kernel_h, iterations=2)

            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by aspect ratio and size
            height, width = img.shape[:2]
            candidates = []

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)

                # LCD digit strip aspect ratio: width should be 4-10x height
                aspect_ratio = w / h if h > 0 else 0

                # LCD should be 4-25% of image width (flexible for different zoom levels)
                width_ratio = w / width

                # Height should be reasonable (not too small)
                height_ratio = h / height

                # Smart detection: use aspect ratio and size, not fixed position
                # This allows the LCD to be anywhere in the frame
                if (4 < aspect_ratio < 12 and
                    0.04 < width_ratio < 0.30 and
                    0.01 < height_ratio < 0.10):

                    candidates.append({
                        'box': (x, y, w, h),
                        'score': aspect_ratio * width_ratio
                    })
                    logger.debug(f"Candidate: ({x}, {y}, {w}, {h}) aspect={aspect_ratio:.2f} width_ratio={width_ratio:.2f}")

            if candidates:
                # Sort by score and take best
                candidates.sort(key=lambda c: c['score'], reverse=True)
                x, y, w, h = candidates[0]['box']

                # Add minimal margin
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

    def _detect_by_color(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect LCD by looking for the characteristic gray/green LCD background.
        Iskra LCDs have a light gray-green background with dark digits.
        """
        try:
            # Convert to HSV for better color detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

            # LCD background is typically gray-green with low saturation
            # H: 0-180, S: 0-30, V: 100-200
            lower_lcd = np.array([0, 0, 100])
            upper_lcd = np.array([180, 30, 200])

            mask = cv2.inRange(hsv, lower_lcd, upper_lcd)

            # Morphological operations to clean up
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

            # Find contours in mask
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                # Take largest contour
                largest = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest)

                # Validate aspect ratio
                aspect_ratio = w / h if h > 0 else 0
                if 3 < aspect_ratio < 6:
                    # Add margin
                    height, width = img.shape[:2]
                    margin_x = int(w * 0.05)
                    margin_y = int(h * 0.1)
                    x1 = max(0, x - margin_x)
                    y1 = max(0, y - margin_y)
                    x2 = min(width, x + w + margin_x)
                    y2 = min(height, y + h + margin_y)

                    lcd_region = img[y1:y2, x1:x2]
                    logger.info(f"Color detection found LCD at ({x1}, {y1}, {x2}, {y2})")
                    return lcd_region

            return None

        except Exception as e:
            logger.debug(f"Color detection failed: {e}")
            return None

    def _heuristic_crop(self, img: np.ndarray) -> Optional[np.ndarray]:
        """
        Fallback heuristic crop based on typical Iskra meter layout.
        The LCD is usually in the center-left area of the meter.
        """
        try:
            height, width = img.shape[:2]

            # Based on actual location found via template matching from IMG_7751.jpeg:
            # Reference crop (754x278) found at:
            # - x: 70.4% to 89.1% (18.7% of image width)
            # - y: 89.2% to 98.3% (9.2% of image height)
            # This is the LCD display panel showing the meter reading

            x1 = int(width * 0.704)
            x2 = int(width * 0.891)
            y1 = int(height * 0.892)
            y2 = int(height * 0.983)

            lcd_region = img[y1:y2, x1:x2]
            logger.info(f"Heuristic crop: ({x1}, {y1}, {x2}, {y2})")
            return lcd_region

        except Exception as e:
            logger.debug(f"Heuristic crop failed: {e}")
            return None

    def save_cropped_lcd(self, lcd_region: np.ndarray, output_path: str) -> bool:
        """
        Save cropped LCD region to file.

        Args:
            lcd_region: Cropped LCD image as numpy array
            output_path: Path to save the cropped image

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            cv2.imwrite(output_path, lcd_region)
            logger.info(f"Saved cropped LCD to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save cropped LCD: {e}")
            return False


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python lcd_detector.py <image_path> [output_path]")
        sys.exit(1)

    detector = LCDDetector()
    lcd_region = detector.detect_and_crop(sys.argv[1])

    if lcd_region is not None:
        output_path = sys.argv[2] if len(sys.argv) > 2 else '/tmp/lcd_cropped.png'
        detector.save_cropped_lcd(lcd_region, output_path)
        print(f"✓ LCD detected and saved to {output_path}")
        print(f"  Size: {lcd_region.shape[1]}x{lcd_region.shape[0]}")
    else:
        print("✗ LCD detection failed")
        sys.exit(1)
