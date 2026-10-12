# Dot-source to load deployment functions; there is no automatic deployment.
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'PhotoInventory.psm1') -DisableNameChecking
function Save-ControlSnapshot($Config) {
    Assert-ArchiveBindings $Config | Out-Null
    $binding=Get-Content -LiteralPath $Config.task_binding_file -Raw -Encoding UTF8 | ConvertFrom-Json
    $root=Resolve-PhotoPath $Config.state_root ('controls\'+[guid]::NewGuid().ToString('N'))
    $null=New-Item -ItemType Directory -Path $root
    $copies=@()
    foreach($source in @($binding.control_files)) {
        Assert-PhotoNoDirectoryLinks ([IO.Path]::GetDirectoryName($source))
        $item=Get-Item -LiteralPath $source -Force
        if($item.PSIsContainer -or ([long]$item.Attributes -band 0x400)){throw 'InvalidControlFile'}
        $dest=Join-Path $root ([guid]::NewGuid().ToString('N')+'.control')
        Copy-Item -LiteralPath $source -Destination $dest
        $hash=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        if((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash -cne $hash){throw 'ControlCopyMismatch'}
        $copies += [pscustomobject]@{source=$source;saved=$dest;sha256=$hash}
    }
    $xml=Export-ScheduledTask -TaskName $binding.task_name
    [IO.File]::WriteAllText((Join-Path $root 'task.xml'),$xml,[Text.UTF8Encoding]::new($true))
    $receipt=[pscustomobject]@{schema_version=2;root=$root;copies=$copies;task_name=$binding.task_name;task_xml=$xml;created_at_utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText((Join-Path $root 'receipt.json'),($receipt|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($true))
    return $receipt
}
function Install-PhotoArchiveRelease($Config,[string]$CodeRoot,[hashtable]$ExpectedHashes,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    Assert-PhotoNoDirectoryLinks $CodeRoot
    if(-not $ExpectedHashes.Count){throw 'EmptyRelease'}
    foreach($relative in $ExpectedHashes.Keys) {
        $source=Resolve-PhotoPath $CodeRoot $relative
        if((Get-PhotoSha256 $source) -cne $ExpectedHashes[$relative].ToLowerInvariant()){throw 'ReleaseMismatch'}
        if([long](Get-Item -LiteralPath $source -Force).Attributes -band 0x400){throw 'ReleaseLinkForbidden'}
    }
    if((Test-Path -LiteralPath $Config.release_code_root) -and @(Get-ChildItem -LiteralPath $Config.release_code_root -Force).Count){throw 'ReleaseAlreadyExists'}
    $stage=Resolve-PhotoPath $Config.state_root ('release-staging\'+[guid]::NewGuid().ToString('N'))
    $null=New-Item -ItemType Directory -Path $stage
    foreach($relative in $ExpectedHashes.Keys) {
        $source=Resolve-PhotoPath $CodeRoot $relative;$dest=Resolve-PhotoPath $stage $relative
        $null=New-Item -ItemType Directory -Path (Split-Path -Parent $dest) -Force
        [IO.File]::Copy($source,$dest,$false)
        if((Get-PhotoSha256 $dest) -cne $ExpectedHashes[$relative].ToLowerInvariant()){throw 'ReleaseCopyMismatch'}
        if([IO.Path]::GetExtension($dest) -in @('.ps1','.psm1')) {
            $tokens=$null;$errors=$null
            $null=[Management.Automation.Language.Parser]::ParseFile($dest,[ref]$tokens,[ref]$errors)
            if($errors.Count){throw 'ReleaseParseError'}
        }
    }
    $manifest=[pscustomobject]@{schema_version=2;archive_id=$Config.archive_id;files=$ExpectedHashes;created_at_utc=[DateTime]::UtcNow.ToString('o')}
    [IO.File]::WriteAllText((Join-Path $stage 'release-manifest.private.json'),($manifest | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($true))
    Assert-PhotoNoDirectoryLinks $Config.release_code_root
    if(Test-Path -LiteralPath $Config.release_code_root) {
        if(@(Get-ChildItem -LiteralPath $Config.release_code_root -Force).Count){throw 'ReleaseChangedDuringDeployment'}
        [IO.Directory]::Delete($Config.release_code_root,$false)
    }
    $null=New-Item -ItemType Directory -Path (Split-Path -Parent $Config.release_code_root) -Force
    [IO.Directory]::Move($stage,$Config.release_code_root)
    return [pscustomobject]@{Files=$ExpectedHashes.Count;ReleaseRoot=$Config.release_code_root;Manifest=(Join-Path $Config.release_code_root 'release-manifest.private.json')}
}
function Get-PhotoTaskControl($Config,[string]$Name,[hashtable]$Adapters=@{}) {
    if($Adapters.ContainsKey('TaskRead')){Get-PhotoBoundVolume $Config $Config.archive_root $Adapters | Out-Null;return & $Adapters.TaskRead $Name}
    $task=Get-ScheduledTask -TaskName $Name
    return [pscustomobject]@{xml=(Export-ScheduledTask -TaskName $Name);state=[string]$task.State;enabled=[bool]$task.Settings.Enabled}
}
function Set-PhotoTaskEnabled($Config,[string]$Name,[bool]$Enabled,[hashtable]$Adapters=@{}) {
    if($Adapters.ContainsKey('TaskEnabled')){Get-PhotoBoundVolume $Config $Config.archive_root $Adapters | Out-Null;& $Adapters.TaskEnabled $Name $Enabled | Out-Null;return}
    if($Enabled){Enable-ScheduledTask -TaskName $Name | Out-Null}else{Disable-ScheduledTask -TaskName $Name | Out-Null}
}
function Assert-PhotoRelease($Config) {
    $manifestPath=Resolve-PhotoPath $Config.release_code_root 'release-manifest.private.json'
    $manifest=Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if($manifest.schema_version -ne 2 -or $manifest.archive_id -cne $Config.archive_id){throw 'WrongReleaseManifest'}
    foreach($p in $manifest.files.PSObject.Properties){if((Get-PhotoSha256 (Resolve-PhotoPath $Config.release_code_root $p.Name)) -cne $p.Value.ToLowerInvariant()){throw 'ReleaseMismatch'}}
}
function Assert-PhotoControlSnapshot($Config,$ControlReceipt) {
    $binding=Get-Content -LiteralPath $Config.task_binding_file -Raw -Encoding UTF8 | ConvertFrom-Json
    if($ControlReceipt.task_name -cne $binding.task_name -or -not(Test-PhotoPathWithin $ControlReceipt.root $Config.state_root)){throw 'WrongControlSnapshot'}
    foreach($copy in $ControlReceipt.copies) {
        if($copy.source -notin $binding.control_files -or -not(Test-PhotoPathWithin $copy.saved $ControlReceipt.root)){throw 'InvalidControlTarget'}
        Assert-PhotoNoDirectoryLinks (Split-Path -Parent $copy.source)
        Assert-PhotoNoDirectoryLinks (Split-Path -Parent $copy.saved)
        if((Get-PhotoSha256 $copy.saved).ToUpperInvariant() -cne $copy.sha256.ToUpperInvariant()){throw 'ControlSnapshotChanged'}
    }
    return $binding
}
function Switch-PhotoArchiveTask($Config,$ControlReceipt,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    Assert-PhotoRelease $Config
    $binding=Assert-PhotoControlSnapshot $Config $ControlReceipt
    $task=Get-PhotoTaskControl $Config $binding.task_name $Adapters
    if($task.state -eq 'Running' -or $task.xml -cne $ControlReceipt.task_xml){throw 'TaskChangedOrRunning'}
    $launcherCopy=@($ControlReceipt.copies | Where-Object source -eq $binding.launcher_path)
    if($launcherCopy.Count -ne 1 -or (Get-PhotoSha256 $binding.launcher_path).ToUpperInvariant() -cne $launcherCopy[0].sha256.ToUpperInvariant()){throw 'LauncherChanged'}
    $entry=Resolve-PhotoPath $Config.release_code_root 'Archive-iCloudPhotos.ps1'
    $ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $command='"'+$ps+'" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "'+$entry+'" -ConfigPath "'+$binding.config_path+'" -Mode Archive'
    $literal=$command | ConvertTo-Json -Compress
    $javascript='var shell = new ActiveXObject("WScript.Shell"); WScript.Quit(shell.Run('+ $literal +', 0, true));' + "`r`n"
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        Set-PhotoTaskEnabled $Config $binding.task_name $false $Adapters
        try{$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        if((Get-PhotoTaskControl $Config $binding.task_name $Adapters).state -eq 'Running'){throw 'TaskStartedDuringSwitch'}
        $temp=$binding.launcher_path+'.photo-archive-'+[guid]::NewGuid().ToString('N')+'.tmp'
        [IO.File]::WriteAllText($temp,$javascript,[Text.UTF8Encoding]::new($false))
        $replaceBackup=$binding.launcher_path+'.pre-switch-'+[guid]::NewGuid().ToString('N')+'.backup'
        [IO.File]::Replace($temp,$binding.launcher_path,$replaceBackup)
        $result=[pscustomobject]@{Switched=$true;TaskName=$binding.task_name;LauncherSHA256=(Get-PhotoSha256 $binding.launcher_path);SwitchedAtUtc=[DateTime]::UtcNow.ToString('o');ControlRoot=$ControlReceipt.root}
        $path=Resolve-PhotoPath $Config.state_root ('deployments\'+[guid]::NewGuid().ToString('N')+'.json')
        $null=New-Item -ItemType Directory -Path (Split-Path -Parent $path) -Force
        [IO.File]::WriteAllText($path,($result | ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($true))
        return $result
    } catch {
        foreach($copy in $launcherCopy){[IO.File]::Copy($copy.saved,$copy.source,$true)}
        throw
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose();Set-PhotoTaskEnabled $Config $binding.task_name $task.enabled $Adapters}
}
function Undo-PhotoArchiveDeployment($Config,$ControlReceipt,[hashtable]$Adapters=@{}) {
    Assert-ArchiveBindings $Config $Adapters | Out-Null
    $binding=Assert-PhotoControlSnapshot $Config $ControlReceipt
    $task=Get-PhotoTaskControl $Config $binding.task_name $Adapters
    if($task.state -eq 'Running'){throw 'TaskRunning'}
    $mutex=[Threading.Mutex]::new($false,$Config.mutex_name);$acquired=$false
    try {
        Set-PhotoTaskEnabled $Config $binding.task_name $false $Adapters
        try{$acquired=$mutex.WaitOne(0)}catch [Threading.AbandonedMutexException]{$acquired=$true}
        if(-not $acquired){throw 'AlreadyRunning'}
        foreach($copy in $ControlReceipt.copies) {
            Assert-PhotoNoDirectoryLinks (Split-Path -Parent $copy.source)
            [IO.File]::Copy($copy.saved,$copy.source,$true)
            if((Get-PhotoSha256 $copy.source).ToUpperInvariant() -cne $copy.sha256.ToUpperInvariant()){throw 'ControlRestoreMismatch'}
        }
        if($Adapters.ContainsKey('TaskRestore')){& $Adapters.TaskRestore $binding.task_name $ControlReceipt.task_xml | Out-Null}
        else {Register-ScheduledTask -TaskName $binding.task_name -Xml $ControlReceipt.task_xml -Force | Out-Null}
        return [pscustomobject]@{Restored=$true;TaskName=$binding.task_name;RestoredAtUtc=[DateTime]::UtcNow.ToString('o')}
    } finally {if($acquired){$mutex.ReleaseMutex()};$mutex.Dispose();Set-PhotoTaskEnabled $Config $binding.task_name $task.enabled $Adapters}
}
function Restore-ControlSnapshot($Config,$ControlReceipt,[hashtable]$Adapters=@{}) {return Undo-PhotoArchiveDeployment $Config $ControlReceipt $Adapters}
