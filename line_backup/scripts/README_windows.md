# Windows での実行手順

## 前提

- Python 3.11 以上がインストール済み
- iTunes または Apple Devices で iPhone のローカルバックアップ（非暗号化）を作成済み

## セットアップ

```powershell
# プロジェクトルートで実行
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## クイックスタート（PowerShell）

```powershell
# バックアップ一覧を確認
python -m line_backup_exporter.cli list-backups

# スクリプトを使った自動スキャン（backup-dir を対話入力）
.\scripts\run_first_scan.ps1
```

## ステップごとの実行例

```powershell
# 1. LINEファイル一覧を出力
python -m line_backup_exporter.cli scan-line `
  --backup-dir "C:\Users\you\AppData\Roaming\Apple Computer\MobileSync\Backup\<backup_id>" `
  --out output

# 2. SQLite候補をコピー
python -m line_backup_exporter.cli extract-candidates `
  --backup-dir "C:\Users\you\...\<backup_id>" `
  --manifest-csv output\manifest_line_files.csv `
  --out output

# 3. DBスキーマを確認
python -m line_backup_exporter.cli inspect-db `
  --db output\extracted\some_Line.sqlite `
  --out output

# 4. テーブルをそのままCSV出力
python -m line_backup_exporter.cli export-raw-table `
  --db output\extracted\some_Line.sqlite `
  --table ZMESSAGE --out output --limit 1000

# 5. 正規化メッセージCSVを作成
python -m line_backup_exporter.cli export-line-csv `
  --db output\extracted\some_Line.sqlite `
  --message-table ZMESSAGE --out output

# 6. HTMLで閲覧
python -m line_backup_exporter.cli render-html `
  --messages-csv output\line_messages_normalized.csv `
  --out output
# → output\html\index.html をブラウザで開く
```

## トラブルシューティング

| 問題 | 対処 |
|---|---|
| `list-backups` で何も表示されない | iTunesで「このコンピュータにバックアップ」を実行 |
| `encrypted: YES` と表示される | iTunes で「ローカルバックアップを暗号化」をオフにして再バックアップ |
| `Manifest.db not found` | --backup-dir が個別バックアップのフォルダ（英数字40文字）を指しているか確認 |
| `inspect-db` が遅い | 大きなテーブルのCOUNT(*)。--sample-rows 0 にすると行数計測をスキップできます |
