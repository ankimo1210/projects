# Record wired network health over time on Windows. Stop with Ctrl+C.
# Example:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1 -MaxSamples 5
# The default download test transfers 10 MB every 30 minutes (about 480 MB/day).
# Set -DownloadEverySamples 0 to disable download tests.

[CmdletBinding()]
param(
    [ValidateRange(5, 3600)][int]$IntervalSeconds = 60,
    [ValidateRange(0, 1000000)][int]$MaxSamples = 0,
    [ValidateRange(0, 1000000)][int]$DownloadEverySamples = 30,
    [ValidateRange(1000000, 100000000)][int]$DownloadBytes = 10000000,
    [string]$OutputPath = (Join-Path $env:LOCALAPPDATA 'NetworkMonitor\network-history.csv')
)

$ErrorActionPreference = 'Stop'

function Measure-Icmp {
    param([string]$Target)

    $times = @()
    $pinger = New-Object System.Net.NetworkInformation.Ping
    try {
        for ($i = 0; $i -lt 3; $i++) {
            try {
                $reply = $pinger.Send($Target, 1000)
                if ($reply.Status -eq [System.Net.NetworkInformation.IPStatus]::Success) {
                    $times += [double]$reply.RoundtripTime
                }
            } catch {
                # Treat a failed ping as packet loss and continue monitoring.
            }
            if ($i -lt 2) { Start-Sleep -Milliseconds 100 }
        }
    } finally {
        $pinger.Dispose()
    }

    $average = $null
    $maximum = $null
    if ($times.Count -gt 0) {
        $average = [Math]::Round(($times | Measure-Object -Average).Average, 1)
        $maximum = ($times | Measure-Object -Maximum).Maximum
    }
    return [pscustomobject]@{
        LossPct = [Math]::Round((3 - $times.Count) * 100 / 3, 1)
        AverageMs = $average
        MaximumMs = $maximum
    }
}

function Measure-Dns {
    $watch = [System.Diagnostics.Stopwatch]::StartNew()
    $ok = $false
    try {
        $addresses = [System.Net.Dns]::GetHostAddresses('www.cloudflare.com')
        $ok = $addresses.Count -gt 0
    } catch {
        # A DNS failure is recorded in the CSV.
    } finally {
        $watch.Stop()
    }
    return [pscustomobject]@{
        Ok = $ok
        Milliseconds = [Math]::Round($watch.Elapsed.TotalMilliseconds, 1)
    }
}

function Invoke-CurlProbe {
    param([string]$Url, [switch]$Head)

    $curlArgs = @(
        '--location', '--silent', '--show-error', '--output', 'NUL',
        '--connect-timeout', '5', '--max-time', '25',
        '--write-out', '%{http_code}|%{time_starttransfer}|%{time_total}|%{speed_download}'
    )
    if ($Head) { $curlArgs += '--head' }
    $curlArgs += $Url

    $raw = $null
    $exitCode = -1
    try {
        $raw = & curl.exe @curlArgs 2>$null
        $exitCode = $LASTEXITCODE
    } catch {
        # Keep recording even when curl cannot reach the server.
    }

    $parts = ([string]($raw -join '')).Trim() -split '\|'
    if ($parts.Count -ne 4) {
        return [pscustomobject]@{ ExitCode = $exitCode; HttpCode = $null; FirstByteMs = $null; TotalMs = $null; Mbps = $null }
    }

    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $styles = [System.Globalization.NumberStyles]::Float
    $firstByte = [double]0
    $total = [double]0
    $bytesPerSecond = [double]0
    $valid = [double]::TryParse($parts[1], $styles, $culture, [ref]$firstByte) -and
        [double]::TryParse($parts[2], $styles, $culture, [ref]$total) -and
        [double]::TryParse($parts[3], $styles, $culture, [ref]$bytesPerSecond)
    if (-not $valid) {
        return [pscustomobject]@{ ExitCode = $exitCode; HttpCode = $parts[0]; FirstByteMs = $null; TotalMs = $null; Mbps = $null }
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        HttpCode = $parts[0]
        FirstByteMs = [Math]::Round($firstByte * 1000, 1)
        TotalMs = [Math]::Round($total * 1000, 1)
        Mbps = if ($exitCode -eq 0 -and $parts[0] -eq '200') { [Math]::Round($bytesPerSecond * 8 / 1000000, 1) } else { $null }
    }
}

if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw 'curl.exe is required (included with current Windows versions).'
}

$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $_.NextHop -and $_.NextHop -ne '0.0.0.0' } |
    Sort-Object { $_.RouteMetric + $_.InterfaceMetric } |
    Select-Object -First 1
if (-not $route) { throw 'No IPv4 default gateway found.' }

$interfaceIndex = $route.InterfaceIndex
$gateway = $route.NextHop
$adapter = Get-NetAdapter | Where-Object { $_.ifIndex -eq $interfaceIndex } | Select-Object -First 1
if (-not $adapter) { throw "No network adapter found for interface $interfaceIndex." }

$OutputPath = [System.IO.Path]::GetFullPath($OutputPath)
$directory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Path $directory -Force | Out-Null

Write-Host "Monitoring $($adapter.Name) through gateway $gateway. CSV: $OutputPath"
Write-Host 'Press Ctrl+C to stop.'

$sample = 0
while ($true) {
    $started = Get-Date
    $sample++
    $timestamp = [DateTimeOffset]::Now.ToString('o')

    $adapter = Get-NetAdapter | Where-Object { $_.ifIndex -eq $interfaceIndex } | Select-Object -First 1
    $statistics = $null
    try { $statistics = Get-NetAdapterStatistics -Name $adapter.Name } catch { }

    $gatewayPing = Measure-Icmp -Target $gateway
    $internetPing = Measure-Icmp -Target '1.1.1.1'
    $dns = Measure-Dns
    $https = Invoke-CurlProbe -Url 'https://www.cloudflare.com/' -Head

    $download = $null
    if ($DownloadEverySamples -gt 0 -and (($sample - 1) % $DownloadEverySamples) -eq 0) {
        $download = Invoke-CurlProbe -Url "https://speed.cloudflare.com/__down?bytes=$DownloadBytes"
    }

    $row = [pscustomobject][ordered]@{
        timestamp = $timestamp
        adapter = if ($adapter) { $adapter.Name } else { $null }
        link_status = if ($adapter) { $adapter.Status } else { 'Missing' }
        link_speed = if ($adapter) { $adapter.LinkSpeed } else { $null }
        gateway = $gateway
        gateway_loss_pct = $gatewayPing.LossPct
        gateway_avg_ms = $gatewayPing.AverageMs
        gateway_max_ms = $gatewayPing.MaximumMs
        internet_loss_pct = $internetPing.LossPct
        internet_avg_ms = $internetPing.AverageMs
        internet_max_ms = $internetPing.MaximumMs
        dns_ok = $dns.Ok
        dns_ms = $dns.Milliseconds
        https_http_code = $https.HttpCode
        https_exit_code = $https.ExitCode
        https_first_byte_ms = $https.FirstByteMs
        https_total_ms = $https.TotalMs
        download_http_code = if ($download) { $download.HttpCode } else { $null }
        download_exit_code = if ($download) { $download.ExitCode } else { $null }
        download_mbps = if ($download) { $download.Mbps } else { $null }
        download_total_ms = if ($download) { $download.TotalMs } else { $null }
        received_packet_errors = if ($statistics) { $statistics.ReceivedPacketErrors } else { $null }
        outbound_packet_errors = if ($statistics) { $statistics.OutboundPacketErrors } else { $null }
        received_discarded_packets = if ($statistics) { $statistics.ReceivedDiscardedPackets } else { $null }
        outbound_discarded_packets = if ($statistics) { $statistics.OutboundDiscardedPackets } else { $null }
    }
    $row | Export-Csv -Path $OutputPath -NoTypeInformation -Append -Encoding UTF8

    $speedText = if ($download -and $null -ne $download.Mbps) { "$($download.Mbps) Mbps" } else { '-' }
    Write-Host "$timestamp gateway loss=$($gatewayPing.LossPct)% internet loss=$($internetPing.LossPct)% HTTPS=$($https.HttpCode) download=$speedText"

    if ($MaxSamples -gt 0 -and $sample -ge $MaxSamples) { break }
    $remaining = $IntervalSeconds - ((Get-Date) - $started).TotalSeconds
    if ($remaining -gt 0) { Start-Sleep -Milliseconds ([int]($remaining * 1000)) }
}
