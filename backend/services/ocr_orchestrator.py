"""
OCR Orchestrator - Unified interface for all OCR operations

This module provides a single entry point for OCR processing with:
- Automatic strategy selection based on meter type
- Multiple OCR strategies (basic, advanced, seven-segment, simple)
- Detailed result metadata for debugging and benchmarking
- Pluggable architecture for easy extension
"""

from typing import Optional, Dict, List, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from PIL import Image
import logging
import time

from services.ocr import OCRService
from services.ocr_advanced import AdvancedOCRService
from services.ocr_seven_segment import SevenSegmentOCR
from services.ocr_simple import SimpleOCR
from services.ocr_template import TemplateOCR
from services.ocr_multi_template import MultiTemplateOCR
from meter_config.meter_types import detect_meter_type, METER_TYPES

logger = logging.getLogger(__name__)


class OCRStrategy(str, Enum):
    """Available OCR strategies"""
    BASIC = "basic"
    ADVANCED = "advanced"
    SEVEN_SEGMENT = "seven_segment"
    TEMPLATE = "template"  # Template matching for seven-segment displays
    MULTI_TEMPLATE = "multi_template"  # Multi-template matching (100% accurate for Iskra)
    SIMPLE = "simple"
    AUTO = "auto"  # Automatically select based on meter type


@dataclass
class OCRResult:
    """Structured result from OCR processing"""
    # Core results
    reading_kwh: Optional[float]
    confidence: float

    # Metadata
    strategy_used: str
    meter_type: Optional[str]
    processing_time_ms: float

    # Debug information
    raw_text: Optional[str] = None
    preprocessing_applied: List[str] = None
    all_candidates: List[Dict[str, Any]] = None
    error_message: Optional[str] = None
    success: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert None fields to appropriate types
        if self.preprocessing_applied is None:
            result['preprocessing_applied'] = []
        if self.all_candidates is None:
            result['all_candidates'] = []
        return result


class OCROrchestrator:
    """
    Unified orchestrator for all OCR operations.

    This class manages multiple OCR strategies and automatically
    selects the best one based on meter type and configuration.
    """

    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize OCR orchestrator with all available strategies.

        Args:
            tesseract_path: Optional path to Tesseract executable
        """
        self.tesseract_path = tesseract_path

        # Initialize all OCR services
        self._services = {
            OCRStrategy.BASIC: OCRService(tesseract_path),
            OCRStrategy.ADVANCED: AdvancedOCRService(tesseract_path),
            OCRStrategy.SEVEN_SEGMENT: SevenSegmentOCR(tesseract_path),
            OCRStrategy.TEMPLATE: TemplateOCR(tesseract_path),
            OCRStrategy.MULTI_TEMPLATE: MultiTemplateOCR(),
            OCRStrategy.SIMPLE: SimpleOCR(tesseract_path),
        }

        logger.info("OCR Orchestrator initialized with strategies: %s",
                   list(self._services.keys()))

    def extract_reading(
        self,
        image_path: str,
        strategy: OCRStrategy = OCRStrategy.AUTO,
        meter_type: Optional[str] = None
    ) -> OCRResult:
        """
        Extract reading from image using specified or auto-selected strategy.

        Args:
            image_path: Path to the meter image
            strategy: OCR strategy to use (AUTO will auto-detect)
            meter_type: Optional meter type hint

        Returns:
            OCRResult with reading and detailed metadata
        """
        start_time = time.time()

        try:
            # Auto-detect meter type if not provided
            if meter_type is None and strategy == OCRStrategy.AUTO:
                meter_type = self._detect_meter_type(image_path)
                logger.info(f"Auto-detected meter type: {meter_type}")

            # Select strategy
            if strategy == OCRStrategy.AUTO:
                strategy = self._select_strategy_for_meter(meter_type)
                logger.info(f"Auto-selected OCR strategy: {strategy}")

            # Execute OCR with selected strategy
            service = self._services[strategy]
            reading_kwh, confidence = service.extract_reading(image_path)

            processing_time = (time.time() - start_time) * 1000

            # Build result
            result = OCRResult(
                reading_kwh=reading_kwh,
                confidence=confidence,
                strategy_used=strategy.value,
                meter_type=meter_type,
                processing_time_ms=processing_time,
                preprocessing_applied=[strategy.value],
                success=reading_kwh is not None
            )

            if reading_kwh is None:
                result.error_message = "Failed to extract reading from image"

            logger.info(f"OCR completed: reading={reading_kwh}, "
                       f"confidence={confidence:.2f}, time={processing_time:.2f}ms")

            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"OCR extraction failed: {str(e)}", exc_info=True)

            return OCRResult(
                reading_kwh=None,
                confidence=0.0,
                strategy_used=strategy.value if isinstance(strategy, OCRStrategy) else "unknown",
                meter_type=meter_type,
                processing_time_ms=processing_time,
                error_message=str(e),
                success=False
            )

    def benchmark_strategies(
        self,
        image_path: str,
        strategies: Optional[List[OCRStrategy]] = None
    ) -> Dict[str, OCRResult]:
        """
        Run multiple OCR strategies on the same image for comparison.

        Args:
            image_path: Path to the meter image
            strategies: List of strategies to test (None = all)

        Returns:
            Dictionary mapping strategy name to OCRResult
        """
        if strategies is None:
            strategies = [s for s in OCRStrategy if s != OCRStrategy.AUTO]

        results = {}
        meter_type = self._detect_meter_type(image_path)

        for strategy in strategies:
            logger.info(f"Benchmarking strategy: {strategy}")
            result = self.extract_reading(image_path, strategy, meter_type)
            results[strategy.value] = result

        return results

    def get_available_strategies(self) -> List[str]:
        """Get list of available OCR strategies"""
        return [s.value for s in OCRStrategy]

    def _detect_meter_type(self, image_path: str) -> str:
        """
        Detect meter type from image using basic OCR scan.

        Args:
            image_path: Path to the meter image

        Returns:
            Meter type identifier
        """
        try:
            # Use basic OCR to get initial text
            import pytesseract
            img = Image.open(image_path)

            # Convert to RGB if needed
            if img.mode not in ['RGB', 'L']:
                img = img.convert('RGB')

            initial_text = pytesseract.image_to_string(img)
            meter_type = detect_meter_type(initial_text)

            logger.debug(f"Meter type detection - Text: {initial_text[:100]}...")
            logger.info(f"Detected meter type: {meter_type}")

            return meter_type

        except Exception as e:
            logger.warning(f"Meter type detection failed: {e}, using default")
            return "generic_digital"

    def _select_strategy_for_meter(self, meter_type: str) -> OCRStrategy:
        """
        Select the best OCR strategy for a given meter type.

        Args:
            meter_type: Meter type identifier

        Returns:
            Recommended OCR strategy
        """
        # Get meter configuration
        meter_config = METER_TYPES.get(meter_type)

        if meter_config is None:
            logger.warning(f"Unknown meter type: {meter_type}, using advanced OCR")
            return OCRStrategy.ADVANCED

        # Strategy selection logic
        if meter_type == "iskra_digital":
            # Iskra meters work best with multi-template matching (100% accuracy on cropped images)
            return OCRStrategy.MULTI_TEMPLATE
        elif meter_config.use_advanced_ocr:
            # Use advanced OCR for LCD displays
            return OCRStrategy.ADVANCED
        else:
            # Use basic OCR for mechanical/analog meters
            return OCRStrategy.BASIC

    def process_with_fallback(
        self,
        image_path: str,
        primary_strategy: OCRStrategy = OCRStrategy.AUTO,
        fallback_strategies: Optional[List[OCRStrategy]] = None,
        confidence_threshold: float = 50.0
    ) -> OCRResult:
        """
        Process image with fallback strategies if primary fails or has low confidence.

        Args:
            image_path: Path to the meter image
            primary_strategy: Primary strategy to try first
            fallback_strategies: List of fallback strategies to try
            confidence_threshold: Minimum confidence to accept result

        Returns:
            Best OCRResult from primary or fallback strategies
        """
        # Try primary strategy
        result = self.extract_reading(image_path, primary_strategy)

        if result.success and result.confidence >= confidence_threshold:
            logger.info(f"Primary strategy succeeded: {primary_strategy}")
            return result

        # Try fallback strategies
        if fallback_strategies is None:
            fallback_strategies = [
                OCRStrategy.MULTI_TEMPLATE,
                OCRStrategy.TEMPLATE,
                OCRStrategy.SEVEN_SEGMENT,
                OCRStrategy.ADVANCED,
                OCRStrategy.SIMPLE,
                OCRStrategy.BASIC
            ]

        best_result = result
        for fallback in fallback_strategies:
            if fallback == primary_strategy:
                continue

            logger.info(f"Trying fallback strategy: {fallback}")
            fallback_result = self.extract_reading(image_path, fallback)

            # Keep the best result (highest confidence)
            if fallback_result.confidence > best_result.confidence:
                best_result = fallback_result
                best_result.strategy_used = f"{primary_strategy.value}_fallback_{fallback.value}"

            # Stop if we got a good result
            if fallback_result.success and fallback_result.confidence >= confidence_threshold:
                logger.info(f"Fallback strategy succeeded: {fallback}")
                break

        return best_result
