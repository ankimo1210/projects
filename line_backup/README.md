# LINE Backup Exporter

**自分の iPhone ローカルバックアップから LINE データをローカルで解析するツールです。**

- 外部通信なし・完全ローカル処理
- Apple ID / iCloud 認証情報は一切要求しない
- バックアップは読み取り専用で扱う（破壊的操作なし）
- iCloud バックアップの直接解析は対象外
- **暗号化バックアップは未対応**（iTunes/Finder で暗号化をオフにしてください）

---

## セットアップ

このプロジェクトはワークスペース（`~/projects/`）の uv メンバーです。Python 依存はワークスペースルートで一括管理されます。

```bash
# ワークスペースルートで一度実行すれば、line_backup を含む全メンバーが editable install
cd ~/projects && make install     # = uv sync --all-packages
```

---

## 実行例

```bash
# 1. バックアップ一覧を確認
python -m line_backup_exporter.cli list-backups

# 2. LINE関連ファイルをスキャン
python -m line_backup_exporter.cli scan-line \
  --backup-dir "/path/to/backup/<backup_id>" \
  --out output

# 3. SQLite候補ファイルをコピー
python -m line_backup_exporter.cli extract-candidates \
  --backup-dir "/path/to/backup/<backup_id>" \
  --manifest-csv output/manifest_line_files.csv \
  --out output

# 4. DBスキーマを確認
python -m line_backup_exporter.cli inspect-db \
  --db output/extracted/some_Line.sqlite \
  --out output

# 5. テーブルを生CSVで出力
python -m line_backup_exporter.cli export-raw-table \
  --db output/extracted/some_Line.sqlite \
  --table ZMESSAGE --out output --limit 1000

# 6. 正規化メッセージCSVを作成
python -m line_backup_exporter.cli export-line-csv \
  --db output/extracted/some_Line.sqlite \
  --message-table ZMESSAGE --out output

# 7. HTMLで閲覧
python -m line_backup_exporter.cli render-html \
  --messages-csv output/line_messages_normalized.csv \
  --out output
```

Windows での詳細手順は [`scripts/README_windows.md`](scripts/README_windows.md) を参照。

---

## 出力ファイル

| ファイル | 内容 |
|---|---|
| `output/manifest_line_files.csv` | Manifest.db から抽出したLINE関連ファイル一覧 |
| `output/manifest_line_files.json` | 同上のJSON版 |
| `output/extracted/` | コピーされたSQLite DBファイル |
| `output/extracted_index.csv` | コピー元と先の対応表 |
| `output/db_schema_report.md` | テーブル/カラム/サンプル行のMarkdownレポート |
| `output/table_samples/<table>.csv` | 各テーブルの先頭数行 |
| `output/raw_tables/<table>.csv` | 生エクスポートCSV |
| `output/line_messages_normalized.csv` | 正規化メッセージCSV |
| `output/html/index.html` | チャット一覧HTML |
| `output/html/chat_<id>.html` | チャットごとのHTMLページ |

---

## トラブルシューティング

| 問題 | 対処 |
|---|---|
| `list-backups` で何も表示されない | iTunes/Apple Devices で「このコンピュータにバックアップ」を実行 |
| `encrypted: YES` と表示される | iTunes で暗号化をオフにして再バックアップ |
| `Manifest.db not found` | `--backup-dir` がバックアップIDフォルダを指しているか確認 |
| LINEファイルが見つからない | バックアップが古い・または部分的の可能性。新しいバックアップを試す |
| `inspect-db` が遅い | 大きなテーブルの行数計測に時間がかかる場合あり。`--sample-rows 0` は現時点非対応だが、通常は数分以内に完了 |

---

## テスト実行

```bash
python -m unittest discover tests
```

---

## 注意事項

- 本ツールは **自分の端末・自分のLINEデータ** のローカル解析専用です
- 抽出したデータは `output/` に保存されます。`.gitignore` により Git 管理から除外されています
- LINEのDB構造はバージョンによって異なります。`inspect-db` でスキーマを確認してから操作してください
