Test-Case 'T25' 'Missing apply plan is rejected before any media file is written' {
    $f=New-TestArchiveFixture
    try {
        $volume=Get-PhotoVolume $f.Root
        $f.Config.archive_id=[guid]::NewGuid().ToString('N')
        $f.Config.destination_volume_id=$volume.volume_id;$f.Config.destination_disk_id=$volume.disk_id
        foreach($source in $f.Config.source_roots){$source.volume_id=$volume.volume_id;$source.disk_id=$volume.disk_id}
        $config=Join-Path $f.State 'config.json';$f.Config | ConvertTo-Json -Depth 16 | Set-Content -LiteralPath $config -Encoding UTF8
        $entry=Join-Path (Split-Path -Parent $PSScriptRoot) 'Archive-iCloudPhotos.ps1'
        $stdout=Join-Path $f.State 'out.txt';$stderr=Join-Path $f.State 'err.txt'
        $exe=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        if(-not(Test-Path -LiteralPath $entry)){throw 'CLI apply gate is not implemented'}
        $p=Start-Process -FilePath $exe -WindowStyle Hidden -ArgumentList @('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',('"'+$entry+'"'),'-ConfigPath',('"'+$config+'"'),'-Mode','Apply') -Wait -PassThru -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        Assert-Equal 30 $p.ExitCode
        $result=Get-Content -LiteralPath $stdout -Raw | ConvertFrom-Json
        Assert-Equal 'MissingPlanPath' $result.Reason
        Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Destination -Recurse -File).Count
    } finally {Remove-TestArchiveFixture $f}
}
