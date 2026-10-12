Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:BoundVolumeCache=@{}

function Test-PhotoPathWithin([string]$Path,[string]$Root) {
    $p=[IO.Path]::GetFullPath($Path).TrimEnd('\')
    $r=[IO.Path]::GetFullPath($Root).TrimEnd('\')
    return $p.Equals($r,[StringComparison]::OrdinalIgnoreCase) -or $p.StartsWith($r+'\',[StringComparison]::OrdinalIgnoreCase)
}
function Initialize-PhotoFileNative {
    if(-not ('PhotoArchive.FileMetadata' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'PhotoFileNative.cs')}
}
function Get-PhotoReparseTag([string]$Path) {
    Initialize-PhotoFileNative
    return [long][PhotoArchive.FileMetadata]::ReparseTag($Path)
}
function Test-PhotoCloudTag([long]$Tag) { return ($Tag -band 0xFFFF0FFFL) -eq 0x9000001AL }
function Get-PhotoRegisteredCloudRoot($Config) {
    $registration=Get-PhotoField $Config 'cloud_registration'
    if(-not $registration){return $null}
    $source=@($Config.source_roots | Where-Object alias -eq ICLOUD)[0]
    if($registration.root -cne $source.path -or $registration.provider_id -notlike 'iCloudPhotos!*'){throw 'WrongCloudRegistration'}
    $values=Get-ItemProperty -LiteralPath $registration.registry_path -ErrorAction Stop
    $paths=@($values.PSObject.Properties | Where-Object Name -notlike 'PS*' | ForEach-Object Value)
    if($registration.root -notin $paths){throw 'WrongCloudRegistration'}
    return $registration.root
}
function Assert-PhotoNoDirectoryLinks([string]$Path,[string]$AllowedCloudRoot=$null) {
    $current=[IO.Path]::GetFullPath($Path)
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item=Get-Item -LiteralPath $current -Force
            if ($item.PSIsContainer -and ([long]$item.Attributes -band 0x400)) {
                if(-not $AllowedCloudRoot -or -not (Test-PhotoPathWithin $current $AllowedCloudRoot) -or -not (Test-PhotoCloudTag (Get-PhotoReparseTag $current))) { throw 'DirectoryLinkForbidden' }
            }
        }
        $parent=[IO.Path]::GetDirectoryName($current.TrimEnd('\'))
        if ($parent -eq $current) { break }; $current=$parent
    }
}
function Resolve-PhotoPath([string]$Root,[string]$Relative,[string]$AllowedCloudRoot=$null) {
    if ([IO.Path]::IsPathRooted($Relative) -or $Relative -match '(^|[\\/])\.\.([\\/]|$)' -or $Relative.Contains(':')) { throw 'PathTraversal' }
    $result=[IO.Path]::GetFullPath([IO.Path]::Combine($Root,$Relative))
    if (-not (Test-PhotoPathWithin $result $Root) -or $result.TrimEnd('\') -eq $Root.TrimEnd('\')) { throw 'PathTraversal' }
    Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($result)) $AllowedCloudRoot
    return $result
}
function Get-PhotoNativeVolume([string]$Path) {
    Initialize-PhotoFileNative
    $volume=[PhotoArchive.FileMetadata]::Volume([IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path)))
    return [pscustomobject]@{native_id=$volume.NativeId;free_bytes=$volume.FreeBytes;cluster_bytes=$volume.ClusterBytes;file_system=$volume.FileSystem}
}
function Get-PhotoVolume([string]$Path) {
    $drive=[IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path))
    if ($drive -notmatch '^([A-Za-z]):\\$') { throw 'LocalVolumeRequired' }
    $letter=$Matches[1]
    $volume=Get-Volume -DriveLetter $letter -ErrorAction Stop
    $disk=Get-Partition -DriveLetter $letter -ErrorAction Stop | Get-Disk -ErrorAction Stop
    if (@($disk).Count -ne 1 -or [string]::IsNullOrWhiteSpace([string]$disk.UniqueId)) { throw 'AmbiguousPhysicalDisk' }
    $native=Get-PhotoNativeVolume $Path
    return [pscustomobject]@{volume_id=([string]$volume.UniqueId).Trim();disk_id=([string]$disk.UniqueId).Trim();native_id=$native.native_id;free_bytes=$native.free_bytes;cluster_bytes=$native.cluster_bytes;file_system=$native.file_system}
}
function Get-PhotoBoundVolume($Config,[string]$Path,[hashtable]$Adapters=@{}) {
    if ($Adapters.ContainsKey('Volume')) {
        if ($Config.archive_id -notlike 'fixture-*' -or -not (Test-PhotoPathWithin $Config.fixture_root $env:TEMP) -or [IO.Path]::GetFileName($Config.fixture_root) -notlike 'photo-archive-test-*') { throw 'TestAdapterForbidden' }
        $all=@($Config.source_roots.path)+@($Config.archive_root,$Config.state_root,$Config.retained_root,$Config.release_code_root)+@($Config.protected_roots)
        foreach($p in $all){if(-not(Test-PhotoPathWithin $p $Config.fixture_root)){throw 'TestAdapterForbidden'}}
        if ([IO.File]::ReadAllText((Join-Path $Config.fixture_root '.fixture-owner')) -cne $Config.fixture_root) { throw 'TestAdapterForbidden' }
        return & $Adapters.Volume $Path
    }
    $native=Get-PhotoNativeVolume $Path
    $drive=[IO.Path]::GetPathRoot([IO.Path]::GetFullPath($Path))
    $key=$Config.archive_id+'|'+$drive+'|'+$native.native_id
    if(-not $script:BoundVolumeCache.ContainsKey($key)){$script:BoundVolumeCache[$key]=Get-PhotoVolume $Path}
    $bound=$script:BoundVolumeCache[$key]
    if($bound.native_id -cne $native.native_id){throw 'NativeMediaChanged'}
    return [pscustomobject]@{volume_id=$bound.volume_id;disk_id=$bound.disk_id;native_id=$native.native_id;free_bytes=$native.free_bytes;cluster_bytes=$native.cluster_bytes;file_system=$native.file_system}
}
function Read-ArchiveConfig([string]$ConfigPath,[switch]$Recovery) {
    $config=Get-Content -LiteralPath $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($config.archive_id -like 'fixture-*') { throw 'FixtureConfigForbidden' }
    if ($config.schema_version -ne 2 -or $config.auto_cleanup -ne $false) { throw 'UnsupportedConfig' }
    if ($config.retention_days -lt 7 -or $config.reserve_c_bytes -lt 34359738368L -or $config.reserve_f_bytes -lt 34359738368L -or $config.hash_workers -lt 1 -or $config.hash_workers -gt 2 -or $config.download_timeout_seconds -gt 600 -or $config.download_timeout_seconds -le 0 -or $config.download_retries -gt 1) { throw 'UnsafeConfig' }
    if($Recovery){Assert-PhotoRecoveryBindings $config | Out-Null}else{Assert-ArchiveBindings $config | Out-Null}
    return $config
}
function Assert-PhotoRecoveryBindings($Config,[hashtable]$Adapters=@{}) {
    $roots=@($Config.source_roots.path)+@($Config.archive_root,$Config.state_root,$Config.retained_root,$Config.release_code_root)+@($Config.protected_roots)
    foreach($root in $roots){if([string]::IsNullOrWhiteSpace($root) -or $root -notmatch '^[A-Za-z]:\\'){throw 'AbsoluteLocalRootRequired'}}
    for($i=0;$i -lt $roots.Count;$i++){for($j=$i+1;$j -lt $roots.Count;$j++){if((Test-PhotoPathWithin $roots[$i] $roots[$j]) -or (Test-PhotoPathWithin $roots[$j] $roots[$i])){throw 'OverlappingRoots'}}}
    $c=@($Config.source_roots | Where-Object alias -eq OLD_C)
    if($c.Count -ne 1){throw 'InvalidRecoveryBinding'}
    foreach($path in @($Config.state_root,$Config.retained_root,$Config.release_code_root)) {
        Assert-PhotoNoDirectoryLinks $path
        $volume=Get-PhotoBoundVolume $Config $path $Adapters
        if($volume.volume_id -cne $c[0].volume_id -or $volume.disk_id -cne $c[0].disk_id){throw 'WrongRecoveryVolume'}
    }
}
function Assert-ArchiveBindings($Config,[hashtable]$Adapters=@{}) {
    $cloudRoot=Get-PhotoRegisteredCloudRoot $Config
    $roots=@($Config.source_roots.path)+@($Config.archive_root,$Config.state_root,$Config.retained_root,$Config.release_code_root)+@($Config.protected_roots)
    foreach($root in $roots) {
        if ([string]::IsNullOrWhiteSpace($root) -or $root -notmatch '^[A-Za-z]:\\') { throw 'AbsoluteLocalRootRequired' }
        Assert-PhotoNoDirectoryLinks $root $cloudRoot
    }
    for($i=0;$i -lt $roots.Count;$i++) { for($j=$i+1;$j -lt $roots.Count;$j++) {
        if ((Test-PhotoPathWithin $roots[$i] $roots[$j]) -or (Test-PhotoPathWithin $roots[$j] $roots[$i])) { throw 'OverlappingRoots' }
    }}
    if ((@($Config.source_roots.alias | Sort-Object -Unique) -join ',') -ne 'ICLOUD,OLD_C,OLD_F') { throw 'InvalidSourceAliases' }
    $volume=Get-PhotoBoundVolume $Config $Config.archive_root $Adapters
    if ($volume.volume_id -cne $Config.destination_volume_id -or $volume.disk_id -cne $Config.destination_disk_id) { throw 'WrongVolume' }
    foreach($source in $Config.source_roots) {
        if(-not(Test-Path -LiteralPath $source.path -PathType Container)){throw 'MissingSourceRoot'}
        $v=Get-PhotoBoundVolume $Config $source.path $Adapters
        if($v.volume_id -cne $source.volume_id -or $v.disk_id -cne $source.disk_id){throw 'WrongSourceVolume'}
    }
    $marker=Join-Path $Config.archive_root 'archive-marker.json'
    if(Test-Path -LiteralPath $marker){
        $m=Get-Content -LiteralPath $marker -Raw -Encoding UTF8 | ConvertFrom-Json
        if($m.schema_version -ne 2 -or $m.archive_id -cne $Config.archive_id -or $m.volume_id -cne $Config.destination_volume_id -or $m.disk_id -cne $Config.destination_disk_id){throw 'WrongArchiveMarker'}
    } elseif ((Test-Path -LiteralPath $Config.archive_root) -and @(Get-ChildItem -LiteralPath $Config.archive_root -Force).Count) { throw 'UnregisteredArchiveContents' }
    return $volume
}
function Get-PhotoField($Object,[string]$Name,$Default=$null) {
    $property=$Object.PSObject.Properties[$Name]
    if($null -eq $property){return $Default}; return $property.Value
}
function Get-PhotoSha256([string]$Path) {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose();$stream.Dispose() }
}
function Get-PhotoTextHash([string]$Text) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
function Get-PhotoInventory($Config,[string[]]$Aliases=@('OLD_C','OLD_F','ICLOUD'),[ValidateSet('MetadataOnly','Fresh','Cached')][string]$HashMode='Fresh',[hashtable]$Adapters=@{},[string[]]$RelativePaths=@(),[hashtable]$HashCache=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $cloudRoot=Get-PhotoRegisteredCloudRoot $Config
    Initialize-PhotoFileNative
    foreach($source in $Config.source_roots | Where-Object { $_.alias -in $Aliases }) {
        $volume=Get-PhotoBoundVolume $Config $source.path $Adapters
        $stack=[Collections.Generic.Stack[string]]::new();$stack.Push($source.path)
        while($stack.Count) {
            $dir=$stack.Pop()
            Assert-PhotoNoDirectoryLinks $dir $cloudRoot
            foreach($item in Get-ChildItem -LiteralPath $dir -Force -ErrorAction Stop) {
                $attributes=[long]$item.Attributes
                if($item.PSIsContainer -and -not($attributes -band 0x400)){$stack.Push($item.FullName);continue}
                $relative=$item.FullName.Substring($source.path.TrimEnd('\').Length+1)
                if($RelativePaths.Count -and $relative -notin $RelativePaths){continue}
                $hash=$null;$errorReason=$null;$streams=@();$tag=$null;$status='Available';$fileId=$null;$usedHashMode='None'
                if($item.PSIsContainer){$status='RetainDirectoryLink'}
                elseif($attributes -band 0x400){
                    try {$tag=Get-PhotoReparseTag $item.FullName} catch {$errorReason=$_.Exception.Message}
                    if(-not $cloudRoot -or -not(Test-PhotoPathWithin $item.FullName $cloudRoot) -or -not(Test-PhotoCloudTag $tag)){$status='RetainUnknownReparse'}
                }
                if(($attributes -band 0x1000) -or ($attributes -band 0x400000)){$status='PendingOnlineOnly'}
                $size=if($item.PSIsContainer){0L}else{[long]$item.Length}
                $mtime=$item.LastWriteTimeUtc.Ticks
                if($status -eq 'Available') {
                    try {
                        $streams=@(Get-Item -LiteralPath $item.FullName -Stream * -ErrorAction Stop | Where-Object {$_.Stream -ne ':$DATA' -and $_.Stream -ne '$DATA'} | Select-Object Stream,Length)
                    } catch {
                        if((Get-PhotoNativeVolume $item.FullName).file_system -ne 'exFAT'){$status='RetainStreamInspectionFailed';$errorReason=$_.Exception.Message}
                    }
                    if($streams.Count){$status='RetainStreams'}
                    if($attributes -band 0x4000){$status='RetainEncryptedSource'}
                    if($status -eq 'Available' -and $HashMode -ne 'MetadataOnly') {
                        try {
                            $fileId=[PhotoArchive.FileMetadata]::Identity($item.FullName)
                            $cacheKey=$item.FullName.ToLowerInvariant()
                            $old=if($HashCache.ContainsKey($cacheKey)){$HashCache[$cacheKey]}else{$null}
                            if($HashMode -eq 'Cached' -and $old -and $old.file_id -ceq $fileId -and $old.size_bytes -eq $size -and $old.mtime_ticks -eq $mtime -and $old.source_volume_id -ceq $source.volume_id -and $old.source_disk_id -ceq $source.disk_id -and $old.sha256 -match '^[a-f0-9]{64}$') {$hash=$old.sha256;$usedHashMode='Cached'}
                            else {$hash=Get-PhotoSha256 $item.FullName;$usedHashMode='Fresh'}
                            $after=Get-Item -LiteralPath $item.FullName -Force
                            if($after.Length -ne $size -or $after.LastWriteTimeUtc.Ticks -ne $mtime -or [PhotoArchive.FileMetadata]::Identity($item.FullName) -cne $fileId){$status='PendingSourceChanged';$hash=$null}
                        } catch {$status='ReadError';$errorReason=$_.Exception.Message}
                    }
                }
                [pscustomobject]@{source_alias=$source.alias;relative_path=$relative;full_path=$item.FullName;source_volume_id=$source.volume_id;source_disk_id=$source.disk_id;file_id=$fileId;size_bytes=$size;allocated_bytes=([long][Math]::Ceiling($size/[double]$volume.cluster_bytes)*$volume.cluster_bytes);mtime_utc=$item.LastWriteTimeUtc.ToString('o');mtime_ticks=$mtime;attributes=$attributes;reparse_tag=$tag;sha256=$hash;hash_mode=$usedHashMode;streams=$streams;read_status=$status;error=$errorReason;observed_at_utc=[DateTime]::UtcNow.ToString('o')}
            }
        }
    }
}
function Read-PhotoMetadata([object[]]$Files,$ToolReceipt) {
    if($null -eq $ToolReceipt){throw 'MissingMetadataTool'}
    if((Get-PhotoSha256 $ToolReceipt.path) -cne $ToolReceipt.sha256.ToLowerInvariant()){throw 'MetadataToolChanged'}
    $command=$ToolReceipt.path;$prefix=@()
    if((Get-PhotoField $ToolReceipt 'driver') -eq 'perl') {
        if((Get-PhotoSha256 $ToolReceipt.driver_path) -cne $ToolReceipt.driver_sha256.ToLowerInvariant()){throw 'MetadataDriverChanged'}
        if((Get-PhotoSha256 $ToolReceipt.source_manifest) -cne $ToolReceipt.source_manifest_sha256.ToLowerInvariant()){throw 'MetadataManifestChanged'}
        $manifest=Get-Content -LiteralPath $ToolReceipt.source_manifest -Raw -Encoding UTF8 | ConvertFrom-Json
        $toolRoot=Split-Path -Parent $ToolReceipt.path
        foreach($entry in $manifest){if((Get-PhotoSha256 (Resolve-PhotoPath $toolRoot $entry.relative_path)) -cne $entry.sha256.ToLowerInvariant()){throw 'MetadataSourceChanged'}}
        $command=$ToolReceipt.driver_path;$prefix=@($ToolReceipt.path)
    }
    $eligible=@($Files | Where-Object {$_.read_status -eq 'Available'})
    for($start=0;$start -lt $eligible.Count;$start+=100) {
        $end=[Math]::Min($start+99,$eligible.Count-1)
        $paths=@($eligible[$start..$end].full_path)
        $emptyConfig=if($PSVersionTable.PSVersion.Major -le 5){'""'}else{''}
        $args=$prefix+@('-config',$emptyConfig,'-j','-G1','-charset','filename=UTF8','-DateTimeOriginal','-OffsetTimeOriginal','-SubSecTimeOriginal','-CreateDate','-CreationDate','-ContentIdentifier','-LivePhotoVideoIndex','-FileType','-FileName','-FileSize','--')+$paths
        $err=[IO.Path]::GetTempFileName()
        try {
            $output=& $command @args 2> $err
            if([string]::IsNullOrWhiteSpace(($output -join "`n"))){throw 'MetadataReadFailed'}
            $records=($output -join "`n") | ConvertFrom-Json
            foreach($record in $records) {
                $normalized=[ordered]@{SourceFile=$record.SourceFile}
                foreach($field in @('DateTimeOriginal','OffsetTimeOriginal','SubSecTimeOriginal','CreateDate','CreationDate','ContentIdentifier','LivePhotoVideoIndex','FileType')) {
                    $matches=@($record.PSObject.Properties | Where-Object {($_.Name -split ':')[-1] -eq $field})
                    if($matches.Count -eq 1){$normalized[$field]=$matches[0].Value}
                    elseif($matches.Count -gt 1) {
                        $unique=@($matches.Value | Sort-Object -Unique)
                        if($unique.Count -eq 1){$normalized[$field]=$unique[0]}else{$normalized['MetadataConflict']=$true}
                    }
                }
                $normalized['raw_tags']=$record
                [pscustomobject]$normalized
            }
        } finally {if(Test-Path -LiteralPath $err){Remove-Item -LiteralPath $err -Force}}
    }
}
function New-PhotoAssets([object[]]$FileRecords,[object[]]$Metadata=@()) {
    $metaIndex=@{}
    foreach($m in $Metadata){$metaIndex[([IO.Path]::GetFullPath($m.SourceFile)).ToLowerInvariant()]=$m}
    # Relations form a graph: content identifiers and same-stem candidates both
    # bind components. A sidecar must protect its image as well as itself.
    $candidates=[Collections.Generic.List[object]]::new();$parents=@{};$ids=@{};$stems=@{}
    foreach($file in $FileRecords) {
        $meta=if($metaIndex.ContainsKey($file.full_path.ToLowerInvariant())){$metaIndex[$file.full_path.ToLowerInvariant()]}else{$null}
        $contentId=if($meta){Get-PhotoField $meta 'ContentIdentifier'}else{$null}
        $context=$file.source_alias+'|'+[IO.Path]::GetDirectoryName($file.relative_path)
        $number=$candidates.Count;$parents[$number]=$number
        $name=[IO.Path]::GetFileNameWithoutExtension($file.relative_path)
        if($name.StartsWith('._')){$name=$name.Substring(2)}
        # XMP may be named photo.jpg.xmp rather than photo.xmp.
        if([IO.Path]::GetExtension($file.relative_path) -in @('.xmp','.aae')){$name=[IO.Path]::GetFileNameWithoutExtension($name)}
        $links=@($context+'|stem|'+$name.ToLowerInvariant())
        if($contentId){$links+= $context+'|live|'+$contentId}
        foreach($link in $links) {
            $map=if($link.Contains('|live|')){$ids}else{$stems}
            if($map.ContainsKey($link)) {
                $other=$map[$link];while($parents[$other] -ne $other){$other=$parents[$other]}
                $current=$number;while($parents[$current] -ne $current){$current=$parents[$current]}
                $parents[$current]=$other
            } else {$map[$link]=$number}
        }
        $candidates.Add([pscustomobject]@{file=$file;metadata=$meta;content_id=$contentId;context=$context})
    }
    $groups=@{}
    for($number=0;$number -lt $candidates.Count;$number++) {
        $parent=$number;while($parents[$parent] -ne $parent){$parent=$parents[$parent]}
        if(-not $groups.ContainsKey($parent)){$groups[$parent]=[Collections.Generic.List[object]]::new()}
        $groups[$parent].Add($candidates[$number])
    }
    foreach($key in $groups.Keys | Sort-Object) {
        $entries=@($groups[$key]);$components=@()
        foreach($e in $entries) {
            $ext=[IO.Path]::GetExtension($e.file.relative_path).ToLowerInvariant()
            $role=if($ext -in @('.mov','.mp4')){'video'}elseif($ext -in @('.aae','.xmp') -or [IO.Path]::GetFileName($e.file.relative_path) -like '._*'){'sidecar'}elseif($ext -eq '.dng'){'raw'}elseif($ext -in @('.jpg','.jpeg','.png','.heic','.avif','.webp')){'image'}else{'unknown'}
            $components += [pscustomobject]@{role=$role;file=$e.file;original_name=[IO.Path]::GetFileName($e.file.relative_path)}
        }
        $key=$entries[0].context+'|'+((@($entries.file.relative_path) | Sort-Object) -join '|')
        $contentIds=@($entries.content_id | Where-Object {$_} | Sort-Object -Unique)
        $hasId=$contentIds.Count -gt 0
        $complete=(@($components | Where-Object {$_.role -in @('sidecar','raw','unknown') -or $_.file.read_status -ne 'Available' -or -not $_.file.sha256}).Count -eq 0)
        $complete=$complete -and @($entries | Where-Object {-not $_.metadata -or (Get-PhotoField $_.metadata 'MetadataConflict' $false) -or -not ((Get-PhotoField $_.metadata 'FileType') -or $_.content_id -or (Get-PhotoField $_.metadata 'DateTimeOriginal') -or (Get-PhotoField $_.metadata 'CreationDate'))}).Count -eq 0
        if($hasId){$complete=$complete -and $contentIds.Count -eq 1 -and @($entries | Where-Object {-not $_.content_id}).Count -eq 0 -and @($components | Where-Object role -eq image).Count -eq 1 -and @($components | Where-Object role -eq video).Count -eq 1}
        else {$complete=$complete -and $entries.Count -eq 1 -and @($entries | Where-Object {$null -ne (Get-PhotoField $_.metadata 'LivePhotoVideoIndex')}).Count -eq 0}
        if($hasId -and -not $complete -and $entries.Count -gt 1) {
            # Ambiguous relations are stored together with their original context.
            $complete=$false
        }
        $dated=@($entries | Where-Object {[IO.Path]::GetExtension($_.file.relative_path).ToLowerInvariant() -notin @('.mov','.mp4')})
        $dateMeta=if($dated.Count){$dated[0].metadata}else{$entries[0].metadata}
        $date=$null;$offset=$null;$subsec=$null;$utc=$null;$confidence='unknown';$bucket='_undated';$dateSource='unknown'
        if($dateMeta -and -not (Get-PhotoField $dateMeta 'MetadataConflict' $false)) {
            foreach($field in @('DateTimeOriginal','CreationDate')) {
                $value=[string](Get-PhotoField $dateMeta $field)
                if($value -match '^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:([+-]\d{2}:\d{2}|Z))?$') {
                    $parsed=[DateTime]::MinValue
                    if([DateTime]::TryParseExact($value.Substring(0,19),'yyyy:MM:dd HH:mm:ss',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$parsed) -and $parsed.Year -ge 1900 -and $parsed -le [DateTime]::UtcNow.AddDays(2)) {
                        $date=$value;$bucket=('{0:0000}\{1:00}' -f $parsed.Year,$parsed.Month);$dateSource=$field
                        $offset=Get-PhotoField $dateMeta 'OffsetTimeOriginal'
                        if(-not $offset -and $Matches[7]){$offset=$Matches[7]}
                        $fraction=[regex]::Match($value,'\.(\d+)')
                        $subsec=if($fraction.Success){$fraction.Groups[1].Value}else{Get-PhotoField $dateMeta 'SubSecTimeOriginal'}
                        $confidence='local_time_only'
                        if($offset -match '^(Z|[+-]\d{2}:\d{2})$') {
                            $iso=$parsed.ToString('yyyy-MM-ddTHH:mm:ss',[Globalization.CultureInfo]::InvariantCulture)
                            if($subsec -match '^\d+$'){$iso+='.'+([string]$subsec).Substring(0,[Math]::Min(7,([string]$subsec).Length))}
                            $zoned=[DateTimeOffset]::MinValue
                            if([DateTimeOffset]::TryParse($iso+$offset,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::None,[ref]$zoned)){$utc=$zoned.UtcDateTime.ToString('o');$confidence='offset_verified'}
                        }
                        break
                    }
                }
            }
        }
        $identity=[ordered]@{schema_version=2;components=@($components | Sort-Object role,@{Expression={$_.file.sha256}} | ForEach-Object {[ordered]@{role=$_.role;sha256=$_.file.sha256}});association=if($complete){'Complete'}else{'PendingAssociation'};context=if($complete){$null}else{$key}}
        $id=Get-PhotoTextHash ($identity | ConvertTo-Json -Depth 8 -Compress)
        [pscustomobject]@{asset_id=$id;components=$components;capture_date_raw=$date;capture_offset=$offset;capture_subsec_raw=$subsec;capture_utc=$utc;date_confidence=$confidence;date_source=$dateSource;calendar_bucket=$bucket;association_status=if($complete){'Complete'}else{'PendingAssociation'};version=2;aliases=@($components.file | ForEach-Object {[pscustomobject]@{source_alias=$_.source_alias;relative_path=$_.relative_path}})}
    }
}
function Convert-PhotoCanonicalValue($Value) {
    if($null -eq $Value){return $null}
    if($Value -is [DateTime] -or $Value -is [DateTimeOffset]){return $Value.ToString('o',[Globalization.CultureInfo]::InvariantCulture)}
    if($Value -is [string] -or $Value -is [ValueType]){return $Value}
    if($Value -is [Collections.IDictionary]) {
        $result=[ordered]@{};$keys=[string[]]@($Value.Keys);[Array]::Sort($keys,[StringComparer]::Ordinal)
        foreach($key in $keys){$result[$key]=Convert-PhotoCanonicalValue $Value[$key]};return $result
    }
    if($Value -is [Collections.IEnumerable]) {
        $items=@(foreach($item in $Value){Convert-PhotoCanonicalValue $item});return ,$items
    }
    $result=[ordered]@{};$keys=[string[]]@($Value.PSObject.Properties.Name);[Array]::Sort($keys,[StringComparer]::Ordinal)
    foreach($key in $keys){$result[$key]=Convert-PhotoCanonicalValue $Value.PSObject.Properties[$key].Value};return $result
}
function Get-PhotoPlanHash($Plan) {
    $copy=[ordered]@{}
    foreach($property in $Plan.PSObject.Properties){if($property.Name -ne 'plan_sha256'){$copy[$property.Name]=$property.Value}}
    return Get-PhotoTextHash ((Convert-PhotoCanonicalValue $copy | ConvertTo-Json -Depth 48 -Compress).Replace("`r`n","`n"))
}
function Get-PhotoSourcePath($Config,$FileRecord) {
    $source=@($Config.source_roots | Where-Object alias -eq $FileRecord.source_alias)
    if($source.Count -ne 1 -or $source[0].volume_id -cne $FileRecord.source_volume_id -or $source[0].disk_id -cne $FileRecord.source_disk_id){throw 'WrongSourceBinding'}
    $path=Resolve-PhotoPath $source[0].path $FileRecord.relative_path (Get-PhotoRegisteredCloudRoot $Config)
    if(-not $path.Equals([IO.Path]::GetFullPath($FileRecord.full_path),[StringComparison]::OrdinalIgnoreCase)){throw 'SourcePathMismatch'}
    return $path
}
function Test-PhotoCachedFile([string]$Path,[string]$Hash,[hashtable]$Cache) {
    $key=$Path.ToLowerInvariant()
    if(-not $Cache.ContainsKey($key)){return $false}
    $known=$Cache[$key]
    if($known.sha256 -cne $Hash -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){return $false}
    $item=Get-Item -LiteralPath $Path -Force
    if([long]$item.Attributes -band 0x400){return $false}
    return $known.size_bytes -eq $item.Length -and $known.mtime_ticks -eq $item.LastWriteTimeUtc.Ticks -and $known.file_id -ceq [PhotoArchive.FileMetadata]::Identity($Path)
}
function Copy-PhotoAssociationSource($File,$Asset) {
    $value=[ordered]@{};foreach($p in $File.PSObject.Properties){$value[$p.Name]=$p.Value}
    $value['association_revision']=3;$value['association_status']=$Asset.association_status;$value['association_group']=$Asset.asset_id
    return [pscustomobject]$value
}
function New-PhotoMigrationPlan($Config,[object[]]$FileRecords,[object[]]$Assets,[object[]]$DestinationIndex=@(),[hashtable]$Adapters=@{},[long]$CopyBudgetBytes=[long]::MaxValue,[hashtable]$DestinationStatCache=@{}) {
    $volume=Assert-ArchiveBindings $Config $Adapters
    $actions=[Collections.Generic.List[object]]::new();$dispositions=[Collections.Generic.List[object]]::new();$ids=@{};$existing=@{}
    foreach($entry in $DestinationIndex){$existing[$entry.asset_id]=$entry}
    $mediaBytes=0L;$largestAsset=0L
    foreach($asset in $Assets) {
        $readable=@($asset.components | Where-Object {$_.file.read_status -ne 'Available' -or $_.file.sha256 -notmatch '^[a-f0-9]{64}$'}).Count -eq 0
        foreach($component in $asset.components){Get-PhotoSourcePath $Config $component.file | Out-Null}
        if(-not $readable){
            foreach($component in $asset.components){$dispositions.Add([pscustomobject]@{source=$component.file;operation='Retain';asset_id=$asset.asset_id;reason=$component.file.read_status})}
            continue
        }
        if(-not $ids.ContainsKey($asset.asset_id)) {
            $stem=[IO.Path]::GetFileNameWithoutExtension($asset.components[0].original_name).Normalize([Text.NormalizationForm]::FormC)
            $stem=[regex]::Replace($stem,'[<>:"/\\|?*\x00-\x1f]','_').TrimEnd(' ','.')
            if($stem.Length -gt 60){$stem=$stem.Substring(0,60)};if(-not $stem){$stem='asset'}
            $folder='media\'+$asset.calendar_bucket+'\'+$stem+'__'+$asset.asset_id.Substring(0,12)
            $components=@();$assetBytes=0L
            foreach($component in $asset.components) {
                $relative=$folder+'\'+$component.original_name
                if((Resolve-PhotoPath $Config.archive_root $relative).Length -gt 240){throw 'UnsupportedDestinationLongPath'}
                $components += [pscustomobject]@{role=$component.role;sha256=$component.file.sha256;size_bytes=$component.file.size_bytes;destination_relative_path=$relative;sources=@(Copy-PhotoAssociationSource $component.file $asset)}
                $assetBytes += [long][Math]::Ceiling($component.file.size_bytes/[double]$volume.cluster_bytes)*$volume.cluster_bytes
            }
            $operation='Copy'
            if($existing.ContainsKey($asset.asset_id)) {
                $prior=$existing[$asset.asset_id]
                foreach($component in $components) {
                    $matches=@($prior.components | Where-Object {$_.role -eq $component.role -and $_.sha256 -ceq $component.sha256})
                    if($matches.Count -ne 1){throw 'ExistingAssetMismatch'}
                    $component.destination_relative_path=$matches[0].destination_relative_path
                    $path=Resolve-PhotoPath $Config.archive_root $component.destination_relative_path
                    if(-not(Test-PhotoCachedFile $path $component.sha256 $DestinationStatCache) -and (Get-PhotoSha256 $path) -cne $component.sha256){throw 'ExistingAssetChanged'}
                }
                $operation='Reuse'
            } elseif($mediaBytes+$assetBytes -gt $CopyBudgetBytes) {
                foreach($component in $asset.components){$dispositions.Add([pscustomobject]@{source=$component.file;operation='Retain';asset_id=$asset.asset_id;reason='RetainCapacity'})}
                continue
            } else { $mediaBytes+=$assetBytes;if($assetBytes -gt $largestAsset){$largestAsset=$assetBytes} }
            $action=[pscustomobject]@{action_id=[guid]::NewGuid().ToString('N');asset_id=$asset.asset_id;operation=$operation;association_status=$asset.association_status;capture_date_raw=$asset.capture_date_raw;capture_offset=$asset.capture_offset;capture_subsec_raw=(Get-PhotoField $asset 'capture_subsec_raw');capture_utc=(Get-PhotoField $asset 'capture_utc');date_confidence=(Get-PhotoField $asset 'date_confidence' 'unknown');date_source=$asset.date_source;components=$components}
            $ids[$asset.asset_id]=$action;$actions.Add($action)
        } else {
            $action=$ids[$asset.asset_id]
            foreach($component in $asset.components) {
                $match=@($action.components | Where-Object {$_.role -eq $component.role -and $_.sha256 -ceq $component.file.sha256})
                if($match.Count -ne 1){throw 'AssetIdentityCollision'}
                $match[0].sources += Copy-PhotoAssociationSource $component.file $asset
            }
        }
        foreach($component in $asset.components){$dispositions.Add([pscustomobject]@{source=$component.file;operation=$action.operation;asset_id=$asset.asset_id;reason=$asset.association_status})}
    }
    if($dispositions.Count -ne $FileRecords.Count){throw 'UnexplainedSourceCount'}
    $directoryBytes=[long]($actions.Count*3+8)*$volume.cluster_bytes
    $metadataBytes=67108864L
    $needed=$mediaBytes+$directoryBytes+$metadataBytes+$largestAsset+[long]$Config.reserve_f_bytes
    if($needed -gt $volume.free_bytes){throw ('InsufficientCapacity required='+$needed+' free='+$volume.free_bytes)}
    $plan=[pscustomobject]@{schema_version=2;plan_id=[guid]::NewGuid().ToString('N');archive_id=$Config.archive_id;destination_volume_id=$Config.destination_volume_id;destination_disk_id=$Config.destination_disk_id;created_at_utc=[DateTime]::UtcNow.ToString('o');actions=@($actions);source_disposition=@($dispositions);physical_capacity_budget=[pscustomobject]@{media_bytes=$mediaBytes;directory_bytes=$directoryBytes;metadata_bytes=$metadataBytes;staging_bytes=$largestAsset;reserve_bytes=[long]$Config.reserve_f_bytes;required_bytes=$needed;free_bytes=$volume.free_bytes;cluster_bytes=$volume.cluster_bytes};plan_sha256=$null}
    $plan.plan_sha256=Get-PhotoPlanHash $plan
    return $plan
}
function Assert-PlanInputs($MigrationPlan,$Config,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    if($MigrationPlan.schema_version -ne 2 -or $MigrationPlan.archive_id -cne $Config.archive_id -or $MigrationPlan.destination_volume_id -cne $Config.destination_volume_id -or $MigrationPlan.destination_disk_id -cne $Config.destination_disk_id){throw 'PlanBindingChanged'}
    if((Get-PhotoPlanHash $MigrationPlan) -cne $MigrationPlan.plan_sha256){throw 'PlanChanged'}
    foreach($action in $MigrationPlan.actions){foreach($component in $action.components){Resolve-PhotoPath $Config.archive_root $component.destination_relative_path | Out-Null;foreach($source in $component.sources){Get-PhotoSourcePath $Config $source | Out-Null}}}
}
Export-ModuleMember -Function *
