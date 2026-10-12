[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ConfigPath,
    [Parameter(Mandatory)][ValidateSet('Inventory','Plan','Apply','Archive','Verify','Restore','CleanupPlan','CleanupApply','ReleaseCloudCache')][string]$Mode,
    [string]$PlanPath,[string]$ReceiptPath,[string]$RestoreRoot,[string]$CleanupPlanPath,
    [string[]]$Aliases=@('OLD_C','OLD_F','ICLOUD'),[switch]$Fresh
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Read-EntryJson([string]$Path) {
    $body=Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')){return $body | ConvertFrom-Json -DateKind String}
    return $body | ConvertFrom-Json
}
try {
    if($Mode -eq 'Apply' -and -not $PlanPath){throw 'MissingPlanPath'}
    if($Mode -in @('Verify','Restore','CleanupPlan','ReleaseCloudCache') -and -not $ReceiptPath){throw 'MissingReceiptPath'}
    if($Mode -eq 'Restore' -and -not $RestoreRoot){throw 'MissingRestoreRoot'}
    if($Mode -eq 'CleanupApply' -and -not $CleanupPlanPath){throw 'MissingCleanupPlanPath'}
    Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'PhotoStorage.psm1') -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'PhotoCloud.psm1') -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'ICloudPhotoArchive.psm1') -DisableNameChecking
    Import-Module (Join-Path $PSScriptRoot 'PhotoCleanup.psm1') -DisableNameChecking
    $config=Read-ArchiveConfig $ConfigPath
    $result=$null;$exitCode=0
    switch($Mode) {
        'Inventory' {
            $rows=@(Get-PhotoInventory -Config $config -Aliases $Aliases -HashMode Fresh)
            $path=Resolve-PhotoPath $config.state_root ('inventories\'+[guid]::NewGuid().ToString('N')+'.json')
            Write-PhotoJsonNew $path $rows
            $result=[pscustomobject]@{Status='InventoryCaptured';Files=$rows.Count;Available=@($rows | Where-Object read_status -eq Available).Count;Output=$path}
        }
        'Plan' {
            $rows=@(Get-PhotoInventory -Config $config -Aliases $Aliases -HashMode Fresh)
            $meta=@(Read-PhotoMetadata -Files $rows -ToolReceipt $config.exiftool)
            $index=Get-PhotoReceiptIndex $config
            if($index.invalid_lines){throw 'CorruptReceiptJournal'}
            $plan=New-PhotoMigrationPlan -Config $config -FileRecords $rows -Assets @(New-PhotoAssets $rows $meta) -DestinationIndex $index.assets
            $path=Resolve-PhotoPath $config.state_root ('plans\'+$plan.plan_id+'.json')
            Write-PhotoJsonNew $path $plan
            $result=[pscustomobject]@{Status='PlanCreated';Output=$path;Inputs=$plan.source_disposition.Count;Actions=$plan.actions.Count;Budget=$plan.physical_capacity_budget}
        }
        'Apply' {
            $receipt=Invoke-PhotoPlan -Config $config -Plan (Read-EntryJson $PlanPath)
            $result=[pscustomobject]@{Status='PlanApplied';RunId=$receipt.run_id;Copied=$receipt.new_files;Committed=$receipt.committed.Count;Retained=$receipt.retained.Count;Receipt=(Resolve-PhotoPath $config.state_root ('runs\'+$receipt.run_id+'.json'))}
        }
        'Archive' {
            $result=Invoke-ICloudPhotoArchive -Config $config -ForceFresh:$Fresh
            switch($result.Status){'PendingIncomplete'{$exitCode=3};'SkippedMissingDrive'{$exitCode=10};'DeferredCapacity'{$exitCode=20};'Blocked'{$exitCode=30}}
        }
        'Verify' {
            $result=Test-PhotoReceipt -Config $config -Receipt (Read-EntryJson $ReceiptPath) -Fresh
            if(-not $result.valid){$exitCode=30}
        }
        'Restore' {$result=Restore-PhotoSources -Config $config -Receipt (Read-EntryJson $ReceiptPath) -DestinationRoot $RestoreRoot}
        'CleanupPlan' {
            $result=New-PhotoCleanupPlan -Config $config -Receipt (Read-EntryJson $ReceiptPath) -IndependentProofs @()
        }
        'CleanupApply' {$result=Invoke-PhotoCleanup -Config $config -CleanupPlan (Read-EntryJson $CleanupPlanPath)}
        'ReleaseCloudCache' {$result=Release-VerifiedCloudCache -Config $config -Receipt (Read-EntryJson $ReceiptPath)}
    }
    $result | ConvertTo-Json -Depth 12
    exit $exitCode
} catch {
    $reason=$_.Exception.Message
    $exitCode=if($reason -match 'InsufficientCapacity'){20}else{30}
    if($Mode -eq 'Archive') {
        try {$probe=Read-EntryJson $ConfigPath;if(-not(Test-Path -LiteralPath ([IO.Path]::GetPathRoot($probe.archive_root)))){$exitCode=10}}catch{}
    }
    [pscustomobject]@{Status=if($exitCode -eq 10){'SkippedMissingDrive'}elseif($exitCode -eq 20){'DeferredCapacity'}else{'Blocked'};Reason=$reason;Scope='DeclaredInputSnapshot'} | ConvertTo-Json
    exit $exitCode
}
