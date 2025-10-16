#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <esp_camera.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

WebServer server(WEB_SERVER_PORT);

// HTML page for web interface
const char index_html[] PROGMEM = R"rawliteral(
<!DOCTYPE HTML>
<html>
<head>
    <title>ESP32-CAM WattBox Meter Reader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; text-align: center; margin: 0; padding: 20px; background: #f4f4f4; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        img { max-width: 100%; height: auto; border: 2px solid #ddd; border-radius: 5px; }
        button { background-color: #4CAF50; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; margin: 10px; }
        button:hover { background-color: #45a049; }
        .status { margin: 20px 0; padding: 10px; background: #e8f5e9; border-radius: 5px; }
        .error { background: #ffebee; color: #c62828; }
        .success { background: #e8f5e9; color: #2e7d32; }
    </style>
</head>
<body>
    <div class="container">
        <h1>WattBox ESP32-CAM Meter Reader</h1>
        <p>Device: <strong>%DEVICE_NAME%</strong></p>
        <div id="status" class="status">Ready</div>
        
        <h2>Live Stream</h2>
        <img src="" id="stream">
        
        <div>
            <button onclick="startStream()">Start Stream</button>
            <button onclick="stopStream()">Stop Stream</button>
            <button onclick="captureImage()">Capture & Send</button>
            <button onclick="toggleFlash()">Toggle Flash</button>
        </div>
        
        <h3>Captured Image</h3>
        <img src="" id="captured" style="display:none;">
    </div>
    
    <script>
        const streamUrl = window.location.hostname;
        
        function startStream() {
            document.getElementById('stream').src = '/stream';
            updateStatus('Streaming...', 'success');
        }
        
        function stopStream() {
            document.getElementById('stream').src = '';
            updateStatus('Stream stopped', '');
        }
        
        function captureImage() {
            updateStatus('Capturing image...', '');
            fetch('/capture')
                .then(response => response.blob())
                .then(blob => {
                    const url = URL.createObjectURL(blob);
                    document.getElementById('captured').src = url;
                    document.getElementById('captured').style.display = 'block';
                    updateStatus('Image captured! Sending to backend...', 'success');
                    sendToBackend();
                })
                .catch(err => updateStatus('Capture failed: ' + err, 'error'));
        }
        
        function sendToBackend() {
            fetch('/send_to_api')
                .then(response => response.json())
                .then(data => {
                    if(data.success) {
                        updateStatus('Image sent to backend successfully!', 'success');
                    } else {
                        updateStatus('Failed to send: ' + data.error, 'error');
                    }
                })
                .catch(err => updateStatus('API error: ' + err, 'error'));
        }
        
        function toggleFlash() {
            fetch('/flash')
                .then(response => response.text())
                .then(state => updateStatus('Flash: ' + state, ''));
        }
        
        function updateStatus(message, type) {
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + type;
        }
    </script>
</body>
</html>
)rawliteral";

camera_fb_t * captured_fb = NULL;
bool flashState = false;

// Initialize camera with AI-Thinker ESP32-CAM settings
bool initCamera() {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_UXGA;  // 1600x1200 for high quality capture
    config.jpeg_quality = 10;
    config.fb_count = 2;

    // Camera init
    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        Serial.printf("Camera init failed with error 0x%x\n", err);
        return false;
    }

    // Adjust camera settings for indoor meter reading with low light
    sensor_t * s = esp_camera_sensor_get();
    s->set_brightness(s, 1);      // -2 to 2 (increased for indoor)
    s->set_contrast(s, 0);        // -2 to 2
    s->set_saturation(s, 0);      // -2 to 2
    s->set_special_effect(s, 0);  // 0 to 6 (0 - No Effect)
    s->set_whitebal(s, 1);        // 0 = disable , 1 = enable
    s->set_awb_gain(s, 1);        // 0 = disable , 1 = enable
    s->set_wb_mode(s, 0);         // 0 to 4 - if awb_gain enabled (0 - Auto)
    s->set_exposure_ctrl(s, 1);   // 0 = disable , 1 = enable
    s->set_aec2(s, 1);            // 0 = disable , 1 = enable
    s->set_ae_level(s, 1);        // -2 to 2 (increased exposure compensation)
    s->set_aec_value(s, 1000);    // 0 to 1200 (MUCH higher for indoor lighting)
    s->set_gain_ctrl(s, 1);       // 0 = disable , 1 = enable
    s->set_agc_gain(s, 10);       // 0 to 30 (increased sensor gain)
    s->set_gainceiling(s, (gainceiling_t)4);  // 0 to 6 (higher gain ceiling)
    s->set_bpc(s, 0);             // 0 = disable , 1 = enable
    s->set_wpc(s, 1);             // 0 = disable , 1 = enable
    s->set_raw_gma(s, 1);         // 0 = disable , 1 = enable
    s->set_lenc(s, 1);            // 0 = disable , 1 = enable
    s->set_hmirror(s, 1);         // 1 = enable horizontal mirror (fix flip)
    s->set_vflip(s, 0);           // 0 = disable , 1 = enable
    s->set_dcw(s, 1);             // 0 = disable , 1 = enable
    s->set_colorbar(s, 0);        // 0 = disable , 1 = enable

    return true;
}

// Connect to WiFi network
void connectWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);
    
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nWiFi Connected!");
        Serial.print("IP Address: ");
        Serial.println(WiFi.localIP());
        Serial.print("Camera Ready! Use 'http://");
        Serial.print(WiFi.localIP());
        Serial.println("' to connect");
    } else {
        Serial.println("\nWiFi Connection Failed!");
    }
}

// Handle root page request
void handleRoot() {
    String html = String(index_html);
    html.replace("%DEVICE_NAME%", DEVICE_NAME);
    server.send(200, "text/html", html);
}

// Handle image capture
void handleCapture() {
    // Release previous frame buffer if exists
    if (captured_fb) {
        esp_camera_fb_return(captured_fb);
        captured_fb = NULL;
    }

    // Turn flash ON
    if (USE_FLASH_FOR_CAPTURE) {
        digitalWrite(FLASH_LED_PIN, HIGH);
    }

    // Capture 3 warmup frames - let auto-exposure adjust to flash
    for(int i = 0; i < 3; i++) {
        camera_fb_t *warmup = esp_camera_fb_get();
        if (warmup) {
            esp_camera_fb_return(warmup);
        }
        delay(50);  // Small delay between frames
    }

    // NOW capture the real frame with adjusted exposure
    captured_fb = esp_camera_fb_get();

    // Turn flash OFF
    if (USE_FLASH_FOR_CAPTURE) {
        digitalWrite(FLASH_LED_PIN, LOW);
    }

    if (!captured_fb) {
        Serial.println("Camera capture failed");
        server.send(500, "text/plain", "Camera capture failed");
        return;
    }

    server.send_P(200, "image/jpeg", (const char *)captured_fb->buf, captured_fb->len);
}

// Handle flash toggle
void handleFlash() {
    flashState = !flashState;
    digitalWrite(FLASH_LED_PIN, flashState ? HIGH : LOW);
    server.send(200, "text/plain", flashState ? "ON" : "OFF");
}

// Send captured image to backend API
void handleSendToAPI() {
    JsonDocument response;
    
    if (!captured_fb) {
        response["success"] = false;
        response["error"] = "No image captured";
        String jsonStr;
        serializeJson(response, jsonStr);
        server.send(400, "application/json", jsonStr);
        return;
    }
    
    // Create HTTP client
    HTTPClient http;
    String url = String("http://") + API_HOST + ":" + String(API_PORT) + API_ENDPOINT;
    
    http.begin(url);
    http.addHeader("Content-Type", "image/jpeg");
    http.addHeader("X-Device-ID", DEVICE_ID);
    http.addHeader("X-Device-Name", DEVICE_NAME);
    
    Serial.print("Sending image to: ");
    Serial.println(url);
    
    int httpResponseCode = http.POST(captured_fb->buf, captured_fb->len);
    
    if (httpResponseCode > 0) {
        String payload = http.getString();
        Serial.print("Response: ");
        Serial.println(payload);
        
        response["success"] = true;
        response["statusCode"] = httpResponseCode;
        response["response"] = payload;
    } else {
        Serial.print("Error sending image: ");
        Serial.println(httpResponseCode);
        
        response["success"] = false;
        response["error"] = "HTTP error";
        response["code"] = httpResponseCode;
    }
    
    http.end();
    
    String jsonStr;
    serializeJson(response, jsonStr);
    server.send(200, "application/json", jsonStr);
}

// Handle stream endpoint
void handleStream() {
    WiFiClient client = server.client();
    
    String response = "HTTP/1.1 200 OK\r\n";
    response += "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
    client.print(response);
    
    Serial.println("Stream started");
    
    while (client.connected()) {
        camera_fb_t *fb = esp_camera_fb_get();
        if (!fb) {
            Serial.println("Camera capture failed during stream");
            delay(100);
            continue;
        }
        
        client.print("--frame\r\n");
        client.print("Content-Type: image/jpeg\r\n\r\n");
        
        size_t sent = 0;
        size_t chunkSize = 1024;
        while (sent < fb->len) {
            size_t toSend = min(chunkSize, fb->len - sent);
            size_t written = client.write(fb->buf + sent, toSend);
            if (written == 0) {
                break;
            }
            sent += written;
        }
        
        client.print("\r\n");
        
        esp_camera_fb_return(fb);
        
        // Small delay to control frame rate
        delay(33); // ~30 FPS
    }
    
    Serial.println("Stream stopped");
}

void setup() {
    Serial.begin(SERIAL_BAUD_RATE);
    Serial.println("\n\nWattBox ESP32-CAM Starting...");
    
    // Initialize flash LED
    pinMode(FLASH_LED_PIN, OUTPUT);
    digitalWrite(FLASH_LED_PIN, LOW);
    
    // Initialize camera
    if (!initCamera()) {
        Serial.println("Camera initialization failed!");
        while(1);
    }
    Serial.println("Camera initialized successfully");
    
    // Connect to WiFi
    connectWiFi();
    
    // Setup web server routes
    server.on("/", handleRoot);
    server.on("/capture", handleCapture);
    server.on("/flash", handleFlash);
    server.on("/send_to_api", handleSendToAPI);
    server.on("/stream", handleStream);
    
    // Start web server
    server.begin();
    Serial.println("HTTP server started on port 80");
}

void loop() {
    // Auto-reconnect WiFi if disconnected
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("WiFi disconnected, reconnecting...");
        connectWiFi();
        delay(5000); // Wait 5 seconds before next attempt
        return;
    }
    
    server.handleClient();
    
    // Auto-capture feature (if enabled)
    static unsigned long lastCapture = 0;
    if (AUTO_CAPTURE_ENABLED && (millis() - lastCapture > CAPTURE_INTERVAL_MS)) {
        Serial.println("Auto-capturing image...");
        
        if (USE_FLASH_FOR_CAPTURE) {
            digitalWrite(FLASH_LED_PIN, HIGH);
            delay(100);
        }
        
        if (captured_fb) {
            esp_camera_fb_return(captured_fb);
        }
        captured_fb = esp_camera_fb_get();
        
        if (USE_FLASH_FOR_CAPTURE) {
            digitalWrite(FLASH_LED_PIN, LOW);
        }
        
        if (captured_fb) {
            Serial.println("Auto-capture successful");
            // You can add automatic upload to API here
        }
        
        lastCapture = millis();
    }
    
    delay(10);
}