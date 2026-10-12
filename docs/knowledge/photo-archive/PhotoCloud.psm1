Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
function Initialize-PhotoCloudNative {
    Initialize-PhotoFileNative
    if(-not('PhotoArchive.CloudNative' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot 'PhotoCloudNative.cs')}
}
function Get-CloudFileStatus($Config,$FileRecord,[hashtable]$Adapters=@{}) {
    if($FileRecord.source_alias -ne 'ICLOUD'){throw 'NotRegisteredCloudSource'}
    $path=Get-PhotoSourcePath $Config $FileRecord
    if($Adapters.ContainsKey('CloudStatus')) {
        Get-PhotoBoundVolume $Config $path $Adapters | Out-Null
        return & $Adapters.CloudStatus $path
    }
    $cloudRoot=Get-PhotoRegisteredCloudRoot $Config
    if(-not $cloudRoot -or -not(Test-PhotoPathWithin $path $cloudRoot)){throw 'NotRegisteredCloudSource'}
    Initialize-PhotoCloudNative
    $item=Get-Item -LiteralPath $path -Force
    $tag=0L;if([long]$item.Attributes -band 0x400){$tag=Get-PhotoReparseTag $path;if(-not(Test-PhotoCloudTag $tag)){throw 'UnknownCloudReparse'}}
    $state=[PhotoArchive.CloudNative]::State($path,[uint32]$item.Attributes,[uint32]$tag)
    $placeholder=($state.Flags -band 1) -ne 0
    $available=(-not($state.Flags -band 0x10)) -and (-not([long]$item.Attributes -band 0x1000)) -and (-not([long]$item.Attributes -band 0x400000))
    $rootPolicy=$null
    if($placeholder) {
        $rootPolicy=[PhotoArchive.CloudNative]::Policy($cloudRoot)
        if($state.SyncRootId -ne $rootPolicy.SyncRootId){throw 'WrongCloudProvider'}
        $available=$available -and $state.OnDiskBytes -ge $item.Length
        if($rootPolicy.HydrationModifiers -band 1){$available=$available -and $state.ValidatedBytes -ge $item.Length}
    }
    $status=if(-not $state.InSync){'NotInSync'}elseif($available){'Available'}else{'OnlineOnly'}
    return [pscustomobject]@{status=$status;is_placeholder=$placeholder;in_sync=$state.InSync;partial=(-not $available);locally_available=$available;on_disk_bytes=$state.OnDiskBytes;validated_bytes=$state.ValidatedBytes;modified_bytes=$state.ModifiedBytes;pin_state=$state.PinState;policy=$rootPolicy}
}
function Ensure-CloudFileAvailable($Config,$FileRecord,[hashtable]$Adapters=@{}) {
    $status=Get-CloudFileStatus $Config $FileRecord $Adapters
    if(-not $status.in_sync){return [pscustomobject]@{status='Pending';reason='NotInSync';committed_files=0;unsettled=$false}}
    if($status.locally_available){return [pscustomobject]@{status='Available';reason='AlreadyAvailable';committed_files=0;unsettled=$false}}
    $path=Get-PhotoSourcePath $Config $FileRecord
    $sourceVolume=Get-PhotoBoundVolume $Config $path $Adapters
    if($sourceVolume.free_bytes - $FileRecord.size_bytes -lt $Config.reserve_c_bytes){return [pscustomobject]@{status='Pending';reason='DownloadCapacity';committed_files=0;unsettled=$false}}
    $last=$null
    for($attempt=0;$attempt -le $Config.download_retries;$attempt++) {
        if($Adapters.ContainsKey('Hydrate')){$last=& $Adapters.Hydrate $path $Config.download_timeout_seconds}
        else {$last=[PhotoArchive.CloudNative]::Hydrate($path,$Config.download_timeout_seconds)}
        if($last.Unsettled){break}
        if($last.Status -eq 'Available') {
            $after=Get-CloudFileStatus $Config $FileRecord $Adapters
            if($after.in_sync -and $after.locally_available){return [pscustomobject]@{status='Available';reason='Acquired';committed_files=0;unsettled=$false}}
        }
    }
    return [pscustomobject]@{status='Pending';reason='AcquisitionFailedOrTimedOut';committed_files=0;unsettled=[bool]$last.Unsettled}
}
Export-ModuleMember -Function *
