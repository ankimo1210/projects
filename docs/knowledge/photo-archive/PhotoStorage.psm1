Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
Import-Module (Join-Path $PSScriptRoot 'PhotoCloud.psm1') -DisableNameChecking

function Write-PhotoJsonNew([string]$Path,$Value) {
    Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($Path))
    $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($Path)) -Force
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
    try {$bytes=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 48 -Compress)+"`n");$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
function Write-PhotoJournalLine([string]$Path,$Value) {
    Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($Path))
    $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($Path)) -Force
    $stream=[IO.File]::Open($Path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::Read)
    try {
        if($stream.Length){$stream.Position=$stream.Length-1;if($stream.ReadByte() -ne 10){$stream.Position=$stream.Length;$stream.WriteByte(10)}}
        $stream.Position=$stream.Length
        $bytes=[Text.Encoding]::UTF8.GetBytes(($Value | ConvertTo-Json -Depth 48 -Compress)+"`n")
        $stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)
    } finally {$stream.Dispose()}
}
function New-PhotoCheckpoint {
    return @{schema_version=2;source_hashes=@{};metadata=@{};destinations=@{};last_full_verified_utc=$null;run_count=0}
}
function Read-PhotoCheckpoint($Config) {
    $root=Resolve-PhotoPath $Config.state_root 'checkpoints'
    if(-not(Test-Path -LiteralPath $root)){return New-PhotoCheckpoint}
    $headers=@(Get-ChildItem -LiteralPath $root -File -Filter 'state-*.sha.json' | Sort-Object Name -Descending)
    if(-not $headers.Count){return New-PhotoCheckpoint}
    $headerPath=$headers[0].FullName
    try {
        $header=Get-Content -LiteralPath $headerPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if($header.schema_version -ne 2 -or $header.archive_id -cne $Config.archive_id -or $header.file -notmatch '^state-\d{21}-[a-f0-9]{32}\.clixml$'){throw 'InvalidCheckpointHeader'}
        $path=Resolve-PhotoPath $root $header.file
        if((Get-PhotoSha256 $path) -cne $header.sha256){throw 'CheckpointHashMismatch'}
        $state=Import-Clixml -LiteralPath $path
        if($state.schema_version -ne 2 -or $state.source_hashes -isnot [Collections.IDictionary] -or $state.metadata -isnot [Collections.IDictionary] -or $state.destinations -isnot [Collections.IDictionary]){throw 'CheckpointSchemaMismatch'}
        return $state
    } catch {throw ('CheckpointCorrupt: '+$_.Exception.Message)}
}
function Save-PhotoCheckpoint($Config,[hashtable]$State) {
    if($State.schema_version -ne 2){throw 'UnsupportedCheckpoint'}
    $root=Resolve-PhotoPath $Config.state_root 'checkpoints'
    $null=New-Item -ItemType Directory -Path $root -Force
    $name='state-'+[DateTime]::UtcNow.ToString('yyyyMMddHHmmssfffffff')+'-'+[guid]::NewGuid().ToString('N')+'.clixml'
    $path=Resolve-PhotoPath $root $name
    if(Test-Path -LiteralPath $path){throw 'CheckpointAlreadyExists'}
    $State | Export-Clixml -LiteralPath $path -Encoding UTF8 -Depth 48
    $hash=Get-PhotoSha256 $path
    Write-PhotoJsonNew (Resolve-PhotoPath $root ($name.Replace('.clixml','.sha.json'))) ([pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;file=$name;sha256=$hash})
    $headers=@(Get-ChildItem -LiteralPath $root -File -Filter 'state-*.sha.json' | Sort-Object Name -Descending)
    foreach($old in $headers | Select-Object -Skip 3) {
        $h=Get-Content -LiteralPath $old.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
        if($h.schema_version -eq 2 -and $h.archive_id -ceq $Config.archive_id -and $h.file -match '^state-\d{21}-[a-f0-9]{32}\.clixml$') {
            $payload=Resolve-PhotoPath $root $h.file
            if((Get-PhotoSha256 $payload) -ceq $h.sha256){Remove-Item -LiteralPath $payload -Force;Remove-Item -LiteralPath (Resolve-PhotoPath $root $old.Name) -Force}
        }
    }
    return $path
}
function Remove-ExpiredPhotoRunLogs($Config) {
    $root=Resolve-PhotoPath $Config.state_root 'runs'
    if(-not(Test-Path -LiteralPath $root)){return 0}
    $removed=0
    foreach($file in Get-ChildItem -LiteralPath $root -File -Filter '*.json') {
        if($file.BaseName -notmatch '^[a-f0-9]{32}$' -or ([long]$file.Attributes -band 0x400)){continue}
        try {$run=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json}
        catch {continue}
        if($run.schema_version -ne 2 -or $run.archive_id -cne $Config.archive_id -or $run.run_id -cne $file.BaseName -or -not (Get-PhotoField $run 'completed_at_utc')){continue}
        if(([DateTimeOffset]::UtcNow-[DateTimeOffset]::Parse([string]$run.completed_at_utc)).TotalDays -le 90){continue}
        $journal=Resolve-PhotoPath $Config.state_root ('journals\'+$file.BaseName+'.jsonl')
        if(Test-Path -LiteralPath $journal) {
            Assert-PhotoNoDirectoryLinks (Split-Path -Parent $journal)
            if([long](Get-Item -LiteralPath $journal -Force).Attributes -band 0x400){continue}
            Remove-Item -LiteralPath $journal -Force
        }
        Remove-Item -LiteralPath (Resolve-PhotoPath $root $file.Name) -Force;$removed++
    }
    return $removed
}
function Initialize-PhotoArchive($Config,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $marker=Join-Path $Config.archive_root 'archive-marker.json'
    if(-not(Test-Path -LiteralPath $marker)) {
        Write-PhotoJsonNew $marker ([pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;volume_id=$Config.destination_volume_id;disk_id=$Config.destination_disk_id;created_at_utc=[DateTime]::UtcNow.ToString('o')})
    }
    foreach($relative in @('media','catalog','receipts','staging','retained')) {
        $path=Resolve-PhotoPath $Config.archive_root $relative
        $null=New-Item -ItemType Directory -Path $path -Force
    }
}
function Get-PhotoStagePath($Config,$Plan,$Action,[int]$ComponentIndex) {
    if($Plan.plan_id -notmatch '^[a-f0-9]{32}$' -or $Action.action_id -notmatch '^[a-f0-9]{32}$' -or $ComponentIndex -lt 0){throw 'InvalidStageIdentity'}
    return Resolve-PhotoPath $Config.archive_root ('staging\'+$Plan.plan_id+'\'+$Action.action_id+'-'+$ComponentIndex+'.part')
}
function Assert-PhotoSourceStreamsProtected([string]$Path) {
    $item=Get-Item -LiteralPath $Path -Force
    if($item.PSIsContainer -or ([long]$item.Attributes -band 0x4401)){throw 'ProtectedSourceStreams: readonly, link or encrypted source'}
    # exFAT has no named streams. Other filesystems must inspect successfully;
    # never infer the filesystem from its allocation-unit size.
    $native=Get-PhotoNativeVolume $Path
    if($native.file_system -eq 'exFAT'){return}
    try {$streams=@(Get-Item -LiteralPath $Path -Stream * -ErrorAction Stop | Where-Object {$_.Stream -ne ':$DATA' -and $_.Stream -ne '$DATA'})}
    catch {throw 'ProtectedSourceStreams: inspection failed'}
    if($streams.Count){throw 'ProtectedSourceStreams'}
}
function Assert-PhotoSourceFresh($Config,$Source,[string]$ExpectedHash,[hashtable]$Adapters=@{}) {
    $path=Get-PhotoSourcePath $Config $Source
    if($Source.source_alias -eq 'ICLOUD') {
        $cloud=Get-CloudFileStatus $Config $Source $Adapters
        if(-not $cloud.in_sync -or -not $cloud.locally_available){throw 'CloudSourceNotReady'}
    }
    $before=Get-Item -LiteralPath $path -Force
    if($before.Length -ne $Source.size_bytes -or $before.LastWriteTimeUtc.Ticks -ne $Source.mtime_ticks -or [PhotoArchive.FileMetadata]::Identity($path) -cne $Source.file_id){throw 'SourceChanged'}
    if((Get-PhotoSha256 $path) -cne $ExpectedHash){throw 'SourceChanged'}
    $after=Get-Item -LiteralPath $path -Force
    if($after.Length -ne $Source.size_bytes -or $after.LastWriteTimeUtc.Ticks -ne $Source.mtime_ticks -or [PhotoArchive.FileMetadata]::Identity($path) -cne $Source.file_id){throw 'SourceChanged'}
    return $path
}
function Copy-PhotoVerifiedComponent($Config,$Plan,$Action,$Component,[int]$ComponentIndex) {
    $source=$Component.sources[0]
    $sourcePath=Get-PhotoSourcePath $Config $source
    $dest=Resolve-PhotoPath $Config.archive_root $Component.destination_relative_path
    if(Test-Path -LiteralPath $dest) {
        if((Get-PhotoSha256 $dest) -cne $Component.sha256){throw 'DestinationConflict'}
        return $false
    }
    $stage=Get-PhotoStagePath $Config $Plan $Action $ComponentIndex
    $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($stage)) -Force
    $input=[IO.File]::Open($sourcePath,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $sha=[Security.Cryptography.SHA256]::Create()
    try {
        $sourceHash=([BitConverter]::ToString($sha.ComputeHash($input))).Replace('-','').ToLowerInvariant()
        if($sourceHash -cne $Component.sha256 -or $input.Length -ne $Component.size_bytes){throw 'SourceChanged'}
        $input.Position=0
        $mode=if(Test-Path -LiteralPath $stage){[IO.FileMode]::Open}else{[IO.FileMode]::CreateNew}
        $output=[IO.File]::Open($stage,$mode,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
        try {
            if($output.Length -gt $input.Length){throw 'InvalidPartialCopy'}
            $remaining=$output.Length
            $sourceBuffer=New-Object byte[] 1048576;$stageBuffer=New-Object byte[] 1048576
            while($remaining -gt 0) {
                $want=[int][Math]::Min(1048576L,$remaining)
                $a=$input.Read($sourceBuffer,0,$want);$b=$output.Read($stageBuffer,0,$want)
                if($a -ne $want -or $b -ne $want){throw 'InvalidPartialCopy'}
                for($i=0;$i -lt $want;$i++){if($sourceBuffer[$i] -ne $stageBuffer[$i]){throw 'InvalidPartialCopy'}}
                $remaining-=$want
            }
            $input.CopyTo($output,1048576);$output.Flush($true)
        } finally {$output.Dispose()}
        if((Get-PhotoSha256 $stage) -cne $Component.sha256){throw 'StageHashMismatch'}
        $input.Position=0
        if(([BitConverter]::ToString($sha.ComputeHash($input))).Replace('-','').ToLowerInvariant() -cne $Component.sha256){throw 'SourceChanged'}
    } finally {$sha.Dispose();$input.Dispose()}
    Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($dest))
    $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($dest)) -Force
    [IO.File]::Move($stage,$dest)
    if((Get-PhotoSha256 $dest) -cne $Component.sha256){throw 'FinalHashMismatch'}
    (Get-Item -LiteralPath $dest).LastWriteTimeUtc=[DateTime]::new([long]$source.mtime_ticks,[DateTimeKind]::Utc)
    return $true
}
function Merge-PhotoAssetReceipts($Earlier,$Later) {
    if($Earlier.components.Count -ne $Later.components.Count){throw 'ConflictingReceiptComponents'}
    $oldTime=[DateTimeOffset]::Parse([string]$Earlier.committed_at_utc)
    $newTime=[DateTimeOffset]::Parse([string]$Later.committed_at_utc)
    $newest=if($newTime -ge $oldTime){$Later}else{$Earlier}
    $other=if($newTime -ge $oldTime){$Earlier}else{$Later}
    foreach($component in $newest.components) {
        $matches=@($other.components | Where-Object {$_.role -ceq $component.role -and $_.sha256 -ceq $component.sha256 -and $_.size_bytes -eq $component.size_bytes -and $_.destination_relative_path -ceq $component.destination_relative_path})
        if($matches.Count -ne 1){throw 'ConflictingReceiptComponents'}
        $aliases=@{};foreach($source in $component.sources){$aliases[$source.source_alias+'|'+$source.relative_path.ToLowerInvariant()+'|'+$source.sha256]=$true}
        foreach($source in $matches[0].sources) {
            $key=$source.source_alias+'|'+$source.relative_path.ToLowerInvariant()+'|'+$source.sha256
            if(-not $aliases.ContainsKey($key)){$component.sources+= $source;$aliases[$key]=$true}
        }
    }
    return $newest
}
function Get-PhotoReceiptIndex($Config,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $assets=@{};$invalid=0;$tails=@()
    $root=Join-Path $Config.archive_root 'receipts'
    if(Test-Path -LiteralPath $root) {
        foreach($file in Get-ChildItem -LiteralPath $root -File -Filter '*.jsonl' | Sort-Object Name) {
            Assert-PhotoNoDirectoryLinks $root
            if([long]$file.Attributes -band 0x400){throw 'ReceiptLinkForbidden'}
            $reader=[IO.File]::OpenText($file.FullName)
            $lastByte=[IO.File]::OpenRead($file.FullName)
            try {$unterminated=$lastByte.Length -gt 0;if($unterminated){$lastByte.Position=$lastByte.Length-1;$unterminated=$lastByte.ReadByte() -ne 10}}finally{$lastByte.Dispose()}
            try {
                while(($line=$reader.ReadLine()) -ne $null) {
                    if([string]::IsNullOrWhiteSpace($line)){continue}
                    try {$record=$line | ConvertFrom-Json -ErrorAction Stop}
                    catch {
                        if($reader.EndOfStream -and $unterminated) {
                            $hash=Get-PhotoSha256 $file.FullName
                            $ackPath=Resolve-PhotoPath $Config.state_root ('receipt-recovery\'+$hash+'.json')
                            $acknowledged=$false
                            if(Test-Path -LiteralPath $ackPath){$ack=Get-Content -LiteralPath $ackPath -Raw | ConvertFrom-Json;$acknowledged=$ack.archive_id -ceq $Config.archive_id -and $ack.journal_sha256 -ceq $hash -and $ack.fresh_verified}
                            $tails+=[pscustomobject]@{path=$file.FullName;sha256=$hash;acknowledged=$acknowledged}
                            if(-not $acknowledged){$invalid++}
                        } else {$invalid++}
                        continue
                    }
                    try {
                        if($record.state -ne 'Committed' -or $record.archive_id -cne $Config.archive_id -or $record.schema_version -ne 2){throw 'InvalidReceipt'}
                        foreach($component in $record.components){Resolve-PhotoPath $Config.archive_root $component.destination_relative_path | Out-Null;if($component.sha256 -notmatch '^[a-f0-9]{64}$'){throw 'InvalidReceipt'}}
                        if($assets.ContainsKey($record.asset_id)){$assets[$record.asset_id]=Merge-PhotoAssetReceipts $assets[$record.asset_id] $record}else{$assets[$record.asset_id]=$record}
                    } catch {$invalid++}
                }
            } finally {$reader.Dispose()}
        }
    }
    return [pscustomobject]@{assets=@($assets.Values);invalid_lines=$invalid;truncated_tails=@($tails)}
}
function Repair-PhotoReceiptTails($Config,$Index,[hashtable]$Adapters=@{}) {
    $pending=@($Index.truncated_tails | Where-Object {-not $_.acknowledged})
    if(-not $pending.Count){return $Index}
    if($Index.invalid_lines -ne $pending.Count){throw 'CorruptReceiptJournal'}
    $proof=Test-PhotoReceipt $Config ([pscustomobject]@{archive_id=$Config.archive_id;committed=$Index.assets}) -Fresh -Adapters $Adapters
    if(-not $proof.valid){throw 'CorruptReceiptData'}
    foreach($tail in $pending) {
        if((Get-PhotoSha256 $tail.path) -cne $tail.sha256){throw 'ReceiptChangedDuringRecovery'}
        Write-PhotoJsonNew (Resolve-PhotoPath $Config.state_root ('receipt-recovery\'+$tail.sha256+'.json')) ([pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;journal_path=$tail.path;journal_sha256=$tail.sha256;fresh_verified=$true;verified_at_utc=$proof.verified_at_utc;note='Incomplete final line excluded; original journal preserved unchanged.'})
    }
    return Get-PhotoReceiptIndex $Config $Adapters
}
function Invoke-PhotoPlan($Config,$Plan,[hashtable]$Adapters=@{},[hashtable]$KnownSourceCache=@{},[hashtable]$DestinationStatCache=@{}) {
    Assert-PlanInputs $Plan $Config $Adapters
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        try {$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        Initialize-PhotoArchive $Config $Adapters
        $index=Get-PhotoReceiptIndex $Config $Adapters
        if($index.invalid_lines){$index=Repair-PhotoReceiptTails $Config $index $Adapters}
        if($index.invalid_lines){throw 'CorruptReceiptJournal'}
        $prior=@{};foreach($record in $index.assets){$prior[$record.asset_id]=$record}
        $run=[guid]::NewGuid().ToString('N');$committed=[Collections.Generic.List[object]]::new();$newFiles=0
        $journal=Resolve-PhotoPath $Config.state_root ('journals\'+$run+'.jsonl')
        $fJournal=Resolve-PhotoPath $Config.archive_root ('receipts\'+$run+'.jsonl')
        foreach($action in $Plan.actions) {
            $volume=Assert-ArchiveBindings $Config $Adapters
            $knownUnchanged=$prior.ContainsKey($action.asset_id)
            if($knownUnchanged) {
                foreach($component in $action.components) {
                    $path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path
                    if(-not(Test-PhotoCachedFile $path $component.sha256 $DestinationStatCache)){$knownUnchanged=$false;break}
                    foreach($source in $component.sources) {
                        $key=$source.full_path.ToLowerInvariant()
                        if(-not $KnownSourceCache.ContainsKey($key)){$knownUnchanged=$false;break}
                        $known=$KnownSourceCache[$key]
                        if($known.sha256 -cne $source.sha256 -or $known.file_id -cne $source.file_id -or $known.size_bytes -ne $source.size_bytes -or $known.mtime_ticks -ne $source.mtime_ticks){$knownUnchanged=$false;break}
                    }
                }
            }
            if($knownUnchanged){$committed.Add($prior[$action.asset_id]);continue}
            $required=0L
            foreach($component in $action.components){$path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path;if(-not(Test-Path -LiteralPath $path)){$required += [long][Math]::Ceiling($component.size_bytes/[double]$volume.cluster_bytes)*$volume.cluster_bytes}}
            if($volume.free_bytes - $required - 1048576L -lt $Config.reserve_f_bytes){throw 'InsufficientCapacity'}
            foreach($component in $action.components){foreach($source in $component.sources){Assert-PhotoSourceFresh $Config $source $component.sha256 $Adapters | Out-Null}}
            Write-PhotoJournalLine $journal ([pscustomobject]@{state='Planned';action_id=$action.action_id;asset_id=$action.asset_id;plan_sha256=$Plan.plan_sha256;utc=[DateTime]::UtcNow.ToString('o')})
            $parts=@();$ordinal=0
            foreach($component in $action.components) {
                if(Copy-PhotoVerifiedComponent $Config $Plan $action $component $ordinal){$newFiles++}
                $parts += [pscustomobject]@{role=$component.role;sha256=$component.sha256;size_bytes=$component.size_bytes;destination_relative_path=$component.destination_relative_path;sources=@($component.sources)}
                $ordinal++
                Write-PhotoJournalLine $journal ([pscustomobject]@{state='Verified';action_id=$action.action_id;component=$ordinal;utc=[DateTime]::UtcNow.ToString('o')})
            }
            $record=[pscustomobject]@{schema_version=2;state='Committed';archive_id=$Config.archive_id;asset_id=$action.asset_id;action_id=$action.action_id;plan_sha256=$Plan.plan_sha256;association_status=$action.association_status;association_revision=3;components=$parts;capture_date_raw=$action.capture_date_raw;capture_offset=$action.capture_offset;capture_subsec_raw=(Get-PhotoField $action 'capture_subsec_raw');capture_utc=(Get-PhotoField $action 'capture_utc');date_confidence=(Get-PhotoField $action 'date_confidence' 'unknown');date_source=$action.date_source;destination_volume_id=$Config.destination_volume_id;destination_disk_id=$Config.destination_disk_id;committed_at_utc=[DateTime]::UtcNow.ToString('o');code_version=(Get-PhotoField $Config 'release_version' 'development')}
            $write=$true
            if($prior.ContainsKey($action.asset_id)) {
                $oldAliases=@($prior[$action.asset_id].components.sources | ForEach-Object {$_.source_alias+'|'+$_.relative_path+'|'+$_.sha256})
                $newAliases=@($record.components.sources | ForEach-Object {$_.source_alias+'|'+$_.relative_path+'|'+$_.sha256})
                $oldSourceInfo=@{};foreach($s in $prior[$action.asset_id].components.sources){$oldSourceInfo[$s.source_alias+'|'+$s.relative_path+'|'+$s.sha256]=$s}
                $needsAssociationUpdate=@($record.components.sources | Where-Object {$key=$_.source_alias+'|'+$_.relative_path+'|'+$_.sha256;$oldSourceInfo.ContainsKey($key) -and (Get-PhotoField $oldSourceInfo[$key] 'association_revision' 0) -lt (Get-PhotoField $_ 'association_revision' 0)}).Count -gt 0
                if(@($newAliases | Where-Object {$_ -notin $oldAliases}).Count -eq 0 -and (Get-PhotoField $prior[$action.asset_id] 'association_revision' 0) -ge 3 -and -not $needsAssociationUpdate){$write=$false}
                else {
                    foreach($component in $record.components) {
                        $old=@($prior[$action.asset_id].components | Where-Object {$_.role -eq $component.role -and $_.sha256 -ceq $component.sha256})
                        foreach($source in $old[0].sources){if(($source.source_alias+'|'+$source.relative_path+'|'+$source.sha256) -notin $newAliases){$component.sources += $source}}
                    }
                }
            }
            if($write){Write-PhotoJournalLine $fJournal $record}
            Write-PhotoJournalLine $journal $record
            $committed.Add($record)
        }
        $result=[pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;run_id=$run;plan_sha256=$Plan.plan_sha256;new_files=$newFiles;committed=@($committed);retained=@($Plan.source_disposition | Where-Object operation -eq Retain);completed_at_utc=[DateTime]::UtcNow.ToString('o');code_version=(Get-PhotoField $Config 'release_version' 'development')}
        Write-PhotoJsonNew (Resolve-PhotoPath $Config.state_root ('runs\'+$run+'.json')) $result
        return $result
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose()}
}
function Test-PhotoReceipt($Config,$Receipt,[switch]$Fresh,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $errors=@();$files=0
    if($Receipt.archive_id -cne $Config.archive_id){throw 'WrongReceiptArchive'}
    foreach($record in $Receipt.committed) {
        if($record.state -ne 'Committed' -or $record.archive_id -cne $Config.archive_id){$errors += 'UncommittedRecord';continue}
        foreach($component in $record.components) {
            try {
                $path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path
                $item=Get-Item -LiteralPath $path -Force
                if(($item.Attributes -band 0x400) -or $item.Length -ne $component.size_bytes -or (Get-PhotoSha256 $path) -cne $component.sha256){throw 'HashMismatch'}
                $files++
            } catch {$errors += [pscustomobject]@{asset_id=$record.asset_id;reason=$_.Exception.Message}}
        }
    }
    return [pscustomobject]@{valid=($errors.Count -eq 0);files=$files;errors=$errors;fresh=$true;verified_at_utc=[DateTime]::UtcNow.ToString('o')}
}
function Get-PhotoIndependentRestoreInput($Config,$Component,[object[]]$Proofs,[hashtable]$Adapters=@{}) {
    foreach($proof in $Proofs) {
        if($proof.kind -notin @('file','retained') -or $proof.sha256 -cne $Component.sha256){continue}
        $path=[IO.Path]::GetFullPath($proof.path)
        if(@($Config.source_roots | Where-Object alias -eq ICLOUD | Where-Object {Test-PhotoPathWithin $path $_.path}).Count){continue}
        if($proof.kind -eq 'retained' -and -not(Test-PhotoPathWithin $path $Config.retained_root)){continue}
        Assert-PhotoNoDirectoryLinks (Split-Path -Parent $path)
        if(-not(Test-Path -LiteralPath $path -PathType Leaf)){continue}
        $volume=Get-PhotoBoundVolume $Config $path $Adapters
        if($volume.volume_id -cne $proof.volume_id -or $volume.disk_id -cne $proof.disk_id -or $volume.disk_id -ceq $Config.destination_disk_id){continue}
        $item=Get-Item -LiteralPath $path -Force
        if(([long]$item.Attributes -band 0x400) -or $item.Length -ne $Component.size_bytes){continue}
        if((Get-PhotoSha256 $path) -ceq $Component.sha256){return $path}
    }
    throw 'IndependentRestoreCopyMissing'
}
function Restore-PhotoSources($Config,$Receipt,[string]$DestinationRoot,[hashtable]$Adapters=@{},[object[]]$IndependentProofs=@()) {
    if($Receipt.archive_id -cne $Config.archive_id){throw 'WrongReceiptArchive'}
    $inputs=@{}
    if($IndependentProofs.Count) {
        Assert-PhotoRecoveryBindings $Config $Adapters
        foreach($record in $Receipt.committed){foreach($component in $record.components){$inputs[$component.destination_relative_path]=Get-PhotoIndependentRestoreInput $Config $component $IndependentProofs $Adapters}}
    } else {
        if(-not(Test-PhotoReceipt $Config $Receipt -Fresh -Adapters $Adapters).valid){throw 'InvalidReceiptData'}
        foreach($record in $Receipt.committed){foreach($component in $record.components){$inputs[$component.destination_relative_path]=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path}}
    }
    $root=[IO.Path]::GetFullPath($DestinationRoot)
    foreach($protected in @($Config.source_roots.path)+@($Config.archive_root,$Config.state_root,$Config.retained_root,$Config.release_code_root)+@($Config.protected_roots)) {
        if((Test-PhotoPathWithin $root $protected) -or (Test-PhotoPathWithin $protected $root)){throw 'UnsafeRestoreRoot'}
    }
    Assert-PhotoNoDirectoryLinks $root
    $files=0;$hashes=@()
    foreach($record in $Receipt.committed){foreach($component in $record.components){
        $input=$inputs[$component.destination_relative_path]
        foreach($source in $component.sources) {
            $output=Resolve-PhotoPath $root ($source.source_alias+'\'+$source.relative_path)
            if(Test-Path -LiteralPath $output){if((Get-PhotoSha256 $output) -cne $component.sha256){throw 'RestoreConflict'}}
            else {
                $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($output)) -Force
                $read=[IO.File]::OpenRead($input);$write=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                try {$read.CopyTo($write,1048576);$write.Flush($true)}finally{$write.Dispose();$read.Dispose()}
                (Get-Item -LiteralPath $output).LastWriteTimeUtc=[DateTime]::new([long]$source.mtime_ticks,[DateTimeKind]::Utc)
            }
            $hash=Get-PhotoSha256 $output;if($hash -cne $component.sha256){throw 'RestoreHashMismatch'};$hashes+=$hash;$files++
        }
    }}
    return [pscustomobject]@{files=$files;hashes=$hashes;completed_at_utc=[DateTime]::UtcNow.ToString('o')}
}
Export-ModuleMember -Function *
