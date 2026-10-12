Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'PhotoStorage.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'PhotoCloud.psm1') -DisableNameChecking
function Get-PhotoAcceptance($Config) {
    $path=Resolve-PhotoPath $Config.state_root 'acceptance.private.json'
    if(-not(Test-Path -LiteralPath $path)){return $null}
    $acceptance=Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
    if($acceptance.schema_version -ne 2 -or $acceptance.archive_id -cne $Config.archive_id -or $acceptance.manual_runs -lt 2 -or $acceptance.scheduled_runs -lt 1 -or -not $acceptance.restore_verified){return $null}
    return $acceptance
}
function Test-PhotoIndependentProof($Config,$Proof,[string]$ExpectedHash,[string]$SourcePath,[hashtable]$Adapters=@{}) {
    if($Proof.kind -ne 'file' -or $Proof.sha256 -cne $ExpectedHash){return $false}
    $path=[IO.Path]::GetFullPath($Proof.path)
    if($path.Equals($SourcePath,[StringComparison]::OrdinalIgnoreCase)){return $false}
    foreach($sync in $Config.source_roots | Where-Object alias -eq ICLOUD){if(Test-PhotoPathWithin $path $sync.path){return $false}}
    Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($path))
    $file=Get-Item -LiteralPath $path -Force
    if([long]$file.Attributes -band 0x400 -or $file.PSIsContainer){return $false}
    $volume=Get-PhotoBoundVolume $Config $path $Adapters
    if($volume.disk_id -ceq $Config.destination_disk_id -or $volume.disk_id -cne $Proof.disk_id -or $volume.volume_id -cne $Proof.volume_id){return $false}
    return (Get-PhotoSha256 $path) -ceq $ExpectedHash
}
function Get-PhotoCleanupHash($Plan) {
    $value=[ordered]@{}
    foreach($p in $Plan.PSObject.Properties){if($p.Name -ne 'cleanup_sha256'){$value[$p.Name]=$p.Value}}
    return Get-PhotoTextHash ((Convert-PhotoCanonicalValue $value | ConvertTo-Json -Depth 48 -Compress).Replace("`r`n","`n"))
}
function New-PhotoCleanupPlan($Config,$Receipt,[object[]]$IndependentProofs=@(),[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    if(-not(Test-PhotoReceipt $Config $Receipt -Fresh -Adapters $Adapters).valid){throw 'InvalidReceiptData'}
    $acceptance=Get-PhotoAcceptance $Config
    $eligible=@();$retained=@();$blocked=if($acceptance){$null}else{'DailyAcceptanceMissing'}
    foreach($record in $Receipt.committed){foreach($component in $record.components){foreach($source in $component.sources){
        $path=Get-PhotoSourcePath $Config $source
        $reason=$blocked
        if($source.source_alias -eq 'ICLOUD'){$reason='CloudCacheOnly'}
        elseif($record.association_status -ne 'Complete'){$reason='PendingAssociation'}
        elseif(($source.attributes -band 0x4400) -or @($source.streams).Count){$reason='SpecialSourceProtected'}
        $matching=@()
        if(-not $reason) {
            foreach($proof in $IndependentProofs){if(Test-PhotoIndependentProof $Config $proof $component.sha256 $path $Adapters){$matching+=$proof}}
            if(-not $matching.Count){$reason='IndependentCopyMissing'}
        }
        $item=[pscustomobject]@{source_alias=$source.source_alias;relative_path=$source.relative_path;path=$path;source=$source;asset_id=$record.asset_id;sha256=$component.sha256;destination_relative_path=$component.destination_relative_path;proofs=$matching;reason=$reason}
        if($reason){$retained+=$item}else{$eligible+=$item}
    }}}
    # A component whose independent copy is also selected for deletion is protected.
    $changed=$true
    while($changed) {
        $changed=$false;$deletePaths=@($eligible | ForEach-Object {$_.path.ToLowerInvariant()});$next=@()
        foreach($item in $eligible) {
            $usable=@($item.proofs | Where-Object {$_.path.ToLowerInvariant() -notin $deletePaths})
            if(-not $usable.Count){$item.reason='CircularDeletionProof';$retained+=$item;$changed=$true}else{$item.proofs=$usable;$next+=$item}
        }
        $eligible=$next
    }
    # Deleting one component must not discard an incompletely protected asset.
    $unsafeAssets=@($retained | Where-Object {$_.source_alias -ne 'ICLOUD'} | ForEach-Object {$_.asset_id+'|'+$_.source_alias})
    $next=@()
    foreach($item in $eligible) {
        if(($item.asset_id+'|'+$item.source_alias) -in $unsafeAssets){$item.reason='AssetProtectionIncomplete';$retained+=$item}else{$next+=$item}
    }
    $eligible=$next
    $plan=[pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;cleanup_id=[guid]::NewGuid().ToString('N');created_at_utc=[DateTime]::UtcNow.ToString('o');eligible=@($eligible);retained=@($retained);blocked_reason=$blocked;acceptance=$acceptance;receipt=$Receipt;cleanup_sha256=$null}
    $plan.cleanup_sha256=Get-PhotoCleanupHash $plan
    return $plan
}
function Invoke-PhotoCleanup($Config,$CleanupPlan,[hashtable]$Adapters=@{}) {
    # This check precedes the digest to reject any attempt to target sync files.
    foreach($item in $CleanupPlan.eligible) {
        if($item.source_alias -eq 'ICLOUD'){throw 'CloudRootDeletionForbidden'}
        foreach($sync in $Config.source_roots | Where-Object alias -eq ICLOUD){if(Test-PhotoPathWithin $item.path $sync.path){throw 'CloudRootDeletionForbidden'}}
    }
    if((Get-PhotoCleanupHash $CleanupPlan) -cne $CleanupPlan.cleanup_sha256){throw 'CleanupPlanChanged'}
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    if(-not(Get-PhotoAcceptance $Config)){throw 'DailyAcceptanceMissing'}
    if(-not(Test-PhotoReceipt $Config $CleanupPlan.receipt -Fresh -Adapters $Adapters).valid){throw 'InvalidReceiptData'}
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        try{$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        $journal=Resolve-PhotoPath $Config.state_root ('cleanup\'+$CleanupPlan.cleanup_id+'.jsonl')
        $moved=0;$deleted=0;$waiting=0
        foreach($item in $CleanupPlan.eligible) {
            $sourcePath=Get-PhotoSourcePath $Config $item.source
            if(-not $sourcePath.Equals($item.path,[StringComparison]::OrdinalIgnoreCase)){throw 'CleanupSourceMismatch'}
            $holdRoot=if($item.source_alias -eq 'OLD_F'){Resolve-PhotoPath $Config.archive_root 'retained'}else{$Config.retained_root}
            $held=Resolve-PhotoPath $holdRoot ($CleanupPlan.cleanup_id+'\'+$item.relative_path)
            $holdReceipt=Resolve-PhotoPath $Config.state_root ('cleanup\'+$CleanupPlan.cleanup_id+'-'+(Get-PhotoTextHash $item.path)+'.json')
            $proofValid=@($item.proofs | Where-Object {Test-PhotoIndependentProof $Config $_ $item.sha256 $sourcePath $Adapters}).Count -gt 0
            if(-not $proofValid){throw 'IndependentProofExpired'}
            $dest=Resolve-PhotoPath $Config.archive_root $item.destination_relative_path
            if((Get-PhotoSha256 $dest) -cne $item.sha256){throw 'ArchiveChanged'}
            if(-not(Test-Path -LiteralPath $holdReceipt)) {
                Assert-PhotoSourceFresh $Config $item.source $item.sha256 $Adapters | Out-Null
                $sourceVolume=Get-PhotoBoundVolume $Config $sourcePath $Adapters;$holdVolume=Get-PhotoBoundVolume $Config $held $Adapters
                if($sourceVolume.disk_id -cne $holdVolume.disk_id -or $sourceVolume.volume_id -cne $holdVolume.volume_id){throw 'CrossVolumeRetentionForbidden'}
                $null=New-Item -ItemType Directory -Path (Split-Path -Parent $held) -Force
                # Record intent before moving; a stopped process cannot lose the mapping.
                $intent=[pscustomobject]@{schema_version=2;source=$sourcePath;held=$held;sha256=$item.sha256;moved_at_utc=[DateTime]::UtcNow.ToString('o');cleanup_sha256=$CleanupPlan.cleanup_sha256}
                Write-PhotoJsonNew $holdReceipt $intent
                [IO.File]::Move($sourcePath,$held);$moved++
                Write-PhotoJournalLine $journal ([pscustomobject]@{state='Retained';source=$sourcePath;held=$held;sha256=$item.sha256;utc=[DateTime]::UtcNow.ToString('o')})
            } else {
                $hold=Get-Content -LiteralPath $holdReceipt -Raw -Encoding UTF8 | ConvertFrom-Json
                if($hold.cleanup_sha256 -cne $CleanupPlan.cleanup_sha256 -or $hold.held -cne $held){throw 'RetentionReceiptChanged'}
                if(-not(Test-Path -LiteralPath $held) -and (Test-Path -LiteralPath $sourcePath)){throw 'RetentionMoveIncomplete'}
                if((Get-PhotoSha256 $held) -cne $item.sha256){throw 'RetainedSourceChanged'}
                if(([DateTime]::UtcNow-[DateTime]::Parse($hold.moved_at_utc)).TotalDays -lt $Config.retention_days){$waiting++;continue}
                Assert-ArchiveBindings $Config $Adapters | Out-Null
                if((Get-PhotoSha256 $dest) -cne $item.sha256 -or @($item.proofs | Where-Object {Test-PhotoIndependentProof $Config $_ $item.sha256 $sourcePath $Adapters}).Count -eq 0){throw 'FinalCopyVerificationFailed'}
                Assert-PhotoNoDirectoryLinks (Split-Path -Parent $held)
                if([long](Get-Item -LiteralPath $held -Force).Attributes -band 0x4400){throw 'ProtectedRetainedSource'}
                Remove-Item -LiteralPath $held -Force;$deleted++
                Write-PhotoJournalLine $journal ([pscustomobject]@{state='DeletedVerifiedCopy';source=$sourcePath;sha256=$item.sha256;utc=[DateTime]::UtcNow.ToString('o')})
            }
        }
        return [pscustomobject]@{MovedToRetention=$moved;Deleted=$deleted;Waiting=$waiting;CleanupId=$CleanupPlan.cleanup_id;EarliestDeletionUtc=[DateTime]::UtcNow.AddDays($Config.retention_days).ToString('o')}
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
function Release-VerifiedCloudCache($Config,$Receipt,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    if(-not(Get-PhotoAcceptance $Config)){throw 'DailyAcceptanceMissing'}
    if(-not(Test-PhotoReceipt $Config $Receipt -Fresh -Adapters $Adapters).valid){throw 'InvalidReceiptData'}
    $capability=Resolve-PhotoPath $Config.state_root 'cloud-release-capability.private.json'
    if(-not(Test-Path -LiteralPath $capability)){throw 'CloudReacquisitionProbeMissing'}
    $tested=Get-Content -LiteralPath $capability -Raw -Encoding UTF8 | ConvertFrom-Json
    if($tested.archive_id -cne $Config.archive_id -or -not $tested.reacquisition_hash_matched -or ([DateTime]::UtcNow-[DateTime]::Parse($tested.verified_at_utc)).TotalDays -gt 1){throw 'CloudReacquisitionProofExpired'}
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        try{$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        $requested=0;$held=0;$errors=@()
        foreach($record in $Receipt.committed){foreach($component in $record.components){foreach($source in $component.sources | Where-Object source_alias -eq ICLOUD){
            if($record.association_status -ne 'Complete'){$held++;continue}
            try {
                $path=Assert-PhotoSourceFresh $Config $source $component.sha256 $Adapters
                $status=Get-CloudFileStatus $Config $source $Adapters
                if(-not $status.is_placeholder -or -not $status.in_sync -or -not $status.locally_available){$held++;continue}
                if($status.policy.HydrationPrimary -eq 3){$held++;continue}
                if($Adapters.ContainsKey('Unpin')){Get-PhotoBoundVolume $Config $path $Adapters | Out-Null;$result=& $Adapters.Unpin $path $Config.download_timeout_seconds}
                else{$result=[PhotoArchive.CloudNative]::Unpin($path,$Config.download_timeout_seconds)}
                if($result.Status -eq 'Available'){$requested++}else{$held++}
                Write-PhotoJournalLine (Resolve-PhotoPath $Config.state_root ('cache-release\'+[DateTime]::UtcNow.ToString('yyyyMMdd')+'.jsonl')) ([pscustomobject]@{path=$path;sha256=$component.sha256;status='UnpinRequested';hresult=$result.HResult;utc=[DateTime]::UtcNow.ToString('o')})
            } catch {$errors += [pscustomobject]@{source_alias='ICLOUD';reason=$_.Exception.Message};$held++}
        }}}
        return [pscustomobject]@{UnpinRequested=$requested;Retained=$held;Errors=$errors;ActualBytesFreed=$null;CloudFilesDeleted=0;Note='Unpin is asynchronous; actual allocation must be measured separately.'}
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
Export-ModuleMember -Function *
