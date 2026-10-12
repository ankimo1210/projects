function Set-TestCloudAdapters($Fixture,[string]$Initial='Available') {
    $state=[pscustomobject]@{status=$Initial;calls=0;acquire_result='Available'}
    $Fixture.Adapters.CloudStatus={param($Path) [pscustomobject]@{status=$state.status;is_placeholder=$true;in_sync=($state.status -ne 'NotInSync');partial=($state.status -eq 'OnlineOnly');locally_available=($state.status -eq 'Available');on_disk_bytes=0L;validated_bytes=0L}}.GetNewClosure()
    $Fixture.Adapters.Hydrate={param($Path,$TimeoutSeconds) $state.calls++;if($state.acquire_result -eq 'Available'){$state.status='Available'};[pscustomobject]@{status=$state.acquire_result;hresult=0;unsettled=$false}}.GetNewClosure()
    $Fixture.Adapters.Metadata={param($Files,$ToolReceipt) @()}
    return $state
}
Test-Case 'T19' 'Timeout remains pending and bounded retries never commit a placeholder' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'pending.jpg' 'real-payload'
        $rows=@(Get-PhotoInventory $f.Config @('ICLOUD') Fresh $f.Adapters)
        $cloud=Set-TestCloudAdapters $f 'OnlineOnly';$cloud.acquire_result='Pending'
        $result=Ensure-CloudFileAvailable -Config $f.Config -FileRecord $rows[0] -Adapters $f.Adapters
        Assert-Equal 'Pending' $result.status
        Assert-Equal 2 $cloud.calls
        Assert-Equal 0 $result.committed_files
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T19' 'Completed acquisition is read again before it becomes an archive file' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'pending.jpg' 'real-payload'
        $null=Set-TestCloudAdapters $f 'OnlineOnly'
        $result=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 1 $result.Copied
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
        Assert-Equal 'real-payload' ([IO.File]::ReadAllText(@(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse)[0].FullName))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T20' 'Unvalidated cloud data is retained and not counted as a success' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'unvalidated.jpg' 'keep-this'
        $null=Set-TestCloudAdapters $f 'NotInSync'
        $result=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 0 $result.Copied
        Assert-True ($result.Pending -gt 0)
        Assert-Equal 'PendingIncomplete' $result.Status
        Assert-Equal 'keep-this' ([IO.File]::ReadAllText((Join-Path $f.Sync 'unvalidated.jpg')))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T21' 'Missing destination skips without making a replacement on C' {
    $f=New-TestArchiveFixture
    try {
        $null=Set-TestCloudAdapters $f
        $f.Adapters.Volume={param($Path) throw 'MissingArchiveDrive'}
        $result=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 'SkippedMissingDrive' $result.Status
        Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Destination -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T20' 'Cloud validation lost after snapshot refuses committing the bytes' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'changed-validation.jpg' 'original-bytes'
        $cloud=Set-TestCloudAdapters $f
        $f.Adapters.Metadata={param($Files,$ToolReceipt) $cloud.status='NotInSync';@()}.GetNewClosure()
        Assert-Throws {Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters} 'CloudSourceNotReady'
        Assert-Equal 0 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T22' 'A missing Live Photo companion is stored with explicit incompleteness' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'live.heic' 'real-image-bytes'
        $null=Set-TestCloudAdapters $f
        $f.Adapters.Metadata={param($Files,$ToolReceipt) [pscustomobject]@{SourceFile=$Files[0].full_path;ContentIdentifier='missing-companion'}}
        $result=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 1 $result.Copied
        Assert-True ($result.Pending -gt 0)
        Assert-Equal $false $result.FullLibraryVerified
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T23' 'New arrivals after snapshot are reported for the next run' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'before.jpg' 'before'
        $null=Set-TestCloudAdapters $f
        $sync=$f.Sync
        $f.Adapters.Metadata={param($Files,$ToolReceipt) [IO.File]::WriteAllText((Join-Path $sync 'after.jpg'),'after');@()}.GetNewClosure()
        $result=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 1 $result.Copied
        Assert-Equal 1 $result.NewAfterSnapshot
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T24' 'Changed inputs create versions and deleted inputs leave archive bytes intact' {
    $f=New-TestArchiveFixture
    try {
        $path=New-TestFile $f.Sync 'version.jpg' 'version-one'
        $null=Set-TestCloudAdapters $f
        $null=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        [IO.File]::WriteAllText($path,'version-two')
        $second=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 1 $second.Copied
        Remove-Item -LiteralPath $path
        $third=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 0 $third.Copied
        Assert-Equal 2 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T24' 'Thirty-day verification catches corruption hidden by ordinary stat caches' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'monthly.jpg' 'first-bytes'
        $null=Set-TestCloudAdapters $f
        $null=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        $state=Read-PhotoCheckpoint -Config $f.Config
        $state.last_full_verified_utc=[DateTime]::UtcNow.AddDays(-31).ToString('o')
        Save-PhotoCheckpoint -Config $f.Config -State $state | Out-Null
        $file=@(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse)[0]
        $time=$file.LastWriteTimeUtc;[IO.File]::WriteAllText($file.FullName,'other-bytes');$file.LastWriteTimeUtc=$time
        Assert-Throws {Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters} 'ArchiveIntegrityChanged'
        Assert-Equal 'other-bytes' ([IO.File]::ReadAllText($file.FullName))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T16' 'Corrupt checkpoint payload cannot authorize cached success' {
    $f=New-TestArchiveFixture
    try {
        $null=Set-TestCloudAdapters $f
        $state=New-PhotoCheckpoint
        $path=Save-PhotoCheckpoint -Config $f.Config -State $state
        [IO.File]::AppendAllText($path,'invalid')
        Assert-Throws {Read-PhotoCheckpoint -Config $f.Config} 'CheckpointCorrupt'
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T24' 'Unchanged daily inputs reuse metadata without making extra archive files' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.Sync 'cached.jpg' 'unchanged'
        $null=Set-TestCloudAdapters $f
        $null=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        $f.Adapters.Metadata={param($Files,$ToolReceipt) if($Files.Count){throw 'Unchanged metadata should be cached'};@()}
        $second=Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 0 $second.Copied
        Assert-Equal 'SnapshotVerified' $second.Status
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
