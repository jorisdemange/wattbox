# ESP32-CAM API

## Quick Start
ESP32-CAM captures meter readings and sends them to your backend.

## Backend Requirements
Create endpoint: `POST http://YOUR_SERVER:8000/api/upload`

Receives:
- **Body**: JPEG image (binary)
- **Headers**:
  - `Content-Type: image/jpeg`
  - `X-Device-ID: meter_cam_001`
  - `X-Device-Name: ESP32-CAM-Meter-1`

Example backend (Python/FastAPI):
```python
@app.post("/api/upload")
async def upload_image(
    request: Request,
    device_id: str = Header(alias="X-Device-ID"),
    device_name: str = Header(alias="X-Device-Name")
):
    image_data = await request.body()
    # Process image (OCR, save, etc.)
    return {"status": "received", "device": device_id}
```

## ESP32 Endpoints

### Web UI
`http://ESP32_IP/` - Control interface

### Direct API
- `GET /capture` - Take photo with flash, returns JPEG
- `GET /send_to_api` - Send last photo to backend
- `GET /flash` - Toggle LED

## Configuration
Edit `.env` file:
```
WIFI_SSID=YourWiFi
WIFI_PASSWORD=YourPassword
API_HOST=192.168.1.100
API_PORT=8000
DEVICE_ID=meter_cam_001
```

## Workflow Integration
```javascript
// Take photo and send to backend
fetch('http://ESP32_IP/capture')
  .then(() => fetch('http://ESP32_IP/send_to_api'))
  .then(r => r.json())
  .then(result => console.log('Photo sent:', result))
```