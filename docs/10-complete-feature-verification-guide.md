# Home Energy Tracker — Complete Feature Verification Guide

This is the complete Windows PowerShell verification document for the project. Use it before a viva, professor demo, deployment rehearsal, or code review.

It contains the commands to start the application, verify every live API and UI feature, inspect Kafka/InfluxDB/Mailpit, test errors, and shut down safely.

For a shorter speaking script, see [Professor Demo Guide](09-professor-demo-guide.md).

---

## 1. What counts as real proof

| Area | Feature | Strong proof |
| --- | --- | --- |
| Frontend | Dashboard, household switching, devices, simulator, alerts | Browser UI plus a successful API request |
| Gateway | One public entry point | A request through port 3000 reaches the Gateway on port 8080 |
| MySQL | Users, devices, alert history | Create, re-read, update, and delete records |
| Kafka | Event-driven ingestion | Energy event visible in Kafka after POST ingestion |
| InfluxDB | Timestamped readings | Usage/insight response changes and point is visible in InfluxDB |
| Insights | Forecast, ranking, standby detective, saving tips | JSON response from each Insight endpoint |
| Email | Local alert delivery | Saved alert plus a Mailpit inbox message |
| Quality | Build, lint, Java test, Compose validation | Successful command exit code |

### Very important honesty rule

The frontend includes deliberate local fallback data only when the explicit
offline-preview setting `VITE_AUTH_ENABLED=false` is used. In its normal,
secure-by-default mode, protected API failures are not silently represented as
live data. Therefore a screen alone is still not enough evidence.

Call a feature live verified only when you can show at least one of:

- HTTP 200, 201, or 204 from the Gateway;
- an UP health response;
- a Kafka, InfluxDB, or Mailpit artifact;
- a persisted record returned after a write.

Two current UI elements are visual presentation only:

- the Gateway status badge in the header is static and is not a health check;
- the current 7-day usage chart is illustrative browser-generated data, not a historical backend chart.

For live time-series evidence, use the Usage, Bill Forecast, Appliance Ranking, and Standby Detective endpoints below.

---

## 2. Prerequisites and safety

### 2.1 Open the project

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker'
docker version
node --version
npm --version
~~~

Expected:

- Docker shows both Client and Server information.
- Node and npm print version numbers.

If Docker does not show a Server section, open Docker Desktop and wait until it says Engine running.

### 2.2 Create a local environment file once

~~~powershell
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
}
~~~

Do not show .env values in a screen recording or presentation. It contains local development credentials and tokens.

### 2.3 Select one frontend mode

Only one process may own port 3000.

| Mode | Use it when | Start it with |
| --- | --- | --- |
| Vite development mode — recommended | Editing React code or showing proxy behavior | Run npm run dev inside frontend |
| Docker/Nginx mode | Testing the production-style frontend container | Start the Compose frontend service |

Do not run Vite and the Docker frontend at the same time.

### 2.4 Test-data safety

Most checks below are read-only. The following checks write local demo data:

- CRUD creates a temporary household and appliance, then removes both;
- ingestion stores a small energy reading;
- direct alert testing stores alert rows and a Mailpit email;
- automatic threshold testing can create repeated alerts while the one-hour total remains above the configured threshold.

Never use the destructive reset command in Section 16 unless you intentionally want to delete MySQL, Kafka, and InfluxDB local data.

---

## 3. Start the system in development mode

### 3.1 Start the backend

Leave the Docker frontend stopped because Vite will use port 3000.

~~~powershell
$backendServices = @(
  'mysql', 'kafka', 'kafka-ui', 'influxdb', 'mailpit', 'keycloak',
  'user-service', 'device-service', 'ingestion-service',
  'usage-service', 'alert-service', 'insight-service', 'api-gateway'
)

docker compose up -d --build $backendServices
docker compose ps
~~~

Expected: all listed containers are running. The first cold startup may take 2–4 minutes.

Do not use only container status as proof. Spring Boot containers can be running while they are still initializing.

### 3.2 Wait for the API Gateway

~~~powershell
$gatewayHealth = 'http://localhost:8080/actuator/health'
$gatewayReply = $null
$deadline = (Get-Date).AddMinutes(5)

do {
  try {
    $gatewayReply = Invoke-RestMethod -Uri $gatewayHealth -TimeoutSec 10
    if ($gatewayReply.status -eq 'UP') {
      Write-Host 'API Gateway is ready.' -ForegroundColor Green
      break
    }
  } catch {
    Write-Host 'Waiting for API Gateway...' -ForegroundColor Yellow
  }
  Start-Sleep -Seconds 5
} while ((Get-Date) -lt $deadline)

if ($null -eq $gatewayReply -or $gatewayReply.status -ne 'UP') {
  throw 'Gateway did not become healthy in five minutes. Check the logs.'
}
~~~

Expected:

~~~text
API Gateway is ready.
~~~

If it fails:

~~~powershell
docker compose logs --tail=100 api-gateway
docker compose logs --tail=100 user-service device-service ingestion-service usage-service alert-service insight-service
~~~

Wait until the Gateway log contains a line similar to Netty started on port 8080 or Started ApiGatewayApplication.

### 3.3 Start Vite in a second terminal

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker/frontend'
npm install
npm run dev
~~~

Expected:

~~~text
VITE ... ready
Local: http://localhost:3000/
~~~

Open [http://localhost:3000](http://localhost:3000), then press Ctrl+Shift+R once.

### 3.4 Obtain short-lived local development tokens

With SECURITY_ENABLED=true, all non-ingestion public API calls need a
Keycloak bearer token. The imported development realm intentionally provides a
CLI test client and three documented local-only accounts. Do not use these
accounts or passwords outside this local Compose environment.

~~~powershell
function New-LocalApiHeaders {
  param(
    [Parameter(Mandatory)] [string] $Username,
    [Parameter(Mandatory)] [string] $Password
  )

  $tokenResponse = Invoke-RestMethod -Method POST -Uri 'http://localhost:8180/realms/home-energy/protocol/openid-connect/token' -ContentType 'application/x-www-form-urlencoded' -Body @{
    grant_type = 'password'
    client_id = 'home-energy-cli'
    username = $Username
    password = $Password
  }

  return @{
    Authorization = "Bearer $($tokenResponse.access_token)"
    'X-Correlation-ID' = "verification-$([guid]::NewGuid().ToString())"
  }
}

$userHeaders = New-LocalApiHeaders -Username 'demo-user' -Password 'DemoUser-ChangeMe-2026!'
$adminHeaders = New-LocalApiHeaders -Username 'demo-admin' -Password 'DemoAdmin-ChangeMe-2026!'
~~~

The imported development tokens expire after approximately 30 seconds. If a
later command returns HTTP 401, rerun this block to refresh both header
variables. demo-user has the ownership claim for database user ID 1;
demo-admin is used only for collection-wide and create/delete routes.

### 3.5 Prove the Vite proxy works

From the project root:

~~~powershell
Invoke-RestMethod 'http://localhost:3000/api/v1/user/1' -Headers $userHeaders |
  Format-Table id, name, email, alerting, energyAlertingThreshold
~~~

Expected: the assigned household record appears.

This proves the real route:

~~~text
Browser/Vite :3000 -> API Gateway :8080 -> User Service :8081 -> MySQL
~~~

If the Vite terminal reports an HTTP proxy ECONNREFUSED error, Vite is running but the Gateway is not ready. Re-run Section 3.2 and hard-refresh the browser after Gateway health reports UP.

---

## 4. Infrastructure health checks

### 4.1 Check gateway health and private-service startup

Only the API Gateway is published to the host on port 8080. The six
application services intentionally use Docker-only exposed ports, so direct
host requests such as localhost:8081 are not a valid health check.

~~~powershell
Invoke-RestMethod 'http://localhost:8080/actuator/health'

$privateServices = @(
  'user-service', 'device-service', 'ingestion-service',
  'usage-service', 'alert-service', 'insight-service'
)

docker compose ps $privateServices
docker compose logs --tail=60 $privateServices |
  Select-String 'Started .*Application|Netty started|APPLICATION FAILED|ERROR'
~~~

Expected:

- Gateway health returns status UP.
- Each private service is running in Docker Compose and its startup logs do
  not contain an application-failure line.

The authenticated public requests in Sections 5 through 9 are the functional
proof that the gateway can reach each relevant private service.

### 4.2 Check Kafka UI, InfluxDB, and Mailpit

~~~powershell
Invoke-RestMethod 'http://localhost:8072/health'
Invoke-WebRequest -UseBasicParsing 'http://localhost:8070' | Select-Object StatusCode
Invoke-WebRequest -UseBasicParsing 'http://localhost:8025' | Select-Object StatusCode
~~~

Expected:

- InfluxDB reports healthy/pass status.
- Kafka UI and Mailpit return HTTP 200 or a normal local redirect response.

Open these local tools:

| Tool | URL | What to check |
| --- | --- | --- |
| Kafka UI | [http://localhost:8070](http://localhost:8070) | Cluster named local, then energy-usage and energy-alerts topics |
| InfluxDB | [http://localhost:8072](http://localhost:8072) | Bucket named usage-bucket and measurement named energy_usage |
| Mailpit | [http://localhost:8025](http://localhost:8025) | Local captured test emails |

### 4.3 Validate Docker Compose configuration

~~~powershell
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.production.example -f docker-compose.prod.yml config --quiet
~~~

Expected: both commands finish with exit code 0.

---

## 5. Select a known live user and device

Run this once before API feature checks. It avoids assuming a particular seeded ID.
Section 3.4 must have completed successfully.

~~~powershell
$api = 'http://localhost:8080/api/v1'
$headers = $userHeaders

$users = Invoke-RestMethod -Uri "$api/user" -Headers $adminHeaders
$users | Format-Table id, name, email, alerting, energyAlertingThreshold

$demoUserId = [int64]1
if ($null -eq ($users | Where-Object { [int64]$_.id -eq $demoUserId })) {
  throw 'Database user ID 1 is required by the imported demo-user Keycloak ownership claim.'
}
$demoUser = Invoke-RestMethod -Uri "$api/user/$demoUserId" -Headers $userHeaders

$devices = Invoke-RestMethod -Uri "$api/device/user/$demoUserId" -Headers $userHeaders
$devices | Format-Table id, name, type, location, userId

if ($null -eq $devices -or $devices.Count -eq 0) {
  throw "User $demoUserId has no devices. Add a device through Section 6 first."
}

$demoDeviceId = [int64]$devices[0].id
Write-Host "Using user $demoUserId and device $demoDeviceId." -ForegroundColor Cyan
~~~

Expected:

- the user list comes from MySQL through the Gateway;
- devices are returned for the chosen user;
- the two variables can be reused below.

The imported demo-user identity is deliberately mapped to database user 1, so
this guide verifies that mapping explicitly. Frontend offline fallback data
uses different demo IDs such as 101, which are not live database proof.

---

## 6. User and device CRUD tests

This is the MySQL persistence test. It creates temporary data, reads it, updates it, and cleans it up.
These collection-wide and cross-household operations require the local
administrator token, so the commands in this section intentionally switch the
default header variable.

~~~powershell
$headers = $adminHeaders
~~~

### 6.1 Create a temporary user

~~~powershell
$stamp = Get-Date -Format 'yyyyMMddHHmmss'
$temporaryUserBody = @{
  name = "Verification Household $stamp"
  surname = 'Local'
  email = "verify.$stamp@example.test"
  address = 'Local test only'
  alerting = $true
  energyAlertingThreshold = 999999
} | ConvertTo-Json

$temporaryUser = Invoke-RestMethod -Method POST -Uri "$api/user" -Headers $headers -ContentType 'application/json' -Body $temporaryUserBody
$temporaryUserId = [int64]$temporaryUser.id
$temporaryUser | ConvertTo-Json -Depth 4
~~~

Expected: HTTP 201 and a user object with a new numeric ID.

### 6.2 Read and update the temporary user

~~~powershell
Invoke-RestMethod -Uri "$api/user/$temporaryUserId" -Headers $headers | ConvertTo-Json -Depth 4

$updatedUserBody = @{
  id = $temporaryUserId
  name = "Verification Household Updated $stamp"
  surname = 'Local'
  email = "verify.$stamp@example.test"
  address = 'Updated local test only'
  alerting = $true
  energyAlertingThreshold = 888888
} | ConvertTo-Json

Invoke-RestMethod -Method PUT -Uri "$api/user/$temporaryUserId" -Headers $headers -ContentType 'application/json' -Body $updatedUserBody
Invoke-RestMethod -Uri "$api/user/$temporaryUserId" -Headers $headers | ConvertTo-Json -Depth 4
~~~

Expected:

- the first request returns the created record;
- PUT says User updated successfully;
- the final GET contains the updated name and threshold.

### 6.3 Create, read, and update an appliance

Valid device types:

~~~text
HVAC, KITCHEN, ENTERTAINMENT, OFFICE, UTILITY, GENERAL,
SPEAKER, CAMERA, THERMOSTAT, LIGHT, LOCK, DOORBELL
~~~

~~~powershell
$temporaryDeviceBody = @{
  name = "Verification Plug $stamp"
  type = 'GENERAL'
  location = 'Local Test Desk'
  userId = $temporaryUserId
} | ConvertTo-Json

$temporaryDevice = Invoke-RestMethod -Method POST -Uri "$api/device" -Headers $headers -ContentType 'application/json' -Body $temporaryDeviceBody
$temporaryDeviceId = [int64]$temporaryDevice.id
$temporaryDevice | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "$api/device/$temporaryDeviceId" -Headers $headers | ConvertTo-Json -Depth 4

$updatedDeviceBody = @{
  id = $temporaryDeviceId
  name = "Verification Plug Updated $stamp"
  type = 'GENERAL'
  location = 'Updated Local Test Desk'
  userId = $temporaryUserId
} | ConvertTo-Json

Invoke-RestMethod -Method PUT -Uri "$api/device/$temporaryDeviceId" -Headers $headers -ContentType 'application/json' -Body $updatedDeviceBody |
  ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "$api/device/user/$temporaryUserId" -Headers $headers |
  Format-Table id, name, type, location, userId
~~~

Expected:

- POST device returns HTTP 200 and a new device ID;
- GET device by ID returns the same appliance;
- PUT returns the updated appliance;
- GET devices by user lists it.

The project also supports POST to /api/v1/device/create. It is an alternative route; do not run it unless you also remove the extra device it creates.

### 6.4 Delete temporary test data

~~~powershell
(Invoke-WebRequest -UseBasicParsing -Method DELETE -Uri "$api/device/$temporaryDeviceId" -Headers $headers).StatusCode
(Invoke-WebRequest -UseBasicParsing -Method DELETE -Uri "$api/user/$temporaryUserId" -Headers $headers).StatusCode
~~~

Expected: 204 for both DELETE requests.

Restore the user-scoped default before testing the selected household:

~~~powershell
$headers = $userHeaders
~~~

---

## 7. Ingestion, Kafka, InfluxDB, and Usage Service

This verifies the core event pipeline:

~~~text
POST reading -> Ingestion Service -> Kafka energy-usage -> Usage Service -> InfluxDB -> Usage and Insight APIs
~~~

### 7.1 Capture usage before ingestion

~~~powershell
$usageBefore = Invoke-RestMethod -Uri "$api/usage/$demoUserId?days=3" -Headers $headers
$usageBefore | ConvertTo-Json -Depth 8

$totalBefore = ($usageBefore.devices | Measure-Object -Property energyConsumed -Sum).Sum
if ($null -eq $totalBefore) { $totalBefore = 0 }
~~~

Expected: a user ID and device usage entries. Fresh databases can show zero until the first reading is ingested.

### 7.2 Send one small, valid energy reading

The value must be kWh, not watts. Convert a watts reading before posting:

~~~text
kWh = watts x hours / 1000
~~~

~~~powershell
$reading = @{
  deviceId = $demoDeviceId
  energyConsumed = 0.25
  timestamp = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json -Compress

$ingestionResponse = Invoke-WebRequest -UseBasicParsing -Method POST -Uri "$api/ingestion" -Headers $headers -ContentType 'application/json' -Body $reading
$ingestionResponse.StatusCode
~~~

Expected: 201.

### 7.3 Wait for the async consumer, then re-check usage

~~~powershell
Start-Sleep -Seconds 15

$usageAfter = Invoke-RestMethod -Uri "$api/usage/$demoUserId?days=3" -Headers $headers
$usageAfter | ConvertTo-Json -Depth 8

$totalAfter = ($usageAfter.devices | Measure-Object -Property energyConsumed -Sum).Sum
if ($null -eq $totalAfter) { $totalAfter = 0 }

[pscustomobject]@{
  TotalBeforeKwh = [math]::Round([double]$totalBefore, 3)
  TotalAfterKwh = [math]::Round([double]$totalAfter, 3)
  ExpectedMinimumIncreaseKwh = 0.25
} | Format-List
~~~

Expected: TotalAfterKwh is about 0.25 kWh higher for the selected user/window.

### 7.4 Show the Kafka message

Visual method:

1. Open [http://localhost:8070](http://localhost:8070).
2. Select the local cluster.
3. Open Topics, then energy-usage.
4. Confirm a record contains your device ID, kWh value, and timestamp.

Terminal method:

~~~powershell
docker exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic energy-usage --from-beginning --max-messages 5 --timeout-ms 5000
~~~

Expected: topic names include energy-usage and event JSON appears. This consumer command is read-only.

### 7.5 Show the InfluxDB point

~~~powershell
Invoke-RestMethod 'http://localhost:8072/health'
~~~

Then in [InfluxDB](http://localhost:8072):

1. Sign in with local values from .env; never show those values.
2. Open Data Explorer and select usage-bucket.
3. Run this Flux query:

~~~flux
from(bucket: "usage-bucket")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "energy_usage")
  |> filter(fn: (r) => r._field == "energyConsumed")
~~~

Expected: a point tagged with your device ID and containing the energyConsumed field.

### 7.6 Inspect logs

~~~powershell
docker compose logs --tail=120 ingestion-service usage-service |
  Select-String 'Ingested Energy Usage Event|Aggregated device energies|Error'
~~~

Expected: an ingestion event and no relevant Kafka/InfluxDB error.

---

## 8. Energy intelligence tests

Run every command with the live user selected in Section 5. These requests go through the Gateway and use MySQL/InfluxDB-backed data where applicable.

### 8.1 Bill Shock Forecast

~~~powershell
Invoke-RestMethod -Uri "$api/insight/bill-forecast/$demoUserId?days=3" -Headers $headers |
  ConvertTo-Json -Depth 6
~~~

Expected fields:

~~~text
currentKwh
currentEstimatedCost
dailyRateKwh
projectedMonthlyKwh
projectedMonthlyCost
tariffSummary
~~~

This powers the dashboard cost and month-end forecast cards.

### 8.2 Appliance ranking

~~~powershell
Invoke-RestMethod -Uri "$api/insight/appliance-ranking/$demoUserId?days=3" -Headers $headers |
  ConvertTo-Json -Depth 8
~~~

Expected: a rankings array ordered from highest to lowest energy use, with device name, location, kWh, percentage of total, and estimated cost.

This is the live-backed proof for the top-consumer and appliance-ranking dashboard features.

### 8.3 Standby Energy Detective

~~~powershell
Invoke-RestMethod -Uri "$api/insight/standby-detective/$demoUserId?days=3" -Headers $headers |
  ConvertTo-Json -Depth 8
~~~

Expected fields:

~~~text
baselineWatts
standbyDailyKwh
standbyMonthlyKwh
standbyMonthlyCost
riskLevel
recommendations
probableCategories
~~~

This is the project novelty. It estimates persistent low-activity or phantom load, turns it into monthly energy/cost impact, and returns concrete actions. It is an explainable heuristic, not a claim of exact appliance-level machine-learning disaggregation.

### 8.4 Savings Tips

~~~powershell
Invoke-RestMethod -Uri "$api/insight/saving-tips/$demoUserId" -Headers $headers |
  ConvertTo-Json -Depth 8
~~~

Expected: recommendations, energy/cost context, and an isAiGenerated flag.

Ollama is optional. When a local AI model is unavailable, the endpoint should safely return deterministic recommendations with isAiGenerated set to false. That fallback is correct behavior, not a failure.

### 8.5 Combined overview

~~~powershell
Invoke-RestMethod -Uri "$api/insight/overview/$demoUserId" -Headers $headers |
  ConvertTo-Json -Depth 8
~~~

Expected: one insight summary response. The current frontend loads its dashboard panels through dedicated endpoints, but this request completes API coverage for the overview route.

### 8.6 Real seven-day usage query

~~~powershell
Invoke-RestMethod -Uri "$api/usage/$demoUserId?days=7" -Headers $headers |
  ConvertTo-Json -Depth 8
~~~

This is the valid backend proof for a seven-day time window. Do not claim the visible browser line chart itself is server-historical data until a historical chart endpoint is added.

---

## 9. Alert and Mailpit tests

### 9.1 Read alert history

~~~powershell
Invoke-RestMethod -Uri "$api/alert/user/$demoUserId" -Headers $headers |
  Select-Object id, userId, message, threshold, energyConsumed, email, createdAt, sent |
  Format-Table -AutoSize

Invoke-RestMethod -Uri "$api/alert" -Headers $adminHeaders |
  Select-Object id, userId, message, threshold, energyConsumed, email, createdAt, sent |
  Format-Table -AutoSize
~~~

Expected:

- the first command shows selected-household alerts;
- the second command shows all local alert records.

### 9.2 Send a direct test alert to Mailpit

This verifies Alert Service storage and local email delivery. It deliberately writes local alert rows. It does not prove the Kafka threshold route; Section 9.4 is the optional full automatic route.

~~~powershell
$manualAlert = @{
  userId = $demoUserId
  message = "Manual local verification alert at $(Get-Date -Format 's')"
  threshold = 999999
  energyConsumed = 0.25
  email = $demoUser.email
} | ConvertTo-Json

Invoke-RestMethod -Method POST -Uri "$api/alert/test-send" -Headers $adminHeaders -ContentType 'application/json' -Body $manualAlert
Start-Sleep -Seconds 3

Invoke-RestMethod -Uri "$api/alert/user/$demoUserId" -Headers $headers |
  Select-Object -First 5 id, message, threshold, energyConsumed, email, createdAt, sent |
  Format-Table -AutoSize
~~~

Expected:

~~~text
Alert email dispatched to Mailpit successfully!
~~~

Open [http://localhost:8025](http://localhost:8025). A new email with an Energy Usage Alert subject should be visible.

Known current behavior: the Alert Service saves a detailed alert row and then saves a delivery-status row after email delivery. Therefore the API can show an extra status-only or blank-looking row. That does not mean Mailpit delivery failed.

### 9.3 Inspect Alert Service logs

~~~powershell
docker compose logs --tail=100 alert-service |
  Select-String 'Received alert event|Sending email|Email sent|Failed'
~~~

Expected: Sending email followed by Email sent for a healthy Mailpit delivery.

### 9.4 Optional full automatic threshold path

Run this only when you specifically need to prove:

~~~text
Ingestion -> Kafka -> Usage aggregation -> energy-alerts -> Alert Service -> Mailpit
~~~

It writes alert history that cannot be deleted individually through the public
API. The scheduler checks the preceding one-hour total every 10 seconds; an
over-threshold event can therefore create repeated alerts until alerting is
disabled.

With security enabled, a JWT user can publish telemetry only for a device
owned by that user's Keycloak ownership claim. Therefore this controlled test
uses the imported demo-user household and its selected device, rather than a
newly created household that has no matching Keycloak user.

First refresh the short-lived tokens from Section 3.4 if necessary, then save
the profile state, temporarily enable a low threshold, publish the reading,
and restore the original profile in a finally block:

~~~powershell
$userHeaders = New-LocalApiHeaders -Username 'demo-user' -Password 'DemoUser-ChangeMe-2026!'
$adminHeaders = New-LocalApiHeaders -Username 'demo-admin' -Password 'DemoAdmin-ChangeMe-2026!'
$headers = $userHeaders

$originalDemoUser = Invoke-RestMethod -Uri "$api/user/$demoUserId" -Headers $adminHeaders

$enableAutomaticAlertBody = @{
  id = $demoUserId
  name = $originalDemoUser.name
  surname = $originalDemoUser.surname
  email = $originalDemoUser.email
  address = $originalDemoUser.address
  alerting = $true
  energyAlertingThreshold = 0.1
} | ConvertTo-Json

try {
  Invoke-RestMethod -Method PUT -Uri "$api/user/$demoUserId" -Headers $adminHeaders -ContentType 'application/json' -Body $enableAutomaticAlertBody

  $thresholdReading = @{
    deviceId = $demoDeviceId
    energyConsumed = 1.0
    timestamp = (Get-Date).ToUniversalTime().ToString('o')
  } | ConvertTo-Json -Compress

  (Invoke-WebRequest -UseBasicParsing -Method POST -Uri "$api/ingestion" -Headers $userHeaders -ContentType 'application/json' -Body $thresholdReading).StatusCode
  Start-Sleep -Seconds 15

  Invoke-RestMethod -Uri "$api/alert/user/$demoUserId" -Headers $userHeaders |
    ConvertTo-Json -Depth 8
} finally {
  $restoreDemoUserBody = @{
    id = $demoUserId
    name = $originalDemoUser.name
    surname = $originalDemoUser.surname
    email = $originalDemoUser.email
    address = $originalDemoUser.address
    alerting = $originalDemoUser.alerting
    energyAlertingThreshold = $originalDemoUser.energyAlertingThreshold
  } | ConvertTo-Json

  Invoke-RestMethod -Method PUT -Uri "$api/user/$demoUserId" -Headers $adminHeaders -ContentType 'application/json' -Body $restoreDemoUserBody
}
~~~

Expected: the ingestion request returns 201; after the asynchronous processing
interval, the selected user's alert history contains an automatic threshold
alert and Mailpit receives a matching email. The finally block restores the
original threshold even if an intermediate command fails. Alert records remain
as historical local test evidence because there is no public alert-delete
endpoint.

---

## 10. Frontend feature checklist

Open [http://localhost:3000](http://localhost:3000) after Section 3.5 succeeds
and sign in through the Keycloak screen. Use the browser DevTools Network tab
for the strongest UI proof: live requests should be 200/201 rather than failed
requests followed by a local fallback.

For a regular household walkthrough, sign in as demo-user with
DemoUser-ChangeMe-2026!. For profile creation and collection-wide administration,
sign out and sign in as demo-admin with DemoAdmin-ChangeMe-2026!. These are
local development accounts only.

| UI area | What to do in the browser | Expected live behavior | Cross-check |
| --- | --- | --- | --- |
| Household switcher | Hover/select a household in the header | An administrator can select profiles; a regular user sees only the assigned household | GET user, then user-specific APIs |
| Add New Account | Sign in as demo-admin, then Header menu -> Add New Account -> fill fields -> Create | A new selected household appears | Administrator POST user returns 201 |
| Dashboard summary | Open Dashboard | kWh, estimated cost, projected bill, top consumer render | Bill Forecast and Ranking endpoints |
| Standby Detective | Inspect risk, monthly loss, and checklist | Baseline/risk/recommendations render | Standby Detective endpoint |
| Saving Tips | Inspect tips panel | Tips render with AI or deterministic fallback | Saving Tips endpoint |
| Devices | Open Devices tab | Real device cards display | GET devices by user |
| Add Appliance | Devices -> Add Appliance -> Register | Card appears and survives refresh | POST device, then GET devices |
| Delete Appliance | Device trash action | Card disappears and stays gone after reload | DELETE device, then GET devices |
| Reading Simulator | Choose a device, enter a kWh value, publish | Status message appears | POST ingestion returns 201 |
| Quick presets | Select Normal, Heavy, or Threshold preset | Input changes to 2.5, 15, or 55 kWh | Inspect input before publishing |
| Alert History | Open Alert History tab | Persisted per-user alerts render | GET alerts by user |

### Recommended browser walkthrough

1. Select a real household.
2. Show Dashboard: forecast, ranking, Standby Energy Detective, and Saving Tips.
3. Open Devices, create a throwaway appliance, refresh, and delete it.
4. Open Reading Simulator, choose a real device, enter 0.25 kWh, and click Simulate and Publish Reading.
5. Wait 15 seconds, then hard-refresh or switch households and return.
6. Open Alert History and show records produced in Section 9.
7. Keep the matching PowerShell API output available if you are presenting.

### Optional frontend fallback test

Do this only after all normal live evidence is complete. It intentionally
starts a separate auth-disabled Vite process; the normal frontend is
secure-by-default and does not silently fall back when a protected API is
unavailable.

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker/frontend'
$env:VITE_AUTH_ENABLED='false'
npm run dev
~~~

Open the Vite URL printed by this separate process. Expected:

- the page may still render demo-looking data;
- browser Network/Console shows failed API requests;
- this is offline presentation fallback, not a live backend result.

Stop the fallback Vite process with Ctrl+C. Restore normal secure frontend
mode in a fresh terminal:

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker/frontend'
Remove-Item Env:VITE_AUTH_ENABLED -ErrorAction SilentlyContinue
npm run dev
~~~

Sign in through Keycloak again before treating a screen as live evidence.

---

## 11. Full API coverage matrix

Gateway base URL:

~~~text
http://localhost:8080/api/v1
~~~

| Method | Route | Authorized principal | What it verifies | Expected successful response |
| --- | --- | --- | --- | --- |
| GET | /user | Administrator | List households | 200 |
| POST | /user | Administrator | Create household | 201 |
| GET | /user/{id} | Owner or administrator | Read one household | 200 |
| PUT | /user/{id} | Owner or administrator | Update household | 200 |
| DELETE | /user/{id} | Owner or administrator | Remove household | 204 |
| GET | /device/{id} | Device owner or administrator | Read a device | 200 |
| POST | /device | Target owner or administrator | Create a device | 200 |
| POST | /device/create | Target owner or administrator | Alternative device-create route | 200 |
| PUT | /device/{id} | Device owner or administrator | Update device | 200 |
| DELETE | /device/{id} | Device owner or administrator | Remove device | 204 |
| GET | /device/user/{userId} | Owner or administrator | List user devices | 200 |
| POST | /ingestion | Owner JWT for the device, or configured device token | Publish kWh reading | 201 |
| GET | /usage/{userId}?days=N | Owner or administrator | Query device usage window | 200 |
| GET | /insight/overview/{userId} | Owner or administrator | Overview insight | 200 |
| GET | /insight/saving-tips/{userId} | Owner or administrator | Savings recommendations | 200 |
| GET | /insight/bill-forecast/{userId}?days=N | Owner or administrator | Forecast/cost | 200 |
| GET | /insight/appliance-ranking/{userId}?days=N | Owner or administrator | Highest-use devices | 200 |
| GET | /insight/standby-detective/{userId}?days=N | Owner or administrator | Standby analysis | 200 |
| POST | /alert/test-send | Administrator | Direct Mailpit alert test | 200 |
| GET | /alert/user/{userId} | Owner or administrator | Per-user alert history | 200 |
| GET | /alert | Administrator | All local alert history | 200 |

---

## 12. Validation, error handling, and observability

### 12.1 Invalid energy reading must be rejected

This should not publish any Kafka event.

~~~powershell
$invalidReading = @{
  deviceId = $demoDeviceId
  energyConsumed = -1
  timestamp = (Get-Date).ToUniversalTime().ToString('o')
} | ConvertTo-Json -Compress

try {
  Invoke-WebRequest -UseBasicParsing -Method POST -Uri "$api/ingestion" -Headers $headers -ContentType 'application/json' -Body $invalidReading -ErrorAction Stop
  throw 'Unexpected success: negative kWh must not be accepted.'
} catch {
  $statusCode = [int]$_.Exception.Response.StatusCode
  Write-Host "Validation response: $statusCode" -ForegroundColor Yellow
}
~~~

Expected: 400.

### 12.2 Missing user must return not found

~~~powershell
try {
  Invoke-WebRequest -UseBasicParsing -Uri "$api/user/999999999" -Headers $adminHeaders -ErrorAction Stop
  throw 'Unexpected success: this test ID should not exist.'
} catch {
  $statusCode = [int]$_.Exception.Response.StatusCode
  Write-Host "Missing-user response: $statusCode" -ForegroundColor Yellow
}
~~~

Expected: 404.

### 12.3 Follow a request through logs with a correlation ID

~~~powershell
$correlationId = "verify-trace-$([guid]::NewGuid().ToString())"
$traceHeaders = @{
  Authorization = $adminHeaders.Authorization
  'X-Correlation-ID' = $correlationId
}

Invoke-RestMethod -Uri "$api/user" -Headers $traceHeaders | Out-Null
docker compose logs --tail=150 api-gateway user-service | Select-String $correlationId
~~~

Expected: at least one log line contains the generated ID. This demonstrates traceability across the Gateway boundary.

---

## 13. Build, test, and production-style frontend checks

### 13.1 Frontend lint and production build

~~~powershell
Push-Location frontend
npm ci
npm run lint
npm run build
Pop-Location
~~~

Expected:

- lint succeeds;
- the TypeScript/Vite build succeeds;
- a production bundle is created in frontend/dist.

### 13.2 Java service tests

The following services include Maven wrappers for Windows:

~~~powershell
$wrapperServices = @(
  'user-service',
  'device-service',
  'ingestion-service',
  'usage-service',
  'alert-service',
  'insight-service'
)

foreach ($service in $wrapperServices) {
  Write-Host "Testing $service" -ForegroundColor Cyan
  Push-Location $service
  & .\mvnw.cmd test
  Pop-Location
}
~~~

Expected: each service ends with BUILD SUCCESS.

The API Gateway currently uses the installed Maven command:

~~~powershell
Push-Location api-gateway
mvn test
Pop-Location
~~~

Expected: BUILD SUCCESS.

### 13.3 Optional Docker/Nginx frontend verification

First stop Vite with Ctrl+C in its terminal. Then start the frontend container:

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker'
docker compose up -d --build frontend
docker compose ps frontend
~~~

Open [http://localhost:3000](http://localhost:3000), then run:

~~~powershell
Invoke-RestMethod 'http://localhost:3000/api/v1/user/1' -Headers $userHeaders |
  Format-Table id, name, email
~~~

Expected: the Nginx frontend serves the UI and proxies the API request through the Gateway.

When finished, stop the container frontend before starting Vite again:

~~~powershell
docker compose stop frontend
~~~

---

## 14. Fast troubleshooting

| Symptom | Meaning | Exact next check |
| --- | --- | --- |
| Vite proxy says ECONNREFUSED for API routes | Vite is running, but Gateway port 8080 is unavailable or still booting | Run the Gateway health loop in Section 3.2 |
| Docker shows no Server version | Docker Desktop engine is stopped | Open Docker Desktop and wait for Engine running |
| Port 3000 is already in use | Vite and Docker/Nginx frontend are both trying to use it | Stop one mode; use Section 2.3 |
| Gateway returns 502 or 500 | A downstream service is down or still booting | Inspect logs for the named downstream service |
| Usage/insights remain zero after ingestion | Kafka or Influx processing has not completed | Wait 15 seconds; inspect Usage Service logs and InfluxDB |
| Mailpit is empty after test-send | Alert Service or Mailpit did not finish delivery | Inspect Alert Service logs and port 8025 |
| UI looks fine while Network calls fail | Check whether the explicit `VITE_AUTH_ENABLED=false` offline-preview mode is running; otherwise treat it as a protected API failure | Restore the normal secure frontend, sign in through Keycloak, and re-run Gateway API checks |
| Repeated alert rows appear | One-hour total still exceeds threshold; scheduler runs every 10 seconds | Disable alerting or raise threshold after test |

Useful diagnostic snapshot:

~~~powershell
docker compose ps
docker compose logs --tail=80 api-gateway user-service device-service ingestion-service usage-service alert-service insight-service
~~~

### 14.1 Gateway or Vite proxy recovery

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker'
docker compose up -d mysql kafka kafka-ui influxdb mailpit user-service device-service ingestion-service usage-service alert-service insight-service api-gateway
docker compose logs --tail=80 api-gateway
Invoke-RestMethod 'http://localhost:8080/actuator/health'
~~~

Only hard-refresh the frontend after the last command returns status UP.

### 14.2 Find one failing service

~~~powershell
docker compose logs --tail=120 user-service
docker compose logs --tail=120 device-service
docker compose logs --tail=120 ingestion-service
docker compose logs --tail=120 usage-service
docker compose logs --tail=120 alert-service
docker compose logs --tail=120 insight-service
~~~

---

## 15. Command order for a professor demo

If you need the minimum live sequence, run these sections in order:

1. Section 3 — start Docker backend and Vite.
2. Section 4 — confirm health.
3. Section 5 — select a real user/device.
4. Section 7.2 — submit one 0.25 kWh event.
5. Section 7.3 — prove Usage changes.
6. Section 7.4 or 7.5 — show Kafka/Influx evidence.
7. Section 8 — show forecast, ranking, standby, and saving-tip JSON.
8. Section 9.1 and 9.2 — show alert history and Mailpit.
9. Section 10 — show the matching frontend tabs.

What to say:

> The frontend calls one Gateway instead of every service. Ingestion accepts a kWh reading quickly, Kafka decouples the event, Usage writes it to InfluxDB, Insight turns it into forecast/ranking/standby information, and Alert stores/sends threshold notifications. The novelty is not only total usage: Standby Energy Detective translates likely phantom load into monthly kWh, cost, risk, and actions.

Be accurate about current scope:

- the app accepts simulated/manual meter readings, not a connected physical smart meter;
- the deterministic analytics work whether or not the optional Ollama integration is available;
- the repository includes deployment material, but do not claim a cloud/TLS deployment exists unless you have actually provisioned and verified it;
- the 7-day UI graph is illustrative. Use the Usage API for server-side time-window proof.

---

## 16. Normal shutdown and destructive reset

### Normal shutdown — keeps all local data

Stop Vite with Ctrl+C in its terminal, then:

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker'
docker compose down
~~~

### Destructive clean reset — deletes local data

Use only when you intentionally want to remove MySQL, Kafka, and InfluxDB volumes:

~~~powershell
Set-Location 'C:/Users/anju2/Desktop/Home-Energy-Tracker'
docker compose down -v
docker compose up -d --build
~~~

This action is irreversible through the application.

---

## 17. Final complete-verification checklist

- [ ] Docker shows a Server version.
- [ ] API Gateway and all six microservices report UP.
- [ ] The request through Vite at port 3000 returns live users.
- [ ] User CRUD creates, reads, updates, and deletes a temporary household.
- [ ] Device CRUD creates, reads, updates, and deletes a temporary appliance.
- [ ] One ingestion request returns HTTP 201.
- [ ] The energy-usage event appears in Kafka.
- [ ] InfluxDB contains an energy_usage point.
- [ ] Usage increases after the test reading.
- [ ] Bill Forecast returns cost/projection data.
- [ ] Appliance Ranking returns ordered device data.
- [ ] Standby Detective returns baseline/risk/monthly-loss data.
- [ ] Saving Tips returns AI or deterministic fallback recommendations.
- [ ] Overview and seven-day Usage routes return JSON.
- [ ] Alert history endpoint returns stored records.
- [ ] Mailpit displays a test email.
- [ ] Dashboard, Devices, Reading Simulator, and Alert History tabs work with live network responses.
- [ ] Invalid ingestion returns HTTP 400 and an unknown user returns HTTP 404.
- [ ] Correlation ID can be found in service logs.
- [ ] Frontend lint/build and Java tests pass.
- [ ] You can distinguish live proof from frontend fallback/illustrative UI behavior.

When every item is checked, you have a complete local evidence record for the Home Energy Tracker project.
