# 実ポジション・残高・取引履歴の保存先

更新: 2026-11-01

本人のポジション・口座残高・取引履歴を公開チェックアウトから分離した。
公開側には汎用コードと架空サンプルを残し、19件の個人入力に依存した回帰テストも
架空fixtureへ置き換えた。金額・配分・個人データのハッシュはこの文書には記録しない。

## 保存したもの

正本はWindowsの `G:\マイドライブ\Repo\projects\portfolio-analyzer\data`。
14ファイル、計247,654 bytesをコピー・照合し、クラウド同期と非共有状態の確認後、
レポ内の同名実ファイルを取り除いた。

| 種類 | ファイル |
|---|---|
| 保有・口座残高 | `portfolio.private.json` |
| 過去の保有スナップショット | `portfolio-2026-08-31.private.json`、9月1日・16日・17日の各通常版／with-cost版（計7本） |
| 取引履歴 | `ibkr-transactions.private.csv`、`securities-transactions.private.csv` |
| DC残高・掛金履歴 | `dc-holding.private.json`、`dc-transactions.private.tsv` |
| 取得原価・時価履歴 | `ibkr-ledger.private.json`、`mtm-history.private.jsonl` |

公開テストの元の個人値を含む断言は、Driveの同じプロジェクト配下の
`personal-test-assertions.json` に断片だけ保存した。個人の取引入力に関する
文書断片は `personal-source-notes.json`、サイズ・ハッシュの移管台帳は
`Repo/migration/2026-11-01-assets/manifest.json` にある。
モデル設定・売買提案・調査資料・過去レポートの一括移動は行っていない。

## Windowsで使う

この端末は設定済み。PowerShellで `portfolio-dashboard` を実行すると、
Drive上の入力を読み、`Repo/projects/portfolio-analyzer/reports/` へ出力する。
入力パスを毎回指定する必要はない。

設定は `%USERPROFILE%\.config\portfolio-analyzer\windows.json`。
ローカルランチャーは既存のWindows版Pythonを使い、子プロセスにだけ
WSLの既存タイムゾーンDBのパスを渡す。グローバル環境変数や本番依存は追加していない。

## Macの初回設定

同じGoogle Driveを同期し、Finderで確認した実在するRepoのパスを使う。
リポジトリのルートで、次の `/実際の/...` を実パスに置き換えて一度実行する。

```bash
uv run --package portfolio-analyzer python \
  portfolio-analyzer/scripts/configure_private_data.py \
  --data-dir "/実際の/Google Drive/Repo/projects/portfolio-analyzer/data"
```

以後は通常のコマンドでDrive上の実データを読む:

```bash
uv run --package portfolio-analyzer python portfolio-analyzer/scripts/build_dashboard.py
```

設定先は `~/.config/portfolio-analyzer/config.json`。
Python 3.12以降を使う。実Macは未検証。
WindowsとMacのネイティブ実行は同じDriveフォルダへ直接読み書きする。
`--input` 等の明示パスは従来どおり優先される。
端末設定を一時的に上書きする場合は `PORTFOLIO_PRIVATE_DATA_DIR` に外部フォルダを指定できる。

## WSLと既存のWindows定期実行

WSLからGドライブを直接読めないため、レポ外の通常コピーを使う:
`/mnt/c/Users/Kazumasa/.local/share/repo-private/projects/portfolio-analyzer/data`。
設定は `~/.config/portfolio-analyzer/wsl.json`。Windows用設定とは分けてある。

`private-inputs-sync` はWindows側からDriveを読み、ポジション・取引CSV・
DC入力・取得原価台帳の6本だけをWSL用コピーへ反映する。
既存の `scripts/windows/run_daily_pl.cmd` も、この更新後に従来のWSL処理を起動する。
定期タスクの登録内容、時刻、メール設定は変更していない。今回メール送信も行っていない。

Drive未接続時は、記録したハッシュと一致する完全なコピーを使う。
接続中の入力欠損やローカル入力の独自変更を検出した場合は、上書きせず停止する。
元の入力はDriveで編集し、Driveアプリの同期完了後に読み込む。
取得原価台帳は、取引CSV更新時に従来どおり再作成する。

WSLの台帳・時価履歴・レポート出力先はローカルコピー側であり、
Driveへの自動書戻しは行わない。WSLで更新した出力を別端末でも使う場合は、
Drive側との差分を確認して必要なファイルをコピーする。
双方向の自動同期や競合解決は追加していない。

## 確認範囲

- Windows・WSLで移管先を読み、Windowsの計算結果が移管前と同一であることを値なしで確認。
- 実ファイル14本をレポ内から除去した状態で、公開テスト704件が成功。
- インストール済みWindowsコマンドのHTML生成、別ホームのPOSIX環境での初回設定と
  公開サンプル実行、日本語・空白パスも確認。実Macはこの代替確認に含まれない。
- 架空fixture、入力パス設定、Drive未接続・欠損・ローカル変更の検出を検証。
- 住宅比較の実残高は確認できていない。以前挙げた箇所は運用利回りだったため、
  住宅のデータ・コードは変更していない。
- 公開側の反映はユーザー指示の通常のcommit/pushで行う。過去のGit履歴や公開済みコピーの除去は含めない。
