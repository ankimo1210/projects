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
Test-Case 'T17' 'A separate process holding the mutex prevents a second copy job' {
    $s=New-TestCopyScenario;$f=$s.Fixture;$worker=$null
    try {
        $scriptPath=Join-Path $f.State 'hold-mutex.ps1';$ready=Join-Path $f.State 'ready.txt'
        $body=@'
param([string]$Name,[string]$Ready)
$m=[Threading.Mutex]::new($false,$Name)
try { $null=$m.WaitOne();[IO.File]::WriteAllText($Ready,'ready');while($true){Start-Sleep -Milliseconds 100} }
finally {$m.ReleaseMutex();$m.Dispose()}
'@
        [IO.File]::WriteAllText($scriptPath,$body,[Text.UTF8Encoding]::new($true))
        $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $worker=Start-Process -WindowStyle Hidden -FilePath $exe -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$scriptPath+'"'),'-Name',('"'+$f.Config.mutex_name+'"'),'-Ready',('"'+$ready+'"')) -PassThru
        $workerStart=$worker.StartTime
        $timer=[Diagnostics.Stopwatch]::StartNew()
        while(-not(Test-Path -LiteralPath $ready) -and $timer.Elapsed.TotalSeconds -lt 10){Start-Sleep -Milliseconds 50}
        Assert-True (Test-Path -LiteralPath $ready) 'worker owns mutex'
        Assert-Throws {Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters} 'AlreadyRunning'
        Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Destination -File -Recurse).Count
    } finally {
        if($worker -and -not $worker.HasExited) {
            $current=Get-Process -Id $worker.Id
            if($current.StartTime -ne $workerStart){throw 'WorkerIdentityChanged'}
            Stop-Process -Id $worker.Id;$worker.WaitForExit()
        }
        Remove-TestArchiveFixture $f
    }
}
Test-Case 'T15' 'Incorrect partial bytes are retained and never become committed media' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        Initialize-PhotoArchive -Config $f.Config -Adapters $f.Adapters
        $partial=Get-PhotoStagePath -Config $f.Config -Plan $s.Plan -Action $s.Plan.actions[0] -ComponentIndex 0
        $null=New-Item -ItemType Directory -Path (Split-Path -Parent $partial) -Force
        [IO.File]::WriteAllText($partial,'bad-data')
        Assert-Throws {Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters} 'InvalidPartialCopy'
        Assert-Equal 'bad-data' ([IO.File]::ReadAllText($partial))
        Assert-Equal 0 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T18' 'An empty file still has a verified restoration mapping' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'empty.jpg' ''
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $plan -Adapters $f.Adapters
        Assert-Equal 1 $receipt.new_files
        Assert-Equal $true (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh -Adapters $f.Adapters).valid
        Assert-Equal 0L @($receipt.committed[0].components)[0].size_bytes
    } finally {Remove-TestArchiveFixture $f}
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
