# 📦 WattBox – Electricity Monitoring App Spec

This spec defines a flexible, modern, self-hostable full stack web application called **WattBox** that receives and processes electricity meter photos from an ESP32-CAM or manual uploads, extracts readings using OCR, and displays electricity usage and cost data over time.

---

## ✅ Project Goals

- Collect images from ESP32-CAM and optional manual uploads (iPhone/web form)
- Extract electricity reading via OCR
- Store raw images and readings with timestamps
- Display dashboard with usage trends, cost, and device health
- Flexible deployment: run on Raspberry Pi or AWS (via Docker)
- Clean, modern UI using Vue 3 and shadcn-vue components

---

## 🧱 Backend Architecture

### Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: SQLite (dev/local) or PostgreSQL (prod)
- **OCR**: Tesseract (via `pytesseract`)
- **Image storage**: Local file system or S3-compatible bucket
- **Containerization**: Docker + docker-compose

### Directory Structure

```
/backend
├── api/
│   ├── upload.py
│   ├── readings.py
│   └── devices.py
├── services/
│   ├── ocr.py
│   ├── storage.py
│   ├── validation.py
│   └── pricing.py
├── models/
│   ├── reading.py
│   └── device.py
├── db/
│   ├── models.py
│   └── crud.py
├── static/uploads/
│   ├── raw/
│   ├── processed/
│   └── failed/
├── templates/
│   └── index.html
├── main.py
├── config.py
└── Dockerfile + docker-compose.yml
```

### API Endpoints

#### Upload

- `POST /upload/device` – image from ESP32

  - Params: `device_id`, optional metadata (battery %, timestamp)
  - Body: `multipart/form-data` with image file

- `POST /upload/manual` – upload from web/iPhone

  - Body: image file + optional manual kWh input

#### Readings

- `GET /readings` – all readings with filters (date range, device)
- `GET /readings/last` – latest reading per device

#### Images

- `GET /images/:path` – serve raw or processed image

#### Devices

- `GET /devices` – list of known devices, last ping, battery level

### Data Model (Reading)

```json
{
  "timestamp": "2025-07-10T08:00:00Z",
  "reading_kwh": 1453.72,
  "photo_path": "/uploads/raw/esp1/2025-07-10.jpg",
  "source": "device" | "manual",
  "device_id": "esp1",
  "battery_percent": 76,
  "ocr_confidence": 93.4,
  "price_per_kwh": 0.42
}
```

---

## 🌐 Frontend Architecture

### Stack

- **Framework**: Vue 3 (Vite, Composition API)
- **UI Library**: shadcn-vue
- **Styling**: Tailwind CSS (default in shadcn-vue)
- **Routing**: Vue Router
- **Charts**: shadcn-vue Charts (built-in)

### Directory Structure

```
/frontend
├── components/
├── views/
│   ├── Dashboard.vue
│   ├── Upload.vue
│   ├── History.vue
│   └── Devices.vue
├── composables/
│   ├── useReadings.ts
│   ├── useUpload.ts
│   └── useDevices.ts
├── assets/
├── router/
│   └── index.ts
├── App.vue
└── main.ts
```

### Views

#### Dashboard.vue

- Line chart showing kWh over time
- Daily cost summary (based on price/kWh)
- Last reading card
- Total monthly estimate

#### Upload.vue

- Manual upload form (image + optional kWh override)
- View uploaded image and confirmation status

#### History.vue

- List of past readings with thumbnails
- Click to view photo + extracted data

#### Devices.vue

- List of ESP32 devices
- Last check-in timestamp
- Battery percentage
- Status indicators (OK, offline, low battery)

---

## 📦 Docker Deployment

- `docker-compose.yml` with:

  - app service
  - db service (sqlite/postgres)
  - optional nginx reverse proxy

- Mount volumes for uploaded images

- Use `.env` to configure:

  - DB string
  - Upload directory
  - Electricity price per kWh

---

## 🔐 Security Notes

- Allowlist device IDs for uploads
- Rate limit `/upload` endpoints
- Optional auth for manual uploads
- Store images in non-public directory with signed URL access only

---

## 📈 Suggestions for Enhancements

- Set daily email or Telegram summary
- Add camera-side status ping (battery, uptime)
- Detect abnormal jumps in consumption
- Send alerts when consumption crosses thresholds
- Auto-rotate image if upside down
- Add “re-OCR” option from history view

---

## ✅ Next Steps

- Start with local SQLite and file storage
- Once stable, move backend to AWS or RPi
- Connect ESP32 to `/upload/device`
- Build Shortcut for iPhone upload
- Expand dashboard with charts and real-time device status

