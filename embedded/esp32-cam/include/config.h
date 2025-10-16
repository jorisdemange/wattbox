#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration - Set these in your .env file (copy .env.example)
// These will be injected at build time from environment variables
#ifdef WIFI_SSID_ENV
const char* WIFI_SSID = WIFI_SSID_ENV;
#else
const char* WIFI_SSID = "Hide yo Kids, Hide yo WiFi";  // Fallback value
#endif

#ifdef WIFI_PASSWORD_ENV
const char* WIFI_PASSWORD = WIFI_PASSWORD_ENV;
#else
const char* WIFI_PASSWORD = "0ui0ui0ui";  // Fallback value
#endif

// Camera Web Server Configuration
const int WEB_SERVER_PORT = 80;                  // Port for web interface
const int STREAM_SERVER_PORT = 81;               // Port for video streaming

// WattBox Backend API Configuration
#ifdef API_HOST_ENV
const char* API_HOST = API_HOST_ENV;
#else
const char* API_HOST = "192.168.10.17";          // Fallback value - Your Mac's IP
#endif

#ifdef API_PORT_ENV
const int API_PORT = API_PORT_ENV;
#else
const int API_PORT = 8000;                       // Fallback value
#endif

const char* API_ENDPOINT = "/api/upload";        // Upload endpoint

// Camera Settings
const int CAPTURE_INTERVAL_MS = 60000;           // Capture image every 60 seconds
const bool AUTO_CAPTURE_ENABLED = false;         // Set to true to enable automatic capture

// Device Configuration
#ifdef DEVICE_NAME_ENV
const char* DEVICE_NAME = DEVICE_NAME_ENV;
#else
const char* DEVICE_NAME = "ESP32-CAM-Meter-1";   // Fallback value
#endif

#ifdef DEVICE_ID_ENV
const char* DEVICE_ID = DEVICE_ID_ENV;
#else
const char* DEVICE_ID = "meter_cam_001";         // Fallback value
#endif

// LED Flash Configuration
const int FLASH_LED_PIN = 4;                     // GPIO4 controls the bright LED
const bool USE_FLASH_FOR_CAPTURE = true;         // Use flash when capturing

// Debug Configuration
const bool SERIAL_DEBUG = true;                  // Enable serial debugging output
const int SERIAL_BAUD_RATE = 115200;            // Serial communication speed

// Camera Model (AI-Thinker ESP32-CAM) - Already defined in platformio.ini
// #define CAMERA_MODEL_AI_THINKER

// Pin definitions for AI-Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27

#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#endif // CONFIG_H