"""
OCR Testing API - Standalone endpoints for testing and benchmarking OCR

This API allows testing OCR functionality independently from the main application:
- No database required
- No file storage required
- Returns detailed debugging information
- Supports benchmarking multiple strategies

Perfect for iterating and refining OCR algorithms before integration.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, status
from typing import Optional, List
from pydantic import BaseModel
import tempfile
import os
import logging

from services.ocr_orchestrator import OCROrchestrator, OCRStrategy, OCRResult
from config import get_settings

router = APIRouter(prefix="/ocr", tags=["ocr-testing"])
logger = logging.getLogger(__name__)

settings = get_settings()
orchestrator = OCROrchestrator(settings.TESSERACT_PATH)


class OCRTestRequest(BaseModel):
    """Request model for OCR testing"""
    strategy: Optional[str] = "auto"
    meter_type: Optional[str] = None


class OCRTestResponse(BaseModel):
    """Response model for OCR testing"""
    reading_kwh: Optional[float]
    confidence: float
    strategy_used: str
    meter_type: Optional[str]
    processing_time_ms: float
    raw_text: Optional[str]
    preprocessing_applied: List[str]
    error_message: Optional[str]
    success: bool


class BenchmarkResponse(BaseModel):
    """Response model for benchmark testing"""
    results: dict
    best_strategy: str
    best_reading: Optional[float]
    best_confidence: float
    total_time_ms: float


class StrategyInfo(BaseModel):
    """Information about an OCR strategy"""
    name: str
    description: str
    best_for: List[str]


@router.post("/test", response_model=OCRTestResponse)
async def test_ocr(
    file: UploadFile = File(...),
    strategy: str = Query("auto", description="OCR strategy to use"),
    meter_type: Optional[str] = Query(None, description="Optional meter type hint")
):
    """
    Test OCR on a single image with specified strategy.

    This endpoint is designed for testing and debugging OCR without
    affecting the main application database or storage.

    Args:
        file: Image file to process
        strategy: OCR strategy (auto, basic, advanced, seven_segment, simple)
        meter_type: Optional meter type hint

    Returns:
        Detailed OCR result with debugging information
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Validate strategy
    try:
        ocr_strategy = OCRStrategy(strategy)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in OCRStrategy]}"
        )

    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info(f"Testing OCR with strategy={strategy} on temp file: {tmp_path}")

        # Process with orchestrator
        result = orchestrator.extract_reading(tmp_path, ocr_strategy, meter_type)

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file: {e}")

        return OCRTestResponse(
            reading_kwh=result.reading_kwh,
            confidence=result.confidence,
            strategy_used=result.strategy_used,
            meter_type=result.meter_type,
            processing_time_ms=result.processing_time_ms,
            raw_text=result.raw_text,
            preprocessing_applied=result.preprocessing_applied or [],
            error_message=result.error_message,
            success=result.success
        )

    except Exception as e:
        logger.error(f"OCR test failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.post("/benchmark", response_model=BenchmarkResponse)
async def benchmark_ocr(
    file: UploadFile = File(...),
    strategies: Optional[List[str]] = Query(None, description="Strategies to test (default: all)")
):
    """
    Benchmark multiple OCR strategies on the same image.

    Useful for comparing different strategies and finding the best one
    for a particular meter type or image quality.

    Args:
        file: Image file to process
        strategies: List of strategies to benchmark (None = all)

    Returns:
        Comparison of all strategies with best result highlighted
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Validate strategies if provided
    ocr_strategies = None
    if strategies:
        try:
            ocr_strategies = [OCRStrategy(s) for s in strategies]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid strategy in list: {str(e)}"
            )

    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info(f"Benchmarking OCR strategies on temp file: {tmp_path}")

        # Run benchmark
        results = orchestrator.benchmark_strategies(tmp_path, ocr_strategies)

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file: {e}")

        # Find best result
        best_strategy = None
        best_confidence = 0.0
        best_reading = None
        total_time = 0.0

        results_dict = {}
        for strategy_name, result in results.items():
            results_dict[strategy_name] = result.to_dict()
            total_time += result.processing_time_ms

            if result.success and result.confidence > best_confidence:
                best_strategy = strategy_name
                best_confidence = result.confidence
                best_reading = result.reading_kwh

        if best_strategy is None:
            best_strategy = "none"

        return BenchmarkResponse(
            results=results_dict,
            best_strategy=best_strategy,
            best_reading=best_reading,
            best_confidence=best_confidence,
            total_time_ms=total_time
        )

    except Exception as e:
        logger.error(f"Benchmark failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark failed: {str(e)}"
        )


@router.get("/strategies", response_model=List[StrategyInfo])
async def get_strategies():
    """
    Get list of available OCR strategies with descriptions.

    Returns:
        List of OCR strategies with information about each
    """
    strategies = [
        StrategyInfo(
            name="auto",
            description="Automatically select best strategy based on meter type detection",
            best_for=["Unknown meter types", "Mixed meter deployments"]
        ),
        StrategyInfo(
            name="basic",
            description="Basic OCR with PIL preprocessing (grayscale, contrast, sharpening)",
            best_for=["Clear mechanical digits", "High contrast displays", "Simple meters"]
        ),
        StrategyInfo(
            name="advanced",
            description="Advanced OCR with region detection and LCD optimization",
            best_for=["LCD displays", "Digital meters", "Complex meter faces"]
        ),
        StrategyInfo(
            name="seven_segment",
            description="Specialized OCR for seven-segment displays (Iskra meters)",
            best_for=["Iskra meters", "Seven-segment displays", "LED meters"]
        ),
        StrategyInfo(
            name="simple",
            description="Multiple preprocessing strategies with exhaustive search",
            best_for=["Difficult images", "Poor lighting", "When other strategies fail"]
        ),
    ]
    return strategies


@router.post("/test-with-fallback", response_model=OCRTestResponse)
async def test_with_fallback(
    file: UploadFile = File(...),
    primary_strategy: str = Query("auto", description="Primary OCR strategy"),
    confidence_threshold: float = Query(50.0, description="Minimum confidence threshold")
):
    """
    Test OCR with automatic fallback to other strategies if primary fails.

    This endpoint mimics production behavior where we try multiple strategies
    to ensure we get a reading.

    Args:
        file: Image file to process
        primary_strategy: Primary strategy to try first
        confidence_threshold: Minimum confidence to accept result

    Returns:
        Best OCR result from primary or fallback strategies
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )

    # Validate strategy
    try:
        ocr_strategy = OCRStrategy(primary_strategy)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid strategy. Must be one of: {[s.value for s in OCRStrategy]}"
        )

    # Save uploaded file to temporary location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        logger.info(f"Testing OCR with fallback, primary={primary_strategy}")

        # Process with fallback
        result = orchestrator.process_with_fallback(
            tmp_path,
            ocr_strategy,
            confidence_threshold=confidence_threshold
        )

        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception as e:
            logger.warning(f"Failed to delete temp file: {e}")

        return OCRTestResponse(
            reading_kwh=result.reading_kwh,
            confidence=result.confidence,
            strategy_used=result.strategy_used,
            meter_type=result.meter_type,
            processing_time_ms=result.processing_time_ms,
            raw_text=result.raw_text,
            preprocessing_applied=result.preprocessing_applied or [],
            error_message=result.error_message,
            success=result.success
        )

    except Exception as e:
        logger.error(f"OCR test with fallback failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for OCR testing API.

    Returns:
        Status information
    """
    return {
        "status": "healthy",
        "service": "OCR Testing API",
        "available_strategies": orchestrator.get_available_strategies()
    }
