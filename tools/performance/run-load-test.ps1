[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://localhost:8080',
    [string]$DeviceToken = $env:WOKWI_INGESTION_TOKEN,
    [switch]$UseDockerK6
)

$ErrorActionPreference = 'Stop'
if (-not $DeviceToken) { throw 'Set WOKWI_INGESTION_TOKEN or pass -DeviceToken.' }
$nativeK6 = Get-Command k6 -ErrorAction SilentlyContinue
$useContainer = $UseDockerK6 -or -not $nativeK6
if ($useContainer -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'k6 is not installed and Docker is unavailable. Install k6 or Docker, then rerun; no result is generated without a real load run.'
}
$directory = Join-Path $PSScriptRoot '..\..\evidence\09_performance'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$rawJson = Join-Path $directory "k6-raw-$timestamp.json"
$summary = Join-Path $directory "k6-summary-$timestamp.json"

if ($useContainer) {
    # Docker Desktop exposes the Windows host through this DNS name. It lets
    # the official k6 image exercise the same gateway port as a native run.
    $containerBaseUrl = $BaseUrl -replace '(?i)://(?:localhost|127\.0\.0\.1)(?=[:/]|$)', '://host.docker.internal'
    $scriptPath = (Resolve-Path (Join-Path $PSScriptRoot 'k6-ingestion.js')).Path
    $evidencePath = (Resolve-Path $directory).Path
    docker run --rm `
        -e "BASE_URL=$containerBaseUrl" `
        -e "WOKWI_INGESTION_TOKEN=$DeviceToken" `
        -v "${scriptPath}:/scripts/k6-ingestion.js:ro" `
        -v "${evidencePath}:/evidence" `
        grafana/k6:latest run `
        --out "json=/evidence/k6-raw-$timestamp.json" `
        --summary-export "/evidence/k6-summary-$timestamp.json" `
        /scripts/k6-ingestion.js
} else {
    $env:BASE_URL = $BaseUrl
    $env:WOKWI_INGESTION_TOKEN = $DeviceToken
    k6 run --out "json=$rawJson" --summary-export $summary (Join-Path $PSScriptRoot 'k6-ingestion.js')
}
if ($LASTEXITCODE -ne 0) {
    throw "k6 exited with code $LASTEXITCODE; see any generated raw evidence in $directory."
}
Get-ComputerInfo | Select-Object OsName,OsVersion,OsBuildNumber,CsNumberOfLogicalProcessors,CsTotalPhysicalMemory | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $directory "hardware-$timestamp.json")
Write-Host "Load test completed. Runtime: $(if ($useContainer) { 'official Docker k6 image' } else { 'native k6' }). Raw results: $rawJson; summary: $summary"
