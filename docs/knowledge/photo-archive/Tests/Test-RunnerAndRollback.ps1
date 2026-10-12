Test-Case 'T01' 'Wrong destination media creates no marker' {
    $f=New-TestArchiveFixture
    try {
        $f.Config.destination_volume_id='different-volume'
        Assert-Throws { Assert-ArchiveBindings -Config $f.Config -Adapters $f.Adapters } 'WrongVolume'
        Assert-Equal $false (Test-Path -LiteralPath (Join-Path $f.Destination 'archive-marker.json'))
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T01' 'Overlapping input and archive are rejected' {
    $f=New-TestArchiveFixture
    try {
        $f.Config.archive_root=$f.OldC
        Assert-Throws { Assert-ArchiveBindings -Config $f.Config -Adapters $f.Adapters } 'OverlappingRoots'
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T01' 'CLI config refuses fixture identifiers' {
    $f=New-TestArchiveFixture
    try {
        $path=Join-Path $f.State 'config.json'
        $f.Config | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $path -Encoding UTF8
        Assert-Throws { Read-ArchiveConfig -ConfigPath $path } 'FixtureConfigForbidden'
    } finally { Remove-TestArchiveFixture $f }
}
