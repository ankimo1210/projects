Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'PhotoStorage.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'PhotoCloud.psm1') -DisableNameChecking
function Invoke-ICloudPhotoArchive($Config,[hashtable]$Adapters=@{},[switch]$ForceFresh) {
    $scope='RegisteredWindowsProjectionSnapshot'
    try {Assert-ArchiveBindings $Config $Adapters | Out-Null}
    catch {
        if($_.Exception.Message -match 'MissingArchiveDrive' -or -not(Test-Path -LiteralPath ([IO.Path]::GetPathRoot($Config.archive_root)))){return [pscustomobject]@{Status='SkippedMissingDrive';Scope=$scope;Copied=0;Pending=0;FullLibraryVerified=$false}}
        throw
    }
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        try {$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){return [pscustomobject]@{Status='AlreadyRunning';Scope=$scope;Copied=0;Pending=0;FullLibraryVerified=$false}}
        $state=Read-PhotoCheckpoint $Config
        $index=Get-PhotoReceiptIndex $Config $Adapters
        if($index.invalid_lines){$index=Repair-PhotoReceiptTails $Config $index $Adapters}
        if($index.invalid_lines){throw 'CorruptReceiptJournal'}
        $fullDue=$ForceFresh -or (-not $state.last_full_verified_utc) -or ([DateTime]::UtcNow-[DateTime]::Parse($state.last_full_verified_utc)).TotalDays -ge $Config.full_hash_interval_days
        if($fullDue) {
            $fullReceipt=[pscustomobject]@{archive_id=$Config.archive_id;committed=$index.assets}
            if(-not(Test-PhotoReceipt -Config $Config -Receipt $fullReceipt -Fresh -Adapters $Adapters).valid){throw 'ArchiveIntegrityChanged'}
            $state.last_full_verified_utc=[DateTime]::UtcNow.ToString('o')
        }
        $listed=@(Get-PhotoInventory -Config $Config -Aliases @('ICLOUD') -HashMode MetadataOnly -Adapters $Adapters)
        $ready=[Collections.Generic.List[object]]::new();$pending=[Collections.Generic.List[object]]::new()
        foreach($row in $listed) {
            if($row.read_status -notin @('Available','PendingOnlineOnly')){$pending.Add($row);continue}
            $availability=Ensure-CloudFileAvailable $Config $row $Adapters
            if($availability.status -eq 'Available'){$ready.Add($row)}else{$row.read_status='PendingCloudAvailability';$pending.Add($row)}
        }
        $rows=@()
        $hashMode=if($fullDue){'Fresh'}else{'Cached'}
        if($ready.Count){$rows=@(Get-PhotoInventory -Config $Config -Aliases @('ICLOUD') -HashMode $hashMode -Adapters $Adapters -RelativePaths @($ready.relative_path) -HashCache $state.source_hashes)}
        foreach($row in $pending){$rows+=$row}
        $meta=@();$needMetadata=@()
        $toolKey=if($Config.exiftool){Get-PhotoTextHash (Convert-PhotoCanonicalValue $Config.exiftool | ConvertTo-Json -Depth 16 -Compress)}else{'fixture-metadata'}
        foreach($row in $rows | Where-Object read_status -eq Available) {
            $key=$row.full_path.ToLowerInvariant()
            if($state.metadata.ContainsKey($key) -and $state.metadata[$key].sha256 -ceq $row.sha256 -and $state.metadata[$key].tool_key -ceq $toolKey){$meta+=$state.metadata[$key].value}
            else {$needMetadata+=$row}
        }
        $newMeta=@()
        if($needMetadata.Count) {
            $newMeta=if($Adapters.ContainsKey('Metadata')){Get-PhotoBoundVolume $Config $Config.archive_root $Adapters | Out-Null;@(& $Adapters.Metadata $needMetadata $Config.exiftool)}else{@(Read-PhotoMetadata -Files $needMetadata -ToolReceipt $Config.exiftool)}
        }
        $newMetaByPath=@{};foreach($m in $newMeta){$newMetaByPath[[IO.Path]::GetFullPath($m.SourceFile).ToLowerInvariant()]=$m}
        foreach($row in $needMetadata) {
            $key=$row.full_path.ToLowerInvariant()
            $value=if($newMetaByPath.ContainsKey($key)){$newMetaByPath[$key]}else{[pscustomobject]@{SourceFile=$row.full_path}}
            $state.metadata[$key]=[pscustomobject]@{sha256=$row.sha256;tool_key=$toolKey;value=$value}
            $meta+=$value
        }
        $assets=@(New-PhotoAssets -FileRecords $rows -Metadata $meta)
        $index=Get-PhotoReceiptIndex $Config $Adapters
        if($index.invalid_lines){throw 'CorruptReceiptJournal'}
        $destinationCache=if($fullDue){@{}}else{$state.destinations}
        $sourceCache=if($fullDue){@{}}else{$state.source_hashes}
        $copyBudget=[long]::MaxValue
        $backfillBaseline=Get-PhotoField $Config 'backfill_baseline_path'
        if($backfillBaseline) {
            $baseline=Get-Content -LiteralPath $backfillBaseline -Raw -Encoding UTF8 | ConvertFrom-Json
            $oldPaths=@{};foreach($b in $baseline){$oldPaths[$b.relative_path.ToLowerInvariant()]=$b}
            $assets=@($assets | Sort-Object @{Expression={
                $changed=@($_.components | Where-Object {$row=$_.file;$key=$row.relative_path.ToLowerInvariant();-not $oldPaths.ContainsKey($key) -or $oldPaths[$key].size_bytes -ne $row.size_bytes -or $oldPaths[$key].mtime_ticks -ne $row.mtime_ticks}).Count -gt 0
                if($changed){0}else{1}
            }})
            $media=Get-PhotoBoundVolume $Config $Config.archive_root $Adapters
            $copyBudget=[Math]::Max(0L,$media.free_bytes-[long]$Config.reserve_f_bytes-8589934592L)
        }
        $plan=New-PhotoMigrationPlan -Config $Config -FileRecords $rows -Assets $assets -DestinationIndex $index.assets -Adapters $Adapters -CopyBudgetBytes $copyBudget -DestinationStatCache $destinationCache
        $receipt=Invoke-PhotoPlan -Config $Config -Plan $plan -Adapters $Adapters -KnownSourceCache $sourceCache -DestinationStatCache $destinationCache
        $state.source_hashes=@{}
        foreach($row in $rows){if($row.read_status -eq 'Available'){$state.source_hashes[$row.full_path.ToLowerInvariant()]=$row}}
        foreach($record in $receipt.committed){foreach($component in $record.components){
            $path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path
            $item=Get-Item -LiteralPath $path -Force
            $state.destinations[$path.ToLowerInvariant()]=[pscustomobject]@{sha256=$component.sha256;size_bytes=$item.Length;mtime_ticks=$item.LastWriteTimeUtc.Ticks;file_id=[PhotoArchive.FileMetadata]::Identity($path)}
        }}
        $state.run_count++
        Save-PhotoCheckpoint -Config $Config -State $state | Out-Null
        Remove-ExpiredPhotoRunLogs $Config | Out-Null
        $after=@(Get-PhotoInventory -Config $Config -Aliases @('ICLOUD') -HashMode MetadataOnly -Adapters $Adapters)
        $beforePaths=@($listed | ForEach-Object relative_path)
        $newAfter=@($after | Where-Object {$_.relative_path -notin $beforePaths}).Count
        $capacityRetained=@($receipt.retained | Where-Object reason -eq RetainCapacity).Count
        $incomplete=@($assets | Where-Object association_status -ne Complete).Count+$newAfter+$capacityRetained
        $free=Get-PhotoBoundVolume $Config $Config.archive_root $Adapters
        return [pscustomobject]@{Status=if($incomplete){'PendingIncomplete'}else{'SnapshotVerified'};Scope=$scope;Listed=$listed.Count;Copied=$receipt.new_files;CommittedAssets=$receipt.committed.Count;Retained=$receipt.retained.Count;RetainCapacity=$capacityRetained;Pending=$incomplete;NewAfterSnapshot=$newAfter;FullLibraryVerified=$false;FullVerificationPerformed=[bool]$fullDue;RunId=$receipt.run_id;FreeFBytes=$free.free_bytes;LowSpaceWarning=($free.free_bytes -lt $Config.warn_f_bytes);FinishedAtUtc=[DateTime]::UtcNow.ToString('o')}
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
Export-ModuleMember -Function Invoke-ICloudPhotoArchive
