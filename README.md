# ⚡ WattBox - Electricity Monitoring System

WattBox is a modern, self-hostable web application for monitoring electricity usage through automated meter reading. It accepts photos from ESP32-CAM devices or manual uploads, extracts readings using OCR, and provides comprehensive analytics and cost tracking.

## 🌟 Features

- **Automated Meter Reading**: OCR-powered extraction of electricity readings from photos
- **Multiple Input Sources**: Support for ESP32-CAM devices and manual uploads
- **Real-time Dashboard**: View current usage, trends, and cost estimates
- **Device Management**: Monitor multiple meters and device health
- **Historical Data**: Browse and analyze past readings
- **Cost Tracking**: Automatic cost calculation based on configurable rates
- **Modern UI**: Clean, responsive interface built with Vue 3 and shadcn-vue
- **Docker Ready**: Easy deployment with Docker Compose

## 📸 Screenshots

### Dashboard
The main dashboard displays current readings, daily averages, monthly estimates, and usage trends.

### Upload
Manual upload interface with drag-and-drop support and optional manual reading input.

### History
Browse all historical readings with filtering by device and date range.

### Devices
Manage and monitor connected ESP32-CAM devices and their health status.

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **SQLite** (development) or **PostgreSQL** (production)
- **Tesseract OCR** for reading extraction
- **SQLAlchemy** for database ORM
- Optional **S3** support for image storage

### Frontend
- **Vue 3** with Composition API
- **TypeScript** for type safety
- **shadcn-vue** UI components
- **Tailwind CSS** for styling
- **Chart.js** for data visualization
- **Axios** for API communication

## 🚀 Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wattbox.git
cd wattbox
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start with Docker Compose:
```bash
# Development mode (with hot reload)
docker-compose -f docker-compose.dev.yml up

# Production mode
docker-compose up -d

# If port 5173 is already in use, the frontend will be available on port 5174
# You can also customize ports using environment variables:
FRONTEND_PORT=5175 BACKEND_PORT=8001 docker-compose -f docker-compose.dev.yml up
```

4. Access the application:
- Frontend: http://localhost (production) or http://localhost:5174 (development)
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

**Note:** If you get a port conflict error, the development frontend is configured to use port 5174 by default to avoid conflicts with other Vite apps.

### Manual Installation

#### Backend Setup

1. Install system dependencies:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract
```

2. Create Python virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run the backend:
```bash
uvicorn main:app --reload
```

#### Frontend Setup

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure environment:
```bash
cp .env.example .env
# Set VITE_API_BASE_URL if needed
```

3. Run development server:
```bash
npm run dev
```

## 📱 ESP32-CAM Integration

Configure your ESP32-CAM to send images to the `/upload/device` endpoint:

```cpp
// Example ESP32 code snippet
String serverUrl = "http://your-server:8000/upload/device";
String deviceId = "esp1";

// POST multipart/form-data with:
// - device_id: Your device identifier
// - file: The captured image
// - battery_percent: Current battery level (optional)
```

## 🔧 Configuration

### Environment Variables

#### Backend
- `DATABASE_URL`: Database connection string
- `UPLOAD_DIRECTORY`: Local directory for image storage
- `TESSERACT_PATH`: Path to Tesseract executable
- `PRICE_PER_KWH`: Electricity price per kWh
- `ALLOWED_DEVICE_IDS`: Comma-separated list of allowed device IDs

#### Frontend
- `VITE_API_BASE_URL`: Backend API URL

### Pricing Configuration

Electricity pricing can be configured in the backend:
- Base price per kWh
- Time-of-use rates (optional)
- Tiered pricing (optional)

## 📊 API Documentation

The backend provides a RESTful API with automatic documentation available at `/docs`.

### Key Endpoints

- `POST /upload/device`: Upload from ESP32-CAM
- `POST /upload/manual`: Manual upload
- `GET /readings`: List all readings
- `GET /readings/last`: Get latest reading
- `GET /readings/daily`: Daily usage statistics
- `GET /devices`: List all devices
- `GET /devices/{id}/health`: Device health report

## 🐳 Deployment

### Docker Deployment

1. Build and start services:
```bash
docker-compose up -d
```

2. View logs:
```bash
docker-compose logs -f
```

3. Stop services:
```bash
docker-compose down
```

### Raspberry Pi Deployment

WattBox is optimized for running on Raspberry Pi:

1. Install Docker and Docker Compose
2. Use the ARM-compatible base images
3. Consider using external storage for images
4. Configure lower memory limits if needed

### Cloud Deployment

For AWS deployment:
1. Use PostgreSQL RDS for the database
2. Configure S3 for image storage
3. Deploy with ECS or EC2
4. Use CloudFront for frontend distribution

## 🧪 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm run test:unit
```

### Code Style

- Backend: Follow PEP 8
- Frontend: ESLint with Vue recommended rules

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Tesseract OCR for text extraction
- Vue.js team for the excellent framework
- shadcn-vue for beautiful UI components

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/wattbox/issues)
- Documentation: Check the `/docs` endpoint for API details

---

Built with ❤️ for efficient electricity monitoring