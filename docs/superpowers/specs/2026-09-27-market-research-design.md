# market-research 統合仕様

更新: 2026-09-27。工程2の設計。製品コード・workspace メンバーはまだ作成していない。
調査基準: main `dd18befe`。[整理計画](../plans/2026-09-27-workspace-cleanup.md) の工程2に対応。
名称・入口・残す機能は本人から判断を委任された。個人口座は独立、旧入口の一斉切替は可、退避は候補ごとの確認を維持する。

## 1. 決定と完了条件

新プロジェクト名・CLI 名は **market-research**、Python import は **market_research**。
最初の入口は **Streamlit + Plotly のローカルアプリ**。同じサービス層を CLI と Jupyter から使い、
結果は共通テンプレートの自己完結 HTML に書き出す。常時サーバー、Next.js、FastAPI は初版に追加しない。
理由は、既存の探索画面と Python 分析コードをまとめ、取得・計算・表示の重複を最小限で解消できるため。

| 比較した案 | 利点 | 費用・制約 | 判断 |
|---|---|---|---|
| Streamlit + 共通 Python サービス | 既存 market-viz の6画面を基にでき、CLI/ノートと計算を共有 | 高度なフロント表現と同時利用に制約 | 採用。1人のローカル研究に合わせる |
| Dash に集約 | stock の8画面を直接使いやすい | callback と研究コードを切り分け、マクロ画面を増築する必要 | 表示内容は移すがフレームワークは採用しない |
| Next.js + FastAPI | UI の自由度、後日の分離が容易 | API・認証・2種類の実行環境が増える | 今回は非採用。必要が具体化したら再判断 |

工程2の完了は、旧機能の行き先、正本にする実装、データ契約、受入テストが下表で対応すること。
工程3の完了は、そのテストが通り、代表操作が新入口で動き、未移行機能と旧データの扱いが明示されること。
設計への採用は、現行の実装を無検証で正しいと認定する意味ではない。

## 2. 機能の行き先

「初版」は工程3の切替条件。「後続」は旧プロジェクトを退避する前に移行するか、個別に非採用を確定する。
この分類だけで旧ファイルやデータを削除しない。

| ID | 旧機能・採用元 | 新しい行き先 | 初版の判断・検証 |
|---|---|---|---|
| F01 | stock / quantkit の日米株・ETF・FX、yfinance・Stooq・J-Quants | data/providers、銘柄画面 | 採用。価格調整・通貨・日付・来歴を Q01–Q05 で照合 |
| F02 | market-viz の ccxt イントラデイ、quantkit の Binance | crypto provider、銘柄画面 | 日足は採用。イントラデイは後続。終端が開いた足を Q03 で拒否 |
| F03 | stock の財務・スクリーナー・テクニカル | research/fundamentals、銘柄・シグナル画面 | 採用。指標定義と欠損、開示日時を照合。未取得項目は空欄 |
| F04 | stock の N225 / 米株バスケットとウェイト比較 | research/baskets、銘柄画面 | 採用。構成銘柄の基準日を表示。現構成銘柄の遡及適用は PIT バックテストから除外 |
| F05 | quantkit の OHLCV品質・キャッシュ・FX換算 | data と storage | 採用元。Q01–Q05 を満たすよう契約を強化 |
| F06 | macrokit の ALFRED、ESRI GDP、MoF JGB、カタログ・snapshot・PIT | macro、マクロ画面 | 採用。Q06–Q08。実測公表日時と推定規則を区別 |
| F07 | quantkit の e-Stat / BLS / BEA / Census / BoJ / MoF / EDINET・SEC | provider 拡張、開示データ | SEC 財務・e-Stat は初版。ほかは後続、既存 fixture とキー付き疎通を別評価。EDINET の discovery を財務抽出済みと扱わない |
| F08 | stock / market-viz / quantkit のバックテスト | research/backtest、比較画面 | quantkit を骨格に単一化。旧2エンジンは比較用のみ。Q09–Q11 |
| F09 | quantkit の features / signals / labels、walk-forward・purge・embargo | research、シグナル・比較画面 | 基本信号と baseline / linear / tree を初版採用。未来ラベルの隔離、prefix 不変性を Q11 で検証 |
| F10 | quantkit の高度モデル、CPCV、MDA、ensemble、Chronos | research の追加モジュール、ノート | 後続。任意依存へ隔離し、初版の起動・取得に torch を要求しない |
| F11 | stock / quantkit の仮想配分・最適化・リスク分解 | research/portfolio、リスク画面 | 仮想ウェイトだけ初版採用。実口座の取込・税額確定・損益台帳は対象外 |
| F12 | quantkit の税/NISA シミュレーション | 明示した仮定による研究ノート | 後続。近似を実口座の税務計算に使わない |
| F13 | market-viz の相関・z-score・DD・ランキング・アラート | 市場概要、シグナル、品質・通知画面 | 採用。アラートはアプリ内表示。外部送信・定時実行は追加しない |
| F14 | quantkit の tearsheet・比較ダッシュボード、Jupyter 01–16 | reports と新 notebooks | 初版は取得→信号→比較→リスク→HTML の5本。高度モデルのノートは対応機能と共に後続へ |
| F15 | autostock の Mag7 探索ループ | examples/autostock、固定した研究 run | 初版は比較可能な再現例。探索を自動で起動しない。全期間入力の隔離を Q11 で確認 |
| F16 | stock の Claude AI チャット・コード実行 | 初版に移さない | 有料 API とコード実行の運用が別途必要。手動分析と明示した CLI を優先。旧機能を削除する判断は退避時 |
| F17 | market-viz の FastAPI・Next.js scaffold | 初版に移さない | 外部 API 互換は維持しない。CLI / ファイル契約を連携境界にする |
| F18 | portfolio-analyzer の口座分析・日次レポート | 現行プロジェクトに保持 | 価格・FX の読取アダプターだけ後続で追加。Q12、日次の既存起動パス維持 |
| F19 | JHRMBS / timesfm_lab / labor_ai_quadrant / rates-ui-lab | 独立したまま参照 | 初版の移動・import 依存化は対象外 |

## 3. 画面と利用の流れ

ローカルに既存データがない初回も、明示的に選んだ合成 demo データで閲覧できる。
demo・実データ・未検証ソースを画面上で区別する。取得ボタン以外の表示操作でネットワークを呼ばない。

| 画面 | 操作・表示 | 旧画面の整理 |
|---|---|---|
| 市場概要 | watchlist、価格変化、volatility、drawdown、相関、取得日時 | market-viz dashboard + correlation |
| 銘柄・バスケット | 個別価格・財務・テクニカル、指数比較、通貨と価格調整の選択 | stock ticker + N225 + 米株 basket、chart workbench |
| シグナル・スクリーナー | 指標条件、横断順位、欠損・対象銘柄・基準日時 | stock screener + market-viz ranking |
| 戦略比較 | 期間・コスト・信号設定、baseline、OOS equity/DD、run の保存 | 3つのバックテスト入口を1つに |
| マクロと公表 | as-of日時、最新値と改定差、公表calendar、GDP/JGBイベント | macrokit CLI + quantkit macro notebooks |
| 仮想配分・リスク | 仮想ウェイト、制約、リスク寄与、FX換算 | 研究用 portfolio 機能。実口座画面は別 |
| 品質・実行履歴 | 品質フラグ、取得失敗、保存run、アプリ内alert、HTML export | data update + alert monitor |

共通選択は universe、通貨、期間、as-of、provider、価格調整方式。
同じ run_id を CLI / notebook / UI で読み、再描画時に計算条件を暗黙に変更しない。

## 4. 正本となる実装と配置

以下の配置は工程3で作る設計上のパス（現時点では未作成）。

```text
market-research/
  src/market_research/
    contracts/       # PriceBatch, MacroObservation, ResearchRun
    data/providers/  # 外部取得・正規化
    storage/         # DuckDB、raw snapshot、versioned export
    macro/           # 公表時点・改定・イベント
    research/        # features/signals/backtest/portfolio/risk
    services/        # UI/CLI/notebook共通のユースケース
    reports/         # Plotly + 共通HTMLテンプレート
    cli.py
  app/               # Streamlitの薄い画面
  configs/           # 非秘密のカタログ・universe・設定
  notebooks/         # 共通サービスを呼ぶ探索例
  tests/fixtures/    # 小さな合成・許諾済み入力
```

| 正本にする層 | 採用元 | 引き継ぐもの / 変更点 |
|---|---|---|
| 取得器の共通 IF・診断 | [quantkit data/base](../../../quantkit/src/quantkit/data/base.py)、[quality](../../../quantkit/src/quantkit/data/quality.py) | FetchResult の data/quality/meta 分離。cache key に provider・adjustment・頻度・通貨・契約版を追加 |
| J-Quants / yfinance / Stooq | [quantkit connectors](../../../quantkit/src/quantkit/data/connectors/) | 新契約に正規化。[stock providers](../../../stock/src/stockkit/data/providers/) の銘柄対応・財務は差分テストで補完 |
| crypto | [market-viz loaders](../../../market-viz/src/market_viz/data/loaders.py) と quantkit Binance | provider は別ID。二つの価格を黙って継ぎ足さない |
| PIT・snapshot | [macrokit pit](../../../macrokit/src/macrokit/pit.py)、[store](../../../macrokit/src/macrokit/store.py)、[snapshot](../../../macrokit/src/macrokit/snapshot.py) | timezone-aware 公表時刻と vintage_kind を採用。quantkit の DataFrame IF は薄い読取変換へ |
| 研究評価 | [quantkit backtest](../../../quantkit/src/quantkit/backtest/engine.py)、[split](../../../quantkit/src/quantkit/backtest/split.py) | 単一の評価エンジン。欠損・コスト・約定基準・lag を追加契約で固定 |
| 可視化・HTML | [quantkit visualization](../../../quantkit/src/quantkit/visualization/)、[共通テンプレート](../../templates/claude-report/README.md) | レポートの token を共通化。UI は market-viz の操作を参照 |

実装を移植してテストを添える。新プロジェクトが旧4パッケージを永続的に import する構成にしない。
旧実装は移行時の比較対象として残す。データ DB の現物は今回読まず、移行も行っていない。

## 5. データ契約 v1

### 5.1 価格・品質・時刻

価格は資産1単位当たりの `currency` 建て価格、volume はソースの単位を別フィールドで記す。
`instrument_id` は市場を含む安定ID、元の symbol / provider_symbol を保持する。
UTC の `bar_start` / `bar_end` / `available_at` / `observed_at` と、市場の timezone / session_date を分ける。
日付だけの値を UTC 午前0時として「公表済み」と判定しない。

主キーは `(instrument_id, provider, interval, bar_end, adjustment, revision_id)`。
raw OHLC と調整済み価格を別に保持し、`adjustment = raw / split / total_return / unknown` を明示。
`adj_close` がないとき raw をコピーして調整済みと偽装しない。J-Quants と yfinance の調整方式を等価と決めつけない。
provider の違う行を同じキャッシュキーへ上書きしない。fallback は run に記録して別系列で比較する。

品質は `ok / warn / reject` と理由、適用ルールの版、原行への参照を保存。
重複・欠損・非正価格・桁異常・未確定足・stale を明示し、暗黙の前埋めをしない。
警告を消すだけの修正や、全欠損をゼロリターンに変える処理は禁止。

[clean_closes](../../../portfolio-analyzer/scripts/daily_pl_report.py) は後続5観測で価格が元の水準へ戻るかを調べる。
したがって、このアルゴリズムは **後日訂正用**。新しいデータ基盤では次を分ける。

- 当時のスナップショット: 当時利用可能な観測だけで判定。疑わしい価格は理由付き quarantine とし、先の価格を見ない。
- 後日訂正: 旧行を残し `supersedes` と `available_at` を追加した別revision。表示は最新訂正を選べる。
- バックテスト: 各判断時刻の `available_at <= decision_at` を満たす版だけを使う。
  後日訂正を全期間へ適用した比較は別モード・別runにし、PIT成績と呼ばない。

[bar_is_final](../../../portfolio-analyzer/src/portfolio_analyzer/mtm.py) の取引中の足を確定終値にしない規則を継承する。
現実装の時刻判定をそのまま一般化せず、休日・短縮取引・DST を fixture で扱う。
現在の FX は live 評価を許す設計なので、FX quote に `live_quote` を明記し、確定日足の `final` と区別する。

### 5.2 マクロ・財務・取得失敗

マクロは `(indicator, period_start, source, release_at, vintage_id)` を識別子とし、
値・単位・季調・頻度・公表時刻の精度・取得時刻・raw hash・`vintage_kind` を保存する。
`as_of` は timezone-aware 日時必須。公表前は存在しない行として返し、`latest` は独立APIにする。
公表日だけしか分からない場合は保守的な利用可能時刻と精度を記録し、推定日時を実測と混ぜない。
追加・訂正は追記し、同時刻の競合は解決ルールがない限りエラー。seq=1 を「真の初回公表」と解釈しない。

[macrokit の既知の制約](../../../macrokit/docs/known-limitations.md) を引き継ぐ際に、
年末年始の営業日、未取得の改定、途中までの取得から作った期待値を初版の品質ゲートにする。
公表スケジュールの推測は実測確認まで参考表示。部分取込runから期待値を確定保存しない。
財務も対象決算期と filing/publication 時刻を分離し、公表前の特徴量には使わない。

取得失敗は 401/403、429、5xx、空応答、schema不一致を区別。credential をログ・例外・manifestへ入れない。
429は Retry-After、再試行は上限付き、schema不一致は自動再試行しない。
古いキャッシュを使う場合は使用日時と stale を画面・runの両方へ残し、成功した新規取得と同一扱いにしない。

### 5.3 バックテスト・研究run

初版の標準は、**前の終値までの情報から決めたウェイトを、次の close-to-close 区間へ1回だけ lag して適用**する
ベクトル型の研究近似。実際の翌日始値での約定を再現したとは呼ばない。
next-open モードは後続とし、その場合は open-to-next-open の保有区間・signal時刻・コストを別契約で定義する。
stock は損益が close-to-close、取引ログが open、market-viz は open系列の変化率を使うため、
旧3実装の数字が一律に一致することを受入条件にしない。差分理由と新契約の手計算値を正本にする。

- weights は未lagの target のみを入力。engine が `lag=1` を適用。二重lagは Q09 で検出。
- コスト: `sum(abs(held_t - held_prev)) * (commission_bps + slippage_bps) / 10000`。
  初回建玉・売却・反転を含む。cash return と借入費は明示した設定のみ。
- 保有額が非ゼロで return が欠ける行は既定で失敗。無保有なら欠損を成績へ混入させない。
  データ列の交差集合へ黙って落として保有銘柄を消さない。
- annualization / risk_free / dd / Sharpe / 初期資産の定義をrunへ記録。約定表は近似の前提を明記。
- run は config、code commit、schema版、入力manifest hash、seed、期間分割、コスト、品質、失敗理由を保持。
  test/lockbox を strategy callback の入力から分離し、各時点で渡す prefix を限定する。

## 6. 個人口座との連携と配置

portfolio-analyzer は別プロジェクトのまま。同アプリだけが保有・取引・口座情報を読む。
新基盤から渡すのは価格・FX・品質・来歴の versioned export（Parquet + JSON manifest）。
個別銘柄の選択も分析設定になり得るため、連携用watchlist・exportは Git 管理外に置く。
初版では相互import・共有DB・既存日次処理の置換をしない。

live DB / cache は WSL の Git 管理外領域、研究runは immutable ID で保持。
重い保存成果物は [成果物保管 ADR](../../decisions/0004-artifact-storage-and-evidence.md) に従う。
依存追加・sync後は portfolio-analyzer のローカル生成を **メール送信なし**で検証する。
Windows 定時タスクや既存起動パスを変更せず、永続データはcopy→検証→明示切替の順に扱う。

## 7. 受入テストと切替手順

| ID | 固定する入力・条件 | 期待結果 |
|---|---|---|
| Q01 | 4/5桁JPコード、米株、FX、同名symbolの異なる市場、MultiIndex列 | 安定IDと原symbolを保持。異なる市場を混同しない |
| Q02 | split/配当、調整列欠落、同symbolでproviderを変える | 調整方式が明示され、cacheを共有上書きしない。既知でない調整を捏造しない |
| Q03 | JST/NY、DST、休場・短縮取引、開いたcrypto足、live FX | 利用可能時刻前の確定値を返さない。FX liveを日足finalにしない |
| Q04 | 欠損・重複・列違い・価格が一時1/10、後続値を差し替え | 取得時点版のprefixが変わらず、後日訂正だけが新revisionになる |
| Q05 | timeout/401/429/空応答/stale cache | bounded retry、エラー分類、ログのsecret非露出、stale表示 |
| Q06 | 公表直前/同時/直後、過去期改定、naive datetime | as_of境界が一致。未来改定を除外、naive拒否 |
| Q07 | vintageの重複・競合・狭い取得窓・中断後再開 | 冪等性、競合検出、coverage不足の明示。seqを初報と誤認しない |
| Q08 | January/December公表、JST/UTCホスト、GDP部分取込 | 正しい市場日か未確定表示。部分取込から期待値を確定しない |
| Q09 | 3〜5日の手計算価格、初回建玉・exit・反転、既知の信号 | lag1回・費用・equityが手計算値に一致。浮動小数の許容誤差は fixture に固定 |
| Q10 | 保有銘柄だけの欠損、空入力、列の欠落、raw/adjusted混在 | 既定で明確に拒否。都合のよい成績を出さない |
| Q11 | 未来価格・ラベルを攪乱、purge/embargo境界、lockbox封印 | その時点の予測/ウェイトは不変、訓練と評価が重ならない |
| Q12 | 合成価格exportと口座側adapter、schema違い、古いFX | 契約版/品質を確認。市場側へ口座情報を出さず、既存日次は従来経路で動く |
| Q13 | demo起動→銘柄→比較→HTML、再起動、オフライン、取得失敗 | 7画面の基本操作、同run再現、明示した取得以外に通信しない |

実装順は、契約とfixture → 取得/保存/PIT → baselineとバックテスト → 7画面とHTML → 連携export → 切替。
各段階で旧実装の該当testsを移植・強化する。市場APIの契約変更は小さいlive疎通を別に行い、fixture成功と区別する。

切替前にF01–F19の採否表へ実装先・テスト・残件を追記し、初版採用機能が全て通ることを確認。
旧データはread-onlyの取り込み元としてschema・件数・範囲・欠損・hashを比較し、元のDBを上書きしない。
起動入口は受入後に一斉切替可能だが、旧プロジェクトの退避は引き続き個別確認。

## 8. 実装前に明示する影響

新workspaceメンバーと上記の新契約を追加する。旧API互換のshimは作らない。
初版依存は既存の pandas / numpy / scipy / DuckDB / PyArrow / requests / httpx / PyYAML /
pydantic / Click / Streamlit / Plotly / yfinance / ccxt / Jinja2 を候補とし、移植するコードがimportするものだけ宣言する。
新しいproduction依存が必要になれば具体的な差分で確認し、ここでは追加しない。

まだ実施していないもの: 実装・データ移管・外部API疎通・全suite再実行・UI操作・個別退避。
