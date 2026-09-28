# Record the default IPv4 adapter's network health over time on Windows. Stop with Ctrl+C.
# Example:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\network-monitor.ps1 -MaxSamples 5
# The default download test transfers 10 MB every 30 minutes (about 480 MB/day).
# A slow result also triggers a 10 MB check against Google (up to 960 MB/day total).
# One-second, multi-target ping history is recorded by network-ping-monitor.ps1.
# Set -DownloadEverySamples 0 to disable download tests.

[CmdletBinding()]
param(
    [ValidateRange(5, 3600)][int]$IntervalSeconds = 60,
    [ValidateRange(0, 1000000)][int]$MaxSamples = 0,
    [ValidateRange(0, 1000000)][int]$DownloadEverySamples = 30,
    [ValidateRange(1000000, 100000000)][int]$DownloadBytes = 10000000,
    [ValidateRange(1, 1000)][int]$LowSpeedThresholdMbps = 150,
    [string]$OutputPath = (Join-Path $env:LOCALAPPDATA 'NetworkMonitor\network-history-detailed.csv')
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
    param([string]$Url, [switch]$Head, [int]$RangeBytes = 0)

    $curlArgs = @(
        '--location', '--silent', '--show-error', '--output', 'NUL',
        '--connect-timeout', '5', '--max-time', '25',
        '--write-out', '%{http_code}|%{time_namelookup}|%{time_connect}|%{time_appconnect}|%{time_starttransfer}|%{time_total}|%{speed_download}|%{size_download}'
    )
    if ($Head) { $curlArgs += '--head' }
    if ($RangeBytes -gt 0) {
        $curlArgs += @('--range', "0-$($RangeBytes - 1)", '--max-filesize', "$RangeBytes")
    }
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
    if ($parts.Count -ne 8) {
        return [pscustomobject]@{
            ExitCode = $exitCode; HttpCode = $null; DnsMs = $null; TcpMs = $null
            TlsMs = $null; WaitAfterTlsMs = $null; FirstByteMs = $null
            BodyMs = $null; TotalMs = $null; Mbps = $null; Bytes = $null
        }
    }

    $culture = [System.Globalization.CultureInfo]::InvariantCulture
    $styles = [System.Globalization.NumberStyles]::Float
    $values = New-Object 'double[]' 7
    $valid = $true
    for ($i = 0; $i -lt 7; $i++) {
        $parsed = [double]0
        if (-not [double]::TryParse($parts[$i + 1], $styles, $culture, [ref]$parsed)) {
            $valid = $false
        } else {
            $values[$i] = $parsed
        }
    }
    if (-not $valid) {
        return [pscustomobject]@{
            ExitCode = $exitCode; HttpCode = $parts[0]; DnsMs = $null; TcpMs = $null
            TlsMs = $null; WaitAfterTlsMs = $null; FirstByteMs = $null
            BodyMs = $null; TotalMs = $null; Mbps = $null; Bytes = $null
        }
    }

    $sizeMatchesRange = ($RangeBytes -eq 0 -or [int64]$values[6] -eq $RangeBytes)
    return [pscustomobject]@{
        ExitCode = $exitCode
        HttpCode = $parts[0]
        DnsMs = [Math]::Round($values[0] * 1000, 1)
        TcpMs = [Math]::Round(($values[1] - $values[0]) * 1000, 1)
        TlsMs = [Math]::Round(($values[2] - $values[1]) * 1000, 1)
        WaitAfterTlsMs = [Math]::Round(($values[3] - $values[2]) * 1000, 1)
        FirstByteMs = [Math]::Round($values[3] * 1000, 1)
        BodyMs = [Math]::Round(($values[4] - $values[3]) * 1000, 1)
        TotalMs = [Math]::Round($values[4] * 1000, 1)
        Mbps = if ($exitCode -eq 0 -and $parts[0] -in @('200', '206') -and $values[6] -gt 0 -and $sizeMatchesRange) {
            [Math]::Round($values[5] * 8 / 1000000, 1)
        } else { $null }
        Bytes = [int64]$values[6]
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
$previousStatsAt = $null
$previousReceivedBytes = $null
$previousSentBytes = $null
while ($true) {
    $started = Get-Date
    $sample++
    $timestamp = [DateTimeOffset]::Now.ToString('o')

    $adapter = Get-NetAdapter | Where-Object { $_.ifIndex -eq $interfaceIndex } | Select-Object -First 1
    $statistics = $null
    if ($adapter) {
        try { $statistics = Get-NetAdapterStatistics -Name $adapter.Name } catch { }
    }
    $receivedMbps = $null
    $sentMbps = $null
    if ($statistics -and $previousStatsAt) {
        $seconds = ($started - $previousStatsAt).TotalSeconds
        $receivedDelta = [int64]$statistics.ReceivedBytes - $previousReceivedBytes
        $sentDelta = [int64]$statistics.SentBytes - $previousSentBytes
        if ($seconds -gt 0 -and $receivedDelta -ge 0 -and $sentDelta -ge 0) {
            $receivedMbps = [Math]::Round($receivedDelta * 8 / $seconds / 1000000, 2)
            $sentMbps = [Math]::Round($sentDelta * 8 / $seconds / 1000000, 2)
        }
    }
    if ($statistics) {
        $previousStatsAt = $started
        $previousReceivedBytes = [int64]$statistics.ReceivedBytes
        $previousSentBytes = [int64]$statistics.SentBytes
    }

    $gatewayPing = Measure-Icmp -Target $gateway
    $internetPing = Measure-Icmp -Target '1.1.1.1'
    $dns = Measure-Dns
    $https = Invoke-CurlProbe -Url 'https://www.cloudflare.com/' -Head
    $googleHttps = Invoke-CurlProbe -Url 'https://www.google.com/generate_204'

    $download = $null
    $verifyDownload = $null
    if ($DownloadEverySamples -gt 0 -and (($sample - 1) % $DownloadEverySamples) -eq 0) {
        $download = Invoke-CurlProbe -Url "https://speed.cloudflare.com/__down?bytes=$DownloadBytes"
        if ($null -eq $download.Mbps -or $download.Mbps -lt $LowSpeedThresholdMbps) {
            $verifyDownload = Invoke-CurlProbe -Url 'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb' -RangeBytes $DownloadBytes
        }
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
        https_dns_ms = $https.DnsMs
        https_tcp_ms = $https.TcpMs
        https_tls_ms = $https.TlsMs
        https_wait_after_tls_ms = $https.WaitAfterTlsMs
        https_first_byte_ms = $https.FirstByteMs
        https_total_ms = $https.TotalMs
        google_https_http_code = $googleHttps.HttpCode
        google_https_exit_code = $googleHttps.ExitCode
        google_https_first_byte_ms = $googleHttps.FirstByteMs
        google_https_total_ms = $googleHttps.TotalMs
        download_expected_bytes = $DownloadBytes
        low_speed_threshold_mbps = $LowSpeedThresholdMbps
        download_http_code = if ($download) { $download.HttpCode } else { $null }
        download_exit_code = if ($download) { $download.ExitCode } else { $null }
        download_dns_ms = if ($download) { $download.DnsMs } else { $null }
        download_tcp_ms = if ($download) { $download.TcpMs } else { $null }
        download_tls_ms = if ($download) { $download.TlsMs } else { $null }
        download_wait_after_tls_ms = if ($download) { $download.WaitAfterTlsMs } else { $null }
        download_first_byte_ms = if ($download) { $download.FirstByteMs } else { $null }
        download_body_ms = if ($download) { $download.BodyMs } else { $null }
        download_mbps = if ($download) { $download.Mbps } else { $null }
        download_bytes = if ($download) { $download.Bytes } else { $null }
        download_total_ms = if ($download) { $download.TotalMs } else { $null }
        verify_http_code = if ($verifyDownload) { $verifyDownload.HttpCode } else { $null }
        verify_exit_code = if ($verifyDownload) { $verifyDownload.ExitCode } else { $null }
        verify_first_byte_ms = if ($verifyDownload) { $verifyDownload.FirstByteMs } else { $null }
        verify_body_ms = if ($verifyDownload) { $verifyDownload.BodyMs } else { $null }
        verify_mbps = if ($verifyDownload) { $verifyDownload.Mbps } else { $null }
        verify_bytes = if ($verifyDownload) { $verifyDownload.Bytes } else { $null }
        received_mbps = $receivedMbps
        sent_mbps = $sentMbps
        received_packet_errors = if ($statistics) { $statistics.ReceivedPacketErrors } else { $null }
        outbound_packet_errors = if ($statistics) { $statistics.OutboundPacketErrors } else { $null }
        received_discarded_packets = if ($statistics) { $statistics.ReceivedDiscardedPackets } else { $null }
        outbound_discarded_packets = if ($statistics) { $statistics.OutboundDiscardedPackets } else { $null }
    }
    $row | Export-Csv -Path $OutputPath -NoTypeInformation -Append -Encoding UTF8

    $speedText = if ($download -and $null -ne $download.Mbps) { "$($download.Mbps) Mbps" } else { '-' }
    Write-Host "$timestamp gateway loss=$($gatewayPing.LossPct)% internet loss=$($internetPing.LossPct)% HTTPS=$($https.HttpCode)/$($googleHttps.HttpCode) download=$speedText"

    if ($MaxSamples -gt 0 -and $sample -ge $MaxSamples) { break }
    $remaining = $IntervalSeconds - ((Get-Date) - $started).TotalSeconds
    if ($remaining -gt 0) { Start-Sleep -Milliseconds ([int]($remaining * 1000)) }
}
