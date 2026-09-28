# Record simultaneous ping results and local adapter traffic once per second.
# Run alongside network-monitor.ps1. Stop with Ctrl+C.
# The CSV rotates at midnight in the local Windows time zone.

[CmdletBinding()]
param(
    [ValidateRange(1, 60)][int]$IntervalSeconds = 1,
    [ValidateRange(100, 5000)][int]$PingTimeoutMs = 900,
    [ValidateRange(0, 1000000)][int]$MaxSamples = 0,
    [string]$OutputDirectory = (Join-Path $env:LOCALAPPDATA 'NetworkMonitor')
)

$ErrorActionPreference = 'Stop'

$route = Get-NetRoute -AddressFamily IPv4 -DestinationPrefix '0.0.0.0/0' |
    Where-Object { $_.NextHop -and $_.NextHop -ne '0.0.0.0' } |
    Sort-Object { $_.RouteMetric + $_.InterfaceMetric } |
    Select-Object -First 1
if (-not $route) { throw 'No IPv4 default gateway found.' }

$interfaceIndex = $route.InterfaceIndex
$adapter = Get-NetAdapter | Where-Object { $_.ifIndex -eq $interfaceIndex } | Select-Object -First 1
if (-not $adapter) { throw "No network adapter found for interface $interfaceIndex." }

$targets = @(
    [pscustomobject]@{ Name = 'gateway'; Address = $route.NextHop },
    [pscustomobject]@{ Name = 'cloudflare'; Address = '1.1.1.1' },
    [pscustomobject]@{ Name = 'google'; Address = '8.8.8.8' }
)
$pingClients = @{}
foreach ($target in $targets) {
    $pingClients[$target.Name] = New-Object System.Net.NetworkInformation.Ping
}

$OutputDirectory = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
Write-Host "Monitoring $($adapter.Name) every $IntervalSeconds second(s). CSV directory: $OutputDirectory"
Write-Host 'Press Ctrl+C to stop.'

$sample = 0
$previousStatsAt = $null
$previousReceivedBytes = $null
$previousSentBytes = $null
try {
    while ($true) {
        $started = Get-Date
        $timestamp = [DateTimeOffset]::Now.ToString('o')
        $sample++

        $tasks = @{}
        $statuses = @{}
        $rtts = @{}
        foreach ($target in $targets) {
            try {
                $tasks[$target.Name] = $pingClients[$target.Name].SendPingAsync($target.Address, $PingTimeoutMs)
            } catch {
                $statuses[$target.Name] = "SendError:$($_.Exception.GetType().Name)"
            }
        }
        foreach ($target in $targets) {
            if (-not $tasks.ContainsKey($target.Name)) { continue }
            try {
                $reply = $tasks[$target.Name].GetAwaiter().GetResult()
                $statuses[$target.Name] = $reply.Status.ToString()
                if ($reply.Status -eq [System.Net.NetworkInformation.IPStatus]::Success) {
                    $rtts[$target.Name] = [double]$reply.RoundtripTime
                }
            } catch {
                $statuses[$target.Name] = "ReceiveError:$($_.Exception.GetType().Name)"
            }
        }

        $currentAdapter = Get-NetAdapter | Where-Object { $_.ifIndex -eq $interfaceIndex } | Select-Object -First 1
        $statistics = $null
        if ($currentAdapter) {
            try { $statistics = Get-NetAdapterStatistics -Name $currentAdapter.Name } catch { }
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

        $row = [pscustomobject][ordered]@{
            timestamp = $timestamp
            adapter = if ($currentAdapter) { $currentAdapter.Name } else { $null }
            link_status = if ($currentAdapter) { $currentAdapter.Status } else { 'Missing' }
            gateway_status = $statuses['gateway']
            gateway_ms = $rtts['gateway']
            cloudflare_status = $statuses['cloudflare']
            cloudflare_ms = $rtts['cloudflare']
            google_status = $statuses['google']
            google_ms = $rtts['google']
            received_mbps = $receivedMbps
            sent_mbps = $sentMbps
            received_packet_errors = if ($statistics) { $statistics.ReceivedPacketErrors } else { $null }
            outbound_packet_errors = if ($statistics) { $statistics.OutboundPacketErrors } else { $null }
            received_discarded_packets = if ($statistics) { $statistics.ReceivedDiscardedPackets } else { $null }
            outbound_discarded_packets = if ($statistics) { $statistics.OutboundDiscardedPackets } else { $null }
        }
        $outputPath = Join-Path $OutputDirectory ("network-ping-detailed-{0:yyyyMMdd}.csv" -f $started)
        $row | Export-Csv -Path $outputPath -NoTypeInformation -Append -Encoding UTF8

        if ($row.gateway_status -ne 'Success' -or
            $row.cloudflare_status -ne 'Success' -or
            $row.google_status -ne 'Success') {
            Write-Host "$timestamp gateway=$($row.gateway_status) cloudflare=$($row.cloudflare_status) google=$($row.google_status)"
        }

        if ($MaxSamples -gt 0 -and $sample -ge $MaxSamples) { break }
        $remaining = $IntervalSeconds - ((Get-Date) - $started).TotalSeconds
        if ($remaining -gt 0) { Start-Sleep -Milliseconds ([int]($remaining * 1000)) }
    }
} finally {
    foreach ($target in $targets) { $pingClients[$target.Name].Dispose() }
}
