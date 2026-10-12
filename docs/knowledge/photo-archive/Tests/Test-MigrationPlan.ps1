Test-Case 'T09' 'Changing a serialized plan invalidates its digest' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'a.jpg' 'source'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $assets=@(New-PhotoAssets $rows @())
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets $assets -DestinationIndex @() -Adapters $f.Adapters
        $roundtrip=$plan | ConvertTo-Json -Depth 32 | ConvertFrom-Json
        Assert-PlanInputs -MigrationPlan $roundtrip -Config $f.Config -Adapters $f.Adapters
        $roundtrip.actions[0].components[0].sha256='00'
        Assert-Throws { Assert-PlanInputs -MigrationPlan $roundtrip -Config $f.Config -Adapters $f.Adapters } 'PlanChanged'
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T09' 'UTC timestamps keep their precision through JSON deserialization' {
    $value=[pscustomobject]@{stamp='2026-10-12T03:00:00.1234000Z';plan_sha256=$null}
    $roundtrip=$value | ConvertTo-Json | ConvertFrom-Json
    Assert-Equal '697ceecab66c2edeaaea1fcd039522ff2c66310b356de62a24a27a1e8d550fcb' (Get-PhotoPlanHash $value)
    Assert-Equal '697ceecab66c2edeaaea1fcd039522ff2c66310b356de62a24a27a1e8d550fcb' (Get-PhotoPlanHash $roundtrip)
}
Test-Case 'T10' 'Physical capacity rounds small files and preserves free reserve' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'a.jpg' 'a'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters
        Assert-True ($plan.physical_capacity_budget.media_bytes -ge 131072L)
        Assert-Equal 34359738368L $plan.physical_capacity_budget.reserve_bytes
        Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Destination -File -Recurse).Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T11' 'Insufficient copy-first capacity aborts without changing old copies' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'a.jpg' 'first'
        $null=New-TestFile $f.OldF 'b.jpg' 'second'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
        $f.Adapters.Volume={param($Path) [pscustomobject]@{volume_id='fixture-volume';disk_id='fixture-disk';free_bytes=34359738368L;cluster_bytes=131072L}}
        Assert-Throws { New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters } 'InsufficientCapacity'
        Assert-Equal 'second' ([IO.File]::ReadAllText((Join-Path $f.OldF 'b.jpg')))
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T12' 'Same-size different contents get separate destination paths' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'same.jpg' 'aaaa'
        $null=New-TestFile $f.OldF 'same.jpg' 'bbbb'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters
        Assert-Equal 2 $plan.actions.Count
        Assert-Equal 2 @($plan.actions.components.destination_relative_path | Sort-Object -Unique).Count
    } finally { Remove-TestArchiveFixture $f }
}
Test-Case 'T11' 'An explicit capacity-limited wave preserves every excluded source' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'one.jpg' 'one'
        $null=New-TestFile $f.OldC 'two.jpg' 'two'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters -CopyBudgetBytes 131072L
        Assert-Equal 1 $plan.actions.Count
        Assert-Equal 2 $plan.source_disposition.Count
        Assert-Equal 1 @($plan.source_disposition | Where-Object reason -eq RetainCapacity).Count
        Assert-Equal 2 @(Get-ChildItem -LiteralPath $f.OldC -File).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T04' 'Byte-identical aliases create one action and two recoverable mappings' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'one.jpg' 'same'
        $null=New-TestFile $f.OldF 'two.jpg' 'same'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
        $plan=New-PhotoMigrationPlan -Config $f.Config -FileRecords $rows -Assets @(New-PhotoAssets $rows @()) -DestinationIndex @() -Adapters $f.Adapters
        Assert-Equal 1 $plan.actions.Count
        Assert-Equal 2 $plan.source_disposition.Count
        Assert-Equal 2 $plan.actions[0].components[0].sources.Count
    } finally { Remove-TestArchiveFixture $f }
}
