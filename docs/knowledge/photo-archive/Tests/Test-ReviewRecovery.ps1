Test-Case 'T06' 'Sidecars protect the related image even without a Live Photo identifier' {
    $f=New-TestArchiveFixture
    try {
        $a=New-TestFile $f.OldC 'one/photo.jpg' 'same-image'
        $b=New-TestFile $f.OldF 'two/photo.jpg' 'same-image'
        $null=New-TestFile $f.OldC 'one/photo.aae' 'edit-A'
        $null=New-TestFile $f.OldF 'two/photo.aae' 'edit-B'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C','OLD_F') Fresh $f.Adapters)
        $assets=@(New-PhotoAssets $rows @([pscustomobject]@{SourceFile=$a;FileType='JPEG'},[pscustomobject]@{SourceFile=$b;FileType='JPEG'}))
        Assert-Equal 0 @($assets | Where-Object association_status -eq Complete).Count
        Assert-Equal 2 $assets.Count
        Assert-Equal 2 @($assets.asset_id | Sort-Object -Unique).Count
        Assert-Equal 4 @($assets.components.file).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T06' 'Missing metadata does not establish a complete standalone image' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'photo.heic' 'image'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        Assert-Equal 'PendingAssociation' @(New-PhotoAssets $rows @())[0].association_status
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T07' 'Capture date preserves local calendar, offset, subseconds and derived UTC' {
    $f=New-TestArchiveFixture
    try {
        $path=New-TestFile $f.OldC 'photo.jpg' 'image'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $a=@(New-PhotoAssets $rows @([pscustomobject]@{SourceFile=$path;FileType='JPEG';DateTimeOriginal='2024:05:31 23:30:00';OffsetTimeOriginal='-07:00';SubSecTimeOriginal='1234'}))[0]
        Assert-Equal '2024\\05'.Replace('\\','\') $a.calendar_bucket
        Assert-Equal '1234' $a.capture_subsec_raw
        Assert-Equal '2024-06-01T06:30:00.1234000Z' $a.capture_utc
        Assert-Equal 'offset_verified' $a.date_confidence
    } finally {Remove-TestArchiveFixture $f}
}
$perl=Join-Path $env:ProgramFiles 'Git/usr/bin/perl.exe'
if(-not(Test-Path -LiteralPath $perl)) {
    $script:Results.Add([pscustomobject]@{id='T22';name='Native metadata stderr';status='Skipped';error='Windows Git Perl is unavailable'})
} else {
Test-Case 'T22' 'Successful native metadata diagnostics on stderr do not block ingestion' {
    $f=New-TestArchiveFixture
    try {
        $null=New-TestFile $f.OldC 'photo.jpg' 'image'
        $rows=@(Get-PhotoInventory $f.Config @('OLD_C') Fresh $f.Adapters)
        $native='my $p=$ARGV[-1]; $p=~s!\\!/!g; print STDERR "  100 image files read\n"; print ''[{"SourceFile":"''.$p.''","FileType":"JPEG"}]''; exit 0;'
        $tool=New-TestFile $f.Root 'fake-exif.pl' $native
        $hash=Get-PhotoSha256 $tool
        $manifest=Join-Path $f.State 'tool-manifest.json'
        Write-PhotoJsonNew $manifest @([pscustomobject]@{relative_path='fake-exif.pl';sha256=$hash})
        $receipt=[pscustomobject]@{path=$tool;sha256=$hash;driver='perl';driver_path=$perl;driver_sha256=(Get-PhotoSha256 $perl);source_manifest=$manifest;source_manifest_sha256=(Get-PhotoSha256 $manifest)}
        $metadata=@(Read-PhotoMetadata $rows $receipt)
        Assert-Equal 1 $metadata.Count
        Assert-Equal 'JPEG' $metadata[0].FileType
        Assert-Equal ([IO.Path]::GetFullPath($rows[0].full_path)) ([IO.Path]::GetFullPath($metadata[0].SourceFile))
    } finally {Remove-TestArchiveFixture $f}
}
}
Test-Case 'T04' 'Receipt aliases survive reverse journal order' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $r=Invoke-PhotoPlan $f.Config $s.Plan $f.Adapters
        $record=$r.committed[0]
        $latest=($record | ConvertTo-Json -Depth 48 | ConvertFrom-Json)
        $later=($record.components[0].sources[0] | ConvertTo-Json -Depth 48 | ConvertFrom-Json)
        $later.relative_path='later.jpg';$later.full_path=Join-Path $f.OldC 'later.jpg'
        $latest.components[0].sources+= $later
        $latest.committed_at_utc=[DateTime]::UtcNow.AddMinutes(1).ToString('o')
        $root=Join-Path $f.Destination 'receipts'
        Write-PhotoJournalLine (Join-Path $root '000-latest.jsonl') $latest
        Write-PhotoJournalLine (Join-Path $root 'zzz-old.jsonl') $record
        $idx=Get-PhotoReceiptIndex $f.Config $f.Adapters
        Assert-True ('later.jpg' -in @($idx.assets[0].components.sources.relative_path))
        Assert-Equal 3 @($idx.assets[0].components.sources).Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T16' 'Truncated final journal line is preserved and valid records permit resuming' {
    $s=New-TestCopyScenario;$f=$s.Fixture
    try {
        $r=Invoke-PhotoPlan $f.Config $s.Plan $f.Adapters
        $file=@(Get-ChildItem -LiteralPath (Join-Path $f.Destination 'receipts') -File)[0].FullName
        [IO.File]::AppendAllText($file,'{"schema_version":2,',[Text.UTF8Encoding]::new($false))
        $before=Get-PhotoSha256 $file
        $again=Invoke-PhotoPlan $f.Config $s.Plan $f.Adapters
        Assert-Equal 0 $again.new_files
        Assert-Equal $before (Get-PhotoSha256 $file)
        Assert-Equal 1 @(Get-ChildItem -LiteralPath (Join-Path $f.State 'receipt-recovery') -File -Filter '*.json').Count
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T24' 'Only completed matching run logs expire after ninety days' {
    $f=New-TestArchiveFixture
    try {
        $old=[guid]::NewGuid().ToString('N');$recent=[guid]::NewGuid().ToString('N');$failed=[guid]::NewGuid().ToString('N')
        foreach($id in @($old,$recent,$failed)){Write-PhotoJournalLine (Join-Path $f.State ('journals/'+$id+'.jsonl')) ([pscustomobject]@{state='Planned'})}
        Write-PhotoJsonNew (Join-Path $f.State ('runs/'+$old+'.json')) ([pscustomobject]@{schema_version=2;archive_id=$f.Config.archive_id;run_id=$old;completed_at_utc=[DateTime]::UtcNow.AddDays(-91).ToString('o')})
        Write-PhotoJsonNew (Join-Path $f.State ('runs/'+$recent+'.json')) ([pscustomobject]@{schema_version=2;archive_id=$f.Config.archive_id;run_id=$recent;completed_at_utc=[DateTime]::UtcNow.ToString('o')})
        Remove-ExpiredPhotoRunLogs $f.Config | Out-Null
        Assert-Equal $false (Test-Path -LiteralPath (Join-Path $f.State ('runs/'+$old+'.json')))
        Assert-Equal $false (Test-Path -LiteralPath (Join-Path $f.State ('journals/'+$old+'.jsonl')))
        Assert-True (Test-Path -LiteralPath (Join-Path $f.State ('runs/'+$recent+'.json')))
        Assert-True (Test-Path -LiteralPath (Join-Path $f.State ('journals/'+$failed+'.jsonl')))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T34' 'Independent C copy restores original aliases when F is absent' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $oldVolume=$f.Adapters.Volume
        $archive=$f.Destination;$oldF=$f.OldF
        $f.Adapters.Volume={param($Path) if((Test-PhotoPathWithin $Path $archive) -or (Test-PhotoPathWithin $Path $oldF)){throw 'DriveMissing'};& $oldVolume $Path}.GetNewClosure()
        $restore=Restore-PhotoSources -Config $f.Config -Receipt $s.Receipt -DestinationRoot $f.Restore -Adapters $f.Adapters -IndependentProofs @($s.Proof)
        Assert-Equal 2 $restore.files
        Assert-Equal 'original-payload' ([IO.File]::ReadAllText((Join-Path $f.Restore 'OLD_F/alias.jpg')))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T30' 'An alternate stream added after planning prevents moving the original' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        $old=Join-Path $f.OldF 'alias.jpg'
        Set-Content -LiteralPath $old -Stream newly-added -Value 'preserve-edit'
        Assert-Throws {Invoke-PhotoCleanup $f.Config $plan $f.Adapters} 'ProtectedSourceStreams'
        Assert-Equal 'preserve-edit' (Get-Content -LiteralPath $old -Stream newly-added)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T30' 'A newly readonly source is retained without force-removing it' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        $old=Join-Path $f.OldF 'alias.jpg';(Get-Item -LiteralPath $old).IsReadOnly=$true
        Assert-Throws {Invoke-PhotoCleanup $f.Config $plan $f.Adapters} 'ProtectedSourceStreams'
        Assert-True (Test-Path -LiteralPath $old)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T06' 'A newly classified cloud alias cannot promote an unreviewed old alias' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        foreach($record in $s.Receipt.committed){foreach($component in $record.components){foreach($source in $component.sources | Where-Object source_alias -eq OLD_F){$source.PSObject.Properties.Remove('association_revision');$source.PSObject.Properties.Remove('association_status')}}}
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        Assert-Equal 0 $plan.eligible.Count
        Assert-True ('LegacyAssociationNeedsRevalidation' -in @($plan.retained.reason))
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T06' 'A sidecar arriving after cleanup planning protects its related source' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        $null=New-TestFile $f.OldF 'alias.aae' 'new-edit'
        Assert-Throws {Invoke-PhotoCleanup $f.Config $plan $f.Adapters} 'RelatedSourceChanged'
        Assert-True (Test-Path -LiteralPath (Join-Path $f.OldF 'alias.jpg'))
        Remove-Item -LiteralPath (Join-Path $f.OldF 'alias.aae')
        $null=Invoke-PhotoCleanup $f.Config $plan $f.Adapters
        $file=@(Get-ChildItem -LiteralPath (Join-Path $f.State 'cleanup') -Filter '*.json' -File)[0]
        $hold=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        $hold.moved_at_utc=[DateTime]::UtcNow.AddDays(-8).ToString('o')
        $hold | ConvertTo-Json | Set-Content -LiteralPath $file.FullName -Encoding UTF8
        $null=New-TestFile $f.OldF 'alias.aae' 'new-edit-after-retention'
        Assert-Throws {Invoke-PhotoCleanup $f.Config $plan $f.Adapters} 'RelatedSourceChanged'
        Assert-True (Test-Path -LiteralPath $hold.held)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T30' 'An alternate stream added during retention prevents final deletion' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        $null=Invoke-PhotoCleanup $f.Config $plan $f.Adapters
        $file=@(Get-ChildItem -LiteralPath (Join-Path $f.State 'cleanup') -Filter '*.json' -File)[0]
        $hold=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        $hold.moved_at_utc=[DateTime]::UtcNow.AddDays(-8).ToString('o')
        $hold | ConvertTo-Json | Set-Content -LiteralPath $file.FullName -Encoding UTF8
        Set-Content -LiteralPath $hold.held -Stream newly-added -Value 'preserve-edit'
        Assert-Throws {Invoke-PhotoCleanup $f.Config $plan $f.Adapters} 'ProtectedSourceStreams'
        Assert-True (Test-Path -LiteralPath $hold.held)
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T31' 'Cleanup resumes after deletion and after the delete-before-journal interruption' {
    $s=New-TestIndependentCleanupScenario;$f=$s.Fixture
    try {
        $plan=New-PhotoCleanupPlan $f.Config $s.Receipt @($s.Proof) $f.Adapters
        $null=Invoke-PhotoCleanup $f.Config $plan $f.Adapters
        $file=@(Get-ChildItem -LiteralPath (Join-Path $f.State 'cleanup') -Filter '*.json' -File)[0]
        $hold=Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json
        $hold.moved_at_utc=[DateTime]::UtcNow.AddDays(-8).ToString('o')
        $hold | ConvertTo-Json | Set-Content -LiteralPath $file.FullName -Encoding UTF8
        $done=Invoke-PhotoCleanup $f.Config $plan $f.Adapters
        Assert-Equal 1 $done.Deleted
        $again=Invoke-PhotoCleanup $f.Config $plan $f.Adapters
        Assert-Equal 0 $again.Deleted
        Assert-Equal 1 $again.AlreadyDeleted
        $journal=Join-Path $f.State ('cleanup/'+$plan.cleanup_id+'.jsonl')
        $intentOnly=@(Get-Content -LiteralPath $journal | Where-Object {$_ -notmatch 'DeletedVerifiedCopy'})
        [IO.File]::WriteAllText($journal,($intentOnly -join "`n")+"`n",[Text.UTF8Encoding]::new($false))
        Assert-Equal 1 (Invoke-PhotoCleanup $f.Config $plan $f.Adapters).AlreadyDeleted
    } finally {Remove-TestArchiveFixture $f}
}
Test-Case 'T33' 'Cleanup digest survives equivalent UTC precision in JSON and both engines' {
    $utc=[DateTime]::Parse('2026-10-12T13:01:51.2362700Z',[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind)
    $typed=[pscustomobject]@{archive_id='fixture-date-roundtrip';created_at_utc=$utc;cleanup_sha256=$null}
    # SHA-256 of the literal schema-2 canonical JSON, calculated independently.
    $expected='216a6b1022f999b8cd902087916446d8f52c85359a93492b86e8a2d4dd43bb85'
    Assert-Equal $expected (Get-PhotoCleanupHash $typed) 'existing DateTime digest stays compatible'
    $text=[pscustomobject]@{archive_id='fixture-date-roundtrip';created_at_utc='2026-10-12T13:01:51.23627Z';cleanup_sha256=$null}
    Assert-Equal $expected (Get-PhotoCleanupHash $text) 'JSON string retains the same instant without trailing zeros'
    $decoded='{"archive_id":"fixture-date-roundtrip","created_at_utc":"2026-10-12T13:01:51.23627Z","cleanup_sha256":null}' | ConvertFrom-Json
    Assert-Equal $expected (Get-PhotoCleanupHash $decoded) 'default parser differs between PowerShell 5.1 and 7'
    $text.created_at_utc='2026-10-12T13:01:51.236271Z'
    Assert-True ((Get-PhotoCleanupHash $text) -cne $expected) 'an actual time change still invalidates the digest'
}
