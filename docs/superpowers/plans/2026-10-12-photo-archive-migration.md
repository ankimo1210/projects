# 写真アーカイブ F: 移植 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. この計画は本人が要求した移植計画の作成物であり、今回のターンでは実装しない。実行指示を受けたら Native 方式で進める。

**Goal:** 写真・動画と関連情報を検証付きでF:へ集約し、日次保存を切り替え、独立コピーを証明できたC:のデータだけを解放する。

**Architecture:** 現行PowerShellのコピー・同名衝突回避・ハッシュ・状態キャッシュ・非表示日次実行を移植する。入力台帳→資産束→不変の適用計画→検証コピー→証跡→日次切替→独立コピー検証→保持→個別解放を分離する。初回と日次は同じ保存契約を使い、cleanupは別入口にする。

**Tech Stack:** Windows PowerShell 5.1 / .NET、追加の読取専用ExifTool Windows版（13.53以上、具体版と配布物hashを実行前に固定）、Cloud Files API、既存形式のPowerShellアサーション。PowerShell 7.6.6でも構文・テストを確認。Python、Anaconda、uvの変更は不要。

**Spec:** [写真移行設計](../specs/2026-10-12-photo-archive-migration-design.md)。

## Global Constraints

- 正本は設計書。物理ファイル操作はWindowsの絶対パスとLiteralPath、Git・リポジトリの編集はWSLのLinuxパスを使う。両者を連結しない。
- 公開Gitには汎用コード、合成fixture、計画のみ。実機bindings、媒体識別、写真名・hash一覧、画像、位置情報、私有台帳・ログはローカル管理領域に置く。
- OLD_C、OLD_F、ICLOUD以外の入力は追加しない。MAC_LEGACYの内部操作、端末バックアップ、LINE、その他プロジェクトは対象外。
- 初回の元データを消さない。OLD_Fもコピーで取り込み、ピーク容量が足りなければ停止する。容量不足を元コピーの削除で解消しない。
- 全SHA-256は新しい読取で証明する。名前・サイズ・更新時刻・短縮hash・プレースホルダーの存在は削除根拠にしない。
- 保存成功は資産の全構成要素と証跡の確定後。入力削除は伝播させない。
- FはexFAT、割当単位128 KiB。hardlinkによる共有や電源断時の完全な原子的transactionを仮定しない。
- 同名別内容、編集版、関連が不明なファイルを上書き・廃棄しない。日時不明は_undated、元の撮影メタデータを書き換えない。
- F空き32 GiB、Cのダウンロード用空き32 GiBを予約。F64 GiB未満で警告。取得600秒上限、同一実行で再試行は最大1回。ハッシュ並列数1、最大2。
- 日次は既存の毎日20時・非表示・対話ユーザー権限・StartWhenAvailable・同時実行抑止を維持。新しいCodex定期タスクは作らない。
- 私有状態は3世代、詳細ログ90日。失敗・復元・cleanup証跡は保持。写真に保存期限は設けない。
- C通常コピーの解放は独立コピーの証明、復元検証、新タスクの手動2回・定時1回、7日保持、削除直前の再検証を満たす個別リストのみ。
- iCloudルートでRemove-Itemを使わない。ローカル実体の解放はプロバイダー方針に従うdehydrate/unpinまたは本人の公式UI操作。
- 自動承認レビューによる拒否を別ツール・シェル・符号化で迂回しない。
- Gitは専用作業場所・codex/ブランチで実装。既存変更を保持し、mainへの直接コミット、push、マージは今回の計画作成では行わない。

## Review Focus

1. ドライブ文字Fが別のUSB媒体を指す、途中で切断、exFATの電源断: 元と確定済み保存を失わず、証跡のない結果を完成扱いしない。
2. 同名別内容、同内容別名、同じ原本と異なるAAE、片方不足のLive Photo: ファイルhash一致だけで資産関係を捨てない。
3. online-only・未同期・未編集原本と派生版・Windowsに見えない構成要素: ファイル集合の保存と全クラウド原本保存を区別し、未取得を成功と数えない。
4. 撮影日時の時差・欠損、ケース/Unicode/長いパス、再解析ポイント・別ストリーム: 不明な入力を誤った日時や外部パスへ送らず、削除を保留する。
5. 既存cacheが残る、同サイズ同時刻の破損、cleanup後のF故障: 新しいhashと独立コピーで検出・復元でき、月次検査とcleanupがcacheを信用しない。

## 実機bindingsと記録の扱い

本日の調査結果と現行タスクの私有XMLは、現行Windows管理フォルダーの `migration-plan-2026-10-12/` に保存する。公開文書には各aliasだけを使う。

実行に必要な `config.private.json` を工程0で作る。以下は合成fixture用の完全な形で、実機設定ではない。

```json
{
  "schema_version": 2,
  "archive_id": "fixture-archive",
  "source_roots": [
    {"alias": "OLD_C", "path": "C:\\fixture\\old-c"},
    {"alias": "OLD_F", "path": "F:\\fixture\\old-f"},
    {"alias": "ICLOUD", "path": "C:\\fixture\\sync"}
  ],
  "protected_roots": ["F:\\fixture\\legacy.photoslibrary"],
  "archive_root": "F:\\fixture\\archive",
  "release_code_root": "C:\\fixture\\release",
  "state_root": "C:\\fixture\\state",
  "retained_root": "C:\\fixture\\retained",
  "destination_volume_id": "fixture-volume",
  "destination_disk_id": "fixture-disk",
  "mutex_name": "Local\\fixture-photo-archive",
  "reserve_c_bytes": 34359738368,
  "reserve_f_bytes": 34359738368,
  "warn_f_bytes": 68719476736,
  "download_timeout_seconds": 600,
  "download_retries": 1,
  "hash_workers": 1,
  "retention_days": 7,
  "auto_cleanup": false,
  "full_hash_interval_days": 30,
  "exiftool": {"path": "C:\\fixture\\tools\\exiftool.exe", "version": "13.53", "sha256": "fixture-tool-hash"},
  "task_binding_file": "C:\\fixture\\state\\task.private.json"
}
```

実機版ではfixture識別子を拒否する。入力・保存先・状態・retained・保護ルートが重なれば拒否する。媒体IDが不安定・非一意なら登録を止め、識別が確定するまで書き込まない。ドライブ番号だけでは識別しない。合成テストは上記の例示パスをそのまま使わず、検証済みの一時fixtureルートへ全パスを置換して実行する。

## ファイル構成（すべて新設予定）

| ファイル | 責務 |
|---|---|
| `docs/knowledge/photo-archive/README.md` | 操作・状態の意味・復元・私有設定の場所。個人パスなし |
| `ICloudPhotoArchive.psm1` | 現行コードを一般化した入口、mutex、日次と初回の共通オーケストレーション |
| `PhotoInventory.psm1` | パス/媒体境界、ハッシュ読取、FileRecord、ExifTool結果、資産束、容量付き適用計画 |
| `PhotoStorage.psm1` | staging、copy/reuse、耐中断journal、証跡、復元 |
| `PhotoCloud.psm1` | 登録済み同期先の取得状態、必要分取得、方針検査、ローカル実体解放 |
| `PhotoCloudNative.cs` | Windows Cloud Files APIの最小wrapper。上書き・削除APIを含めない |
| `Archive-iCloudPhotos.ps1` | `-ConfigPath` と列挙型 `-Mode` の薄いCLI |
| `Install-PhotoArchive.ps1` | 私有リリース配備、元コード退避、task XML・隠しJSの切替/復旧 |
| `Tests/TestHelpers.ps1` | 合成fixture、アサーション、mock adapter、境界確認付きfixture破棄 |
| `Tests/Test-InventoryAndAssets.ps1` | 入力・名前・日時・関連・容量 |
| `Tests/Test-CopyAndResume.ps1` | copy/reuse、hash、再実行、破損、中断、復元 |
| `Tests/Test-CloudAndCleanup.ps1` | 取得/保留、独立コピー、保持期間、cleanup guard |
| `Tests/Test-RunnerAndRollback.ps1` | 終了コード、mutex、配備、切戻し |
| `Tests/Run-All.ps1` | 既存形式の全テストとJSON集計。Pester依存なし |

上表のパスは相対的に同じディレクトリー内。現在は未作成であり、下記の実装後用コマンドを今実行してはいけない。PowerShellの公開関数は明記した入力だけを使い、実機pathsを既定値に埋め込まない。

### Task 0: 制御状態の退避と安全な実行環境

**Files:** Create `Install-PhotoArchive.ps1`, `Tests/TestHelpers.ps1`, `Tests/Test-RunnerAndRollback.ps1`。
**Private outputs:** `config.private.json`, `task-before.xml`, コード/旧state/JSの退避と `control-hashes.json`。
**Interfaces:** `Read-ArchiveConfig(ConfigPath) -> Config`; `Assert-ArchiveBindings(Config) -> VerifiedBindings`; `Save-ControlSnapshot(Config) -> ControlReceipt`; `Restore-ControlSnapshot(ControlReceipt)`。

- [ ] 専用worktree/ブランチを準備。まずattached worktreeを確認し、適切なものがなければ現在HEADを起点に新設する。WSLからGitを操作し、無関係の未コミット差分を持ち込まない。
- [ ] 現行module/entry/test/JS/状態とタスクXMLを私有場所へコピーし、hash一致を確認する。既存の独自テストを基準として取り込み、Start-Processに非表示指定、fixture再帰削除に絶対境界検査を追加する。既存動作のbaselineを5.1で測る。
- [ ] 現行運用、volume/disk ID、mutex、同期ルート登録をbindingsへ格納する。写真はまだ動かさない。ExifToolの公式配布物を取得する前に新しい依存として実行承認の範囲を確認し、取得後に版・URL・配布物/実行ファイルhashを固定する。
- [ ] 間違う媒体・重なるroot・fixture設定の実機利用を拒否するテストを先に追加する。
```powershell
$f = New-TestArchiveFixture
$bad = Copy-TestConfig $f.Config
$bad.destination_volume_id = 'another-volume'
Assert-Throws { Assert-ArchiveBindings -Config $bad -Adapters $f.Adapters } 'WrongVolume'
$bad = Copy-TestConfig $f.Config
$bad.archive_root = $bad.source_roots[0].path
Assert-Throws { Assert-ArchiveBindings -Config $bad -Adapters $f.Adapters } 'OverlappingRoots'
Assert-Equal $false (Test-Path -LiteralPath $f.MarkerPath) 'failed binding creates nothing'
```
- [ ] 失敗を確認後、絶対パス・root境界・媒体・マーカーの検査と制御退避を実装。実機ではtest adapterを受け付けない。すべての削除/移動先は操作直前に再検証する。
- [ ] テストが通ることを確認し、相互に重ならない実機bindingを確定する。タスク一時停止は実データ実行直前に行い、現在の実行終了とmutex取得が確認できるまで保存処理を開始しない。旧タスクを停止したまま長時間準備しない。
- [ ] 変更ファイルだけを検証・コミットする。コミット案: `feat(photo-archive): add verified host bindings and rollback snapshot`。

### Task 1: 読取台帳・撮影年月・資産束

**Files:** Create `PhotoInventory.psm1`, `Tests/Test-InventoryAndAssets.ps1`。
**Interfaces:** `Get-PhotoInventory(Config,Aliases,HashMode) -> FileRecord[]`; `Read-PhotoMetadata(Files,ToolReceipt) -> Metadata[]`; `New-PhotoAssets(FileRecords,Metadata) -> AssetRecord[]`。
**HashMode:** `MetadataOnly` / `Fresh` / `Cached`。Freshだけが初回受入・cleanupの根拠になる。

テストの合成データはTestHelpersで作る。LivePairFilesはHEIC/MOV各1個と一致するContentIdentifier、EditedVariantFilesは同一画像と異なるAAE各1個、OffsetMetadataは撮影日時`2024:05:31 23:30:00`と`-07:00`、UnknownDateFileは日時なしとする。EqualNameSizeDifferentHashは同名同サイズ別バイト2個、ExactDuplicateBundleは元位置の異なる同一束2個。ExpectedSourceHashesは元位置ごとのSHA-256を並べたstring配列とする。入力fixtureと完成fixtureを別に作り、期待値を本番関数で計算しない。

- [ ] T01〜T08を追加し、既存のファイル単体処理では関連情報を保全できないことをFAILで確認する。
```powershell
$f = New-TestArchiveFixture
New-TestFile $f.OldC 'a.jpg' 'same-bytes'
New-TestFile $f.OldF 'b.jpg' 'same-bytes'
New-TestFile $f.OldF 'a.jpg' 'different-bytes'
$rows = Get-PhotoInventory -Config $f.Config -Aliases @('OLD_C','OLD_F') -HashMode Fresh
Assert-Equal 3 $rows.Count 'source rows retained'
Assert-Equal 2 @($rows.sha256 | Select-Object -Unique).Count 'content hashes distinguish collision'
$assets = New-PhotoAssets -FileRecords $f.LivePairFiles -Metadata $f.LivePairMetadata
Assert-Equal 2 $assets[0].components.Count 'Live Photo keeps image and video'
$assets = New-PhotoAssets -FileRecords $f.EditedVariantFiles -Metadata $f.EditedVariantMetadata
Assert-Equal 2 $assets.Count 'different AAE remains a separate version'
$dated = New-PhotoAssets -FileRecords $f.OffsetFile -Metadata $f.OffsetMetadata
Assert-Equal '2024/05' $dated[0].calendar_bucket 'recorded capture month preserved'
$unknown = New-PhotoAssets -FileRecords $f.UnknownDateFile -Metadata @()
Assert-Equal '_undated' $unknown[0].calendar_bucket 'copy time is not capture time'
```
- [ ] 元の名前・サイズ・割当量・時刻・ID・属性・再解析tag・streamsを取得。接続や権限不明の行はPending/Blockedにする。Photosパッケージは保護境界として除外し、件数不一致に混ぜない。
- [ ] 読取前後のstatとSHA-256を取得し、変化した入力を安定したsnapshotへ取り直す。リンクをたどる前に最終パスを検証し、未知の再解析ポイントはRetain。コピー日時やmtimeだけで内容を証明しない。
- [ ] ExifToolには読取タグだけを渡す。JSON、group付きtag、元文字列を保持する。使用タグはDateTimeOriginal、OffsetTimeOriginal、SubSecTimeOriginal、CreateDate、CreationDate、ContentIdentifier、LivePhotoVideoIndex、FileType、FileName、FileSize。GPSや本文を解析ログへ出さない。
- [ ] Live Photoの対応を画像/動画の識別子と検証済み形式で判定。AAE・XMP・RAW・編集版を関連束にする。同一原本で異なる編集を別版にし、あいまいな対応を勝手に選ばない。未対応成分は元文脈を保った保留束としてコピー可能にするが、cleanupは不可。
- [ ] ケース差・Unicode・long pathを試す。対応できない入力は台帳へ理由付きで残し、無言で省略しない。
- [ ] 新テストと既存baselineを通す。コミット案: `feat(photo-archive): inventory original files and asset components`。

### Task 2: 内容対応・容量・dry-run計画

**Files:** Modify `PhotoInventory.psm1`; tests `Test-InventoryAndAssets.ps1`。
**Interfaces:** `New-PhotoMigrationPlan(Config,FileRecords,Assets,DestinationIndex) -> MigrationPlan`; `Assert-PlanInputs(MigrationPlan,Config)`。
**Plan fields:** plan_id、snapshot_ids、plan_sha256、actions、source_disposition、physical_capacity_budget、blocked_reasons。実行時の計画書自体もSHA-256で固定する。

計画hashは自身の`plan_sha256`を除いたペイロードを、UTF-8・LF・プロパティ順固定の正規化JSONにして計算する。各actionは完全なcomponent hashと元/先のrelative pathを保持する。適用モードは`-PlanPath`を必須にし、ファイルの存在だけで暗黙に最新planを選ばない。束の同一性は設計書の`bundle-id`規則に従い、別名・元位置は復元用台帳へ保持する。

- [ ] T09〜T12を追加する。
```powershell
$f = New-TestArchiveFixture
$plan = New-PhotoMigrationPlan -Config $f.Config -FileRecords $f.EqualNameSizeDifferentHash -Assets $f.Assets -DestinationIndex @()
Assert-Equal 2 @($plan.actions | Where-Object operation -eq Copy).Count 'equal size is not a duplicate'
$plan = New-PhotoMigrationPlan -Config $f.Config -FileRecords $f.ExactDuplicateBundle -Assets $f.Assets -DestinationIndex $f.VerifiedDestination
Assert-Equal 1 @($plan.actions | Where-Object operation -eq Reuse).Count 'complete identical bundle can reuse'
Assert-Equal 2 $plan.source_disposition.Count 'both aliases remain restorable'
$small = Copy-TestConfig $f.Config
$small.reserve_f_bytes = $f.AvailableBytes
Assert-Throws { New-PhotoMigrationPlan -Config $small -FileRecords $f.Rows -Assets $f.Assets -DestinationIndex @() } 'InsufficientCapacity'
Assert-Equal 0 @(Get-ChildItem -LiteralPath $f.Destination -File -Recurse).Count 'dry run writes no media'
```
- [ ] Copy/Reuse/Retainをすべての入力へ割り当てる。Reuseは完成束と元名の対応まで一致する場合のみ。違うmetadata/編集成分、未知の関係は統合しない。
- [ ] 新規ファイル・資産フォルダー・staging・証跡・既存コピー保持のピーク占有を128 KiB単位で算出する。C/Fの32 GiB予約を含め、各バッチ直前に再計算する。
- [ ] 同じalias/pathのsource変更、plan改変、媒体変更は適用拒否。snapshot後の新着は別planを作り、先の計画へ黙って追加しない。
- [ ] dry-runには対象数、論理/占有増分、保留、復元先、C解放の暫定上限を出す。69.49 GiBは候補値として表示し、実際のhash対応後にのみ重複量へ移す。
- [ ] 全suiteでPASS。コミット案: `feat(photo-archive): build immutable migration and capacity plans`。

### Task 3: 検証コピー・再開・復元

**Files:** Create `PhotoStorage.psm1`, `Tests/Test-CopyAndResume.ps1`。
**Interfaces:** `Invoke-PhotoPlan(Config,Plan) -> RunReceipt`; `Test-PhotoReceipt(Config,Receipt,Fresh) -> Verification`; `Restore-PhotoSources(Config,Receipt,DestinationRoot) -> RestoreReceipt`。

- [ ] T13〜T18を追加し、既存の一ファイルcopyでは束単位の確定・再開を保証しないことをFAILで確認。
```powershell
$f = New-TestArchiveFixture
$receipt = Invoke-PhotoPlan -Config $f.Config -Plan $f.Plan
Assert-Equal $true (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh).valid 'copied bytes freshly verify'
$again = Invoke-PhotoPlan -Config $f.Config -Plan $f.Plan
Assert-Equal 0 $again.new_files 'rerun does not create extra files'
Set-TestFileSameSizeAndTimeDifferentBytes $f.CommittedFile
Assert-Equal $false (Test-PhotoReceipt -Config $f.Config -Receipt $receipt -Fresh).valid 'same size/time corruption detected'
$restored = Restore-PhotoSources -Config $f.Config -Receipt $f.GoodReceipt -DestinationRoot $f.RestoreRoot
Assert-Equal (($f.ExpectedSourceHashes | Sort-Object) -join '|') (($restored.hashes | Sort-Object) -join '|') 'aliases and components restore exactly'
```
- [ ] WindowsのFileStreamをCreateNewで開き、安定したsource handleからcopy。Flush(true)、close、元/destの再読取を行ってから確定パスへ移す。すべての構成要素を検証してCommitted証跡を保存する。短縮hashは命名用に限定。
- [ ] journalはPlanned→Staged→Verified→Committed。任意の段階で中断してもsourceを維持し、再実行は存在するdestを読み直して継続する。末尾途中のjournal、index破損、rename後receipt前の停止、切断で完成数を過大計上しない。
- [ ] 中断テストは合成fixtureの専用workerだけを、PIDと開始時刻を確認して停止。worker起動は非表示。実運用コードに任意クラッシュ用フラグを残さない。
- [ ] 新規・Reuse・source mutation・同時実行・ゼロbyte・未知形式・4 GB超のstream実行を検証する。大きなfixtureは本番写真ではなく必要時に別の統合テストで作る。
- [ ] 元のrelative path、名前、関係、時刻、streamsが復元できることを試す。復元先に別内容があれば上書きせず停止。
- [ ] 全suiteでPASS。コミット案: `feat(photo-archive): verify and resume asset copies`。

### Task 4: クラウド取得と日次入口

**Files:** Create `PhotoCloud.psm1`, `PhotoCloudNative.cs`, `ICloudPhotoArchive.psm1`, `Archive-iCloudPhotos.ps1`, `Tests/Test-CloudAndCleanup.ps1`; modify runner tests。
**Interfaces:** `Get-CloudFileStatus(Config,FileRecord)`; `Ensure-CloudFileAvailable(Config,FileRecord) -> Available/Pending`; `Invoke-ICloudPhotoArchive(Config) -> RunSummary`。
**CLI modes:** `Inventory`, `Plan`, `Apply`, `Archive`, `Verify`, `Restore`, `CleanupPlan`, `CleanupApply`, `ReleaseCloudCache`。旧CLIの入力は移行期間にadapterで読めるが、実機bindingを省略して本番へ書く入口は作らない。

CLI引数は全モードの`-ConfigPath`に加え、Applyは`-PlanPath`、Verify/Restoreは`-ReceiptPath`、Restoreは`-RestoreRoot`、CleanupApplyは`-CleanupPlanPath`、ReleaseCloudCacheは`-ReceiptPath`を必須にする。Inventory/Planは写真本体に書き込まず、検証済みstate領域へ新しい出力を作る。

- [ ] T19〜T24を追加する。mockはOS/同期プロバイダーの境界だけに置き、コピー・hash・journalは実ファイルでテストする。
```powershell
$f = New-TestArchiveFixture
Set-TestCloudResponse $f.Adapters 'Timeout'
$result = Ensure-CloudFileAvailable -Config $f.Config -FileRecord $f.Placeholder -Adapters $f.Adapters
Assert-Equal 'Pending' $result.status 'timeout remains pending'
Assert-Equal 0 $result.committed_files 'placeholder is not completed media'
Set-TestCloudResponse $f.Adapters 'Complete'
$result = Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
Assert-Equal 1 $result.Copied 'hydrated new file is verified and archived'
Remove-TestSource $f.SyncSource
$result = Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters
Assert-Equal $true (Test-Path -LiteralPath $f.ArchivedFile) 'cloud deletion does not remove archive'
Set-TestVolumePresent $f.Adapters $false
Assert-Equal 'SkippedMissingDrive' (Invoke-ICloudPhotoArchive -Config $f.Config -Adapters $f.Adapters).Status 'missing F does not fall back to C'
```
- [ ] Cloud Files APIは登録済み同期ルートの取得と状態確認に限定。プロバイダーの媒体/ユーザーbindingとin-sync方針を確認する。600秒で制御できる非同期取得・キャンセルを実装し、workerが残る間はpartialを再利用/削除しない。
- [ ] 未取得は取得後の新しいsource stat/hashで読み直す。期限超過・ログアウト・再試行失敗はPending。Snapshot後の新着は差分snapshotへ分離する。
- [ ] 元の同時実行mutex、hash cache、非連動保存を共通化。version2のstateと古いstateを分離する。30日full検証は保存実体の新しいhashで行う。
- [ ] 日次の取得入力はICLOUDに限定し、初回OLD_C/OLD_Fの再取り込みを止める。ローカルFに新しい版・追加ファイル・移動があれば別の来歴として照合する。ユーザーの編集を破損と決めつけて上書きしない。
- [ ] 終了コードは0=SnapshotVerified、3=PendingIncomplete、10=SkippedMissingDrive、20=DeferredCapacity、30=Blocked/Error。終了コード0でも全iCloud原本の完全性まで意味しない。RunSummaryのscopeを必須にする。
- [ ] 旧テストのonline-only「無言で対象外」を、新モードでは取得または保留に更新する。古い動作比較は別baselineで保持。
- [ ] 全suiteとNative APIの構文/ロード検証。コミット案: `feat(photo-archive): archive cloud files with bounded acquisition`。

### Task 5: 実データのパイロットと完全性判定

**Files:** Create `README.md`; private outputs `pilot-plan.json`, `pilot-receipt.json`, `restore-test.json`, `capacity-after-pilot.json`。
**Prerequisite:** Task0〜4の全テストPASS。Macパッケージ保護、ルート/媒体guard、元データ不変を確認。

- [ ] 合成fixtureで既存同名衝突・元削除非連動・再実行・空き不足・cache破損・曖昧束を一度通してから本番へ進む。
- [ ] 最大256ファイルまたは2 GiBまで、構成要素を切らない代表束を選ぶ。HEIC、JPEG、PNG、MOV、MP4、AAE、DNG/AVIF、名前衝突、日時不明、Live Photo、online-onlyを含める。大きい動画一件は別枠で測る。
- [ ] copy後の全hashと元データ不変を確認。Windowsで画像を開く、動画を開始/中間/末尾まで再生する、raw/sidecarを対応先へ復元する。暗黙の再圧縮や向き変更が起きないことを確かめる。
- [ ] 実際のLive Photo一件で、識別子・画像・動画・編集成分とWindows投影を比較する。Windows側に必要な成分がなければ公式未編集原本の別snapshotで補完する。原本取得/認証を代行できない場合はその成分を保護継続し、全原本保存を未完了として記録する。
- [ ] 当日のonline-only集合を再計測し、固定の58件を対象にしない。取得し直したデータが派生版なら元形式と混同しない。
- [ ] 小ファイル数、read/hash/write、metadata、cloud待機、最大staging、C/F空きと割当増分を測る。初回の所要時間と容量を実測から更新する。
- [ ] パイロットが不合格なら当該束だけ保留にしてsourceを残す。容量が不合格なら全体適用を止める。実データのファイルを公開コミットへ入れない。

### Task 6: 全体取り込みと日次切替

**Files:** Modify `Install-PhotoArchive.ps1`, runner tests、README；private outputs 全入力台帳、全体plan/receipts、新旧task XML・deployment receipt。
**Interfaces:** `Install-PhotoArchiveRelease(Config,CodeRoot,ExpectedHashes)`; `Switch-PhotoArchiveTask(Config,ControlReceipt)`; `Undo-PhotoArchiveDeployment(Config,ControlReceipt)`。

- [ ] T25〜T28を追加し、設定やhash不一致のreleaseは切替されないこと、失敗時に旧taskへ戻ることを実ファイルとtask adapterでテスト。
```powershell
$f = New-TestArchiveFixture
Set-TestReleaseHashMismatch $f
Assert-Throws { Install-PhotoArchiveRelease -Config $f.Config -CodeRoot $f.Release -ExpectedHashes $f.Hashes } 'ReleaseMismatch'
Assert-Equal $f.OldTaskXml (Get-TestTaskXml $f) 'failed deploy leaves task unchanged'
Switch-PhotoArchiveTask -Config $f.Config -ControlReceipt $f.ControlReceipt -Adapters $f.Adapters
Undo-PhotoArchiveDeployment -Config $f.Config -ControlReceipt $f.ControlReceipt -Adapters $f.Adapters
Assert-Equal $f.OldTaskXml (Get-TestTaskXml $f) 'rollback restores original task'
```
- [ ] 書込処理直前に旧タスクを一時停止し、runningでないこととmutex取得を確認。制御snapshotを更新。同期サービスは稼働を維持する。
- [ ] OLD_C、OLD_Fの全件Fresh台帳・資産対応を確定してplan適用。F側の旧コピーを残したピーク予算を確認してから各batchを開始する。変更されたsourceにはその場で削除判断をしない。
- [ ] ICLOUDを当日snapshotとして取り込む。読取不能・足りない構成要素・未取得を元位置で保持し、入力数から消さない。全入力にcopy/reuse/retainの対応があることをA01で突き合わせる。
- [ ] 全F保存をFresh hashで再検証。代表束をCの復元fixtureへ戻し、名前・バイト・関係・元情報を検証する。
- [ ] リポジトリの汎用コードを私有releaseへ配置し、hash一致を確認してから起動器と既存タスクを切り替える。20時・非表示・権限・取り逃し補完・同時実行抑止を保持する。
- [ ] 手動1回、同じ入力で手動2回目を実施。2回目に不要コピーが増えず、変更分だけ追加されることを確認。次の定時実行を1回確認する。終了コードとRunSummaryのPendingを併記する。
- [ ] 定時実行をまだ確認していない場合は「運用切替済み・定時未検証」で止め、完了と書かない。待機中に新しい監視ジョブを勝手に作らない。
- [ ] 失敗時は新運用停止→旧コード/state/JS/task XML復元→C保存先で小範囲動作確認。完了後にprivate receiptへ切替成功を記録する。
- [ ] 全suite、5.1/7.6構文、相対リンク、required pre-commit、privacy差分検査。コミット案: `feat(photo-archive): deploy verified archive and preserve task rollback`。push/マージは実行時の別途許可の範囲に従う。

### Task 7: 独立コピー・C解放・復旧の合格判定

**Files:** Modify `PhotoStorage.psm1`, `PhotoCloud.psm1`, entry、README；tests `Test-CloudAndCleanup.ps1`, `Test-CopyAndResume.ps1`。
**Interfaces:** `New-PhotoCleanupPlan(Config,Receipt,IndependentProofs) -> CleanupPlan`; `Invoke-PhotoCleanup(Config,CleanupPlan) -> CleanupReceipt`; `Release-VerifiedCloudCache(Config,VerifiedFileRecords) -> ReleaseReceipt`。

- [ ] T29〜T34を先に追加する。
```powershell
$f = New-TestArchiveFixture
$plan = New-PhotoCleanupPlan -Config $f.Config -Receipt $f.GoodReceipt -IndependentProofs @()
Assert-Equal 0 $plan.eligible.Count 'F alone does not authorize C deletion'
$plan = New-PhotoCleanupPlan -Config $f.Config -Receipt $f.GoodReceipt -IndependentProofs $f.ProofOnSameDisk
Assert-Equal 0 $plan.eligible.Count 'two paths on F are not independent copies'
$plan = New-PhotoCleanupPlan -Config $f.Config -Receipt $f.GoodReceipt -IndependentProofs $f.GoodIndependentProof
Set-TestFileSameSizeAndTimeDifferentBytes $f.OldCFile
Assert-Throws { Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $plan } 'SourceChanged'
Assert-Equal $true (Test-Path -LiteralPath $f.OldCFile) 'changed source is retained'
Assert-Throws { Invoke-PhotoCleanup -Config $f.Config -CleanupPlan $f.PlanInsideCloudRoot } 'CloudRootDeletionForbidden'
```
- [ ] F以外の物理媒体の新しいreadback hash、または独立に取得したクラウド未編集原本のhashを各構成要素へ対応させる。証明不能はRetainとしてC側を独立コピーに使う。iPhoneバックアップをiCloud写真の原本コピーだと仮定しない。
- [ ] cleanup候補集合の依存関係を検査し、互いの削除予定ファイルを独立コピーと数えない。全削除後のコピー構成を計算する。OLD_F旧コピーの整理は、F新保存と別媒体の証明がある対象に同じ7日保持・Fresh照合を適用する。Fのみの新旧2コピーは削除の保護根拠にしない。
- [ ] 元とFのFresh hash、資産完全性、復元合格、日次受入を確認してEligibleの個別リストを作る。OLD_Cの通常ファイルは設定済みのC側retainedへ、OLD_Fの旧コピーは`archive_root\retained`へ個別移動し、日時と元位置を記録する。保持先は各元ファイルと同じ物理媒体に限定し、これらを独立コピーの数には加えない。
- [ ] 7日保持の経過に加えて、その時点のFと独立コピー、元の保持ファイルをFreshで再検証してから確定削除する。許可済みリストのファイルをLiteralPathで一件ずつ処理する。一括root再帰削除や元同期フォルダーの削除を禁止する。
- [ ] iCloudキャッシュは別モードで、F照合・in-sync・プロバイダー方針・少数の再取得試験に合格したものだけ解放する。APIが許されない場合はunpinまたは公式UI操作へ切り分け、元データを消すコマンドへ変更しない。
- [ ] readonly/権限エラー、媒体切断、破損、コード変化、cache偽陽性を拒否し、確定済み保管を残す。拒否された削除を別方式で迂回しない。
- [ ] 最終の論理/占有/空き容量を別々に測る。Cの解放済み、7日保持中、独立コピー未証明で保持、F追加占有、Macライブラリ保管継続を区別する。通常の写真copyを移動した量を全ドライブの容量節約と数えない。
- [ ] A01〜A15を全て照合し、未解決条件があればその資産と工程を残件にする。コミット案: `feat(photo-archive): guard cache release and verified copy cleanup`。

## 共通検証コマンド（実装後に限る）

Windowsの実行パスは私有bindingから取得する。実行中の共有sourceに直接テストfixtureを書かない。

```powershell
param([Parameter(Mandatory)][string]$photoConfigPath)
$photoCodeRoot = (Get-Content -LiteralPath $photoConfigPath -Raw | ConvertFrom-Json).release_code_root
& (Join-Path $photoCodeRoot 'Tests\Run-All.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Photo archive tests failed' }
& (Join-Path $photoCodeRoot 'Archive-iCloudPhotos.ps1') -ConfigPath $photoConfigPath -Mode Inventory
& (Join-Path $photoCodeRoot 'Archive-iCloudPhotos.ps1') -ConfigPath $photoConfigPath -Mode Plan
```

`Run-All.ps1` は5.1と現在の7系で同じsuiteを非表示起動し、全ケースのPassed/Failed/Skippedを出す。Cloud Filesの実プロバイダー試験が実行できない場合はSkipped理由を出す。合成試験PASSを本番クラウド取得の合格へ置き換えない。ケース一覧を下表と対応させる。

## 検証マトリクス

| テスト | 入力・失敗点 | 担当 | 受入 |
|---|---|---|---|
| T01 | 誤媒体、root重複、保護パッケージ | 0/1 | A01,A07 |
| T02 | traversal、外部リンク、未知reparse | 1 | A01,A03 |
| T03 | 同名別内容 | 1/2 | A02,A03 |
| T04 | 別名同内容と復元alias | 1/2 | A03,A09 |
| T05 | Live Photoの画像/動画/識別子 | 1 | A03,A05 |
| T06 | AAE差分、片方不足、RAW/未知形式 | 1 | A03 |
| T07 | 時差、動画時刻、欠損日時 | 1 | A04 |
| T08 | Unicode/ケース/長パス/streams | 1 | A03,A09 |
| T09 | plan改変、snapshot差分 | 2 | A01,A06 |
| T10 | exFAT割当・ディレクトリー・stagingピーク | 2 | A07,A14 |
| T11 | 古いF保持を含む容量不足 | 2 | A07 |
| T12 | 名前・サイズ一致だけの誤Reuse | 2 | A02,A03 |
| T13 | source変更、copy前後hash | 3 | A02 |
| T14 | 同サイズ・同時刻のdest破損 | 3 | A08 |
| T15 | 部分copy、rename後receipt前停止 | 3 | A06,A07 |
| T16 | 壊れたjournal/cache/index | 3 | A06,A08 |
| T17 | 二重ジョブ、同じplan再適用 | 3/4 | A06 |
| T18 | 元位置復元、衝突拒否、4GB超 | 3 | A09 |
| T19 | online-only正常取得/timeout | 4 | A05 |
| T20 | 未同期・別プロバイダー・拒否 | 4 | A05,A11 |
| T21 | F未接続、Cへの代替保存禁止 | 4 | A07 |
| T22 | 撮影原本と派生版、成分不足 | 4/5 | A03,A05 |
| T23 | snapshot後の新着/連続変更 | 4 | A01,A05 |
| T24 | 元の削除非連動、月次Fresh hash | 4 | A08 |
| T25 | 配備hash不一致/途中失敗 | 6 | A09 |
| T26 | XML/JS/状態/コード切戻し | 6 | A09 |
| T27 | 非表示、20時、権限、mutex | 6 | A12 |
| T28 | 手動2回・実定時1回 | 6 | A06,A12 |
| T29 | 独立コピーなし/同一媒体 | 7 | A10 |
| T30 | 削除直前source/dest変更 | 7 | A10 |
| T31 | 7日保持未達、証跡失効 | 7 | A09,A10 |
| T32 | 同期ルートの通常削除拒否 | 7 | A11 |
| T33 | dehydrate許可/拒否/再取得 | 7 | A11 |
| T34 | F故障後に独立コピーから復元 | 7 | A09,A10 |
| T35 | 公開差分の個人情報なし | 全工程 | A13 |
| T36 | 処理量・占有・実空きの分離 | 5/7 | A14 |
| T37 | 旧F整理、削除対象間の循環証明拒否 | 7 | A15 |

## 停止条件と復旧判断

- **媒体/境界不一致**: 全書込停止、binding再確認。既存sourceを保持。
- **破損/未説明のhash差**: 該当資産のcopy/cleanup停止。私有証跡を残し、独立コピーから復旧。
- **容量不足**: 現バッチを始めない。未完了はstagingとして数える。別媒体が必要な量を具体的に報告。
- **クラウド成分/原本取得不能**: 利用できるファイルを保管し、資産をPending。原本の取得経路が検証できるまで全原本保存完了とは言わない。
- **独立コピー未証明**: Fへの配置と日次切替は進められる。該当C原本の解放だけを保留。
- **定時未検証/7日保持中**: 工程の状態を残し、完了と書かない。経過時間で本人の許可を作らない。
- **自動承認レビュー拒否**: 操作・理由を報告して停止。同じ削除の迂回実行は行わない。

## 工程別の完了報告

| 工程 | 必須の証拠 | 報告の状態 |
|---|---|---|
| 入力/plan確定 | 入力対応台帳、能力検査、Fresh hash、ピーク予算 | 調査・計画確定 |
| Fへの保管 | 全copy/reuse/retain対応、Fresh hash、復元 | 保管先移行完了または保留あり |
| 日次切替 | 配備hash、手動2回、定時1回、元C書込なし | 切替完了または定時未検証 |
| Cの容量解放 | 独立コピー、7日保持、再検証、削除receipt、実空き | 解放完了または保護継続 |
| 全体 | A01〜A15、残件一覧、scope、復旧方法 | 全条件合格の場合だけ全体完了 |

## 計画作成時点の状態

- [x] 現行コード・独自テスト・起動器・タスク設定を読取確認。
- [x] 現在の形式・件数・AAE・再解析ポイント・変化するcloud状態を確認。
- [x] プライバシーを保つ実機別紙の保存先を決定し、公開設計から分離。
- [x] 容量・完全性・復元・切替・cleanupの合格条件とテストを定義。
- [ ] Task0〜7の実装。
- [ ] 全件内容照合とピーク容量の確定。
- [ ] 写真の移動、旧コピーの削除、自動保存先の変更。

この計画の作成は、新しい依存のインストール、写真移行、タスク変更、Gitへのコミット/pushを実行したことを意味しない。実行指示を受けたら前提を再確認して工程0から進める。

### 計画文書の検証（2026-10-12）

相対リンク4件の実在、設定例JSONの構文、工程0〜7の順序、受入15項目とテスト37件の対応、PowerShell例8ブロックの5.1/7.6構文を確認した。対象文書のpre-commitでは競合マーカー・大容量ファイル・秘密鍵の検査が通り、対象外の形式検査はSkipped。これは文書の検証であり、計画中の実装テスト・実データ受入の合格ではない。

## 実行状況（2026-10-12）

専用ブランチ`codex/photo-archive`で実行。詳細と残件は[写真移行の進捗](../../knowledge/photo-archive/STATUS.md)を参照する。上のチェックリストは計画作成時点の記録であり、現在の状態は以下。

| 範囲 | 状態と証拠 |
|---|---|
| 実装・検証 | コピー、再開、クラウド取得、日次CLI、配備／切戻し、復元、保持／削除の保護を実装。68ケースがWindows PowerShell 5.1／7.6で合格。実機受入は以下の範囲 |
| 第1波 | 旧C／旧Fの入力32,252件を保存／再利用32,247件・保護5件へ対応。保存20,219ファイルをFresh照合。元入力の事後検査で変更・追加・欠落0件 |
| 日次移植 | リリース`4968d108`を私有配置。実タスクの切替／切戻しで制御5ファイルとXMLを復旧確認後、新入口へ切替。手動2回で300ファイル追加・再実行の追加0件。新規300件もFresh照合。対象11,780／11,782件の対応に漏れなし |
| 定時受入 | 2026-10-12 20:00:01の実タスクを20:11:15の証跡と照合。終了コード3、追加0件、保存済み元位置1,877件＋保留9,906件、重複0件。旧Cの追加・欠落・サイズ／更新時刻の変化0件。手動2回・定時1回の受入済み。全保存成功ではない |
| 第2波・完全性 | 容量待ち。日次2回目では9,905入力を元位置保持。全原本／編集関連の完全性は未確認 |
| 独立コピー・容量解放 | 旧F12,986件のFresh再検査と関連再判定済み。候補9,870件・約62 GiBについてC独立コピーとF保持への移動を実行中。関連未確認3,116件を保護。先頭の最終削除は2026-10-19 22:15 JST以降、後続は各実保持開始から7日後。確定削除0件 |

全件のピーク予算がFの空きを超えたため、原本を残して2波へ分割した。旧判定の証跡はバイト保存にのみ使い、整理には元位置ごとの新しい関連判定を要求する。日次切替の受入済み・旧F保持工程を実行中として記録し、全移行完了とはしない。このチャットへ毎日23:55 JSTのフォローアップを設定し、稼働中の処理との競合を避けながら、保持満了後の再検証・整理・第2波を続ける。

