# market-research

市場データ・マクロ指標・バックテスト・可視化を1つの研究基盤にまとめるプロジェクトです。
価格・マクロ・財務データをCLIで明示取得し、保存した版を通信なしで読めます。
保存済みの価格・SEC開示値を使う市場概要、銘柄・バスケット、スクリーナー、
戦略比較、マクロと公表、仮想配分・リスク、品質表示の7画面を実装しました。
口座向けの一方向exportは明示操作で作れます。口座側の任意読取を追加しましたが、
既存の日次レポートは従来の取得経路を使います。旧stock・market-viz・autostockは
[旧市場索引](../_archive/market/README.md)に退避し、固有機能は旧成果として残しています。
[設計仕様](../docs/superpowers/specs/2026-09-27-market-research-design.md)と
[進捗](docs/STATUS.md)と[工程3初版の受入記録](docs/STAGE3_ACCEPTANCE.md)を参照してください。

## 起動（WSL、リポジトリルートから）

```bash
uv sync --package market-research --group dev
uv run --no-sync market-research demo --json
uv run --no-sync market-research demo --html /tmp/market-research-demo.html --json
uv run --no-sync streamlit run market-research/app/main.py
uv run --no-sync pytest market-research/tests -q
```

画面は「市場概要」「銘柄・バスケット」「シグナル・スクリーナー」「戦略比較」
「マクロと公表」「仮想配分・リスク」「品質・実行履歴」の7つです。
既定の**合成デモ**では7画面で同じ `run_id` を使います。価格・指標・
ポートフォリオは架空データで、閲覧時にネットワークへ接続しません。
デモは架空の足終端から1時間後を判断時刻とし、その時点で利用可能な価格だけを使います。
品質・実行履歴画面から、同じrunの自己完結HTMLレポートをダウンロードできます。
「合成runを永続保存」を押すと、指定したWSLデータルートの runs/ にmanifest・結果・HTMLを不変IDで保存し、再起動後に再読込してハッシュを照合します。Gitのコミットと作業ツリーの変更有無も記録します。
CLI の --html は指定した WSL パスに同じレポートを書き出します。
CLIの --save-run も同じ保存形式を使います。例: uv run --no-sync market-research --data-root /home/kazumasa/.local/share/market-research demo --json --save-run。
`demo --json` は同じ run の入力ハッシュと要約を標準出力へ出します。

画面左の「データ」を「保存データ」にすると、保存先は **WSLのパス**で指定し、
完全な価格snapshot IDとタイムゾーン付き基準時刻を選びます。銘柄・バスケットと
シグナル・スクリーナー、戦略比較、マクロと公表、仮想配分・リスク、品質・実行履歴の7画面が保存済みデータに接続されます。
年率換算の観測数、手動の構成基準日と条件の閾値を明示します。
比較対象の価格snapshotを選ぶと、同じ通貨・調整方式・セッション日・終値時刻の系列を
基準化して並べます。欠損日は補完しません。
SEC財務snapshotの選択肢にはCIK・開示項目・formを表示します。保存データには企業名の
対応表がないため、対象銘柄とCIKを利用者が照合し、同じCIKを入力した場合だけ財務値を表示します。
保存データモードは研究runを永続保存せず、再現可能なrun IDも発行しません。
マクロsnapshotは価格snapshotがない保存先でも閲覧でき、同じ条件の過去snapshotを選ぶと改定差を示します。
改定差は行の単位・頻度・季節調整が一致する場合だけ計算します。
一覧は最新1000件までです。古いsnapshotは左側の「追加snapshot ID」にIDを1行ずつ入力すると選べます（最大20件）。
未完了・基準時刻より未来・読取不能なsnapshotは追加できません。
ESRIの公表calendarは保存時点で既知だった予定として表示します。戦略比較は、同一銘柄について実際に判断時点ごとに保存した複数のPIT snapshotを明示選択した場合だけ計算します。zero / mean / ridge / tree / buy-and-hold を同じlag1と費用で比較し、後日一括取得した履歴から過去の観測版を捏造しません。
画面でデータの取得は行いません。

バスケットは現在の構成を過去へ固定した `retrospective` 近似です。
PAFを1とする手動の価格加重で、構成基準日をPAF仮定日として記録します。
既定は公式指数値やPITバックテストではありません。比較対象を公式指数として指定する場合は出典を手動で記録し、通貨・調整方式・日付・終値時刻・品質・snapshot観測時刻を照合します。出典の真正性と過去の指数構成は自動確認できません。
欠損した構成銘柄は前値で埋めず、その日の水準を空欄にします。
仮想配分は手動ウェイトを全銘柄に入力し、銘柄上限と最低現金比率を検査します。
選択した観測窓に欠損があればリスクを計算せず、揃った価格の標本共分散から
年率ボラティリティと銘柄別寄与を表示します。USDとJPYを混ぜる場合は追加価格snapshotとJPY=Xの保存済みFX snapshot、UTC評価時刻・FX鮮度上限を明示して円換算します。これはretrospectiveの仮想配分で、実口座やPIT成績ではありません。
市場概要は順位と相関を表示し、相関の有効な共通リターン数を別表に示します。
品質画面はsnapshotの出典、欠損・除外と画面内アラートを表示します。
合成デモrunは明示操作で保存できます。保存データモードの研究runと取得失敗履歴はまだ永続記録していません。通知の外部送信は行いません。

## 口座側へ価格・FXを渡す（明示操作）

保存済みの確定・品質合格・raw の日足snapshotを、通信なしで
不変の prices.parquet と manifest.json に書き出します。
株価は --snapshot-id を繰り返し、USD/JPY の保存済みsnapshotは
--fx-snapshot-id で指定します。時刻はタイムゾーン付きで指定してください。

~~~bash
uv run --no-sync market-research --data-root /home/kazumasa/.local/share/market-research \
  export-portfolio --snapshot-id PRICE_SNAPSHOT_ID \
  --fx-snapshot-id FX_SNAPSHOT_ID \
  --as-of 2026-09-26T00:00:00+00:00
~~~

既定の出力先は --data-root の下の exports/EXPORT_ID/（Git管理外）です。
別の場所を使う場合だけ --destination に **WSLのパス**を指定します。
manifestには契約版、元snapshot ID、基準時刻、ParquetのSHA-256を記録します。
口座番号、保有数量、取引、損益は出力しません。
[portfolio-analyzer側の任意読取](../portfolio-analyzer/README.md#市場価格exportの任意読取)では
版・ハッシュ・時刻と価格・FXそれぞれの鮮度を検査します。定時タスクと現行の日次取得経路は
このexportを自動では使用しません。

## 研究ノート

[不動産市場の国際比較・地価調査](docs/REAL_ESTATE_BENCHMARK.md)では、福岡・東京と海外都市の公的系列、原本の配置、再計算方法、比較の限界をまとめています。
[国内住宅NOIのHTML](docs/data/validation/japan_noi_valuation_2026-09-30.html)は、住宅J-REITの実収支を使い、都市別のNOI利回りと融資・修繕積立・出口価格の感応度を確認できます。
[3社・通年NOI比較のHTML](docs/data/validation/japan_noi_comparison_2026-10-01.html)は、531住宅の実績12か月、28取得案件の鑑定予想NOI、NY・Londonの参考値を区別して表示します。社別比較・全物件検索・融資と出口の操作を含みます。

[合成デモの5本のノート](notebooks/README.md)は取得済みデータの来歴、
PIT信号、同条件の戦略比較、retrospective仮想リスク、HTML出力を共通APIで再実行します。
各ノートは独立に動き、保存済みセル出力はありません。HTMLノートは同一合成runを描画し、
戦略比較ノートと仮想リスクノートの結果を単一レポートへ再掲する機能ではありません。

## Mag7 固定例（工程3c）

`market_research.examples.autostock.run_mag7_example` は、保存済みの米国株7銘柄の
各判断時点に観測済みの日足snapshotを入力に、旧 autostock の126期モメンタム順位、
銘柄上限0.5、総上限1.0、費用5bpsを再現する研究例です。戦略には各時点までの価格だけを渡し、
目標ウェイトを1期ずらして評価します。lockbox以降の判断とリターンは除きます。
現在の検証は合成データです。旧戦略の完全データでの配分値とは一致しました。
旧エンジンは任意の戦略へ全期間の価格を渡すため、エンジン全体の先読み防止を証明したものではありません。
旧 autostock の一括取得Parquetからは、過去に実際に観測可能だった
価格の版を復元できないため、過去の成績をPITで再現したとは扱いません。
固定例はライブラリとテストから使えます。専用CLI・画面は設けていません。
[旧 autostock](../_archive/market/autostock/README.md) は成果として退避しました。

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
  基準通貨の未指定・異通貨のリターンを拒否します。保存済みraw日足の明示評価時刻でのUSD→JPY換算は仮想リスク向けに実装済みです。live FXやPIT成績への一般化はしていません。
  先頭からその時点までの価格だけを戦略へ渡します。

合成デモの結果は投資助言、実約定の再現、モデル性能の承認を意味しません。
