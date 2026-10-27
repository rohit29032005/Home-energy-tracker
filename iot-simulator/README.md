# Home Energy Tracker — Local Wokwi Simulator

This folder is deliberately separate from the Java microservices. Open **this folder only** in VS Code.

## What it simulates

- Potentiometer: simulated household energy consumption.
- Top button: Eco mode (`1–6 kWh`).
- Middle button: Heavy mode (`8–20 kWh`).
- Bottom button: Alert-test mode (`26–40 kWh`), above the demo user's `25 kWh` threshold.
- OLED: mode, reading, Wi-Fi/API status.
- ESP32: posts a reading every eight seconds to `POST /api/v1/ingestion`.

## One-time setup

1. Install the VS Code extensions **PlatformIO IDE** and **Wokwi Simulator**.
2. In VS Code, open this `iot-simulator` folder.
3. Request your Wokwi 30-day license: `F1` → `Wokwi: Request a new License`.
   Complete the sign-in and **Get Your License** steps yourself in the browser.
4. Keep the backend/API Gateway running on port `8080`.
5. For the VS Code Wokwi Simulator, use `http://host.wokwi.internal:8080/api/v1/ingestion` in the local `include/config.h`. This lets the virtual ESP32 reach the local API Gateway directly; a Cloudflare tunnel is not required.

## Run it

1. Use PlatformIO: `F1` → `PlatformIO: Build`.
   The first build downloads the ESP32 framework and libraries, so it can take a few minutes.
2. After a successful build, run `F1` → `Wokwi: Start Simulator`.
3. Open the Serial Monitor if you want to see each JSON payload and API response.

`201` on the OLED or Serial Monitor means the Home Energy Tracker accepted the reading.

## Notes

- `include/config.h` is ignored by Git because it is local simulator configuration. It also holds the device ID selected for the demo household.
- The VS Code Wokwi simulator uses `host.wokwi.internal` to reach the local backend. Do not use `localhost` from inside the virtual ESP32.
- The RGB LED is intentionally not used until a dedicated current-limiting resistor is added.
