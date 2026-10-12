function New-TestCopyScenario {
    $f=New-TestArchiveFixture
    $null=New-TestFile $f.OldC 'original.jpg' 'original-payload'
    $null=New-TestFile $f.OldF 'alias.jpg' 'original-payload'
    $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
    $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters
    return [pscustomobject]@{Fixture=$f;Plan=$plan}
}
Test-Case 'T13' 'Changed source refuses copying before a committed receipt exists' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        [IO.File]::WriteAllText((Join-Path $f.OldC 'original.jpg'),'changed-source')
        Assert-Throws { Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters } 'SourceChanged'
        Assert-Equal 'changed-source' ([IO.File]::ReadAllText((Join-Path $f.OldC 'original.jpg')))
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T14' 'Fresh verification detects same-size same-time corruption' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        Assert-Equal $true (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh -Adapters $f.Adapters).valid
        $path=Join-Path $f.Destination $receipt.committed[0].components[0].destination_relative_path
        $time=(Get-Item -LiteralPath $path).LastWriteTimeUtc
        [IO.File]::WriteAllText($path,'tampered-payload')
        (Get-Item -LiteralPath $path).LastWriteTimeUtc=$time
        Assert-Equal $false (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh -Adapters $f.Adapters).valid
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T15' 'Matching partial bytes resume without changing the source' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        Initialize-PhotoArchive -Config $f.Config -Adapters $f.Adapters
        $partial=Get-PhotoStagePath -Config $f.Config -Plan $s.Plan -Action $s.Plan.actions[0] -ComponentIndex 0
        $null=New-Item -ItemType Directory -Path (Split-Path -Parent $partial) -Force
        [IO.File]::WriteAllText($partial,'original-')
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        Assert-Equal 1 $receipt.new_files
        $path=Join-Path $f.Destination $receipt.committed[0].components[0].destination_relative_path
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText($path))
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.OldC 'original.jpg')))
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T15' 'Publish before receipt interruption is recovered by reading bytes' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        Initialize-PhotoArchive -Config $f.Config -Adapters $f.Adapters
        $path=Join-Path $f.Destination $s.Plan.actions[0].components[0].destination_relative_path
        $null=New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force
        [IO.File]::WriteAllText($path,'original-payload')
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        Assert-Equal 0 $receipt.new_files
        Assert-Equal 1 $receipt.committed.Count
        Assert-Equal $true (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh -Adapters $f.Adapters).valid
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T16' 'A partial receipt line is never promoted to a completed asset' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $journal=@(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'receipts') -File)[0].FullName
        [IO.File]::AppendAllText($journal,'{"incomplete":',[Text.UTF8Encoding]::new($false))
        $index=Get-PhotoReceiptIndex -Config $f.Config -Adapters $f.Adapters
        Assert-Equal 1 $index.assets.Count
        Assert-Equal 1 $index.invalid_lines
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T17' 'Applying the same plan twice creates no extra media files' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $first=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $second=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        Assert-Equal 1 $first.new_files
        Assert-Equal 0 $second.new_files
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -Recurse -File).Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T18' 'Both original coordinates are restored, with conflicts rejected' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $restore=Restore-PhotoSources -Config $f.Config -Receipt $receipt -DestinationRoot $f.Restore -Adapters $f.Adapters
        Assert-Equal 2 $restore.files
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.Restore 'OLD_C\original.jpg')))
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.Restore 'OLD_F\alias.jpg')))
        [IO.File]::WriteAllText((Join-Path $f.Restore 'OLD_C\original.jpg'),'different')
        Assert-Throws { Restore-PhotoSources -Config $f.Config -Receipt $receipt -DestinationRoot $f.Restore -Adapters $f.Adapters } 'RestoreConflict'
    } finally { Remove-TestArchiveFixture $f }
}
