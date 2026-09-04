[CmdletBinding()]
param(
    [string]$EditorPath,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$projectFile = Join-Path $PSScriptRoot 'Komorebi3D.uproject'
$sourceFile = Join-Path $PSScriptRoot 'SourceAssets\komorebi.glb'
$pythonScript = Join-Path $PSScriptRoot 'Content\Python\bootstrap_scene.py'
$mapFile = Join-Path $PSScriptRoot 'Content\Maps\Komorebi_Dusk.umap'
$completionFile = Join-Path $PSScriptRoot 'Saved\komorebi_import.json'

foreach ($inputFile in @($projectFile, $sourceFile, $pythonScript)) {
    if (-not (Test-Path -LiteralPath $inputFile -PathType Leaf)) {
        throw "Missing project input: $inputFile. Prepare a working copy first."
    }
}

if (-not $EditorPath) {
    $registeredRoot = 'HKLM:\SOFTWARE\EpicGames\Unreal Engine\5.8'
    if (Test-Path -LiteralPath $registeredRoot) {
        $engineDirectory = (Get-ItemProperty -LiteralPath $registeredRoot).InstalledDirectory
        if ($engineDirectory) {
            $candidate = Join-Path $engineDirectory 'Engine\Binaries\Win64\UnrealEditor.exe'
            if (Test-Path -LiteralPath $candidate) { $EditorPath = $candidate }
        }
    }
    if (-not $EditorPath) {
        $candidate = Join-Path $env:ProgramFiles 'Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
        if (Test-Path -LiteralPath $candidate) { $EditorPath = $candidate }
    }
}
if (-not $EditorPath -or -not (Test-Path -LiteralPath $EditorPath -PathType Leaf)) {
    throw 'Unreal Engine 5.8 was not found. Install it through Epic Games Launcher, or pass -EditorPath with the full UnrealEditor.exe path.'
}
Write-Host "Editor: $EditorPath"
Write-Host "Project: $projectFile"
if ($CheckOnly) { exit 0 }

if (-not (Test-Path -LiteralPath $mapFile)) {
    $bootstrapArgs = @(
        ('"' + $projectFile + '"'),
        ('-ExecutePythonScript="' + $pythonScript + '"'),
        '-unattended'
    )
    $importProcess = Start-Process -FilePath $EditorPath -ArgumentList $bootstrapArgs -Wait -PassThru
    if ($importProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $completionFile) -or -not (Test-Path -LiteralPath $mapFile)) {
        throw 'Initial scene import did not complete. Check Saved\Logs. Existing files have been retained.'
    }
}

$openArgs = @(('"' + $projectFile + '"'), '/Game/Maps/Komorebi_Dusk')
Start-Process -FilePath $EditorPath -ArgumentList $openArgs | Out-Null
