# Phase 0 – Phase 4 Testing Guide 🧪

> **Historical guide:** some early endpoint examples below predate the current Gateway routes. For the current, professor-safe commands and API payloads, use [Professor Demo Guide](09-professor-demo-guide.md) as the source of truth.

This document provides step-by-step instructions, exact terminal commands (for Windows PowerShell and Linux/macOS Bash), and the **exact expected output** for validating Phases 0 through 4 of the **Home Energy Tracker** platform.

---

## 📑 Quick Navigation
1. [Phase 0: Baseline & Code Integrity Verification](#1-phase-0-baseline--code-integrity-verification)
2. [Phase 1: Containerization & Infrastructure Verification](#2-phase-1-containerization--infrastructure-verification)
3. [Phase 2: Backend API & Gateway Verification](#3-phase-2-backend-api--gateway-verification)
4. [Phase 3: Energy Intelligence & Ingestion Verification](#4-phase-3-energy-intelligence--ingestion-verification)
5. [Phase 4: Web Dashboard Verification (Frontend)](#5-phase-4-web-dashboard-verification-frontend)

---

## 1. Phase 0: Baseline & Code Integrity Verification

### Step 0.1: Environment File Verification
Copy the `.env.example` file to `.env` in the root directory.

- **PowerShell (Windows)**:
  ```powershell
  Copy-Item .env.example .env
  ```
- **Bash (Linux/macOS)**:
  ```bash
  cp .env.example .env
  ```

**Expected Output**:
*(Executes silently without errors. The `.env` file is created in the project root).*

---

### Step 0.2: Maven Unit Tests Execution
Run unit tests on the intelligence logic module (`insight-service`).

- **Command**:
  ```bash
  cd insight-service
  mvn test
  ```

**Expected Terminal Output**:
```text
[INFO] Scanning for projects...
[INFO] ------------------< com.hometracker:insight-service >-------------------
[INFO] Building 0.0.1-SNAPSHOT
[INFO] --------------------------------[ jar ]---------------------------------
[INFO] 
[INFO] --- surefire:3.5.3:test (default-test) @ insight-service ---
[INFO] Running com.hometracker.insight_service.InsightServiceApplicationTests
[INFO] Tests run: 1, Failures: 0, Errors: 0, Skipped: 0
[INFO] Running com.hometracker.insight_service.service.BillCalculationServiceTest
[INFO] Tests run: 7, Failures: 0, Errors: 0, Skipped: 0
[INFO] Running com.hometracker.insight_service.service.InsightServiceTest
[INFO] Tests run: 4, Failures: 0, Errors: 0, Skipped: 0
[INFO] 
[INFO] Results:
[INFO] 
[INFO] Tests run: 12, Failures: 0, Errors: 0, Skipped: 0
[INFO] 
[INFO] ------------------------------------------------------------------------
[INFO] BUILD SUCCESS
[INFO] ------------------------------------------------------------------------
```

---

## 2. Phase 1: Containerization & Infrastructure Verification

> **Prerequisite**: Ensure Docker Desktop (or the Docker daemon) is running.

### Step 1.1: Launch Docker Stack
Start the 12-container microservice stack in detached mode.

- **Command**:
  ```bash
  docker compose up -d
  ```

**Expected Terminal Output**:
```text
[+] Running 12/12
 ✔ Container home-energy-mysql          Started
 ✔ Container home-energy-kafka          Started
 ✔ Container home-energy-influxdb       Started
 ✔ Container home-energy-mailpit        Started
 ✔ Container home-energy-user-service   Started
 ✔ Container home-energy-device-service Started
 ✔ Container home-energy-ingestion-service Started
 ✔ Container home-energy-usage-service   Started
 ✔ Container home-energy-alert-service   Started
 ✔ Container home-energy-insight-service Started
 ✔ Container home-energy-api-gateway     Started
```

---

### Step 1.2: Check Container Status
Verify all containers are healthy and operational.

- **Command**:
  ```bash
  docker compose ps
  ```

**Expected Terminal Output**:
```text
NAME                            IMAGE                         COMMAND                  SERVICE             CREATED         STATUS                  PORTS
home-energy-api-gateway         home-energy-api-gateway       "java -jar /app/app.…"   api-gateway         2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8080->8080/tcp
home-energy-user-service        home-energy-user-service      "java -jar /app/app.…"   user-service        2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8081->8081/tcp
home-energy-device-service      home-energy-device-service    "java -jar /app/app.…"   device-service      2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8082->8082/tcp
home-energy-ingestion-service   home-energy-ingestion-service "java -jar /app/app.…"   ingestion-service   2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8083->8083/tcp
home-energy-usage-service       home-energy-usage-service     "java -jar /app/app.…"   usage-service       2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8084->8084/tcp
home-energy-alert-service       home-energy-alert-service     "java -jar /app/app.…"   alert-service       2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8085->8085/tcp
home-energy-insight-service     home-energy-insight-service   "java -jar /app/app.…"   insight-service     2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8086->8086/tcp
home-energy-mysql               mysql:8.3                     "docker-entrypoint.s…"   mysql               2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:3306->3306/tcp
home-energy-kafka               confluentinc/cp-kafka:7.6.0   "/etc/confluent/dock…"   kafka               2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:9092->9092/tcp, 0.0.0.0:9094->9094/tcp
home-energy-influxdb            influxdb:2.7                  "/entrypoint.sh infl…"   influxdb            2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:8072->8086/tcp
home-energy-mailpit             axllent/mailpit               "/mailpit"               mailpit             2 minutes ago   Up 2 minutes (healthy)   0.0.0.0:1025->1025/tcp, 0.0.0.0:8025->8025/tcp
```

---

## 3. Phase 2: Backend API & Gateway Verification

### Step 2.1: API Gateway Health Check & Correlation ID Propagation
Test API Gateway actuator endpoint and check response headers.

- **PowerShell**:
  ```powershell
  Invoke-WebRequest -Uri "http://localhost:8080/actuator/health" -Method GET | Select-Object StatusCode, Headers, Content
  ```
- **cURL (Bash)**:
  ```bash
  curl -i http://localhost:8080/actuator/health
  ```

**Expected Output**:
```http
HTTP/1.1 200 OK
Content-Type: application/vnd.spring-boot.actuator.v3+json
X-Correlation-ID: e4a7b219-91df-4b36-a511-9a74288b901f

{"status":"UP"}
```

---

### Step 2.2: User Service API via Gateway
Fetch registered users.

- **Command**:
  ```bash
  curl -i http://localhost:8080/users
  ```

**Expected Output**:
```json
HTTP/1.1 200 OK
Content-Type: application/json
X-Correlation-ID: 7b31c940-1a22-4d89-982e-9d211054ab1c

[
  {
    "id": 1,
    "name": "Sarah Miller",
    "email": "sarah.m@example.com",
    "address": "123 Green Energy Way",
    "tariffRate": 0.18
  }
]
```

---

### Step 2.3: Device Service API via Gateway
Fetch registered appliances for user `1`.

- **Command**:
  ```bash
  curl -i http://localhost:8080/devices?userId=1
  ```

**Expected Output**:
```json
HTTP/1.1 200 OK
Content-Type: application/json

[
  {
    "id": 1,
    "userId": 1,
    "deviceName": "HVAC System",
    "category": "CLIMATE",
    "powerRatingWatts": 3500.0,
    "isStandbyMonitored": true
  },
  {
    "id": 2,
    "userId": 1,
    "deviceName": "Smart Refrigerator",
    "category": "KITCHEN",
    "powerRatingWatts": 180.0,
    "isStandbyMonitored": true
  }
]
```

---

### Step 2.4: Standardized Error Handling Check
Query a non-existent user resource to verify structured exception output.

- **Command**:
  ```bash
  curl -i http://localhost:8080/users/9999
  ```

**Expected Output**:
```json
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "timestamp": "2026-09-12T02:22:00Z",
  "status": 404,
  "error": "Not Found",
  "message": "User with ID 9999 not found",
  "path": "/users/9999"
}
```

---

## 4. Phase 3: Energy Intelligence & Ingestion Verification

### Step 3.1: Ingest Smart Meter Reading (Kafka Event Dispatch)
Submit a live energy reading via the Ingestion Service gateway route.

- **PowerShell**:
  ```powershell
  Invoke-RestMethod -Uri "http://localhost:8080/ingestion/readings" -Method POST -ContentType "application/json" -Body '{"deviceId":1,"kwh":2.45,"timestamp":"2026-09-12T02:00:00Z"}'
  ```
- **cURL (Bash)**:
  ```bash
  curl -i -X POST http://localhost:8080/ingestion/readings \
    -H "Content-Type: application/json" \
    -d '{"deviceId": 1, "kwh": 2.45, "timestamp": "2026-09-12T02:00:00Z"}'
  ```

**Expected Output**:
```json
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "status": "SUCCESS",
  "message": "Energy reading ingested into Kafka topic 'energy-usage'",
  "readingId": "evt_98412389"
}
```

---

### Step 3.2: Month-End Bill Shock Forecast Endpoint
Fetch calculated 30-day bill forecast for user `1`.

- **Command**:
  ```bash
  curl -i http://localhost:8080/insight/bill-forecast/1
  ```

**Expected Output**:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "userId": 1,
  "currentMonthKwh": 412.5,
  "currentCost": 74.25,
  "projectedMonthKwh": 650.0,
  "projectedBill": 128.50,
  "tariffTier": "Tier 2 Standard",
  "currency": "USD"
}
```

---

### Step 3.3: Standby Energy Detective Endpoint
Execute the phantom load detection engine for user `1`.

- **Command**:
  ```bash
  curl -i http://localhost:8080/insight/standby-detective/1
  ```

**Expected Output**:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "userId": 1,
  "baselinePowerWatts": 145.0,
  "estimatedMonthlyWastedKwh": 104.4,
  "estimatedMonthlyWastedCost": 18.79,
  "riskLevel": "MEDIUM",
  "detectedStandbyAppliances": [
    {
      "deviceName": "Entertainment System / OLED TV",
      "estimatedStandbyWatts": 45.0
    },
    {
      "deviceName": "Desktop Gaming PC (Sleep Mode)",
      "estimatedStandbyWatts": 35.0
    }
  ],
  "recommendations": [
    "Use smart power strips to cut off idle entertainment center loads.",
    "Enable deep sleep modes on gaming desktops and monitors."
  ]
}
```

---

### Step 3.4: Appliance Consumption Ranking Endpoint
Fetch top power-consuming appliances.

- **Command**:
  ```bash
  curl -i http://localhost:8080/insight/appliance-ranking/1
  ```

**Expected Output**:
```json
HTTP/1.1 200 OK
Content-Type: application/json

{
  "userId": 1,
  "rankings": [
    {"deviceName": "HVAC System", "kwh": 280.0, "percentageOfTotal": 67.8},
    {"deviceName": "Water Heater", "kwh": 85.0, "percentageOfTotal": 20.6},
    {"deviceName": "Smart Refrigerator", "kwh": 47.5, "percentageOfTotal": 11.5}
  ]
}
```

---

## 5. Phase 4: Web Dashboard Verification (Frontend)

### Step 4.1: Production Build Test
Verify clean TypeScript compilation and bundle packaging.

- **Command**:
  ```bash
  cd frontend
  npm run build
  ```

**Expected Terminal Output**:
```text
> frontend@0.0.0 build
> tsc -b && vite build

vite v5.4.2 building for production...
transforming...
✓ 48 modules transformed.
dist/index.html                  0.48 kB │ gzip:  0.31 kB
dist/assets/index-D8x2nK_a.css  14.22 kB │ gzip:  3.65 kB
dist/assets/index-Bq8sL1_x.js  245.81 kB │ gzip: 78.43 kB
✓ built in 1.42s
```

---

### Step 4.2: Start Frontend Development Server
Run the UI locally connected to the API Gateway (`http://localhost:8080`).

- **Command**:
  ```bash
  npm run dev
  ```

**Expected Terminal Output**:
```text
  VITE v5.4.2  ready in 280 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```

---

### Step 4.3: Manual UI Verification Checklist
Open **`http://localhost:5173`** in your browser and check the following elements:

| UI Component | Verification Checklist | Expected Behavior |
| :--- | :--- | :--- |
| **User Switcher** | Header dropdown | Toggles active user context between "Sarah Miller" and other profiles |
| **Summary Cards** | Top stats row | Displays Total kWh, Current Bill, Forecasted Bill, and Top Device |
| **Standby Detective** | Standby card | Displays baseline power (e.g. `145 W`), monthly phantom cost, and Risk Badge (`MEDIUM`) |
| **Usage Charts** | Recharts area chart | Renders 7-day kWh consumption trends and appliance breakdown bar chart |
| **Reading Simulator** | Simulator widget | Submitting a reading triggers a live POST to ingestion service with a success toast notification |
| **Device Manager** | Appliances tab | Displays registered devices, power ratings (W), and allows adding new appliances |

---

## 💡 Troubleshooting Notes

1. **Docker Daemon Connection Error**:
   If `docker compose up` fails with `failed to connect to the docker API`, open **Docker Desktop** on Windows/macOS and ensure the engine is fully started.

2. **Port Conflicts**:
   If ports `8080` or `3306` are in use, identify the conflicting process with:
   - PowerShell: `Get-NetTCPConnection -LocalPort 8080`
   - Linux: `sudo lsof -i :8080`

3. **Running Without Docker**:
   If running individual Spring Boot microservices locally without Docker containers, navigate into any service folder (e.g., `cd user-service`) and execute:
   ```bash
   mvn spring-boot:run
   ```
