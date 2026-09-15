# portfolio-analyzer: 全口座合計の NAV／累計損益と日次リスクモニター — 設計

日付: 2026-09-15 · 対象: `portfolio-analyzer`（日次レポート `scripts/daily_pl_report.py`、`dashboard.py`、`mailer.py`）

## 1. 背景と目的

- 日次レポートの NAV・累計損益・日次損益・期間損益・開設来損益・損益の内訳は、IBKR の取引履歴を日次再生できる海外口座だけで計算している。国内口座の取引 CSV（入金 5 件・売買・配当を全部含み、開設からの現金再生がスナップショットと 1 円の差もなく一致）と DC の掛金履歴（基準点＋月次掛金）は 2026-09-13 に入ったが、銘柄カードにしか使っていない。**→ 3 口座合計にする。**
- リスクは、メインのダッシュボード（`core.py`）に集中度・ファクター型ストレス・逆ストレス・週次 ES／DD・株債相関・セクター／発行体ルックスルーがあるが、**国別・通貨のルックスルーは無く、日次レポートとメールにはリスク項目が一切ない。** → 日次で動くリスクセクションを日次レポートとメールに載せる（本人の選択: 表示先＝日次レポート＋メール、ルックスルー元データ＝既存参照ファイルに手で追加、合計化の範囲＝時系列・KPI・内訳表まで）。

## 2. A. 全口座合計の NAV／損益

### 2.1 口座ごとの日次系列（`timeseries.AccountSeries`）

| フィールド | 海外（IBKR） | 国内（`jpbroker`） | DC（`dcplan`） |
|---|---|---|---|
| `nav` | 既存 `value_paths.nav`（現金＋評価） | 現金（受渡日基準で受渡金額を累積）＋ Σ数量×終値 | 口数×基準価額 |
| `deposits_cum` | `paths.deposits_cum` | `入金(振込)` の累積 | 拠出金累計（基準点を掛金履歴で前後に歩かせた原価） |
| `pnl` | `nav − deposits_cum` | 同左 | 同左（＝含み損益） |
| `unrealized` | Σ(評価 − 原価) | Σ(評価 − 原価)。原価は受渡金額ベース（手数料込み） | `pnl` と同じ |
| `realized_cum` | 既存 | 売却の実現損益累積（平均法、手数料込み原価） | 0 |
| `dividends_cum` | 既存 | `入金(配当)`・`入金(分配)` の累積 | 0 |
| `fees_cum` / `fx_translation_cum` / `forex_cum` | 既存 | 0（手数料は原価に含む、と注記） | 0 |
| `xirr_flows` | 入金フロー | 入金フロー | None（履歴前の掛金日付が不明） |
| 未定義 | なし | なし（CSV 開始前は現金 0・数量 0） | 掛金履歴の最初の約定日（2025-08-26）より前は `None` |

恒等式（口座ごと、各日）: `pnl = unrealized + realized_cum + dividends_cum + fees_cum + fx_translation_cum + forex_cum`。国内は `現金 = 入金 − 買い受渡 + 売り受渡 + 配当` なので `NAV − 入金 = (評価 − 保有原価) + (売却代金 − 売却原価) + 配当` で成立する。テストで各日の恒等式を検証する。

`timeseries.combine(series) -> AccountSeries`: 要素ごとの和。どれかが `None` の日は `None`。

### 2.2 ペイロードの変更（`daily_pl_report.py`）

- `series.nav / pnl / deposits / daily_pnl` → 合計。`series.accounts = {id: {nav, pnl}}` を追加（口座別の線は今回は描かない。データだけ）。
- `headline.pnl_window`（`pnl[-1] − pnl[wi]`、`pnl[wi]` が `None` なら最初に定義された日を使い注記）、`pnl_incept`（＝合計 `pnl[-1]`）、`realized_cum`、`dividends_net`、`max_dd_window`（合計 `pnl` と `nav` で計算）→ 合計。
- `headline.xirr` → 海外＋国内の入金フローと両口座の NAV で計算。`headline.xirr_scope = "海外＋国内（DC 除く）"` を追加し表示に使う。
- `attribution = {window, incept, accounts: {id: {window, incept}}}`。キーは既存 7 つのまま。
- 履歴レコードに `total_pnl_incept_jpy`、`deposits_cum_jpy` を追加。
- 注記に「累計損益は 3 口座の NAV − 累計入金。国内の手数料は取得原価に含む。DC は掛金履歴の始まる 2025-08-26 から（それ以前の掛金は拠出金累計に含む）」。

### 2.3 表示（`dashboard.py`・`mailer.py`）

- 「海外証券口座 NAV と損益」「日次損益 海外証券口座」「期間損益 海外証券口座…」「損益の内訳 海外証券口座」の見出し・キャプションを「全口座」に変える。
- 損益の内訳の表に、合計の下へ口座別の行（海外／国内／DC の期間内・開設来）を足す。
- 資金加重リターンの枠に `xirr_scope` を出す。
- 既存テストの「海外証券口座」を前提にした断言を更新する。

## 3. B. 日次リスクモニター

### 3.1 実務の型（調査結果の要約）

日次のリスクレポートは (1) ルックスルーのエクスポージャー（資産クラス・通貨・国／地域・セクター・銘柄の重複合算）、(2) 集中度と限度、(3) リスク量（ボラ・VaR／ES・ベータ）、(4) リスク寄与（評価額比率とは別物）、(5) ストレス（仮想＋過去エピソード）、(6) 日次の推移、で構成される。出典: Sharesight exposure report、CME「Currency Risk in Equity Portfolios」、justETF、AnalystPrep／Ryan O'Connell（component・marginal VaR）、Portfolio Optimization Book §11.3、PanAgora（JOIM）。

### 3.2 データ（`data/analysis_reference.private.json` への手追加）

- 発行体 46 件の `issuer` エクスポージャーに `country` を足す（日本・米国・台湾・オランダ）。
- 商品ごとに `country_default`（発行体で覆えない残りの国。SMH／QQQ／XLE＝米国、1329／1475／2561／個別株＝日本）、必要なら `currency_mix`・`country_mix`。
- DC（ハッピーエイジング40、2026-08-31 月次レポート）: 国内債券 32.83・大型バリュー 15.64・小型 15.60・外国債券(ヘッジなし) 14.98・TCW 外国株式 13.97・MSCI Emerging 4.98・コール等 2.00。
  `currency_mix = {JPY 0.6607, USD 0.1652, その他外貨 0.1741}`、`country_mix = {日本 0.6607, 米国 0.1652, 欧州 0.0879, 新興国 0.0498, その他先進国 0.0364}`（外国株式は米 70／欧 20／他 10、外国債券は米 45／欧 40／他 15 で按分した**推定**、と注記）。
- `policy.limits` に暫定 3 件を追加: `foreign_currency_max`（外貨エクスポージャー ≤ 40%）、`foreign_country_max`（海外の単一国 ≤ 30%）、`lookthrough_issuer_max`（ルックスルー後の単一銘柄 ≤ 15%）。既存と同じく `status: draft`。
- `episodes`（価格で再現する過去局面）: `yen_carry_unwind_2024`（2024-07-31→08-05）、`ai_capex_digestion_2024`（2024-07-10→10-31）、`tariff_shock_2025`（2025-04-02→04-08）。価格履歴に無い 2022／2020／2018 は既存のファクター換算シナリオ（`kind: historical`）で出す。

### 3.3 計算（新モジュール `src/portfolio_analyzer/risk.py`、純 Python・float）

入力: 当日の保有（`mtm.Row` から symbol／口座／評価額／通貨／資産クラス／ticker）、参照ファイル、日次の円建て収益率行列（既にダウンロードしている 2 年分の終値 × USD/JPY。ベンチマーク `1306.T`・`SPY` を追加取得）、ポリシー限度。

| 出力 | 定義 |
|---|---|
| `exposures.asset_class / currency / country / sector` | ルックスルー後の円額と比率。商品の `exposures` を評価額に掛けて集計。通貨は `currency_mix`（既定＝建値通貨 100%）、国は発行体の `country`＋残りは `country_default`。現金は 現金等／JPY／日本 |
| `exposures.issuers` | 発行体を商品横断で合算（例: アドバンテスト＝6857 直接＋1329・1475 経由）。上位 15 と経由商品 |
| `concentration` | `largest_position_ratio`、`top5_ratio`、実効数（1/HHI: 銘柄・セクター・通貨・国）、`largest_issuer_lookthrough_ratio`、`foreign_currency_ratio`、`largest_foreign_country_ratio`、`max_sector_ratio`、`cash_ratio` |
| `stats` | 直近 252 営業日、現在ウェイト固定の日次円建て収益率から: 年率ボラ、過去シミュレーション VaR（1 日 95／99%）、ES 97.5%、20 日 VaR（√20 換算と明記）、最悪日、ベータ（対 TOPIX＝1306.T 現地通貨、対 S&P500＝SPY 現地通貨、対 USD/JPY。単回帰） |
| `contributions` | 同じ窓の共分散で `RC_i = w_i (Σw)_i / (wᵀΣw)`（合計 1）。通貨・セクター・国へは各商品のルックスルー比率で按分。銘柄別に単独ボラも |
| `stress.scenarios` | 参照ファイルの全シナリオ（単一・複合・historical）を `Σ 評価額 × factor_loading × shock` で換算（`core.py` と同じ式） |
| `stress.episodes` | 参照ファイルの `episodes` を、現在ウェイトで実際の商品収益率を掛けて再現（開始日直前終値→終了日終値）。価格履歴が届かないものは出さない |
| `policy` | 既存 6＋新規 3 の限度を評価（`<=`／`>=`）。値・状態（ok／breach／na）を返す |
| `prev` | 履歴の前日レコードの `risk` から、ボラ・VaR・外貨比率などの前日比 |

価格のダウンロード開始日は `min(today − history_days, 最古エピソード開始 − 7 日)` にする。IBKR・国内・DC の再生は開始が早まっても壊れない（取引前は 0／None）。

### 3.4 表示

- 日次レポートとメールの両方に「リスク」セクション（順序: KPI → 口座別 → 資産配分 → **リスク** → 損益の内訳 → 保有 → …）。
  1. 限度の状態（超過があれば先頭で赤字）
  2. エクスポージャー 4 本（資産クラス・通貨・国・セクター）— メールは `emailchart.shares`、ダッシュボードは CSS バー
  3. ルックスルー上位銘柄（経由商品つき）
  4. リスク量（ボラ・VaR・ES・ベータ、前日比）
  5. リスク寄与（銘柄上位・通貨・セクター・国。評価額比率と並べる）
  6. ストレス（仮想シナリオ・過去エピソードの円額と比率、`hbars`）
- 履歴レコードに `risk` ブロック（ボラ・VaR・ES・外貨比率・単一銘柄ルックスルー比率・最大セクター比率・ベータ 3 つ・超過数）。

### 3.5 テスト

- `test_timeseries.py`: `combine` の None 伝播。`test_jpbroker.py`: `account_paths` の現金再生＝入金−買＋売＋配当、各日の恒等式、CSV 前は 0。`test_dcplan.py`: `account_paths` の None 区間・掛金＝入金。
- `test_risk.py`: ルックスルーの合計＝評価額、発行体の商品横断合算、通貨 mix の既定、寄与度の合計＝1、VaR の符号と分位、ベータ（人工データで既知の傾き）、シナリオ換算、エピソード再現、限度の演算子。
- `test_daily_pl_report.py`: 開始日の前倒し。`test_dashboard.py`／`test_mailer.py`: リスクセクションの文言と全口座ラベル、内訳表の口座別行。
- README: 合計化の定義とリスクの定義（各指標の窓・方法・限界）。

## 4. やらないこと

- 運用会社の構成銘柄ファイルの日次取得（本人が「手で追加」を選択）。
- メインのダッシュボード（`core.py`）への国・通貨の追加（共通モジュールなので後から可能）。
- 多変量回帰のファクター分解（単回帰ベータと既存のファクター係数で足りる）。
- 20 日 VaR の重複窓推定（√20 換算で出し、注記する）。
