[CmdletBinding()]
param(
    [ValidateSet('ml-inference-service', 'kafka', 'influxdb', 'mailpit', 'alert-service')]
    [string]$Target,
    [string]$BaseUrl = 'http://localhost:8080',
    [string]$DeviceToken = $env:WOKWI_INGESTION_TOKEN
)

$ErrorActionPreference = 'Stop'
if (-not $DeviceToken) { throw 'Set WOKWI_INGESTION_TOKEN or pass -DeviceToken.' }
$directory = Join-Path $PSScriptRoot '..\..\evidence\10_resilience'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$runId = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $directory "fault-$Target-$runId.md"
$stopped = $false
$recovered = $false

"# Controlled fault injection: $Target`n`nStarted: $(Get-Date -Format o)" | Set-Content -Encoding utf8 $log
docker compose ps | Out-String | Add-Content $log
try {
  docker compose stop $Target
  if ($LASTEXITCODE -ne 0) { throw "Could not stop fault target '$Target'." }
  $stopped = $true
  "`n## State while $Target was stopped" | Add-Content $log
  $payload = @{ deviceId = 1; energyConsumed = 0.31; timestamp = [DateTime]::UtcNow.ToString('o') } | ConvertTo-Json -Compress
  try {
    $response = Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/v1/ingestion" -Headers @{ 'X-Device-Token' = $DeviceToken } -ContentType 'application/json' -Body $payload
    "Ingestion HTTP status while faulted: $($response.StatusCode)" | Add-Content $log
  } catch {
    "Ingestion error while faulted: $($_.Exception.Message)" | Add-Content $log
  }
  docker compose logs --tail=150 $Target api-gateway ingestion-service usage-service alert-service ml-inference-service | Out-String | Add-Content $log
}
finally {
  if ($stopped) {
    "`n## Recovery action" | Add-Content $log
    docker compose start $Target
    if ($LASTEXITCODE -ne 0) {
      "Failed to start ${Target}: docker compose start returned $LASTEXITCODE" | Add-Content $log
    } else {
      $deadline = (Get-Date).AddMinutes(3)
      do {
        Start-Sleep -Seconds 5
        $state = docker compose ps $Target
        $state | Out-String | Add-Content $log
        $recovered = [bool]($state -match 'running|Up')
      } until ($recovered -or (Get-Date) -gt $deadline)
    }
    "`nRecovery container-state observation finished: $(Get-Date -Format o); recovered=$recovered" | Add-Content $log
  }
}

if (-not $recovered) {
  throw "Fault scenario did not observe '$Target' in a running container state. See $log."
}
Write-Host "Fault scenario captured in $log. It proves the recorded container-state recovery only; review service logs before claiming delivery or data-recovery semantics."
