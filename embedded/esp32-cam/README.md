# ESP32-CAM WattBox Meter Reader

Automated electricity meter reading module for the WattBox monitoring system using ESP32-CAM.

## Features

- 📸 Live video streaming for meter positioning
- 🔦 Flash LED control for better image capture
- 📡 Automatic image upload to WattBox backend
- ⏱️ Optional automatic capture at intervals
- 🌐 Web interface for control and monitoring

## Hardware Requirements

- ESP32-CAM board (AI Thinker model)
- ESP32-CAM-MB programmer board (or FTDI adapter)
- USB cable
- Stable power supply (5V)

## Setup Instructions

### 1. Environment Configuration

Copy the example environment file and add your credentials:

```bash
cd embedded/esp32-cam
cp .env.example .env
```

Edit `.env` with your settings:
```
WIFI_SSID=your_wifi_network
WIFI_PASSWORD=your_wifi_password
API_HOST=192.168.1.100  # Your WattBox backend IP
API_PORT=8000
DEVICE_NAME=ESP32-CAM-Meter-1
DEVICE_ID=meter_cam_001
```

**Important:** Never commit the `.env` file to Git. It's already in `.gitignore`.

### 2. Install PlatformIO

If using VS Code:
- Install the PlatformIO extension
- Open the `embedded/esp32-cam` folder

If using CLI:
```bash
pip install platformio
```

### 3. Build and Upload

Using VS Code:
- Click PlatformIO icon → Project Tasks → Upload

Using CLI:
```bash
cd embedded/esp32-cam
pio run -t upload
pio device monitor  # View serial output
```

### 4. Access the Web Interface

Once uploaded and connected to WiFi:
1. Check serial monitor for the device IP address
2. Open browser: `http://[ESP32-IP]/`
3. Use the web interface to:
   - Start/stop live stream
   - Capture and send images
   - Toggle flash LED

## API Integration

The ESP32-CAM sends captured images to your WattBox backend:
- Endpoint: `http://[API_HOST]:[API_PORT]/api/upload`
- Method: POST
- Content-Type: image/jpeg
- Headers: X-Device-ID, X-Device-Name

## Configuration Options

Edit `include/config.h` for additional settings:
- `CAPTURE_INTERVAL_MS`: Auto-capture interval (default: 60000ms)
- `AUTO_CAPTURE_ENABLED`: Enable/disable auto-capture
- `USE_FLASH_FOR_CAPTURE`: Use flash when capturing
- Camera pins and settings

## Troubleshooting

### Upload Issues
- Ensure correct USB port in `platformio.ini`
- Press RESET button during upload if needed
- Check USB cable supports data transfer

### WiFi Connection Failed
- Verify credentials in `.env`
- Check WiFi signal strength
- Ensure 2.4GHz network (ESP32 doesn't support 5GHz)

### Camera Issues
- Power cycle the ESP32-CAM
- Check camera ribbon cable connection
- Ensure adequate power supply (>500mA)

## Security Notes

- WiFi credentials are stored in `.env` file (not in source code)
- `.env` is excluded from Git via `.gitignore`
- Consider using WPA3 if your network supports it
- For production: Enable ESP32 secure boot and flash encryption

## Development

To modify the firmware:
1. Edit source files in `src/` and `include/`
2. Test locally with `pio run`
3. Upload with `pio run -t upload`
4. Monitor debug output with `pio device monitor`