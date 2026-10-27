[CmdletBinding()]
param(
    # Keep the public identity-provider hostname aligned with the configured
    # JWT issuer and the Keycloak redirect URI used by the frontend.
    [string]$BaseUrl = 'http://localhost:8080',
    [string]$KeycloakUrl = 'http://localhost:8180',
    [string]$Realm = 'home-energy',
    [string]$ClientId = 'home-energy-cli',
    [string]$DeviceToken = $env:WOKWI_INGESTION_TOKEN,
    # Keycloak tokens live for 30 seconds, while Spring Security permits a
    # 60-second clock-skew tolerance by default. Wait beyond both windows.
    [int]$ExpiredTokenWaitSeconds = 95
)

$ErrorActionPreference = 'Stop'
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
[System.Net.WebRequest]::DefaultWebProxy = $null
$evidenceDirectory = Join-Path $PSScriptRoot '..\..\evidence\06_security'
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null

function Get-AccessToken([string]$username, [string]$password) {
    $body = @{ grant_type = 'password'; client_id = $ClientId; username = $username; password = $password }
    (Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/$Realm/protocol/openid-connect/token" -Body $body -ContentType 'application/x-www-form-urlencoded').access_token
}

function Invoke-Case([string]$name, [scriptblock]$action, [int]$expectedStatus) {
    $observedStatus = 0
    $body = $null
    try {
        $response = & $action
        $observedStatus = [int]$response.StatusCode
        $body = $response.Content
    } catch {
        # Windows PowerShell 5 throws for a non-2xx Invoke-WebRequest
        # response, whereas PowerShell 7 can return it with
        # -SkipHttpErrorCheck.  Capture that status so expected 401/403
        # cases remain genuine validation results on both shells.
        $httpResponse = $_.Exception.Response
        if ($null -ne $httpResponse -and $null -ne $httpResponse.StatusCode) {
            $observedStatus = [int]$httpResponse.StatusCode
            $body = $_.Exception.Message
        } else {
            throw "Case '$name' could not reach the service: $($_.Exception.Message)"
        }
    }
    [pscustomobject]@{ case = $name; expected_status = $expectedStatus; observed_status = $observedStatus; passed = ($observedStatus -eq $expectedStatus); response = $body }
}

if (-not $DeviceToken) { throw 'Set WOKWI_INGESTION_TOKEN or pass -DeviceToken before running this validation.' }

$userOne = Get-AccessToken 'demo-user' 'DemoUser-ChangeMe-2026!'
$userTwo = Get-AccessToken 'demo-user-two' 'DemoUserTwo-ChangeMe-2026!'
$admin = Get-AccessToken 'demo-admin' 'DemoAdmin-ChangeMe-2026!'
$headersOne = @{ Authorization = "Bearer $userOne" }
$headersTwo = @{ Authorization = "Bearer $userTwo" }
$headersAdmin = @{ Authorization = "Bearer $admin" }
$reading = @{ deviceId = 1; energyConsumed = 0.25; timestamp = [DateTime]::UtcNow.ToString('o') } | ConvertTo-Json -Compress

$results = @(
    Invoke-Case 'valid-user-owned-profile' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user/1" -Headers $headersOne } 200
    Invoke-Case 'missing-jwt' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user/1" } 401
    Invoke-Case 'invalid-jwt' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user/1" -Headers @{ Authorization = 'Bearer invalid.token.value' } } 401
    Invoke-Case 'wrong-user-profile' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user/2" -Headers $headersOne } 403
    Invoke-Case 'wrong-user-device-list' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/device/user/1" -Headers $headersTwo } 403
    Invoke-Case 'admin-user-list' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user" -Headers $headersAdmin } 200
    Invoke-Case 'machine-token-ingestion' { Invoke-WebRequest -UseBasicParsing -Method Post -Uri "$BaseUrl/api/v1/ingestion" -Headers @{ 'X-Device-Token' = $DeviceToken } -ContentType 'application/json' -Body $reading } 201
)

# This is a real expiry check rather than a malformed-token substitute. The
# default wait passes the 30-second token lifetime and gateway clock skew.
Start-Sleep -Seconds $ExpiredTokenWaitSeconds
$results += Invoke-Case 'expired-jwt' { Invoke-WebRequest -UseBasicParsing -Uri "$BaseUrl/api/v1/user/1" -Headers $headersOne } 401

$results | Select-Object case, expected_status, observed_status, passed | Export-Csv -NoTypeInformation -Path (Join-Path $evidenceDirectory 'security_results.csv')
$results | ConvertTo-Json -Depth 3 | Set-Content -Encoding utf8 -Path (Join-Path $evidenceDirectory 'security_results.json')
if ($results.passed -contains $false) { throw 'At least one security validation case failed. See evidence/06_security/security_results.csv.' }
Write-Host "Security validation passed. Evidence: $evidenceDirectory"
