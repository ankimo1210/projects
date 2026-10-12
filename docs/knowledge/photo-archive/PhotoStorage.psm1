Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking

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
function Assert-PhotoSourceFresh($Config,$Source,[string]$ExpectedHash) {
    $path=Get-PhotoSourcePath $Config $Source
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
    (Get-Item -LiteralPath $dest).LastWriteTimeUtc=[DateTime]::Parse($source.mtime_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
    return $true
}
function Get-PhotoReceiptIndex($Config,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $assets=@{};$invalid=0
    $root=Join-Path $Config.archive_root 'receipts'
    if(Test-Path -LiteralPath $root) {
        foreach($file in Get-ChildItem -LiteralPath $root -File -Filter '*.jsonl' | Sort-Object Name) {
            Assert-PhotoNoDirectoryLinks $root
            if([long]$file.Attributes -band 0x400){throw 'ReceiptLinkForbidden'}
            $reader=[IO.File]::OpenText($file.FullName)
            try {
                while(($line=$reader.ReadLine()) -ne $null) {
                    if([string]::IsNullOrWhiteSpace($line)){continue}
                    try {
                        $record=$line | ConvertFrom-Json
                        if($record.state -ne 'Committed' -or $record.archive_id -cne $Config.archive_id -or $record.schema_version -ne 2){throw 'InvalidReceipt'}
                        foreach($component in $record.components){Resolve-PhotoPath $Config.archive_root $component.destination_relative_path | Out-Null;if($component.sha256 -notmatch '^[a-f0-9]{64}$'){throw 'InvalidReceipt'}}
                        $assets[$record.asset_id]=$record
                    } catch {$invalid++}
                }
            } finally {$reader.Dispose()}
        }
    }
    return [pscustomobject]@{assets=@($assets.Values);invalid_lines=$invalid}
}
function Invoke-PhotoPlan($Config,$Plan,[hashtable]$Adapters=@{}) {
    Assert-PlanInputs $Plan $Config $Adapters
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        try {$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        Initialize-PhotoArchive $Config $Adapters
        $index=Get-PhotoReceiptIndex $Config $Adapters
        if($index.invalid_lines){throw 'CorruptReceiptJournal'}
        $prior=@{};foreach($record in $index.assets){$prior[$record.asset_id]=$record}
        $run=[guid]::NewGuid().ToString('N');$committed=[Collections.Generic.List[object]]::new();$newFiles=0
        $journal=Resolve-PhotoPath $Config.state_root ('journals\'+$run+'.jsonl')
        $fJournal=Resolve-PhotoPath $Config.archive_root ('receipts\'+$run+'.jsonl')
        foreach($action in $Plan.actions) {
            $volume=Assert-ArchiveBindings $Config $Adapters
            $required=0L
            foreach($component in $action.components){$path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path;if(-not(Test-Path -LiteralPath $path)){$required += [long][Math]::Ceiling($component.size_bytes/[double]$volume.cluster_bytes)*$volume.cluster_bytes}}
            if($volume.free_bytes - $required - 1048576L -lt $Config.reserve_f_bytes){throw 'InsufficientCapacity'}
            foreach($component in $action.components){foreach($source in $component.sources){Assert-PhotoSourceFresh $Config $source $component.sha256 | Out-Null}}
            Write-PhotoJournalLine $journal ([pscustomobject]@{state='Planned';action_id=$action.action_id;asset_id=$action.asset_id;plan_sha256=$Plan.plan_sha256;utc=[DateTime]::UtcNow.ToString('o')})
            $parts=@();$ordinal=0
            foreach($component in $action.components) {
                if(Copy-PhotoVerifiedComponent $Config $Plan $action $component $ordinal){$newFiles++}
                $parts += [pscustomobject]@{role=$component.role;sha256=$component.sha256;size_bytes=$component.size_bytes;destination_relative_path=$component.destination_relative_path;sources=@($component.sources)}
                $ordinal++
                Write-PhotoJournalLine $journal ([pscustomobject]@{state='Verified';action_id=$action.action_id;component=$ordinal;utc=[DateTime]::UtcNow.ToString('o')})
            }
            $record=[pscustomobject]@{schema_version=2;state='Committed';archive_id=$Config.archive_id;asset_id=$action.asset_id;action_id=$action.action_id;plan_sha256=$Plan.plan_sha256;association_status=$action.association_status;components=$parts;capture_date_raw=$action.capture_date_raw;capture_offset=$action.capture_offset;date_source=$action.date_source;destination_volume_id=$Config.destination_volume_id;destination_disk_id=$Config.destination_disk_id;committed_at_utc=[DateTime]::UtcNow.ToString('o');code_version=(Get-PhotoField $Config 'release_version' 'development')}
            $write=$true
            if($prior.ContainsKey($action.asset_id)) {
                $oldAliases=@($prior[$action.asset_id].components.sources | ForEach-Object {$_.source_alias+'|'+$_.relative_path+'|'+$_.sha256})
                $newAliases=@($record.components.sources | ForEach-Object {$_.source_alias+'|'+$_.relative_path+'|'+$_.sha256})
                if(@($newAliases | Where-Object {$_ -notin $oldAliases}).Count -eq 0){$write=$false}
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
function Restore-PhotoSources($Config,$Receipt,[string]$DestinationRoot,[hashtable]$Adapters=@{}) {
    if(-not(Test-PhotoReceipt $Config $Receipt -Fresh -Adapters $Adapters).valid){throw 'InvalidReceiptData'}
    $root=[IO.Path]::GetFullPath($DestinationRoot)
    foreach($protected in @($Config.source_roots.path)+@($Config.archive_root,$Config.state_root,$Config.retained_root,$Config.release_code_root)+@($Config.protected_roots)) {
        if((Test-PhotoPathWithin $root $protected) -or (Test-PhotoPathWithin $protected $root)){throw 'UnsafeRestoreRoot'}
    }
    Assert-PhotoNoDirectoryLinks $root
    $files=0;$hashes=@()
    foreach($record in $Receipt.committed){foreach($component in $record.components){
        $input=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path
        foreach($source in $component.sources) {
            $output=Resolve-PhotoPath $root ($source.source_alias+'\'+$source.relative_path)
            if(Test-Path -LiteralPath $output){if((Get-PhotoSha256 $output) -cne $component.sha256){throw 'RestoreConflict'}}
            else {
                $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($output)) -Force
                $read=[IO.File]::OpenRead($input);$write=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
                try {$read.CopyTo($write,1048576);$write.Flush($true)}finally{$write.Dispose();$read.Dispose()}
                (Get-Item -LiteralPath $output).LastWriteTimeUtc=[DateTime]::Parse($source.mtime_utc,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
            }
            $hash=Get-PhotoSha256 $output;if($hash -cne $component.sha256){throw 'RestoreHashMismatch'};$hashes+=$hash;$files++
        }
    }}
    return [pscustomobject]@{files=$files;hashes=$hashes;completed_at_utc=[DateTime]::UtcNow.ToString('o')}
}
Export-ModuleMember -Function *
