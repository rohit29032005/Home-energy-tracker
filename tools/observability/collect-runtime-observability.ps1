[CmdletBinding()]
param(
    [string]$PrometheusUrl = 'http://localhost:9090',
    [string]$GatewayUrl = 'http://localhost:8080'
)

$ErrorActionPreference = 'Stop'
$directory = Join-Path $PSScriptRoot '..\..\evidence\08_observability'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
Invoke-WebRequest -UseBasicParsing "$GatewayUrl/actuator/prometheus" | Select-Object StatusCode,Content | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 (Join-Path $directory "gateway-metrics-$timestamp.json")
Invoke-RestMethod "$PrometheusUrl/api/v1/targets" | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $directory "prometheus-targets-$timestamp.json")
Invoke-RestMethod "$PrometheusUrl/api/v1/query?query=home_energy_alerts_suppressed_total" | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $directory "alert-dedup-metrics-$timestamp.json")
Invoke-RestMethod "$PrometheusUrl/api/v1/query?query=ml_inference_latency_seconds_count" | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $directory "ml-inference-metrics-$timestamp.json")
docker stats --no-stream --format '{{json .}}' | Set-Content -Encoding utf8 (Join-Path $directory "docker-resource-usage-$timestamp.jsonl")
Write-Host "Runtime observability evidence captured in $directory"
