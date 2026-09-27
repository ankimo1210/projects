# market-research

市場データ・マクロ指標・バックテスト・可視化を1つの研究基盤にまとめるプロジェクトです。
工程3bの価格・マクロ・財務データの取得と保存は main に入っています。
CLIで明示取得し、保存した版を通信なしで読めます。工程3cでは保存済みの価格・SEC開示値を使う
市場概要、銘柄・バスケット、スクリーナー、仮想配分・リスク、品質表示の画面を追加中です。
個人口座の連携と旧プロジェクトからの切替は後続です。
[設計仕様](../docs/superpowers/specs/2026-09-27-market-research-design.md)と
[進捗](docs/STATUS.md)を参照してください。

## 起動（WSL、リポジトリルートから）

```bash
uv sync --package market-research --group dev
uv run --no-sync market-research demo --json
uv run --no-sync streamlit run market-research/app/main.py
uv run --no-sync pytest market-research/tests -q
```

画面は「市場概要」「銘柄・バスケット」「シグナル・スクリーナー」「戦略比較」
「マクロと公表」「仮想配分・リスク」「品質・実行履歴」の7つです。
既定の**合成デモ**では7画面で同じ `run_id` を使います。価格・指標・
ポートフォリオは架空データで、閲覧時にネットワークへ接続しません。
デモは架空の足終端から1時間後を判断時刻とし、その時点で利用可能な価格だけを使います。
`demo --json` は同じ run の入力ハッシュと要約を標準出力へ出します。

画面左の「データ」を「保存データ」にすると、保存先は **WSLのパス**で指定し、
完全な価格snapshot IDとタイムゾーン付き基準時刻を選びます。銘柄・バスケットと
シグナル・スクリーナー、仮想配分・リスク、品質・実行履歴の5画面が保存済みデータに接続されます。
年率換算の観測数、手動の構成基準日と条件の閾値を明示します。
比較対象の価格snapshotを選ぶと、同じ通貨・調整方式・セッション日・終値時刻の系列を
基準化して並べます。欠損日は補完しません。
SEC財務snapshotの選択肢にはCIK・開示項目・formを表示します。保存データには企業名の
対応表がないため、対象銘柄とCIKを利用者が照合し、同じCIKを入力した場合だけ財務値を表示します。
保存データモードは研究runを永続保存せず、再現可能なrun IDも発行しません。
戦略比較とマクロ・公表の2画面は未接続と表示します。画面でデータの取得は行いません。

バスケットは現在の構成を過去へ固定した `retrospective` 近似です。
PAFを1とする手動の価格加重で、構成基準日をPAF仮定日として記録します。
公式指数値やPITバックテストではありません。
欠損した構成銘柄は前値で埋めず、その日の水準を空欄にします。
仮想配分は手動ウェイトを全銘柄に入力し、銘柄上限と最低現金比率を検査します。
選択した観測窓に欠損があればリスクを計算せず、揃った価格の標本共分散から
年率ボラティリティと銘柄別寄与を表示します。実口座やFX換算は扱いません。
市場概要は順位と相関を表示し、相関の有効な共通リターン数を別表に示します。
品質画面はsnapshotの出典、欠損・除外と画面内アラートを表示します。
保存runと取得失敗履歴はまだ記録していません。通知の外部送信は行いません。

## 実データの取得・保存

[データ取得ガイド](docs/DATA.md)に、CLI、カレンダー、再開・失敗時の扱いをまとめています。
既定の保存先は WSL の `~/.local/share/market-research`（Git管理外）で、`--data-root` で変更できます。
`prices`・`macro`・`fundamentals`・`releases`・`snapshots` は通信しません。
通信は `fetch-prices`・`fetch-macro`・`fetch-fundamentals` の明示操作だけです。

```bash
uv run --no-sync market-research fetch-prices \
  --provider binance --market CRYPTO --symbol BTCUSDT --provider-symbol BTCUSDT \
  --currency USDT --timezone UTC --adjustment raw --start 2026-09-24 --end 2026-09-25
uv run --no-sync market-research snapshots
```

マクロはALFRED、ESRI GDP、MoF JGB、e-Stat、財務はSEC companyfactsを扱います。
例えば公開データのMoF 10年債利回りは次のように取得します。出力の `snapshot_id` を
`macro --snapshot-id ... --as-of ...` に渡して時点別に読みます。

```bash
uv run --no-sync market-research fetch-macro \
  --provider mof-jgb --tenor-years 10 --start 2026-09-24 --end 2026-09-26
```

ALFREDには `FRED_API_KEY`、e-Statには `ESTAT_APP_ID`、SECには連絡先を含む
`SEC_USER_AGENT` が必要です。入力例と時刻の精度は[データ取得ガイド](docs/DATA.md)を参照してください。

東証 `XTKS`、NYSE `XNYS`、NASDAQ `XNAS` の日足は、`--calendar` を省くと
`exchange-calendars` の取引時間表を自動で使います。明示した `--calendar` を優先します。
その他の市場は確認済みの時間表を指定してください。詳しくは[データ取得ガイド](docs/DATA.md)。

## 実装済みの契約

- 銘柄IDは市場を含みます。価格はUTCの足終端・利用可能時刻・取得時刻と、
  provider・調整方式・revisionを持ちます。
- yfinance形式のスナップショット正規化は、取得時に使ったprovider symbolと、
  各行の確認済み開始・終了時刻および確定状態を明示入力として要求します。
  日付ラベルやタイムゾーンだけから終値の確定時刻を推測しません。`Adj Close` は方式未確認の
  `unknown` として元終値から分離します。未確定足は保持し、時点別読取で理由付き除外します。
- 取得元・期間・銘柄記号・通貨・調整方式・カレンダーを含むmanifestと、SHA256付き入力を保存。
  DuckDBの行とmanifestはtransactionで結び、改定前の版を上書きしません。
- マクロは公表日時以前に値を返さず、後の改定を別の版として保持します。
  ALFREDとSECの日付だけの版は翌NY暦日からの `estimated`、MoFとe-Statは
  取得完了時刻からの `snapshot` として扱い、実測時刻と区別します。
- バックテストは意思決定時の目標ウェイトを1期遅らせる
  close-to-close **研究近似**です。保有中の欠損・非有限値・列の食い違い、
  基準通貨の未指定・異通貨のリターンを拒否します。FX換算そのものは未実装です。
  先頭からその時点までの価格だけを戦略へ渡します。

合成デモの結果は投資助言、実約定の再現、モデル性能の承認を意味しません。
