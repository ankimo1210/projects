# 写真アーカイブ

Windowsの写真保存をF:の通常フォルダーへ集約する。元の写真・動画・編集ファイルのバイト列を変えず、元の名前と場所への復元対応を私有台帳に残す。

- [移植計画](../../superpowers/plans/2026-10-12-photo-archive-migration.md)
- [保存・復元の設計](../../superpowers/specs/2026-10-12-photo-archive-migration-design.md)
- [現在の進捗](STATUS.md)

## 保存と同期

撮影・日常の閲覧はiPhone/iCloud、PCの保管はF:、C:は受け取り・検証に使う。同期元から消えたファイルをアーカイブから削除しない。編集された内容は別の版として保存し、確定済みの原本を上書きしない。

撮影日時が不明なものは`_undated`へ保存する。Live Photoや編集情報の対応が未確認なら、ファイルを保全して関係確認を保留する。Windowsに表示されるファイルの保存を「全iCloud原本の完全なバックアップ」とは呼ばない。Appleのアルバム・人物・非破壊編集履歴を通常ファイルだけで再現するものではない。

既存の日次保存の切替は配備・復元検証後に行う。実機の保存場所、台帳、ログ、写真名、認証やアカウントの識別子は公開リポジトリに置かない。設定はWindowsのローカル管理領域にある私有JSONから読み込む。

## 運用上の条件

F:の文字だけで保存先を判断せず、媒体とアーカイブの識別子を確認する。F:の空き32 GiBを維持し、64 GiB未満は警告する。接続がなければ保留し、別のC:保存へ自動で切り替えない。

初回と削除前は新しいSHA-256で照合し、関連ファイル一式と元位置の復元を確認する。C:の通常コピーを削除するには、F:と別の物理媒体または取得し直して照合済みのクラウド原本が必要。同じF:上の二つのフォルダーは独立コピーではない。削除候補も7日保持し、日次処理から通常ファイルを削除しない。

iCloud同期先では通常の削除を使わない。検証済みの受け取りキャッシュだけを、同期サービスが認める方法で解放する。元の同期ファイルとクラウドの写真を維持する。

## 開発と検証

コードはWindows PowerShell 5.1とPowerShell 7系に対応する。`Tests/Run-All.ps1`は両方の実行結果を集計し、完全な結果をWindowsの一時領域に保存する。写真本体を使う試験と合成データの試験を区別する。

ExifToolは読み取り専用で使う。今回の実機ではWindows ZIPの配布先からHTMLが返ったため、作者の13.59版ソースと既存のWindows Git Perlを使う。作者のコミット、ソース一式、起動器のハッシュを私有記録に固定し、変更されていれば処理を止める。システム全体のPATHは変更しない。

Cloud Files APIの引数・構造はMicrosoftの文書とインストール済みWindows SDKで確認する。取得は非同期で上限を設け、キャンセルが確定していない入力を保存完了にしない。

- [Microsoft: プレースホルダー取得](https://learn.microsoft.com/en-us/windows/win32/api/cfapi/nf-cfapi-cfhydrateplaceholder)
- [Microsoft: ローカル保持状態](https://learn.microsoft.com/en-us/windows/win32/api/cfapi/ne-cfapi-cf_pin_state)
- [ExifTool作者のリポジトリ](https://github.com/exiftool/exiftool)

## 実行入口

`Archive-iCloudPhotos.ps1`の全モードに私有の`-ConfigPath`が必要。実機の値は私有設定を参照する。

| モード | 追加引数・動作 |
|---|---|
| `Inventory` / `Plan` | `-Aliases`で入力を限定。計画と写真の保存は別操作 |
| `Apply` | `-PlanPath`。改変されていない計画だけを適用 |
| `Archive` | 日次のiCloud投影。`-Fresh`で通常キャッシュを使わず検査 |
| `Verify` | `-ReceiptPath`。保存実体をFresh照合 |
| `Restore` | `-ReceiptPath -RestoreRoot`。既存の別内容は上書きしない |
| `Restore`（F障害） | 上記に`-IndependentProofsPath`。別媒体の通常コピー／C保持ファイルを媒体IDとhashで検証して入力に使う |
| `CleanupPlan` | `-ReceiptPath`、任意の`-IndependentProofsPath`。証明がなければ保持 |
| `CleanupApply` | `-CleanupPlanPath`。日次受入・7日保持・直前再検証を要求 |
| `ReleaseCloudCache` | `-ReceiptPath`。日次受入と少数再取得の証明を要求。同期ファイルの通常削除は行わない |

終了コードは0=宣言したsnapshotの検証済み、3=保留あり、10=F未接続、20=容量保留、30=エラー／安全条件不一致。0でも全iCloud原本の完全性を意味しない。日次の保留件数と対象範囲を併せて読む。

配備は`Install-PhotoArchive.ps1`の関数で検証済みリリースを作り、制御ファイルとタスクXMLの退避を照合してから切り替える。F障害時の切戻しは`Read-ArchiveConfig -Recovery`と`Undo-PhotoArchiveDeployment`でC側の退避を検証する。開発途中のコードを現行日次タスクへ直接設定しない。

付随ファイルの関係が不明な画像も保護する。旧関連判定のreceiptは元位置ごとに再判定が必要。新しい別名を取り込んでも、旧別名の保護を自動で解除しない。後着の付随ファイルと代替ストリームは移動前・削除前に再検査し、取得できなければ保持する。復元用の別名は記録ファイルの名前順に依存せず統合する。
