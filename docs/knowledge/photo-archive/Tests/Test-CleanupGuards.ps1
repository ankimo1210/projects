Test-Case 'T29' 'F alone and another path on the same disk never authorize cleanup' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $receipt -IndependentProofs @() -Adapters $f.Adapters
        Assert-Equal 0 $plan.eligible.Count
        Assert-True ($plan.retained.Count -gt 0)
        $proof=@([pscustomobject]@{kind='file';path=(Join-Path $f.OldC 'original.jpg');sha256=$receipt.committed[0].components[0].sha256;volume_id='fixture-volume';disk_id='fixture-disk'})
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $receipt -IndependentProofs $proof -Adapters $f.Adapters
        Assert-Equal 0 $plan.eligible.Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T31' 'Unaccepted daily cutover leaves every original protected' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $receipt -IndependentProofs @() -Adapters $f.Adapters
        Assert-Equal 'DailyAcceptanceMissing' $plan.blocked_reason
        Assert-Equal 0 $plan.eligible.Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T33' 'Cloud cache release is refused until deployment and recovery acceptance exist' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        Assert-Throws {Release-VerifiedCloudCache -Config $f.Config -Receipt $receipt -Adapters $f.Adapters} 'DailyAcceptanceMissing'
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.OldC 'original.jpg')))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T32' 'A cleanup plan addressing the cloud source is rejected' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $receipt -IndependentProofs @() -Adapters $f.Adapters
        $plan.eligible=@([pscustomobject]@{source_alias='ICLOUD';path=(Join-Path $f.Sync 'cloud.jpg')})
        Assert-Throws {Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan -Adapters $f.Adapters} 'CloudRootDeletionForbidden'
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T30' 'Changing a serialized cleanup decision invalidates its application' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $s.Plan -Adapters $f.Adapters
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $receipt -IndependentProofs @() -Adapters $f.Adapters
        $plan.created_at_utc='2000-01-01T00:00:00.0000000Z'
        Assert-Throws {Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan -Adapters $f.Adapters} 'CleanupPlanChanged'
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.OldC 'original.jpg')))
    } finally {Remove-TestArchiveFixture $f}
}
function New-TestIndependentCleanupScenario {
    $f=New-TestArchiveFixture
    $oldF=$f.OldF;$archive=$f.Destination
    $f.Config.destination_volume_id='fixture-F';$f.Config.destination_disk_id='fixture-disk-F'
    foreach($source in $f.Config.source_roots){$isF=$source.alias -eq 'OLD_F';$source.volume_id=if($isF){'fixture-F'}else{'fixture-C'};$source.disk_id=if($isF){'fixture-disk-F'}else{'fixture-disk-C'}}
    $f.Adapters.Volume={param($Path) $isF=(Test-PhotoPathWithin $Path $oldF) -or (Test-PhotoPathWithin $Path $archive);[pscustomobject]@{volume_id=if($isF){'fixture-F'}else{'fixture-C'};disk_id=if($isF){'fixture-disk-F'}else{'fixture-disk-C'};free_bytes=1099511627776L;cluster_bytes=131072L}}.GetNewClosure()
    $null=New-TestFile $f.OldC 'original.jpg' 'original-payload';$null=New-TestFile $f.OldF 'alias.jpg' 'original-payload'
    $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
    $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @(Get-TestPhotoMetadata $rows)) -DestinationIndex @() -Adapters $f.Adapters
    $receipt=Invoke-PhotoPlan -Config $f.Config -Plan $plan -Adapters $f.Adapters
    [pscustomobject]@{schema_version=2;archive_id=$f.Config.archive_id;manual_runs=2;scheduled_runs=1;restore_verified=$true} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $f.State 'acceptance.private.json') -Encoding UTF8
    $proof=[pscustomobject]@{kind='file';path=(Join-Path $f.OldC 'original.jpg');sha256=$rows[0].sha256;volume_id='fixture-C';disk_id='fixture-disk-C'}
    return [pscustomobject]@{Fixture=$f;Receipt=$receipt;Proof=$proof}
}
Test-Case 'T31' 'Eligible old-F duplicate is retained for seven days before deletion' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $s.Receipt -IndependentProofs @($s.Proof) -Adapters $f.Adapters
        Assert-Equal 1 $plan.eligible.Count
        $first=Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan -Adapters $f.Adapters
        Assert-Equal 1 $first.MovedToRetention;Assert-Equal 0 $first.Deleted
        $second=Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan -Adapters $f.Adapters
        Assert-Equal 1 $second.Waiting;Assert-Equal 0 $second.Deleted
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.OldC 'original.jpg')))
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'media') -File -Recurse).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T30' 'A changed original is not moved by an older cleanup plan' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $s.Receipt -IndependentProofs @($s.Proof) -Adapters $f.Adapters
        $old=Join-Path $f.OldF 'alias.jpg';[IO.File]::WriteAllText($old,'changed-original')
        Assert-Throws {Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan -Adapters $f.Adapters} 'SourceChanged'
        Assert-Equal 'changed-original' ([IO.File]::ReadAllText($old))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T37' 'A planned deletion cannot be the proof for another planned deletion' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan -Config $f.Config -Receipt $s.Receipt -IndependentProofs @($s.Proof) -Adapters $f.Adapters
        # Source C cannot be discarded because its supposed independent proof is on F.
        Assert-Equal 0 @($plan.eligible | Where-Object source_alias -eq OLD_C).Count
        Assert-Equal 1 @($plan.retained | Where-Object source_alias -eq OLD_C).Count
        Assert-Equal 1 @($plan.eligible | Where-Object source_alias -eq OLD_F).Count
    } finally {Remove-TestArchiveFixture $f}
}
