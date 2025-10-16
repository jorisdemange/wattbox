# OCR Testing - Quick Start

**TL;DR:** Test and refine OCR without running the full app.

## Quick Commands

### Test Single Image

```bash
# CLI (recommended)
cd backend
python cli/ocr_tool.py test meter_photo.jpg

# API (requires server running)
curl -X POST "http://localhost:8000/ocr/test?strategy=auto" -F "file=@meter_photo.jpg"
```

### Compare All Strategies

```bash
# CLI
python cli/ocr_tool.py benchmark meter_photo.jpg

# API
curl -X POST "http://localhost:8000/ocr/benchmark" -F "file=@meter_photo.jpg"
```

### Test All Failed Images

```bash
# Batch test failed images
python cli/ocr_tool.py batch ./static/uploads/failed/ --output failed_results.csv

# Benchmark to find best strategy
python cli/ocr_tool.py batch-benchmark ./static/uploads/failed/ --output benchmark.json
```

## Available Strategies

| Strategy | When to Use |
|----------|-------------|
| `auto` | Default - auto-detects meter type |
| `seven_segment` | Iskra meters, LED displays |
| `advanced` | LCD displays, digital meters |
| `simple` | Poor lighting, difficult images |
| `basic` | Mechanical meters, high contrast |

## Typical Workflow

1. **Collect failed images** from `backend/static/uploads/failed/`
2. **Benchmark them**:
   ```bash
   python cli/ocr_tool.py batch-benchmark ./static/uploads/failed/ --output results.json
   ```
3. **Analyze which strategy works best**
4. **Update config** in `.env`:
   ```bash
   OCR_DEFAULT_STRATEGY=seven_segment
   OCR_CONFIDENCE_THRESHOLD=60.0
   ```
5. **Re-test** to verify improvements

## Configuration (.env)

```bash
# Default strategy
OCR_DEFAULT_STRATEGY=auto

# Minimum confidence to accept result
OCR_CONFIDENCE_THRESHOLD=50.0

# Enable fallback to other strategies
OCR_ENABLE_FALLBACK=true

# Tesseract path (if not in system PATH)
TESSERACT_PATH=/opt/homebrew/bin/tesseract
```

## Full Documentation

See [OCR_TESTING.md](OCR_TESTING.md) for complete guide including:
- All testing methods (API, CLI, Python)
- How to add custom OCR strategies
- Troubleshooting guide
- Best practices
- Detailed examples

## API Endpoints

With server running (`uvicorn main:app --reload`):

- **Test**: `POST /ocr/test`
- **Benchmark**: `POST /ocr/benchmark`
- **Strategies**: `GET /ocr/strategies`
- **Fallback**: `POST /ocr/test-with-fallback`
- **Docs**: `http://localhost:8000/docs`

## CLI Commands

```bash
# Test single image
python cli/ocr_tool.py test <image> [--strategy STRATEGY]

# Benchmark single image
python cli/ocr_tool.py benchmark <image> [--output FILE]

# Batch test folder
python cli/ocr_tool.py batch <folder> [--strategy STRATEGY] [--output FILE]

# Batch benchmark folder
python cli/ocr_tool.py batch-benchmark <folder> [--output FILE]

# Help
python cli/ocr_tool.py --help
```

## Tips

1. **Start with benchmark**: See which strategies work for your meter type
2. **Use CLI for iteration**: Faster than API for testing changes
3. **Check confidence scores**: < 50% usually means wrong reading
4. **Enable fallback**: Better chance of success in production
5. **Test on real images**: Use actual failed images from your deployment

## Need Help?

- Check [OCR_TESTING.md](OCR_TESTING.md) for detailed documentation
- Run with `--help` for command options
- Check API docs at `/docs` endpoint
- See logs for error details (`LOG_LEVEL=DEBUG`)
