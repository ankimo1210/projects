# AIバブル定量リサーチ実行計画

> **For agentic workers:** 実行時は `superpowers:executing-plans`（インライン）または `superpowers:subagent-driven-development` を用い、Task ごとに検証する。各 Task の見出しは `Task N` 形式（実行スクリプトが brief を抜き出すため）。

**Goal:** AI関連株の価格が要求する成長、投資・資金の持続性、過熱の証拠を検証し、保有資産への条件付き影響を返す。

**Architecture:** 公開の市場研究を独立した入力・出力として作り、既存の保有とETF分解へ読取で接続する。現在の評価、急騰と崩落の基底率（記述）、予測性能の検証を別の段階にする。

**Tech Stack:** Python 3.12以上、標準ライブラリ、既に宣言済みのDuckDB、pytest、ruff。統計計算の追加依存は必要性を確認してから提案する。

**Spec:** [研究仕様](../../2026-10-21-ai-bubble-research-design.md)。問い、時点、定義、品質、欠損、非公開情報、保存上限は同文書を正とする。

作成日: 2026-10-21。改訂: 同日（2回目のレビューを反映し、Task 形式へ組み直し）。状態: **Task 1 着手**。

## Global Constraints

- 作業対象は `portfolio-analyzer`。既存の日次レポート・メール・定時タスクを変更しない。
- 新規の本番依存、有料契約、公開APIの変更、外部送信・公開は事前の明示承認なしに行わない。外部取得の User-Agent に利用者のメールアドレスを入れない。
- 既存の私有入力は読取専用。研究データは `/home/kazumasa/projects/_data/portfolio-analyzer/ai-bubble/<run_id>/` に置く。私有の金額を Git 追跡ファイルへ書かない（リポジトリは公開）。
- 取得・計算は1GiB保存・1GiBピークメモリ以内を目標、保存2GiBで停止して見直す。
- 欠損をゼロ・中央値で埋めない。未評価額、基準時刻、会計基準を全段階で維持する。
- Python実行はWSLの `/home/kazumasa/projects` から `uv run --no-sync`。他プロジェクトを同期・修正しない。
- コミットは利用者の指示があるまで行わない。

## Review Focus

1. 同じ決算期の訂正が、訂正前の基準日時点へ混入しないこと → Task 1。
2. 分割、ADR、累計四半期、赤字、一時評価益で、安く見える倍率を作らないこと → Task 2/3。
3. 同じ急騰の連続月、同時期の業種、未完了の将来結果を独立標本として数えないこと → Task 4/6。
4. リース・再投資・希薄化を落としたり二重控除したりしないこと → Task 2/3。
5. ETFと直接保有の重複、未分類、為替、未校正βが、全体損失を過小表示しないこと → Task 5。
6. 判定用の割引率・RONIC・シナリオ規則が、価格を見た後に動いていないこと（PREREG の sha256 と manifest）→ Task 1/2。
7. 固有層の損失に V の乖離が混ざっていないこと（中央シナリオの損失がゼロ）→ Task 5。

## ファイル配置

| パス（project相対） | 責務 |
|---|---|
| `src/portfolio_analyzer/ai_bubble/__init__.py` | 内部の研究モジュール。既存APIの変更は不要 |
| `src/portfolio_analyzer/ai_bubble/inputs.py` | 縦持ち財務の検証、時点選択、品質結果 |
| `src/portfolio_analyzer/ai_bubble/sec.py` | companyfacts／submissions の解析（ネットワークは呼出側） |
| `src/portfolio_analyzer/ai_bubble/runs.py` | run root、manifest、PREREG の hash |
| `src/portfolio_analyzer/ai_bubble/valuation.py` | DCF、逆算、インプライドIRR、シナリオ経路、V判定 |
| `src/portfolio_analyzer/ai_bubble/funding.py` | 四半期化、資金残高、先行指標、F判定 |
| `src/portfolio_analyzer/ai_bubble/history.py` | French データの解析、急騰・崩落・エピソード、暦年クラスタ |
| `src/portfolio_analyzer/ai_bubble/portfolio.py` | 発行体集約、固有層の再評価、系統層の再生、為替 |
| `scripts/research_ai_bubble.py` | 入力rootと出力rootを明示する手動実行CLI |
| `tests/test_ai_bubble_*.py` | 手計算、時点、欠損、統合の検証。実データ・ネットワーク非依存 |
| `docs/ai-bubble/README.md` | 確定した定義・取得方法・実行方法・結果への索引 |
| `docs/ai-bubble/PREREG.md`・`docs/ai-bubble/prereg.json` | 事前登録（人が読む文と、コードが読む設定） |

`core.py`や`risk.py`の再編は行わない。既存 `data/*.private.*` 形式の変更も不要とする。

## Task 1: M0 入手可能性と研究条件を固定する

**成果物:** PREREG（銘柄規則・割引率規則・シナリオ規則・判定規則・S の定義・代理表）、入力辞書、時点選択と品質監査、米3社／日本2社の pilot、採用銘柄の確定。

**Files:** `inputs.py`、`sec.py`、`runs.py`、`scripts/research_ai_bubble.py`、`tests/test_ai_bubble_inputs.py`、`tests/test_ai_bubble_sec.py`、`docs/ai-bubble/README.md`、`docs/ai-bubble/PREREG.md`、`docs/ai-bubble/prereg.json`。

**Interfaces:**
- `select_as_of(rows: list[dict], as_of_utc: str) -> list[dict]`: 仕様§4.1の必須キーを検証し、`available_at <= as_of_utc` の中から `(issuer_id, metric, period_start, period_end, accounting_basis)` ごとに当時の最新版を選ぶ。同じキー・同じ `available_at` で値が違えば `ValueError`。
- `audit_inputs(rows: list[dict]) -> dict`: `{"ok", "errors", "missing", "issuers", "sources"}` を返す。検証不能な行は後続へ合格扱いで渡さない。
- `parse_companyfacts(raw: dict, issuer_id: str, accepted: dict[str, str], concepts: dict[str, str]) -> list[dict]`: `accepted` は accession → 受理時刻（submissions の `acceptanceDateTime`）。受理時刻が無い accession は `filed` の翌営業日（米国東部 00:00）から利用可能とする。
- `new_run(root: Path, as_of_utc: str, prereg: Path) -> Path`: run root を作り、`manifest.json` に as_of・作成時刻・git commit と未コミット有無・PREREG の sha256 を書く。

- [ ] 実行時のGit状態を記録し、既存の利用可能exportだけ確認する。
- [ ] PREREG を書く: 仕様§3.1の候補集合と採用規則、§5.1の `r_j`・RONIC・格子、§5.2の φ・ストレス・利益率・再投資、§8の判定表、§7.1の定義、クラスタ数の条件（10）、seed 20261021、系統層の局面と代理表、為替ショック、割引率上昇幅（+2pt、取得値で確認）、AI露出の分類名。
- [ ] テストを先に作る（RED を確認）:
  - 同期間に値100・訂正値120、利用可能時刻が順に 2026-01-10T21:00Z・2026-02-10T21:00Z なら、as_of 2026-01-31 は100、2026-02-28 は120。
  - 未公表行は選ばれない。必須キー欠損、タイムゾーン無し、通貨・単位欠損は品質エラー。同時刻の値の衝突は `ValueError`。
  - companyfacts の手作り fixture: 受理時刻がある accession はその時刻、無いものは `filed` の翌営業日 00:00 ET（金曜の `filed` なら月曜）。
  - `new_run` が PREREG の sha256 を manifest に書き、既存の run root を上書きしない。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests/test_ai_bubble_inputs.py portfolio-analyzer/tests/test_ai_bubble_sec.py -q`
  Expected: 実装前は `ModuleNotFoundError`、最小実装後は全件 passed。
- [ ] pilot: SEC から米3社（NVIDIA・Microsoft・Oracle。非営業評価益とリースの大きい企業を含む）の companyfacts と submissions を取得し、取得時刻と sha256 を記録。各社3値以上を原提出書類の本文と照合する。
- [ ] 日本2社（アドバンテスト・東京エレクトロン）を IR の決算短信・財務データから取り、同様に照合する。J-Quants は既存キーが環境変数にある場合だけ使う。取れない項目は理由付きで欠損にする。
- [ ] 候補20社超の時価総額（同じ基準時刻、米ドル換算）を取り、§3.1の規則で採用銘柄を確定して PREREG に追記する（以後変えない）。
- [ ] 実測サイズ・時間を記録し、無料でできる主張と不足データを仕分ける。私有額を公開manifestへ入れない。

**Gate:** 原資料と値・期間・公表日を照合できる企業だけ Task 2 へ。過去PIT構成が足りなくても、現在の個社診断は進める。

## Task 2: M1 現在価格が要求する成長を求める

**成果物:** 個社の実績倍率、判定用 `r_j` での必要売上成長と必要利益率、インプライドIRR、終端価値比率、基底率に対する位置、V 判定と感応度。

**Files:** `valuation.py`、`tests/test_ai_bubble_valuation.py`、`scripts/research_ai_bubble.py`。

**Interfaces:**
- `enterprise_value(cf: list[float], terminal_cf: float, discount_rate: float, terminal_growth: float) -> float`: 1年後からT年後までのFCFFと、**独立して渡すT+1年の終端FCFF**を割り引く。`r <= g` は `ValueError`。
- `terminal_fcff(nopat_next: float, terminal_growth: float, ronic: float) -> float` = `nopat_next × (1 − g/RONIC)`。
- `growth_path(g0: float, g_inf: float, phi: float, years: int, shocks: dict[int, float] | None = None) -> list[float]`: `g_t = g_inf + (g0 − g_inf)φ^t`、`shocks` の年は値を置き換える。
- `project_fcff(base: dict, scenario: dict, years: int) -> dict`: 売上・利益率・税率・売上/投下資本から FCFF と終端FCFF を作る。
- `solve_roots(f, lo: float, hi: float, steps: int = 400) -> list[float]`: 格子で符号変化を探し二分法で解く（複数解をすべて返す）。
- `required_growth(...) -> dict`・`implied_irr(...) -> dict`: `{"status": "ok" | "no_solution" | "multiple", "solutions", "bounds"}`。
- `per(price: float, eps: float | None, adr_ratio: float = 1.0) -> float | None`、`v_classify(ev_central, ev_optimistic, ev_observed, band=0.10) -> str`。

- [ ] 通常終値・株数・現金・債務と会計期間をそろえ、利益の平常化を20四半期以上で比較できる企業を区別する。
- [ ] テストを先に作る（RED を確認）:
  - 年率10%、成長0%、毎年CF10、終端CF10の定常企業はEV 100（T=1でも T=5でも）。
  - 末年CF10、終端CF20、r=10%、g=0%、T=1 なら EV = 10/1.1 + 20/(0.1×1.1) = 2100/11。終端CFを末年CFへ戻す実装を検出する。
  - `terminal_fcff(100, 0.03, 0.15)` = 80。`growth_path(0.5, 0.03, 0.6, 3)` = [0.312, 0.1992, 0.13152]。
  - `solve_roots((x−0.1)(x−0.3), 0, 1)` は 0.1 と 0.3 の両方。符号変化が無ければ空。
  - 既知の g0・r から EV を作り、`required_growth`・`implied_irr` で元の値へ 1e-6 以内で戻る。範囲外は `no_solution`。
  - PER: 価格・EPSを同率で分割調整してPER不変。ADR 1株=普通株5株、ADR価格100、普通株EPS 1 なら PER 20。EPS ≤ 0 は `None`。
  - `v_classify`: 観測100に対し中央95 → 弱める、中央80・楽観85 → 支持、中央80・楽観120 → 混在、観測EV ≤ 0 → 保留。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests/test_ai_bubble_valuation.py -q`
  Expected: 実装前は失敗、最小実装後は全件 passed。
- [ ] 基底率（仕様§5.3の文献）の入手可否を確認し、入手できた分布だけを使う。入手できなければ V の歴史比較を「データ不足」とする。
- [ ] Task 1 を通過した企業に適用し、`r_j`・格子・RONIC・T=5 の結果と原資料を確認する。検証済みの会社だけ初回表にする。

**Gate:** 終端価値の大きさ、再投資、リース、株式報酬／希薄化の扱いを説明できること。「適正価格」「バブル確率」の一点推定は出さない。

## Task 3: M2 利益と設備投資の資金持続性を検証する

**成果物:** CFの橋渡し、非営業利益、投資／リース、先行指標、顧客・相手先の集中、24か月の資金不足境界、F 判定。

**Files:** `funding.py`、`tests/test_ai_bubble_funding.py`、`scripts/research_ai_bubble.py`。

**Interfaces:**
- `quarterize(rows: list[dict]) -> list[dict]`: 同じ会計年度の累計値から単独四半期を作る。期間が連続しなければ欠損理由を返す。
- `funding_path(cash: float, quarters: list[dict]) -> dict`: 8四半期の営業CF、債務元本返済、投資支払を受け、四半期残高・期間末不足・最大途中不足を返す。必要額・期日が不明なら `status="unevaluated"` と理由。
- `duplicate_payments(quarters: list[dict]) -> list[str]`: 同じ支払IDが複数の区分に入っていれば返す（品質エラー）。
- `f_classify(central: dict, stress: dict) -> str`。

- [ ] キャッシュフロー、運転資金、評価益、設備投資、リース、債務満期、受注・受注残・RPO、顧客集中を四半期・TTMで突き合わせる。
- [ ] テストを先に作る（RED を確認）:
  - 現金100、CF20、確定支払80、追加投資60なら不足20。CF40なら不足0。
  - 現金100、Q1元本返済120、Q2営業CF40、その他0なら期末残高20でも最大途中不足20。
  - 上期累計CF150とQ1 CF60からQ2 CF90。期間が欠けた累計は欠損理由付きで返す。
  - 未知の最低支払は `unevaluated`、金額ゼロとは区別する。リース元本を財務と投資の両方に入れると重複として検出する。
  - `f_classify`: 中央で途中不足が正 → 支持、中央・ストレスとも不足ゼロ → 弱める、ストレスだけ不足 → 混在、未評価があればデータ不足。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests/test_ai_bubble_funding.py -q`
  Expected: 実装前は失敗、最小実装後は全件 passed。
- [ ] 需要成長・マージン・投資継続を動かして、資金不足と投資回収の境界を出す。最終需要が分からない層は保留する。

**Gate:** 売上、顧客設備投資、最終利用者の支払を足し合わせないこと。

## Task 4: M3a 急騰と崩落の基底率（記述版 S）

**成果物:** GSY との検算、閾値別の急騰件数・崩落率・急騰後リターン、無条件の崩落確率、暦年クラスタの区間、現在の位置、S 判定。

**Files:** `history.py`、`tests/test_ai_bubble_history.py`、`scripts/research_ai_bubble.py`。

**Interfaces:**
- `parse_french_industry(text: str) -> dict`: 49業種ファイルから月次の時価加重リターンと構成企業数を返す。`-99.99`・`-999` は欠損。
- `parse_french_factors(text: str) -> dict`: 月次の `Mkt-RF` と `RF`。
- `levels(returns: list[float | None]) -> list[float | None]`: 欠損以降は `None`。
- `forward_drawdown(levels: list[float | None], start: int, months: int) -> float | None`: 将来窓が完全なときだけ、`start` 以降のどの時点からの最大下落も含めて返す。
- `runup_flags(ind: list, mkt: list, nfirms: list, threshold: float = 1.0, five_year: float = 0.5, min_firms: int = 10, net: str = "difference") -> list[bool | None]`。
- `episode_starts(flags: list[bool | None], gap: int = 24) -> list[int]`。
- `cluster_bootstrap(values_by_cluster: dict[str, list[float]], reps: int, seed: int) -> list[float]`: クラスタ（暦年）単位で復元抽出し、平均の分布を返す。

- [ ] French の49業種（月次・時価加重・構成企業数）と市場ファクターを取得し、版・取得時刻・sha256 を記録する。
- [ ] テストを先に作る（RED を確認）:
  - 指数100→150→90なら窓内DDは−40%、100→140→110なら 110/140−1。未完了の窓、内部欠損は `None`。
  - 24か月で業種+110%・市場+5%・60か月で業種+110% なら急騰。業種+110%・市場+20%（差+90%）なら急騰でない。構成企業9社の月は `None`。
  - 急騰月が 5,6,7,40 ならエピソード開始は 5 と 40、5 と 20 なら 5 だけ。
  - クラスタA=[1,1]・B=[0] のブートストラップ値はすべて {0, 2/3, 1} のどれか（行単位の抽出なら 1/3 が出る）。点推定は 2/3。
  - French 形式の小さな CSV 断片（見出し行、空行、年次の節を含む）から月次値と構成企業数を読み、年次の節を月次に混ぜない。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests/test_ai_bubble_history.py -q`
  Expected: 実装前は失敗、最小実装後は全件 passed。
- [ ] GSY の主定義で 1928-01〜2012-03 の急騰件数と崩落数、1928〜2013 の無条件崩落確率を計算し、GSY（40件・21件・14%）と並べる。大きく違えば原因を調べてから先へ進む。
- [ ] 全期間（結果の確定した月まで）で閾値別の表と暦年クラスタの区間を作り、分析対象企業のFF49業種と自社株価の現在の位置を示す。
- [ ] 各時系列分割の独立な暦年クラスタ数を数え、Task 6 を行うかを PREREG の条件で決める。

**Gate:** 後から選んだAI勝ち組、中央値補完、日付を遡った資料、現在の予想EPSを過去へ入れた結果を採用しない。S の頻度を「バブルの確率」と呼ばない。

## Task 5: M5 保有への影響（基本）と最小版レポート

**成果物:** 公開の市場結果（V/F/S）と、私有の発行体別影響（固有層・系統層を並べた円建て損失、AI露出の評価済み比率）。

**Files:** `portfolio.py`、`scripts/research_ai_bubble.py`、`tests/test_ai_bubble_portfolio.py`、`tests/test_ai_bubble_cli.py`、`docs/ai-bubble/README.md`、`docs/STATUS.md`。

**Interfaces:**
- `issuer_exposure(paths: list[dict]) -> dict`: 各経路は `position_symbol, issuer_id, value_jpy, economic_currency, fx_hedge_ratio, as_of`。発行体で合算し、未知ウェイトを残す。
- `repricing_change(ev_observed: float, net_debt: float, ev_scenario: float) -> float | None`: 株主価値の変化率。株主価値が正でなければ `None`。
- `fx_compose(local_return: float, fx_change: float) -> float`。
- `systematic_layer(values: dict[str, float], proxy_map: dict[str, str], proxy_prices_jpy: dict[str, list], dates: list[str], episodes: list[dict]) -> list[dict]`: 代理系列を保有へ写し、既存の `risk.episode_impacts` に渡す。代理の無い保有は未評価。

- [ ] 現在保有を読取で集約し、ETF構成の鮮度・残余・財務評価範囲・AI露出の分母を表示する。
- [ ] テストを先に作る（RED を確認）:
  - 直接保有20＋ETF80の中の同社25%なら発行体40。二重集計はしない。未知ウェイト20%を既知80%へ再正規化しない。
  - 現地価格−30%、対円為替−10%なら円建て−37%。円建て・非ヘッジの米国株ETFにもUSD/JPYショックが伝わる。
  - 時価総額100・純有利子負債25・観測EV125、中央FCFF10（永続、g=0）なら `r*` = 8%。ストレスFCFF8・r=10%で EV 80 → 株主価値 55 → −45%。中央の変化はゼロ。
  - 代理系列 [100, 60] の保有100は系統層で −40、代理の無い保有は未評価。
  - 仕様§8の V の10%境界、F の全シナリオ／一部不足、S の条件、欠損優先を固定する。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests/test_ai_bubble_portfolio.py portfolio-analyzer/tests/test_ai_bubble_cli.py -q`
  Expected: 実装前は失敗、最小実装後は全件 passed。統合fixtureで、私有金額が公開JSON／HTMLへ出ないこと、既存入力hashが実行前後で不変なことも確認する。
- [ ] CLIで市場と私有の出力を分け、必要なら共通HTMLテンプレートで可視化し、実際に表示して確認する。
- [ ] `uv run --no-sync pytest portfolio-analyzer/tests -q`、対象の `ruff check`／`ruff format --check`、`git diff --check` を実行する。
  既存失敗があれば関連するベースラインと比較し、今回の変更が原因と未検証で断定しない。
- [ ] 設定・hash・版・seed・実サイズ・検証結果を保存し、`docs/STATUS.md` を証拠と一致させる。

**Gate:** 未評価部分がある場合は全体を安全・危険と断定しない。未完了な共同回帰の校正や売買案の最適化は、この研究へ黙って追加しない。

## Task 6: M3b 予測性能の検証（条件付き）

- [ ] Task 4 で数えた独立な暦年クラスタが各分割で10以上の場合だけ行う。満たさなければ「予測シグナルとして未確立（標本不足）」と記録して閉じる。
- [ ] 行う場合は仕様§7.3に従い、`purged_splits` と暦年クラスタの区間を TDD で実装し、無条件・急騰条件付き・単一指標のベースラインと比べる。

## Task 7: M4 価格の爆発性を補助検証する（任意）

- [ ] Task 4 までで残った問いに検定が役立つか判断する。不要なら省略理由を記録する。
- [ ] 必要なら numpy の依存追加を利用者に承認してもらってから、仕様§7.4に従って実装する。承認が無ければ実施しない。

## 進め方と見積り

優先順は **Task 1 → 2 → 3 → 4 → 5**。これが最小版。Task 6・7 は条件と承認しだい。
現在の割高条件を知るために、長期の全銘柄データ整備や高度な予測器の完成を待たない。

人手を含む調査工数の粗い見積りは、Task 1 が半日〜1日、Task 2/3 が2〜4日、Task 4 が半日〜1日、Task 5 が半日〜1日。
これは納期・計算時間の確約ではなく、資料整備と照合に支配される見積り。
有料データが必要なら取得前に範囲・料金・代替案を示す。

## 確認済みと未確認（2026-10-21）

- 確認: projectのREADME、既存AI研究、ETF PER再構成メモ、STATUS、主要な読取・リスク計算の入口、宣言済み依存、参照データの発行体展開率。
- 確認: SEC、EDINET、Frenchデータ、GSY 本文（定義・件数）。FRED はこの環境から接続できない（米国財務省・財務省・FRB H.10 の原表で代える）。
- 未確認: 私有の現在保有額、最新の全企業財務、APIキー・有料契約、全履歴のPIT完全性、基底率文献の入手可否、研究の計算結果。
