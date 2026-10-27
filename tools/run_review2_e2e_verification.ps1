param(
    [string]$BaseUrl = "http://127.0.0.1:8080/api/v1",
    [string]$EvidenceDirectory = "",
    # Keep the requested issuer aligned with the gateway JWT issuer setting.
    [string]$KeycloakUrl = "http://localhost:8180",
    [string]$Realm = "home-energy",
    [string]$ClientId = "home-energy-cli",
    [string]$AdminUsername = "demo-admin",
    [string]$AdminPassword = "DemoAdmin-ChangeMe-2026!",
    [string]$MailpitUrl = "http://127.0.0.1:8025",
    [string]$DeviceToken = $env:WOKWI_INGESTION_TOKEN
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""

if ([string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
    $EvidenceDirectory = Join-Path $PSScriptRoot "..\research-output\evidence"
}

New-Item -ItemType Directory -Force -Path $EvidenceDirectory | Out-Null

$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runId = "review2-$runStamp-$([guid]::NewGuid().ToString('N').Substring(0, 8))"
$correlationHeaders = @{ "X-Correlation-ID" = $runId }
$script:adminHeaders = $null
$script:adminRefreshAtUtc = [datetime]::MinValue

function Get-AccessToken([string]$username, [string]$password) {
    $body = @{ grant_type = "password"; client_id = $ClientId; username = $username; password = $password }
    return Invoke-RestMethod -Method Post -Uri "$KeycloakUrl/realms/$Realm/protocol/openid-connect/token" `
        -Body $body -ContentType "application/x-www-form-urlencoded"
}

function Get-AdminHeaders {
    $nowUtc = (Get-Date).ToUniversalTime()
    if ($null -eq $script:adminHeaders -or $nowUtc -ge $script:adminRefreshAtUtc) {
        $tokenResponse = Get-AccessToken $AdminUsername $AdminPassword
        if ([string]::IsNullOrWhiteSpace([string]$tokenResponse.access_token)) {
            throw "Keycloak did not return an administrator access token."
        }
        $expiresInSeconds = 30
        if ($null -ne $tokenResponse.expires_in) {
            $expiresInSeconds = [int]$tokenResponse.expires_in
        }
        # Refresh before expiry so the polling loops remain valid when the
        # realm intentionally uses short-lived access tokens.
        $marginSeconds = [Math]::Min(5, [Math]::Max(1, [int][Math]::Floor($expiresInSeconds / 3)))
        $script:adminRefreshAtUtc = $nowUtc.AddSeconds([Math]::Max(1, $expiresInSeconds - $marginSeconds))
        $script:adminHeaders = @{ Authorization = "Bearer $($tokenResponse.access_token)"; "X-Correlation-ID" = $runId }
    }
    return $script:adminHeaders
}

function To-JsonBody([object]$Value) {
    return $Value | ConvertTo-Json -Compress -Depth 10
}

function Submit-Reading([long]$DeviceId, [double]$EnergyConsumed) {
    $payload = [ordered]@{
        deviceId       = $DeviceId
        energyConsumed = $EnergyConsumed
        timestamp      = (Get-Date).ToUniversalTime().ToString("o")
    }
    $response = Invoke-WebRequest -UseBasicParsing -Method Post `
        -Uri "$BaseUrl/ingestion" -Headers $machineHeaders -ContentType "application/json" `
        -Body (To-JsonBody $payload)
    return [ordered]@{
        payload    = $payload
        statusCode = $response.StatusCode
        submittedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    }
}

function Get-DeviceTotal([object]$Usage) {
    $devices = @($Usage.devices)
    $sum = ($devices | Measure-Object -Property energyConsumed -Sum).Sum
    if ($null -eq $sum) { return 0.0 }
    return [math]::Round([double]$sum, 2)
}

function Get-MailpitMessages {
    $response = Invoke-RestMethod -Method Get -Uri "$MailpitUrl/api/v1/messages"
    if ($null -eq $response.messages) { return @() }
    return @(
        foreach ($message in $response.messages) {
            $message
        }
    )
}

function Test-MailpitRecipient([object]$Message, [string]$Recipient) {
    if ($null -eq $Message -or $null -eq $Message.To) { return $false }
    return (@($Message.To | Where-Object { $_.Address -ieq $Recipient }).Count -gt 0)
}

if ([string]::IsNullOrWhiteSpace($DeviceToken)) {
    throw "Set WOKWI_INGESTION_TOKEN or pass -DeviceToken before running end-to-end validation."
}

$machineHeaders = @{ "X-Device-Token" = $DeviceToken; "X-Correlation-ID" = $runId }

$result = [ordered]@{
    evidenceType = "Controlled local end-to-end functional verification"
    runId = $runId
    startedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    baseUrl = $BaseUrl
    authentication = [ordered]@{
        keycloakRealm = $Realm
        setupActor = $AdminUsername
        telemetryActor = "machine-token"
    }
    testBoundary = "Synthetic REST telemetry was submitted through the same ingestion endpoint used by the Wokwi ESP32 simulator. Values are not calibrated physical-meter measurements."
    expectedAnalytics = [ordered]@{
        totalUsageKwh = 1.50
        currentEstimatedCost = 0.18
        dailyRateKwh = 0.50
        projectedMonthlyKwh = 15.00
        projectedMonthlyCost = 11.80
        rankingPercent = 100.00
        standbyBaselineWatts = 4.17
        standbyDailyKwh = 0.10
        standbyMonthlyKwh = 3.00
        standbyMonthlyCost = 0.36
        standbyRisk = "LOW"
    }
}

try {
    $result.gatewayHealth = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8080/actuator/health" -Headers $correlationHeaders

    # Controlled analytics case: one isolated household, one device, 1.50 kWh total over 3 days.
    $analyticsUserInput = [ordered]@{
        name = "Review2 Analytics $runStamp"
        surname = "Verification"
        email = "review2.analytics.$runStamp@example.test"
        address = "Controlled local verification"
        alerting = $false
        energyAlertingThreshold = 999999.0
    }
    $analyticsUser = Invoke-RestMethod -Method Post -Uri "$BaseUrl/user" -Headers (Get-AdminHeaders) `
        -ContentType "application/json" -Body (To-JsonBody $analyticsUserInput)

    $analyticsDeviceInput = [ordered]@{
        name = "Controlled Analytics Device $runStamp"
        type = "GENERAL"
        location = "Verification Lab"
        userId = $analyticsUser.id
    }
    $analyticsDevice = Invoke-RestMethod -Method Post -Uri "$BaseUrl/device" -Headers (Get-AdminHeaders) `
        -ContentType "application/json" -Body (To-JsonBody $analyticsDeviceInput)

    $analyticsStartedAt = Get-Date
    $analyticsPosts = @(0.25, 0.50, 0.75 | ForEach-Object {
        Submit-Reading -DeviceId ([long]$analyticsDevice.id) -EnergyConsumed ([double]$_)
    })

    $usageDeadline = (Get-Date).AddSeconds(90)
    do {
        Start-Sleep -Seconds 3
        $analyticsUsage = Invoke-RestMethod -Method Get -Uri "$BaseUrl/usage/$($analyticsUser.id)?days=3" -Headers (Get-AdminHeaders)
        $analyticsUsageTotal = Get-DeviceTotal $analyticsUsage
    } while ($analyticsUsageTotal -ne 1.50 -and (Get-Date) -lt $usageDeadline)

    $analyticsForecast = Invoke-RestMethod -Method Get -Uri "$BaseUrl/insight/bill-forecast/$($analyticsUser.id)?days=3" -Headers (Get-AdminHeaders)
    $analyticsRanking = Invoke-RestMethod -Method Get -Uri "$BaseUrl/insight/appliance-ranking/$($analyticsUser.id)?days=3" -Headers (Get-AdminHeaders)
    $analyticsStandby = Invoke-RestMethod -Method Get -Uri "$BaseUrl/insight/standby-detective/$($analyticsUser.id)?days=3" -Headers (Get-AdminHeaders)

    $result.analyticsCase = [ordered]@{
        user = $analyticsUser
        device = $analyticsDevice
        submissions = $analyticsPosts
        usage = $analyticsUsage
        observedUsageTotalKwh = $analyticsUsageTotal
        forecast = $analyticsForecast
        ranking = $analyticsRanking
        standby = $analyticsStandby
        endToEndAvailabilityLatencySeconds = [math]::Round(((Get-Date) - $analyticsStartedAt).TotalSeconds, 2)
        passed = [ordered]@{
            usageTotal = ($analyticsUsageTotal -eq 1.50)
            currentCost = ([math]::Round([double]$analyticsForecast.currentEstimatedCost, 2) -eq 0.18)
            dailyRate = ([math]::Round([double]$analyticsForecast.dailyRateKwh, 2) -eq 0.50)
            projectedKwh = ([math]::Round([double]$analyticsForecast.projectedMonthlyKwh, 2) -eq 15.00)
            projectedCost = ([math]::Round([double]$analyticsForecast.projectedMonthlyCost, 2) -eq 11.80)
            ranking = (@($analyticsRanking.rankings).Count -eq 1 -and [math]::Round([double]$analyticsRanking.rankings[0].percentageOfTotal, 2) -eq 100.00)
            standby = ([math]::Round([double]$analyticsStandby.baselineWatts, 2) -eq 4.17 -and $analyticsStandby.riskLevel -eq "LOW")
        }
    }

    # Controlled alert case: alerting user + 1.00 kWh > 0.10 kWh threshold.
    $alertUserInput = [ordered]@{
        name = "Review2 Alert $runStamp"
        surname = "Verification"
        email = "review2.alert.$runStamp@example.test"
        address = "Controlled local verification"
        alerting = $true
        energyAlertingThreshold = 0.10
    }
    $alertUser = Invoke-RestMethod -Method Post -Uri "$BaseUrl/user" -Headers (Get-AdminHeaders) `
        -ContentType "application/json" -Body (To-JsonBody $alertUserInput)

    $alertDeviceInput = [ordered]@{
        name = "Controlled Alert Device $runStamp"
        type = "GENERAL"
        location = "Verification Lab"
        userId = $alertUser.id
    }
    $alertDevice = Invoke-RestMethod -Method Post -Uri "$BaseUrl/device" -Headers (Get-AdminHeaders) `
        -ContentType "application/json" -Body (To-JsonBody $alertDeviceInput)

    $alertStartedAt = Get-Date
    $baselineEmailMessages = @(Get-MailpitMessages)
    $baselineEmailMessageIds = @($baselineEmailMessages | ForEach-Object { [string]$_.ID })
    $alertRecords = @()
    $matchingAlert = $null
    $mailpitMessages = @()
    $matchingMailpitMessage = $null
    $disableResponse = $null

    # Always turn the synthetic user's alerting back off, including if a
    # downstream service or mail poll fails during the controlled test.
    $disableAlertInput = [ordered]@{
        name = $alertUser.name
        surname = $alertUser.surname
        email = $alertUser.email
        address = $alertUser.address
        alerting = $false
        energyAlertingThreshold = $alertUser.energyAlertingThreshold
    }
    try {
        $alertSubmission = Submit-Reading -DeviceId ([long]$alertDevice.id) -EnergyConsumed 1.00
        $alertDeadline = (Get-Date).AddSeconds(75)
        do {
            Start-Sleep -Seconds 5
            $alertResponse = Invoke-WebRequest -UseBasicParsing -Method Get -Uri "$BaseUrl/alert/user/$($alertUser.id)" -Headers (Get-AdminHeaders)
            $alertText = [string]$alertResponse.Content
            if ([string]::IsNullOrWhiteSpace($alertText) -or $alertText.Trim() -eq "[]") {
                $alertRecords = @()
            }
            else {
                # Windows PowerShell can preserve a parsed JSON array as one
                # nested Object[] here. Flatten it before testing alert fields.
                $parsedAlertRecords = $alertText | ConvertFrom-Json
                $alertRecords = @(
                    foreach ($parsedAlert in $parsedAlertRecords) {
                        $parsedAlert
                    }
                )
            }
            $matchingAlert = $alertRecords | Where-Object {
                ([long]$_.userId -eq [long]$alertUser.id) -and
                ([string]$_.alertType -eq "THRESHOLD") -and
                ([bool]$_.sent) -and
                ([string]$_.email -ieq [string]$alertUser.email) -and
                ([math]::Abs([double]$_.threshold - 0.10) -lt 0.0001) -and
                ([double]$_.energyConsumed -ge 1.00)
            } | Select-Object -First 1
        } while ($null -eq $matchingAlert -and (Get-Date) -lt $alertDeadline)

        $mailpitDeadline = (Get-Date).AddSeconds(45)
        do {
            Start-Sleep -Seconds 3
            $mailpitMessages = @(Get-MailpitMessages)
            $matchingMailpitMessage = $mailpitMessages | Where-Object {
                ($baselineEmailMessageIds -notcontains [string]$_.ID) -and
                ([string]$_.From.Address -ieq "noreply@hometracker.com") -and
                (Test-MailpitRecipient $_ $alertUser.email) -and
                ([string]$_.Subject -eq "Energy Usage Alert for User $($alertUser.id)")
            } | Select-Object -First 1
        } while ($null -eq $matchingMailpitMessage -and (Get-Date) -lt $mailpitDeadline)
    }
    finally {
        $disableResponse = Invoke-WebRequest -UseBasicParsing -Method Put -Uri "$BaseUrl/user/$($alertUser.id)" `
            -Headers (Get-AdminHeaders) -ContentType "application/json" -Body (To-JsonBody $disableAlertInput)
    }

    $result.alertCase = [ordered]@{
        user = $alertUser
        device = $alertDevice
        submission = $alertSubmission
        expectedCondition = "1.00 kWh > 0.10 kWh"
        alertRecords = $alertRecords
        matchingThresholdAlert = $matchingAlert
        observedAlertRecordCount = $alertRecords.Count
        alertObservationLatencySeconds = [math]::Round(((Get-Date) - $alertStartedAt).TotalSeconds, 2)
        alertingDisabledStatusCode = $disableResponse.StatusCode
        alertAssertions = [ordered]@{
            matchingThresholdAlert = ($null -ne $matchingAlert)
            persistedAsSent = ($null -ne $matchingAlert -and [bool]$matchingAlert.sent)
            correctRecipient = ($null -ne $matchingAlert -and [string]$matchingAlert.email -ieq [string]$alertUser.email)
            correctThreshold = ($null -ne $matchingAlert -and [math]::Abs([double]$matchingAlert.threshold - 0.10) -lt 0.0001)
            triggerValueObserved = ($null -ne $matchingAlert -and [double]$matchingAlert.energyConsumed -ge 1.00)
        }
        mailpit = [ordered]@{
            baselineMessageCount = $baselineEmailMessages.Count
            observedMessageCount = $mailpitMessages.Count
            matchingMessage = $matchingMailpitMessage
            deliveryObserved = ($null -ne $matchingMailpitMessage)
        }
        passed = ($null -ne $matchingAlert -and $null -ne $matchingMailpitMessage -and $disableResponse.StatusCode -eq 200)
    }

    $result.completedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    $analyticsFailures = @($result.analyticsCase.passed.Values | Where-Object { -not $_ })
    $result.overallPassed = ($analyticsFailures.Count -eq 0 -and $result.alertCase.passed)
}
catch {
    $result.error = [ordered]@{
        message = $_.Exception.Message
        type = $_.Exception.GetType().FullName
    }
    $result.completedAtUtc = (Get-Date).ToUniversalTime().ToString("o")
    $result.overallPassed = $false
}

$outputPath = Join-Path $EvidenceDirectory "review2_e2e_results_$runStamp.json"
$result | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $outputPath -Encoding utf8
Write-Output $outputPath
Write-Output ($result | ConvertTo-Json -Depth 12)

if (-not $result.overallPassed) {
    exit 1
}
