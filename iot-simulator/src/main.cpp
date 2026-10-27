#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <Wire.h>
#include <time.h>

#include "config.h"

#ifndef HOME_ENERGY_INGESTION_DEVICE_TOKEN
#define HOME_ENERGY_INGESTION_DEVICE_TOKEN ""
#endif

namespace {

constexpr int kPotPin = 34;
constexpr int kOledSdaPin = 21;
constexpr int kOledSclPin = 22;
constexpr int kEcoButtonPin = 25;    // top button
constexpr int kHeavyButtonPin = 26;  // middle button
constexpr int kAlertButtonPin = 27;  // bottom button

constexpr unsigned long kPostIntervalMs = 8000;
constexpr unsigned long kDisplayIntervalMs = 200;
constexpr unsigned long kWifiRetryIntervalMs = 10000;

Adafruit_SSD1306 display(128, 64, &Wire, -1);
// WiFiClientSecure secureClient;
WiFiClient apiClient;

enum class MeterMode { Eco, Heavy, AlertTest };

MeterMode currentMode = MeterMode::Eco;
float currentEnergyKwh = 0.0F;
String apiStatus = "Starting...";

unsigned long lastPostAt = 0;
unsigned long lastDisplayAt = 0;
unsigned long lastWifiAttemptAt = 0;

int lastEcoState = HIGH;
int lastHeavyState = HIGH;
int lastAlertState = HIGH;

const char* modeName() {
  switch (currentMode) {
    case MeterMode::Eco:
      return "ECO";
    case MeterMode::Heavy:
      return "HEAVY";
    case MeterMode::AlertTest:
      return "ALERT TEST";
  }

  return "UNKNOWN";
}

float simulatedEnergyKwh() {
  const float dial = static_cast<float>(analogRead(kPotPin)) / 4095.0F;

  switch (currentMode) {
    case MeterMode::Eco:
      return 1.0F + (dial * 5.0F);
    case MeterMode::Heavy:
      return 8.0F + (dial * 12.0F);
    case MeterMode::AlertTest:
      // User 1 has a 25 kWh alert threshold in the demo database.
      return 26.0F + (dial * 14.0F);
  }

  return 0.0F;
}

String fallbackTimestamp() {
  // Keeps the ingestion payload valid if NTP has not synchronized yet.
  const unsigned long elapsedSeconds = millis() / 1000UL;
  const unsigned long hours = (elapsedSeconds / 3600UL) % 24UL;
  const unsigned long minutes = (elapsedSeconds / 60UL) % 60UL;
  const unsigned long seconds = elapsedSeconds % 60UL;

  char timestamp[25];
  snprintf(timestamp, sizeof(timestamp), "2026-09-25T%02lu:%02lu:%02luZ",
           hours, minutes, seconds);
  return String(timestamp);
}

String utcTimestamp() {
  struct tm timeInfo {};

  if (!getLocalTime(&timeInfo, 1000)) {
    return fallbackTimestamp();
  }

  char timestamp[25];
  strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeInfo);
  return String(timestamp);
}

void connectToWiFi() {
  lastWifiAttemptAt = millis();

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wokwi WiFi");

  for (int attempt = 0; attempt < 30 && WiFi.status() != WL_CONNECTED;
       ++attempt) {
    delay(500);
    Serial.print('.');
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected: ");
    Serial.println(WiFi.localIP());
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    apiStatus = "WiFi connected";
  } else {
    apiStatus = "WiFi unavailable";
    Serial.println(apiStatus);
  }
}

void sendReading() {
  if (WiFi.status() != WL_CONNECTED) {
    apiStatus = "WiFi disconnected";
    return;
  }

  currentEnergyKwh = simulatedEnergyKwh();
  const String payload = String("{\"deviceId\":") + String(DEVICE_ID) +
                         ",\"energyConsumed\":" +
                         String(currentEnergyKwh, 2) +
                         ",\"timestamp\":\"" + utcTimestamp() + "\"}";

  HTTPClient http;
  if (!http.begin(apiClient, INGESTION_URL)) {
    apiStatus = "HTTP init failed";
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Token", HOME_ENERGY_INGESTION_DEVICE_TOKEN);
  const int responseCode = http.POST(payload);

  if (responseCode > 0) {
    apiStatus = "API: " + String(responseCode);
    Serial.println(payload);
    Serial.println(http.getString());
  } else {
    apiStatus = "API error: " + String(responseCode);
    Serial.println(apiStatus);
  }

  http.end();
}

void updateModeFromButtons() {
  const int ecoState = digitalRead(kEcoButtonPin);
  const int heavyState = digitalRead(kHeavyButtonPin);
  const int alertState = digitalRead(kAlertButtonPin);

  if (lastEcoState == HIGH && ecoState == LOW) {
    currentMode = MeterMode::Eco;
    lastPostAt = millis() - kPostIntervalMs;
  }

  if (lastHeavyState == HIGH && heavyState == LOW) {
    currentMode = MeterMode::Heavy;
    lastPostAt = millis() - kPostIntervalMs;
  }

  if (lastAlertState == HIGH && alertState == LOW) {
    currentMode = MeterMode::AlertTest;
    lastPostAt = millis() - kPostIntervalMs;
  }

  lastEcoState = ecoState;
  lastHeavyState = heavyState;
  lastAlertState = alertState;
}

void drawDashboard() {
  currentEnergyKwh = simulatedEnergyKwh();

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  display.setCursor(0, 0);
  display.println("HOME ENERGY TRACKER");

  display.setCursor(0, 16);
  display.print("Mode: ");
  display.println(modeName());

  display.setCursor(0, 30);
  display.print("Energy: ");
  display.print(currentEnergyKwh, 2);
  display.println(" kWh");

  display.setCursor(0, 44);
  display.println(apiStatus);

  if (currentMode == MeterMode::AlertTest) {
    display.setCursor(0, 56);
    display.println("Above 25 kWh threshold");
  }

  display.display();
}

}  // namespace

void setup() {
  Serial.begin(115200);

  pinMode(kEcoButtonPin, INPUT_PULLUP);
  pinMode(kHeavyButtonPin, INPUT_PULLUP);
  pinMode(kAlertButtonPin, INPUT_PULLUP);

  Wire.begin(kOledSdaPin, kOledSclPin);
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 OLED not found");
    while (true) {
      delay(100);
    }
  }

  // secureClient.setInsecure();  // Demo-only: Cloudflare Quick Tunnel uses HTTPS.
  connectToWiFi();
  drawDashboard();
}

void loop() {
  updateModeFromButtons();

  const unsigned long now = millis();

  if (WiFi.status() != WL_CONNECTED &&
      now - lastWifiAttemptAt >= kWifiRetryIntervalMs) {
    connectToWiFi();
  }

  if (now - lastPostAt >= kPostIntervalMs) {
    lastPostAt = now;
    sendReading();
  }

  if (now - lastDisplayAt >= kDisplayIntervalMs) {
    lastDisplayAt = now;
    drawDashboard();
  }

  delay(20);
}
