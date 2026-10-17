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
Test-Case 'T01' 'Fast media checks retain a stable physical identity' {
    $f=New-TestArchiveFixture
    try {
        $one=Get-PhotoNativeVolume $f.Root
        $two=Get-PhotoNativeVolume $f.Root
        Assert-True ([string]::IsNullOrWhiteSpace($one.native_id) -eq $false)
        Assert-Equal $one.native_id $two.native_id
        Assert-True ($one.free_bytes -gt 0)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T25' 'A release with changed bytes is refused before installation' {
    $f=New-TestArchiveFixture
    try {
        $src=Join-Path $f.Root 'code-source';$null=New-Item -ItemType Directory -Path $src
        $file=New-TestFile $src 'Archive-iCloudPhotos.ps1' 'exit 0'
        $expected=@{'Archive-iCloudPhotos.ps1'=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
        [IO.File]::WriteAllText($file,'exit 99')
        Assert-Throws {Install-PhotoArchiveRelease -Config $f.Config -CodeRoot $src -ExpectedHashes $expected -Adapters $f.Adapters} 'ReleaseMismatch'
        Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Config.release_code_root -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T25' 'Verified release installation preserves source and writes exact bytes' {
    $f=New-TestArchiveFixture
    try {
        $src=Join-Path $f.Root 'code-source';$null=New-Item -ItemType Directory -Path $src
        $file=New-TestFile $src 'Archive-iCloudPhotos.ps1' 'exit 0'
        $expected=@{'Archive-iCloudPhotos.ps1'=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()}
        $result=Install-PhotoArchiveRelease -Config $f.Config -CodeRoot $src -ExpectedHashes $expected -Adapters $f.Adapters
        Assert-Equal 1 $result.Files
        Assert-Equal 'exit 0' ([IO.File]::ReadAllText((Join-Path $f.Config.release_code_root 'Archive-iCloudPhotos.ps1')))
        Assert-Equal 'exit 0' ([IO.File]::ReadAllText($file))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T26' 'Launcher switch and rollback preserve the original controls' {
    $f=New-TestArchiveFixture
    try {
        $launcher=New-TestFile $f.Root 'launcher.js' 'original-launcher'
        $configPath=New-TestFile $f.State 'config.json' '{}'
        $binding=[pscustomobject]@{task_name='fixture-task';launcher_path=$launcher;config_path=$configPath;control_files=@($launcher)}
        $binding | ConvertTo-Json | Set-Content -LiteralPath $f.Config.task_binding_file -Encoding UTF8
        $entry=New-TestFile $f.Config.release_code_root 'Archive-iCloudPhotos.ps1' 'exit 0'
        $hash=(Get-FileHash -LiteralPath $entry -Algorithm SHA256).Hash.ToLowerInvariant()
        [pscustomobject]@{schema_version=2;archive_id=$f.Config.archive_id;files=@{'Archive-iCloudPhotos.ps1'=$hash}} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $f.Config.release_code_root 'release-manifest.private.json') -Encoding UTF8
        $controlRoot=Join-Path $f.State 'controls';$null=New-Item -ItemType Directory -Path $controlRoot
        $saved=New-TestFile $controlRoot 'launcher.control' 'original-launcher'
        $receipt=[pscustomobject]@{root=$controlRoot;task_name='fixture-task';task_xml='<Task>original</Task>';copies=@([pscustomobject]@{source=$launcher;saved=$saved;sha256=(Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash})}
        $task=[pscustomobject]@{xml='<Task>original</Task>';enabled=$true}
        $f.Adapters.TaskRead={param($Name) [pscustomobject]@{xml=$task.xml;state='Ready';enabled=$task.enabled}}.GetNewClosure()
        $f.Adapters.TaskEnabled={param($Name,$Enabled) $task.enabled=$Enabled}.GetNewClosure()
        $f.Adapters.TaskRestore={param($Name,$Xml) $task.xml=$Xml;$task.enabled=$true}.GetNewClosure()
        $switch=Switch-PhotoArchiveTask -Config $f.Config -ControlReceipt $receipt -Adapters $f.Adapters
        Assert-Equal $true $switch.Switched
        Assert-Equal $true $task.enabled
        $undo=Undo-PhotoArchiveDeployment -Config $f.Config -ControlReceipt $receipt -Adapters $f.Adapters
        Assert-Equal $true $undo.Restored
        Assert-Equal 'original-launcher' ([IO.File]::ReadAllText($launcher))
        Assert-Equal '<Task>original</Task>' $task.xml
        $null=Switch-PhotoArchiveTask -Config $f.Config -ControlReceipt $receipt -Adapters $f.Adapters
        $archivePath=$f.Config.archive_root
        $f.Adapters.Volume={param($Path) if(Test-PhotoPathWithin $Path $archivePath){throw 'DriveMissing'};[pscustomobject]@{volume_id='fixture-volume';disk_id='fixture-disk';free_bytes=1099511627776L;cluster_bytes=131072L}}.GetNewClosure()
        Assert-True (Undo-PhotoArchiveDeployment -Config $f.Config -ControlReceipt $receipt -Adapters $f.Adapters).Restored 'rollback without F'
        Assert-Equal 'original-launcher' ([IO.File]::ReadAllText($launcher))
    } finally {Remove-TestArchiveFixture $f}
}
