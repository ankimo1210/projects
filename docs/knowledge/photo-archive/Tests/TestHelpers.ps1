$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$script:Results = [Collections.Generic.List[object]]::new()
function Assert-Equal($Expected, $Actual, [string]$Name = 'value') {
    if ($Expected -cne $Actual) { throw "$Name expected [$Expected], got [$Actual]" }
}
function Assert-True([bool]$Value, [string]$Name = 'condition') {
    if (-not $Value) { throw "$Name was false" }
}
function Assert-Throws([scriptblock]$Operation, [string]$Pattern) {
    $caught = $null
    try { & $Operation | Out-Null } catch { $caught = $_.Exception.Message }
    if ($null -eq $caught -or $caught -notmatch $Pattern) { throw "Expected error $Pattern, got [$caught]" }
}
function Test-Case([string]$Id, [string]$Name, [scriptblock]$Body) {
    try { & $Body; $script:Results.Add([pscustomobject]@{id=$Id;name=$Name;status='Passed';error=$null}) }
    catch { $script:Results.Add([pscustomobject]@{id=$Id;name=$Name;status='Failed';error=$_.Exception.Message}) }
}
function New-TestArchiveFixture {
    $root = Join-Path $env:TEMP ('photo-archive-test-' + [guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $root
    $paths = @{}
    foreach ($name in @('old-c','old-f','sync','archive','state','retained','protected','release','restore')) {
        $paths[$name] = Join-Path $root $name
        $null = New-Item -ItemType Directory -Path $paths[$name]
    }
    [IO.File]::WriteAllText((Join-Path $root '.fixture-owner'), $root)
    $config = [pscustomobject]@{
        schema_version=2;archive_id='fixture-archive';fixture_root=$root
        source_roots=@(
            [pscustomobject]@{alias='OLD_C';path=$paths['old-c'];volume_id='fixture-volume';disk_id='fixture-disk'},
            [pscustomobject]@{alias='OLD_F';path=$paths['old-f'];volume_id='fixture-volume';disk_id='fixture-disk'},
            [pscustomobject]@{alias='ICLOUD';path=$paths['sync'];volume_id='fixture-volume';disk_id='fixture-disk'}
        )
        protected_roots=@($paths['protected']);archive_root=$paths['archive'];state_root=$paths['state']
        retained_root=$paths['retained'];release_code_root=$paths['release']
        destination_volume_id='fixture-volume';destination_disk_id='fixture-disk'
        mutex_name=('Local\PhotoArchiveFixture-' + [guid]::NewGuid().ToString('N'))
        reserve_c_bytes=34359738368L;reserve_f_bytes=34359738368L;warn_f_bytes=68719476736L
        download_timeout_seconds=1;download_retries=1;hash_workers=1;retention_days=7;auto_cleanup=$false
        full_hash_interval_days=30;exiftool=$null;task_binding_file=(Join-Path $paths['state'] 'task.json')
    }
    $adapters=@{Volume={param($Path) [pscustomobject]@{volume_id='fixture-volume';disk_id='fixture-disk';free_bytes=1099511627776L;cluster_bytes=131072L}}}
    return [pscustomobject]@{Root=$root;Config=$config;Adapters=$adapters;OldC=$paths['old-c'];OldF=$paths['old-f'];Sync=$paths['sync'];Destination=$paths['archive'];State=$paths['state'];Restore=$paths['restore']}
}
function Remove-TestArchiveFixture($Fixture) {
    $root=[IO.Path]::GetFullPath($Fixture.Root)
    $temp=[IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    if (-not $root.StartsWith($temp,[StringComparison]::OrdinalIgnoreCase) -or [IO.Path]::GetFileName($root) -notlike 'photo-archive-test-*') { throw 'UnsafeFixtureCleanup' }
    if ([IO.File]::ReadAllText((Join-Path $root '.fixture-owner')) -cne $root) { throw 'WrongFixtureOwner' }
    Remove-Item -LiteralPath $root -Recurse -Force
}
function New-TestFile([string]$Root,[string]$Name,[string]$Content) {
    $path=Join-Path $Root $Name
    $null=New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($path)) -Force
    [IO.File]::WriteAllText($path,$Content,[Text.UTF8Encoding]::new($false))
    return $path
}
