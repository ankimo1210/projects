Test-Case 'T02' 'Relative traversal cannot reach outside an input' {
    $f=New-TestArchiveFixture
    try { Assert-Throws { Resolve-PhotoPath $f.OldC '..\outside.jpg' } 'PathTraversal' } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T02' 'Directory junction cannot extend the inventory boundary' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldF 'outside.jpg' 'must-not-follow'
        $junction=Join-Path $f.OldC 'external'
        $null=New-Item -ItemType Junction -Path $junction -Target $f.OldF
        Assert-Equal 0xA0000003L (Get-PhotoReparseTag $junction)
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        Assert-Equal 1 $rows.Count
        Assert-Equal 'RetainDirectoryLink' $rows[0].read_status
        Assert-Equal $null $rows[0].sha256
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T08' 'NTFS alternate streams prevent cleanup eligibility' {
    $f=New-TestArchiveFixture
    try {
        $path=New-TestFile $f.OldC 'with-stream.jpg' 'image'
        Set-Content -LiteralPath $path -Stream metadata -Value 'must-retain'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        Assert-Equal 'RetainStreams' $rows[0].read_status
        Assert-Equal 1 $rows[0].streams.Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T03' 'Equal name and size are not equal content' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'a.jpg' 'aaaa'
        $null=New-TestFile $f.OldF 'a.jpg' 'bbbb'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C','OLD_F') -HashMode Fresh -Adapters $f.Adapters)
        Assert-Equal 2 $rows.Count
        Assert-Equal 2 @($rows.sha256 | Sort-Object -Unique).Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T14' 'Fresh hashing bypasses a matching but obsolete stat cache' {
    $f=New-TestArchiveFixture
    try {
        $path=New-TestFile $f.OldC 'cache.jpg' 'aaa'
        $first=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)[0]
        $cache=@{};$cache[$path.ToLowerInvariant()]=$first
        $time=(Get-Item -LiteralPath $path).LastWriteTimeUtc
        [IO.File]::WriteAllText($path,'bbb');(Get-Item -LiteralPath $path).LastWriteTimeUtc=$time
        $cached=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Cached -Adapters $f.Adapters -HashCache $cache)[0]
        $fresh=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters -HashCache $cache)[0]
        Assert-Equal 'Cached' $cached.hash_mode
        Assert-Equal $first.sha256 $cached.sha256
        Assert-Equal 'Fresh' $fresh.hash_mode
        Assert-True ($fresh.sha256 -cne $first.sha256)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T04' 'Duplicate bytes preserve both source coordinates' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'a.jpg' 'same'
        $null=New-TestFile $f.OldF 'b.jpg' 'same'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C','OLD_F') -HashMode Fresh -Adapters $f.Adapters)
        $assets=@(New-PhotoAssets -FileRecords $rows -Metadata @(Get-TestPhotoMetadata $rows))
        Assert-Equal 2 $assets.Count
        Assert-Equal 1 @($assets.asset_id | Sort-Object -Unique).Count
        Assert-Equal 'a.jpg' $assets[0].components[0].file.relative_path
        Assert-Equal 'b.jpg' $assets[1].components[0].file.relative_path
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T05' 'Matching Live Photo identifiers bind both components' {
    $f=New-TestArchiveFixture
    try {
        $image=New-TestFile $f.OldC 'pair.heic' 'image'
        $video=New-TestFile $f.OldC 'different-name.mov' 'video'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        $meta=@([pscustomobject]@{SourceFile=$image;ContentIdentifier='live-1';DateTimeOriginal='2024:05:31 23:30:00';OffsetTimeOriginal='-07:00'},[pscustomobject]@{SourceFile=$video;ContentIdentifier='live-1'})
        $assets=@(New-PhotoAssets -FileRecords $rows -Metadata $meta)
        Assert-Equal 1 $assets.Count
        Assert-Equal 2 $assets[0].components.Count
        Assert-Equal 'Complete' $assets[0].association_status
        Assert-Equal '2024\05' $assets[0].calendar_bucket
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T06' 'AAE and incomplete Live Photo remain protected' {
    $f=New-TestArchiveFixture
    try {
        $img=New-TestFile $f.OldC 'a.heic' 'image'
        $null=New-TestFile $f.OldC 'a.aae' 'edit-version-1'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        $assets=@(New-PhotoAssets -FileRecords $rows -Metadata @([pscustomobject]@{SourceFile=$img;ContentIdentifier='missing-video'}))
        Assert-Equal 1 $assets.Count
        Assert-Equal 1 @($assets | Where-Object association_status -eq PendingAssociation).Count
        Assert-Equal 2 @($assets.components.file.relative_path).Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T07' 'Unknown date is not the file copy time' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'date.jpg' 'image'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        $asset=@(New-PhotoAssets -FileRecords $rows -Metadata @())[0]
        Assert-Equal '_undated' $asset.calendar_bucket
        Assert-Equal $null $asset.capture_offset
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T08' 'Unicode and bracket names are read literally' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC '[1]-日本語.jpg' 'original'
        $rows=@(Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C') -HashMode Fresh -Adapters $f.Adapters)
        Assert-Equal 1 $rows.Count
        Assert-Equal '[1]-日本語.jpg' $rows[0].relative_path
        Assert-Equal 'Available' $rows[0].read_status
    } finally { Remove-TestArchiveFixture $f }
}
