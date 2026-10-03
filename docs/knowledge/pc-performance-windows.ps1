param(
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$taskResults = [ordered]@{
    schema_version = 1
    started_at_utc = [DateTime]::UtcNow.ToString('o')
    power_plan = ((powercfg /getactivescheme) -replace '^.*?\((.*)\)\s*$', '$1')
    cpu_load_percent_before = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -EQ '_Total').PercentProcessorTime
    memory_speed_MTs = @(Get-CimInstance Win32_PhysicalMemory | Select-Object -ExpandProperty ConfiguredClockSpeed)
    network_adapters = @(Get-NetAdapter -Physical | Select-Object InterfaceDescription, Status, LinkSpeed)
    powershell_version = $PSVersionTable.PSVersion.ToString()
    script_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    measurements = @()
    unavailable = @()
}

# Describe the default route by label only; never save a private gateway address.
$taskRoutes = @(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Where-Object { $_.NextHop -ne '0.0.0.0' } | Sort-Object RouteMetric)
$taskTargets = [ordered]@{ cloudflare = '1.1.1.1'; google = '8.8.8.8' }
if ($taskRoutes.Count -gt 0) { $taskTargets = [ordered]@{ default_gateway = $taskRoutes[0].NextHop; cloudflare = '1.1.1.1'; google = '8.8.8.8' } }
$taskPing = [System.Net.NetworkInformation.Ping]::new()
try {
    foreach ($taskEntry in $taskTargets.GetEnumerator()) {
        $taskSamples = @()
        $taskLost = 0
        for ($taskIndex = 0; $taskIndex -lt 5; $taskIndex++) {
            try {
                $taskReply = $taskPing.Send($taskEntry.Value, 2000)
                if ($taskReply.Status -eq 'Success') { $taskSamples += $taskReply.RoundtripTime } else { $taskLost++ }
            } catch { $taskLost++ }
        }
        $taskResults.measurements += [ordered]@{ name = "ping_$($taskEntry.Key)"; unit = 'ms'; samples = $taskSamples; lost = $taskLost; sent = 5; timer_resolution_ms = 1 }
    }
} finally { $taskPing.Dispose() }

$taskDownload = @()
for ($taskIndex = 0; $taskIndex -lt 3; $taskIndex++) {
    $taskCurl = & curl.exe --silent --show-error --fail --connect-timeout 10 --max-time 30 --output NUL --write-out '%{http_code},%{size_download},%{speed_download},%{time_connect},%{time_appconnect},%{time_starttransfer},%{time_total}' 'https://speed.cloudflare.com/__down?bytes=10000000'
    if ($LASTEXITCODE -ne 0) { $taskResults.unavailable += 'Cloudflare download failed'; break }
    $taskParts = ($taskCurl -join '').Split(',')
    if ($taskParts.Count -ne 7 -or $taskParts[0] -ne '200' -or [long]$taskParts[1] -ne 10000000) { throw 'Unexpected download response' }
    $taskDownload += [ordered]@{ bytes = [long]$taskParts[1]; megabytes_per_second = [double]$taskParts[2] / 1000000; megabits_per_second = [double]$taskParts[2] * 8 / 1000000; connect_s = [double]$taskParts[3]; TLS_s = [double]$taskParts[4]; TTFB_s = [double]$taskParts[5]; total_s = [double]$taskParts[6] }
}
$taskResults.measurements += [ordered]@{ name = 'cloudflare_10MB_download'; samples = $taskDownload; requested_total_bytes = 30000000 }

Push-Location -LiteralPath ([System.IO.Path]::GetTempPath())
try {
    foreach ($taskKind in @('native_cmd', 'wsl_true')) {
        $taskTimes = @()
        for ($taskIndex = 0; $taskIndex -lt 7; $taskIndex++) {
            $taskTimer = [System.Diagnostics.Stopwatch]::StartNew()
            if ($taskKind -eq 'native_cmd') { & $env:ComSpec /d /c exit 0 } else { & wsl.exe -d Ubuntu --cd /tmp --exec /bin/true }
            $taskTimer.Stop()
            if ($LASTEXITCODE -ne 0) { throw "Process boundary check failed: $taskKind" }
            if ($taskIndex -ge 2) { $taskTimes += $taskTimer.Elapsed.TotalMilliseconds }
        }
        $taskResults.measurements += [ordered]@{ name = "launch_$taskKind"; unit = 'ms'; samples = $taskTimes; warmups = 2; wsl_already_running = $true }
    }
} finally { Pop-Location }

$taskResults.gpu_idle_snapshot_after = (& nvidia-smi.exe --query-gpu=temperature.gpu,power.draw,pcie.link.gen.max,pcie.link.width.max --format=csv,noheader) -join ''
try {
    $taskOllama = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 2
    $taskResults.ollama_model_count = @($taskOllama.models).Count
    $taskResults.unavailable += 'No LLM inference benchmark ran; tokens/s unmeasured'
} catch {
    $taskResults.unavailable += 'Ollama local API unavailable; no model tokens/s measured'
}
$taskResults.completed_at_utc = [DateTime]::UtcNow.ToString('o')
$taskResults.status = 'ok'
$taskResults | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
Write-Output 'Windows network and process-boundary measurements saved.'
