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
