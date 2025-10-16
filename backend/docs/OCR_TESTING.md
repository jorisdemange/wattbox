# OCR Testing Guide

This guide explains how to test and refine OCR functionality independently from the main WattBox application.

## Overview

WattBox now has a **fully modular OCR system** that allows you to:

- Test OCR on images without running the full application
- Compare different OCR strategies side-by-side
- Iterate quickly on OCR algorithms
- Benchmark performance on test images
- Gradually integrate improvements back into the main app

## Architecture

### Components

1. **OCR Orchestrator** (`services/ocr_orchestrator.py`)
   - Unified interface for all OCR operations
   - Automatic strategy selection based on meter type
   - Multiple OCR strategies with fallback support
   - Detailed result metadata for debugging

2. **OCR Testing API** (`api/ocr_test.py`)
   - Standalone HTTP API for OCR testing
   - No database or storage dependencies
   - Perfect for web-based testing workflows

3. **OCR CLI Tool** (`cli/ocr_tool.py`)
   - Command-line tool for offline testing
   - Batch processing capabilities
   - Benchmarking and comparison features

### Available OCR Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `auto` | Automatically selects best strategy | Unknown meter types, mixed deployments |
| `basic` | Basic preprocessing (grayscale, contrast, sharpening) | Clear mechanical digits, high contrast |
| `advanced` | Region detection with LCD optimization | LCD displays, digital meters |
| `seven_segment` | Specialized for seven-segment displays | Iskra meters, LED displays |
| `simple` | Multiple preprocessing strategies | Difficult images, poor lighting |

## Testing Methods

### Method 1: OCR Testing API

The easiest way to test OCR with a web interface or API client.

#### Start the API Server

```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
uvicorn main:app --reload
```

The OCR testing endpoints are available at: `http://localhost:8000/ocr`

#### Test Single Image

```bash
curl -X POST "http://localhost:8000/ocr/test?strategy=auto" \
  -F "file=@meter_photo.jpg"
```

**Response:**
```json
{
  "reading_kwh": 7510.3,
  "confidence": 85.5,
  "strategy_used": "seven_segment",
  "meter_type": "iskra_digital",
  "processing_time_ms": 234.5,
  "success": true
}
```

#### Benchmark All Strategies

```bash
curl -X POST "http://localhost:8000/ocr/benchmark" \
  -F "file=@meter_photo.jpg"
```

**Response:**
```json
{
  "results": {
    "basic": {
      "reading_kwh": null,
      "confidence": 0.0,
      "success": false
    },
    "advanced": {
      "reading_kwh": 7510.3,
      "confidence": 72.1,
      "success": true
    },
    "seven_segment": {
      "reading_kwh": 7510.3,
      "confidence": 85.5,
      "success": true
    }
  },
  "best_strategy": "seven_segment",
  "best_confidence": 85.5
}
```

#### Test with Fallback

```bash
curl -X POST "http://localhost:8000/ocr/test-with-fallback?primary_strategy=auto&confidence_threshold=70.0" \
  -F "file=@meter_photo.jpg"
```

#### List Available Strategies

```bash
curl http://localhost:8000/ocr/strategies
```

#### API Documentation

Full interactive API documentation: `http://localhost:8000/docs`

---

### Method 2: CLI Tool (Recommended for Batch Testing)

Perfect for offline testing and processing multiple images.

#### Installation

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

#### Test Single Image

```bash
python cli/ocr_tool.py test meter_photo.jpg
```

**Output:**
```
======================================================================
Image: meter_photo.jpg
======================================================================
✓ SUCCESS
Reading:     7510.3 kWh
Confidence:  85.50%
Strategy:    seven_segment
Meter Type:  iskra_digital
Time:        234.50ms
```

#### Test with Specific Strategy

```bash
python cli/ocr_tool.py test meter_photo.jpg --strategy seven_segment
```

#### Benchmark Single Image

```bash
python cli/ocr_tool.py benchmark meter_photo.jpg --output results.json
```

**Output:**
```
======================================================================
Benchmark: meter_photo.jpg
======================================================================
┌─────────────────┬────────────────┬────────────┬──────────┬─────────┐
│ Strategy        │ Reading (kWh)  │ Confidence │ Time     │ Success │
├─────────────────┼────────────────┼────────────┼──────────┼─────────┤
│ basic           │ FAILED         │ 0.00%      │ 123.45ms │ ✗       │
│ advanced        │ 7510.3         │ 72.10%     │ 245.67ms │ ✓       │
│ seven_segment   │ 7510.3         │ 85.50%     │ 234.50ms │ ✓       │
│ simple          │ 7510.3         │ 65.30%     │ 456.78ms │ ✓       │
└─────────────────┴────────────────┴────────────┴──────────┴─────────┘

Best Strategy: seven_segment
Best Confidence: 85.50%
```

#### Batch Test All Images in Folder

```bash
python cli/ocr_tool.py batch ./test_images/ --output results.csv
```

**Output:**
```
======================================================================
Batch Test Summary
======================================================================
Total images:     25
Successful:       22
Failed:           3
Success rate:     88.0%
```

Results saved to `results.csv`:
```csv
image,reading_kwh,confidence,strategy_used,meter_type,processing_time_ms,success
test_images/meter1.jpg,7510.3,85.5,seven_segment,iskra_digital,234.5,True
test_images/meter2.jpg,8432.1,78.2,advanced,generic_digital,245.6,True
...
```

#### Batch Benchmark

```bash
python cli/ocr_tool.py batch-benchmark ./test_images/ --output benchmark.json
```

#### CLI Help

```bash
python cli/ocr_tool.py --help
python cli/ocr_tool.py test --help
python cli/ocr_tool.py benchmark --help
```

---

### Method 3: Python Integration

Use the OCR orchestrator directly in Python scripts.

```python
from services.ocr_orchestrator import OCROrchestrator, OCRStrategy

# Initialize orchestrator
orchestrator = OCROrchestrator()

# Test with auto strategy
result = orchestrator.extract_reading('meter_photo.jpg', OCRStrategy.AUTO)

print(f"Reading: {result.reading_kwh} kWh")
print(f"Confidence: {result.confidence}%")
print(f"Strategy: {result.strategy_used}")
print(f"Meter Type: {result.meter_type}")
print(f"Time: {result.processing_time_ms}ms")

# Benchmark all strategies
results = orchestrator.benchmark_strategies('meter_photo.jpg')
for strategy_name, result in results.items():
    print(f"{strategy_name}: {result.reading_kwh} kWh ({result.confidence}%)")

# Use fallback strategies
result = orchestrator.process_with_fallback(
    'meter_photo.jpg',
    primary_strategy=OCRStrategy.SEVEN_SEGMENT,
    confidence_threshold=70.0
)
```

---

## Configuration

OCR behavior is configured in [config.py](../config.py) and can be overridden with environment variables:

```bash
# Default OCR strategy (auto, basic, advanced, seven_segment, simple)
OCR_DEFAULT_STRATEGY=auto

# Minimum confidence threshold for accepting results
OCR_CONFIDENCE_THRESHOLD=50.0

# Enable automatic fallback to other strategies
OCR_ENABLE_FALLBACK=true

# Save preprocessed images for debugging
OCR_DEBUG_MODE=false

# Tesseract executable path (if not in PATH)
TESSERACT_PATH=/opt/homebrew/bin/tesseract
```

---

## Workflow for Refining OCR

### Step 1: Collect Test Images

Gather images where OCR is failing:

```bash
# Failed images are automatically moved here by the app
ls backend/static/uploads/failed/
```

### Step 2: Benchmark Test Images

```bash
cd backend
python cli/ocr_tool.py batch-benchmark ./static/uploads/failed/ --output failed_benchmark.json
```

This shows which strategies work best for each image.

### Step 3: Analyze Results

Open `failed_benchmark.json` and look for patterns:
- Which strategies fail most often?
- Which meter types have the lowest confidence?
- Are there common preprocessing issues?

### Step 4: Refine OCR Strategy

Based on analysis:

1. **Adjust existing strategies**: Modify preprocessing in `services/ocr_*.py`
2. **Add new strategy**: Create new OCR service class
3. **Update meter detection**: Modify `meter_config/meter_types.py`

### Step 5: Test Improvements

```bash
# Test on single problematic image
python cli/ocr_tool.py test problem_image.jpg --strategy advanced

# Re-benchmark after changes
python cli/ocr_tool.py batch-benchmark ./static/uploads/failed/ --output new_benchmark.json
```

### Step 6: Compare Results

```bash
# Compare before/after benchmarks
diff failed_benchmark.json new_benchmark.json
```

### Step 7: Update Configuration

Once satisfied, update the default strategy:

```bash
# .env file
OCR_DEFAULT_STRATEGY=seven_segment  # or your best strategy
OCR_CONFIDENCE_THRESHOLD=60.0       # adjust based on results
```

### Step 8: Test in Production

The improved OCR will now be used by all upload endpoints:
- `/upload/device` (ESP32)
- `/upload/manual` (Web/iPhone)
- `/api/upload` (ESP32 alternative)

---

## Adding New OCR Strategies

### 1. Create Strategy Class

Create `services/ocr_my_strategy.py`:

```python
import pytesseract
from PIL import Image
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class MyCustomOCR:
    def __init__(self, tesseract_path: Optional[str] = None):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def extract_reading(self, image_path: str) -> Tuple[Optional[float], float]:
        """
        Extract reading from image with custom logic.

        Returns:
            (reading_kwh, confidence)
        """
        try:
            # Your custom preprocessing and OCR logic here
            img = Image.open(image_path)
            # ... preprocessing ...
            text = pytesseract.image_to_string(img)
            # ... parsing ...

            return reading_value, confidence
        except Exception as e:
            logger.error(f"Custom OCR failed: {e}")
            return None, 0.0
```

### 2. Register Strategy in Orchestrator

Edit `services/ocr_orchestrator.py`:

```python
from services.ocr_my_strategy import MyCustomOCR

class OCRStrategy(str, Enum):
    # ... existing strategies ...
    MY_CUSTOM = "my_custom"

class OCROrchestrator:
    def __init__(self, tesseract_path: Optional[str] = None):
        self._services = {
            # ... existing services ...
            OCRStrategy.MY_CUSTOM: MyCustomOCR(tesseract_path),
        }
```

### 3. Test New Strategy

```bash
python cli/ocr_tool.py test meter.jpg --strategy my_custom
```

---

## Troubleshooting

### OCR Returns No Results

1. **Check image format**:
   ```bash
   file meter_photo.jpg
   # Should be: JPEG image data
   ```

2. **Test with all strategies**:
   ```bash
   python cli/ocr_tool.py benchmark meter_photo.jpg
   ```

3. **Enable debug logging**:
   ```bash
   export LOG_LEVEL=DEBUG
   python cli/ocr_tool.py test meter_photo.jpg
   ```

### Low Confidence Scores

1. **Check image quality**:
   - Resolution too low (< 800px width)
   - Poor lighting or glare
   - Blurry or out of focus
   - Meter display partially obscured

2. **Try preprocessing manually**:
   ```python
   from services.ocr import OCRService
   ocr = OCRService()
   processed = ocr.preprocess_image('meter.jpg')
   processed.save('processed.jpg')
   # Inspect processed.jpg
   ```

3. **Adjust confidence threshold**:
   ```bash
   # In .env
   OCR_CONFIDENCE_THRESHOLD=40.0  # Lower threshold
   ```

### Tesseract Not Found

```bash
# macOS
brew install tesseract

# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# Set path in .env
TESSERACT_PATH=/opt/homebrew/bin/tesseract
```

### API Returns 500 Error

1. Check logs:
   ```bash
   # Terminal running uvicorn will show error details
   ```

2. Test directly with CLI:
   ```bash
   python cli/ocr_tool.py test meter.jpg
   ```

3. Verify dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## Best Practices

### Image Quality

For best OCR results:
- **Resolution**: At least 800px width
- **Lighting**: Even, no glare on display
- **Focus**: Sharp focus on meter display
- **Angle**: Straight-on, not tilted
- **Distance**: Fill frame but don't crop digits

### Testing Workflow

1. **Start small**: Test single images first
2. **Benchmark**: Compare all strategies
3. **Iterate**: Make small changes and re-test
4. **Batch test**: Verify on larger dataset
5. **Monitor**: Track confidence scores over time

### Production Integration

1. **Test thoroughly**: Use CLI tool with test dataset
2. **Set conservative threshold**: Start with higher confidence requirement
3. **Enable fallback**: Always have backup strategies
4. **Monitor failures**: Check `/failed` folder regularly
5. **Log strategy used**: Track which strategies work best

---

## Examples

### Example 1: Testing Failed Images

```bash
# Collect failed images
cd backend
ls static/uploads/failed/

# Test each strategy
for img in static/uploads/failed/*.jpg; do
    echo "Testing: $img"
    python cli/ocr_tool.py benchmark "$img"
done
```

### Example 2: Batch Processing with Different Strategies

```bash
# Test with auto strategy
python cli/ocr_tool.py batch ./test_images/ --strategy auto --output auto_results.csv

# Test with seven_segment strategy
python cli/ocr_tool.py batch ./test_images/ --strategy seven_segment --output segment_results.csv

# Compare results
diff auto_results.csv segment_results.csv
```

### Example 3: API Testing with cURL

```bash
# Test image
curl -X POST "http://localhost:8000/ocr/test?strategy=auto" \
  -H "accept: application/json" \
  -F "file=@meter.jpg" | jq

# Benchmark
curl -X POST "http://localhost:8000/ocr/benchmark" \
  -F "file=@meter.jpg" | jq '.best_strategy'

# Test with fallback
curl -X POST "http://localhost:8000/ocr/test-with-fallback?primary_strategy=seven_segment&confidence_threshold=70" \
  -F "file=@meter.jpg" | jq
```

### Example 4: Python Script for Automated Testing

```python
#!/usr/bin/env python3
import glob
from services.ocr_orchestrator import OCROrchestrator, OCRStrategy

orchestrator = OCROrchestrator()

# Test all images in folder
for image_path in glob.glob('./test_images/*.jpg'):
    print(f"\nTesting: {image_path}")

    # Benchmark all strategies
    results = orchestrator.benchmark_strategies(image_path)

    # Find best
    best = max(results.items(), key=lambda x: x[1].confidence)

    print(f"Best: {best[0]} - {best[1].reading_kwh} kWh ({best[1].confidence}%)")
```

---

## Summary

The modular OCR system allows you to:

- ✅ Test OCR completely separately from the main app
- ✅ Compare different strategies side-by-side
- ✅ Iterate quickly without touching the database
- ✅ Batch process test images efficiently
- ✅ Gradually integrate improvements into production

**Next Steps:**

1. Collect failed images from your deployment
2. Run batch benchmarks to identify patterns
3. Refine OCR strategies based on results
4. Update configuration for best strategy
5. Monitor performance in production

For questions or issues, check the main [README](../../README.md) or file an issue.
