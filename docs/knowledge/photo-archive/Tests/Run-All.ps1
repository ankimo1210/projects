param([switch]$Child)
$ErrorActionPreference='Stop'
if (-not $Child) {
    $engines=@((Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'))
    $pwsh=Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) { $engines += $pwsh.Source }
    $failed=$false
    foreach ($engine in $engines) {
        $report=@(& $engine -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $PSCommandPath -Child)
        $engineExit=$LASTEXITCODE
        $reportPath=Join-Path $env:TEMP ('photo-archive-results-'+[guid]::NewGuid().ToString('N')+'.json')
        [IO.File]::WriteAllText($reportPath,($report -join "`n"),[Text.UTF8Encoding]::new($true))
        $result=($report -join "`n") | ConvertFrom-Json
        [pscustomobject]@{Engine=$result.Engine;Passed=$result.Passed;Failed=$result.Failed;Failures=@($result.Results | Where-Object status -eq Failed);Report=$reportPath} | ConvertTo-Json -Depth 6
        if ($engineExit -ne 0) { $failed=$true }
    }
    if ($failed) { exit 1 }; exit 0
}
. (Join-Path $PSScriptRoot 'TestHelpers.ps1')
$code=Split-Path -Parent $PSScriptRoot
foreach ($name in @('PhotoInventory','PhotoStorage','PhotoCloud','ICloudPhotoArchive','Install-PhotoArchive')) {
    $ext=if($name -eq 'Install-PhotoArchive'){'ps1'}else{'psm1'}
    $file=Join-Path $code "$name.$ext"
    if (Test-Path -LiteralPath $file) {
        if($ext -eq 'ps1'){. $file}else{Import-Module $file -Force -DisableNameChecking}
    }
}
foreach($file in Get-ChildItem -LiteralPath $PSScriptRoot -File -Filter 'Test-*.ps1' | Sort-Object Name) { . $file.FullName }
$failed=@($script:Results | Where-Object status -eq Failed)
[pscustomobject]@{Engine=$PSVersionTable.PSVersion.ToString();Passed=@($script:Results | Where-Object status -eq Passed).Count;Failed=$failed.Count;Results=@($script:Results)} | ConvertTo-Json -Depth 6
if ($failed.Count) { exit 1 }; exit 0
