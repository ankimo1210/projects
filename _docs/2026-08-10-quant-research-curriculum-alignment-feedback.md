# quant_research — curriculum_map.yml 原典整合性レビュー フィードバックノート

作成日: 2026-08-10
対象: `analytics/quant_research/curriculum_map.yml`（Stage 1 / B1–B4 / Week 1–16）
比較対象: ユーザー提供の原典カリキュラム「Quant Research / Data Science — Top University
Composite Curriculum v1.0（2026-08-09）」

注記: このレビュー実施時点で別セッションが同プロジェクトを並行編集していた
（`tools/build_nb06`–`build_nb11.py` が調査中に出現）。本ノートの指摘は
2026-08-10 07:12 時点のスナップショットに基づく。

## 結論

Stage 1（B1–B4、週1–16）はトピックレベルでほぼ完全に整合。相違点の大半は
`design_corrections` に理由付きで明記された意図的な層分けであり、うち3件は
**原典の設計上の欠陥を正しく訂正している**（下記1章）。一方で、原典の中核規約
のうち2つ（評価規約・プレースメント診断）が Stage 1 の範囲内であるにも関わらず
取り込まれていない。

## 1. マップが原典を訂正した箇所（評価できる差分）

| # | 原典の記述 | マップの訂正 |
|---|---|---|
| 1 | B1 Block Project の入力に「Coupon, Observed price **or yield**」を併記 | 教育用ゼロカーブモード（coupon/price を `prohibited_inputs` に指定）と債券価格モード（`P_i = sum_j C_ij * D(t_ij)`）に分離。原典のままだと観測方程式が定義できない |
| 2 | B3 Block Project を「BOJ Event Study」とし、末尾で因果解釈の妥当性を「議論する」 | 既定を `announcement response` に固定し、`disallowed_claim_without_extra_identification: 金融政策の因果効果` を明記。因果版は surprise measure と識別戦略を要求する advanced 扱い |
| 3 | B4 Block Project の制約に「Monotonicity」を無条件で列挙 | 負金利下では `D(T)` が1を超えたり局所的に増加し得るため、普遍的な no-arbitrage condition として強制せず optional に降格。非負フォワードを仮定と明記。JGB を対象にする以上これが正しい |

## 2. 抜けている原典要素（Stage 1 の範囲内）

| 原典 | 現状 |
|---|---|
| §2 Assessment Philosophy — 4成果物（Derivation Note / Implementation / Experiment / Technical Memo 2–4頁）、採点配分 25/30/30/15、**合格 75/100** | 無し。`memo` は `B3-W11` の artifact 名1件のみで規約化されていない |
| §8/§9 Placement-Out・Placement Tests（B1 を2週に圧縮可、等の診断） | 無し |

## 3. 縮約（意図的だが記録が薄い箇所）

- Core Textbooks は各ブロック2–4冊のみ。Matrix Cookbook / Durrett / Øksendal /
  Efron & Hastie / Harrell / Angrist & Pischke / CLRS / Skiena、および
  MIT 18.06SC・18.600・18.650 が欠落。原典の Priority A/B 階層が失われている
- Core→Advanced 降格8件のうち **Poisson process**（B2-W7）と
  **heap/tree/graph**（B4-W16）の2件は `design_corrections` に理由の記載が無い
- Stage 2 (B5–B11) / Stage 3 (R1–R4) / Capstone は対象外（README に明記済みで
  これは意図的。ただし `curriculum_map.yml` 自体にも scope 限定の一文があると
  ファイル単体で読んだときに誤解されない）

## 4. バグ

`curriculum_map.yml:494`

```yaml
      causal:
        - Hernán & Robins, Causal Inference: What If
```

クォート無しの `: ` を YAML がマッピング区切りと解釈し、文字列でなく
`{"Hernán & Robins, Causal Inference": "What If"}` という dict になる。他の
references はすべて文字列なので、参照文献を文字列として走査する処理はここで
壊れる。修正:

```yaml
        - "Hernán & Robins, Causal Inference: What If"
```

## 5. マップと実装の乖離（レビュー時点、別件）

`scope.status.b2_mvp: implemented` だが Notebook 06–11 は本レビュー開始時点で
未生成（ジェネレータのみ）。README も12冊実装済みと記載しており、実体より
先行している。

## 優先度（次にやるなら）

1. line 494 の YAML バグ修正（1行、独立して安全）
2. Poisson process / heap-tree-graph の降格理由を `design_corrections` に追記
3. 評価規約（4成果物・採点配分・合格点）を `curriculum_map.yml` トップレベルに追加
4. プレースメント診断（B1/B2/B4）を追加。週別 `exit_criteria` を流用可能
5. 参考文献の階層化（Priority A/B + オンライン資料）

1・2 は行単位で独立しており、B2 Notebook 生成作業と衝突しない。3–5 は
`curriculum_map.yml` 全体に触れるため、別セッションの編集が落ち着いてから。

---

## 追記: 対応結果（2026-08-10 08:17 再検証）

上記の指摘5件はすべて対応済み。並行して B2 の実装も完了し、コミット
`34d45aef Add B1-B2 quant research textbook`（54 files, +26,146）に到達した。
以下は再検証の実測。

### 指摘への対応

| # | 指摘 | 対応 |
|---|---|---|
| 1 | `curriculum_map.yml:494` の YAML パースバグ | 修正済み。`- "Hernán & Robins, Causal Inference: What If"` とクォート（現 137行・618行） |
| 2 | 評価規約が無い | トップレベルに `assessment` 追加。`derivation_note` / `implementation` / `experiment` / `technical_memo`（2–4頁）、配分 25/30/30/15、`pass_mark: 75`、`completion_rule` に「講義や教科書を読み終えただけでは修了としない」 |
| 3 | プレースメント診断が無い | トップレベルに `placement` 追加。B1/B2/B4 の診断項目を原典どおり収録、B3 は placement-out 不可。原典に無い歯止めとして「placement診断は学習速度だけを変える。成果物、採点、exit_criteria、再現性・検証要件は免除しない」を追加 |
| 4 | Poisson process / heap・tree・graph の降格理由が無い | 両方 `design_corrections` に追記（398行・820行） |
| 5 | 参考文献の欠落 | Matrix Cookbook / Durrett / Øksendal / Efron & Hastie / Harrell / Angrist & Pischke / CLRS / Skiena を追加。MIT 18.06SC・18.600・18.650、Stanford Boyd を `online` キーで復活。`reference_priority` を新設 |

### 実装の進捗

| 項目 | レビュー時 07:12 | 再検証 08:17 |
|---|---|---|
| Notebook | 6冊（00–05） | 12冊（00–11）、全て実行済み出力あり |
| テスト | 53 passed | 98 passed（1.55s） |
| `src/quant_textbook` | 4モジュール | 8モジュール（`probability` `convergence` `stochastic` `monte_carlo` 追加） |
| `build_notebooks.py --check` | `ModuleNotFoundError: build_nb08` | `checked 12 notebooks: valid Python and deterministic JSON` |
| HTML | 6冊・00:01 の古いビルド | 12冊・08:15 に再ビルド |
| git | 未追跡（`git ls-files` = 0） | コミット済み（50 files tracked） |

コミットの品質: `_build/` の生成物は1件も含まれていない。ルート
`pyproject.toml` / `Makefile` / `uv.lock` / `analytics/README.md` の登録変更が
同一コミットに含まれ、ワークスペース側と整合している。README の
「実装済み Notebook」表（12冊）と「現在の範囲」も実体と一致し、レビュー時に
指摘した「README が実体より先行」状態は解消した。

### 残っている差分（意図的なもののみ）

- Stage 2（B5–B11）/ Stage 3（R1–R4）/ Capstone は `curriculum_map.yml` の
  対象外。README に「後続」として明記済みで想定どおり
- Plotly が CDN 依存（12ファイルが `cdn.plot.ly` を参照）。README に記載済みの
  既知事項。`analytics/report` のオフライン自己完結ポータルへ将来統合する際に
  再検討が必要

Stage 1 の原典整合性については、このノートで追う項目は残っていない。

---

## 追記2: B3–B4 実装レビュー（2026-08-10 12:39）

B3・B4 が実装され Stage 1（B1–B4、Week 1–16、全24章）が完結した。対象コミット:

- `998593b4 Add B3 inference textbook chapters`
- `97c2d4ff Add B4 optimization textbook chapters`
- `e11987ce Document Stage 1 B4 implementation update`
- `b117d13b Fix update note formatting`

### 機械的検証（すべて再実行して再現を確認）

| 検証 | 結果 |
|---|---|
| `uv run --no-sync pytest analytics/quant_research/tests -q` | 249 passed（3.14s） |
| `tools/build_notebooks.py --check` | checked 24 notebooks: valid Python and deterministic JSON |
| Notebook 実行状態 | 24/24、code cell 247、出力ゼロの章なし |
| `jupyter-book build --all -W --keep-going` | build succeeded / warning 0 |
| `_toc.yml` ↔ 実ファイル | 24 entries、欠損 0、TOC 外の Notebook も 0 |
| ローカル絶対パス漏れ | `/home/kazumasa` 0件、`/tmp/...` 0件 |
| 新規依存 | なし（`analytics/quant_research/pyproject.toml` 無変更、scipy のみ） |

`docs/updates/2026-08-10-stage-1-b4.md` に記載された数値はすべて再現した。

### 評価できる点

1. **マップの設計判断がコードのデータ契約まで落ちている。**
   `constrained_curves.py` で `monotone: bool = False`（任意制約・既定 off）、
   `monotonicity_assumption = "non-negative forward rates and the anchor D(0)=1"`、
   `monotonicity_warning = "monotonicity is optional: negative rates can imply
   D(T)>1 or locally increasing D"`。`minimum_discount=1e-8` は map の
   `epsilon_D: 1e-08` と一致し、さらに「floor-implied rate at longest node (%):
   61.40」と閾値の金利換算を出力している（map の「epsilon_D の尺度根拠を記録」に対応）。
   `nb23 §10` で負金利 fixture を実際に回している。

2. **B3 の claim class が型になっている。**
   `ClaimClass = Literal["association", "announcement-response", "causal-effect"]`。
   `causal-effect` を選ぶと診断に警告が積まれ、nb17 の claim audit は
   `causal claim supported: False` と limitations を機械的に出力する。
   「因果と呼ばない」が注意書きでなく実行される契約になっている。

3. **不利な結果を消していない（最重要）。**
   B4 Project の標準化 LOO RMSE は 11.4620 half-spreads で B1 baseline の 3.7235
   より悪い（最悪は30年債の 35.2436）。in-sample の KKT certificate と hard
   constraint gate は通っており「成功」と書くこともできた場面で、
   `generalization_supported` を事前コミットした two-half-spread gate から機械的に
   算出し `assert` で固定、「結果を良く見せるため primary smoothness を再調整
   しない」と明記している。

4. **仕様変更を隠していない。** 実装中の2つの判断変更を、コードより先に
   `curriculum_map.yml` へ反映してから実装している。
   - B4-W15: `objective gap、gradient mapping、feasibility による停止判定` →
     `objective gap による事後評価と、gradient mapping、feasibility による停止判定`
   - B4 project: `robust loss` を required の説明から外し Advanced へ

5. **依存を増やさず限界を明記。** 凸最適化に cvxpy を入れず scipy で通し、
   「SciPy 1.13 には汎用 DCP checker や専用 SOCP certificate がない。教材の SOCP
   例は一般 solver による数値解であり conic certificate とは呼ばない」と明記。

### 新規の指摘（2件、原因は同一）

`assessment` と `placement` は本ノートの指摘を受けて B1/B2 実装後に追加された。
B3/B4 には織り込まれたが、**B1/B2 章に後追いされていない**。

**指摘1: 4成果物・75点 gate が B1/B2 章に無い。**
map は `assessment.applies_to: 各 block` だが、言及がある章は 12, 17, 18, 21, 22,
23 の6章ですべて B3/B4。

| 章 | 該当節 |
|---|---|
| `12_b3_overview` | §2 成果物と採点契約 |
| `18_b4_overview` | §2 4成果物と75点gate |
| `17_b3_project` | §13 Block成果物と採点check |
| `23_b4_project` | §12 Core / Advancedと75点gate |
| `00_overview` / `06_b2_overview` / `05_b1_project` / `11_b2_project` | 該当節なし |

**指摘2: B2 の placement 診断がどこにも出ていない。**
`placement.blocks.B2.diagnostic` の6項目（conditional expectation の導出、LLN と
CLT の区別、martingale の定義、optional stopping の成立条件、Itô lemma、
Monte Carlo CI の構成・診断）に対応する記述が B2 章に無い。

| Block | placement の扱い |
|---|---|
| B1 | `00_overview §4 事前診断` あり |
| B2 | 記述なし |
| B3 | 「B3はplacement-outしない」と明記 |
| B4 | 「placement で圧縮しても成果物、KKT監査、再現性要件は免除しない」と明記 |

### 提案

`tools/build_nb00.py` / `build_nb05.py` / `build_nb06.py` / `build_nb11.py` に
B3/B4 と同形式の節を追加し、再生成・再実行する。4ファイルに節を足すだけで既存
内容には触れない。実行前に別セッションが同プロジェクトを編集していないか確認する。

---

## 追記3: Stage 2A/2B（B5–B8）レビュー（2026-08-10 22:00）

対象コミット: `f05761dc Add Stage 2A Treasury learning chapters`、
`98544e02 Add B7-B8 Treasury dynamics textbook`。
Stage 1 の指摘2件（追記2）も同時に解消済み。全48章・Week 1–32。

### 機械的検証（すべて再実行して再現）

| 検証 | 結果 |
|---|---|
| `pytest` | 323 passed（287→323） |
| `build_notebooks.py --check` | 48/48 決定論的 |
| `jupyter-book build --all -W --keep-going` | 48 pages / warning 0 |
| `ruff check` / `ruff format --check` | All checks passed / 98 files |
| execution_count | 48冊すべて 1 から連番、error output 0 |
| `_toc.yml` / README / on-disk | 48 で一致、孤立なし |
| 絶対パス漏れ | 0 |

### 独立検証 — データ層

Claude 側が別途取得した Treasury XML / SEC JSON のキャッシュに対し、GPT が追加した
`tools/audit_stage2_feasibility.py` をそのまま実行した。

- 6 artifact の SHA-256（Treasury 37ファイルの manifest hash と SEC 5ファイル）が
  **すべて doc 記載値と一致**
- 集計値も全一致: entries 9,157 / complete core panel 4,901（2007-01-02〜）/
  phantom 2010-10-11 / Dec-2008 3M 欠測3件 / facts 25,046 / period groups 12,366 /
  repeated 7,139 (57.7%) / value-changed 426 (3.44%) / acceptance 不一致 86 (8.6%) /
  frames 6,428 entities
- baseline も一致: no-change 5.9308 bp、AR(1) 5.9409 bp、+0.170%

B5–B6 の snapshot も、こちらの XML から独立に再構成して 2,750行 ×5 = 13,750値が
**mismatch 0**（追記2 で実施）。

### 評価できる点

1. **他者の報告を鵜呑みにせず再計算している。** Claude の spike レポートの数値を
   引き写さず、`audit_stage2_feasibility.py` を書いて raw cache から再計算し、
   content hash とともに記録した。ネットワークに接続せず入力も変更しない設計。
2. **罠を回帰テストに落とした。** `tests/fixtures/treasury_phantom_row.xml` は
   実データの 2010-10-11（全 tenor 欠損・`BC_30YEARDISPLAY` だけ 0.00）の最小再現。
   テスト2本が付いている。
3. **パーサ修正が精密。** 2010 は phantom row を除外して 252→251行・`accepted=True`、
   一方 2003（30Y 構造的欠測）は `accepted=False` のまま。休場日の偽行だけ落とし、
   構造的欠測は分析者に突きつける、という区別ができている。
4. **SEC を「5 gate 通過」と書かなかった。** Baseline 未実施を理由に 4/5 相当と明示し、
   B9 を条件付き候補のまま保留。さらに SEC 公式仕様で Frames が "last filed" 寄りの
   集約であることを裏取りし、Claude の実測（frames が13か月後の修正値を返す）を
   一次資料で補強している。
5. **B9 の PIT contract を7項目で先に固定。** 特に「SEC は受理から公開までの lag を
   保証しないため受理日の**翌**営業日から利用可能とする」は、実測より保守的な運用規則。
6. **不利な結果を4回連続で消していない。** B7 は locked test で random walk が5 tenor
   すべて最小 RMSE、B8 は aggregate RMSE で random walk 11.13 bp < Bayesian 11.26 <
   HMM 11.29。`no model selected` を結論とし、outer test を見た再調整をしていない。

### 指摘

原典 B5–B8 の topic を `curriculum_map.yml` と Notebook 本文へ 1:1 で照合した。
**map が Core と書いているのに本文に無い項目**が2件。

**指摘1（重要）: B6-W24 の purging / embargo / grouped split が本文に無い。**

`curriculum_map.yml` の B6-W24 core は「grouped split、purging、embargoの適用境界」と
明記している。しかし `34_week24_evaluation_under_shift.ipynb` の markdown・code の
どちらにも `purg` / `embargo` / `grouped split` が1件も無い（節は Nested temporal
protocol / Feature drift / Split conformal interval の3つ）。`embargo` は
`curriculum_map.yml` 以外、リポジトリ全体で0件。

purging 自体は `src/quant_textbook/learning.py` に実装があり
（"Chronological indices with a purged gap before later partitions"、
"expanding-window folds with a purged boundary"）機構としては効いている。
つまり**結果はリークしていないが、リーク制御を教える章がそれを説明していない**。
金融 ML の leakage 制御の中心概念なので、優先度は高い。

**指摘2（軽微）: B6-W21 の bagging intuition が本文に無い。**

map core は「regression tree split、bagging intuition、gradient boosting」。
`bagging` / `bootstrap aggregating` / `random forest` はいずれも B6 の6冊に0件。
`stump` と boosting は実装済み。

**参考: map 自体が原典から落としている項目（design_corrections に記載なし）**

| Block | 原典にあり map・本文とも無い |
|---|---|
| B5 | Bayes predictor、irreducible noise、missing data |
| B6 | RKHS、SVM |
| B7 | spurious regression |

いずれも「Core を過密にしない」方針と整合的だが、Stage 1 では同種の判断を
`design_corrections` に理由付きで残していた。同じ扱いにすると追跡できる。

なお当初 B7 の unit root / dynamic factor / structural break も欠落と見えたが、
それぞれ Dickey–Fuller diagnostic（W25）、Dynamic Nelson–Siegel（W27）、
Break-aware audit（W28）として実装済みで、名称違いによる誤検出だった。
B5-W18 の proximal も map が「coordinate descentまたはproximal update」と
選択式にしており、coordinate descent が実装済みなので充足している。

### 提案

1. `tools/build_nb34.py` に purging / embargo / grouped split の節を追加する。
   `learning.py` に purge 実装があるので、その boundary を可視化する lab にできる。
2. `tools/build_nb31.py` に bagging intuition を1節追加する。
3. map が原典から落とした項目を `design_corrections` に明記する。
4. B9 着手前に SEC の Baseline gate を完了する（GPT 自身が残作業として列挙済み）。

---

## 追記4: SEC PIT contract レビュー（2026-08-11 07:39）

対象コミット: `a7e16336 Add SEC PIT B9 contract and cache tooling`。
前提として Claude 側が `_docs/2026-08-11-sec-baseline-gate.md` で SEC の
Baseline gate を実測し「pass」と報告していた。

### 機械的検証

| 検証 | 結果 |
|---|---|
| `pytest` | 331 passed（323→331、新規8件） |
| `ruff check` / `format --check` | All checks passed / 102 files |

追加規模: `sec_pit.py` 448行、`test_sec_pit.py` 170行、
`fetch_sec_b9_cache.py` 186行、`test_fetch_sec_b9_cache.py` 81行。

### この回の要点 — Claude 側の実験に欠陥が見つかった

**GPT は Claude のレポートを取り込まず、方法論の欠陥を指摘した。**

Claude の Baseline gate 実験は universe を `us-gaap/Assets/USD` frame の
`CY2015Q4I`（= 2015年末時点で存在が確定していた 7,018 社）から選び、
その企業群の **2008 年まで遡って**パネルを構築していた。
2015 年に生存していた企業だけを 2008 年の母集団として使う構成であり、
look-ahead / survivorship bias そのものである。B9 で防ごうとしている問題を、
gate 実験自体が犯していた。

GPT の対処はコードで境界を強制するもの。

```python
class PITUniverseSpec:
    """An anchored cohort specification that cannot use a current Frame."""
    anchor_period_end: date      # 2015-12-31
    anchor_as_of: date           # 2016-04-01
    analysis_start: date         # __post_init__ で >= anchor_as_of を強制
```

`analysis_start < anchor_as_of` は `ValueError` になり、**過去への遡及が
そもそも構成できない**。`test_fixed_anchor_cohort_excludes_future_selected_and_small_assets`
が、anchor 日より後に availability を持つ企業の除外を検証している。

### Gate 判定の格下げ

Claude が「Baseline: pass」「Sample: pass」と書いた箇所を、GPT は
**「provisional pass」「hold」**へ下げた。根拠は2点とも妥当である。

1. strict split の n=84 が事前に定めた n≥200 未満 — Claude 自身レポート本文では
   認識していたが、トップレベルの gate 表へ反映し忘れていた。自分の表記の
   不整合を GPT が正した形。
2. universe 選定の look-ahead — Claude が見落としていた問題。

さらに Claude の数値に `provisional`（暫定であり最終ではない）という限定を付け、
「archive を含む再取得後に同じ manifest から再計算する」とした。

### accession 解決の fail-closed 化

Claude が指摘した「accn の 12.2% が submissions の `recent` に無く `filed` へ
フォールバックしている」問題に対し、契約を
「acceptance metadata が見つからない accession は**失敗として扱い、
`filed` 単独へ fallback しない**」に変更。`filings.files` の全 archive を
結合して解決する設計になった。

`fetch_sec_b9_cache.py` は User-Agent を12文字以上かつ `@` を含むことで検証し、
CIK 検証・rate limit・content hash manifest を持つ。正常系だけでなく
naive datetime 拒否・unresolved accession 拒否など失敗系もテストされている。

### 所感

これで3回連続、GPT は外部からの指摘（Claude のレポート）を検証せず取り込むのでは
なく、指摘自体を疑ってより厳しい基準で再検証している。今回は最初にレビューする側
だった Claude の方法論に穴があり、それを向こうが見つけた。

---

## 追記5: B9 M6 protocol レビュー（2026-08-11 11:03）

`a7e16336` 以降の**未コミット**作業。Claude 側は
`_docs/2026-08-11-sec-b9-panel-realdata-run.md` で panel builder を実データ
試走し、(1) accession 未解決の fail-closed が正しく動くこと、(2) 同日に複数
四半期を提出する遅延提出者が **60社中14社（23.3%）**存在し例外停止することを
報告していた。

### 機械的検証

| 検証 | 結果 |
|---|---|
| `pytest` | 364 passed（337→364） |
| `ruff check` | All checks passed |
| 解析系の network-free | `sec_panel.py` / `sec_cache_integrity.py` / `audit_sec_b9_panel.py` / `build_b9_panel.py` に `urlopen` なし |

### 指摘への対応

**同日提出パターン** — Claude が挙げた3案のうち**案2（除外して件数を診断へ記録）**
が採用された。

```python
if target_available <= previous_available:
    excluded_non_increasing_availability_pair_count += 1
    availability_affected_ciks.add(cik)
    continue
```

例外停止から「除外 + 影響 CIK 集合の保持」へ。あわせて `sec_pit.py` の vintage
ソートキーが `(filed, acceptance_datetime, accn)` から
`(availability_date, acceptance_datetime, filed, accn)` へ変わり、
availability を第一キーにする順序へ揃えられた。

**Sample gate** — `hold` → **`pass`**。261 success cache で
**strict both split n=413**（要求 200 を超過）、training 2,195 行。
追記4 で残っていた n 不足は解消。

### 最大の変更 — universe 選定の根本修正

`docs/contracts/b9-m6-protocol.json` という事前登録プロトコルが新設された。

```json
"historical_seed": {
  "source_url": "https://www.sec.gov/Archives/edgar/full-index/2016/QTR1/master.idx",
  "forms": ["10-K"], "filed_start": "2016-01-01", "filed_end": "2016-03-31",
  "requested_cik_count": 300, "selection_method": "evenly_spaced_cik_rank"
}
```

seed が **2016年Q1に実際に10-Kを提出した企業**になり、Frames API（現在時点の
集約）を過去へ適用する構成が完全に排除された。追記4 で指摘された
look-ahead / survivorship への根本対処である。

### 追加された部品

| ファイル | 役割 | 規模 |
|---|---|---:|
| `docs/contracts/b9-m6-protocol.json` | 事前登録プロトコル | — |
| `src/quant_textbook/sec_cache_integrity.py` | cache manifest・hash・archive parity 検証 | 453行 |
| `tools/audit_sec_b9_panel.py` | derived artifact の detached 再監査 | 1,869行 |
| `tools/prepare_sec_b9_seed_cohort.py` | EDGAR full-index からの seed cohort 生成 | 302行 |
| `tools/prepare_us_federal_holiday_manifest.py` | 営業日カレンダーの固定・hash 化 | 87行 |

### fail-closed の実データ確認

Claude の60社キャッシュで再走したところ、次の順に拒否された。手作りキャッシュでは
通らない。パラメータの後付け変更を防ぐ設計として妥当。

1. `manifest.json` 不在 → cache integrity 検証で拒否
2. batch manifest の schema 不一致（`caches` / `failures` / `requested_cik_sha256`）
3. `--protocol` 未指定 → `batch-cache runs require an explicit B9 M6 protocol`
4. seed / holiday manifest 未指定 → 拒否

Claude の60社アドホック cache は seed manifest と整合しないため、試走はここで打ち切り。

### 所感と残件

**新たな指摘はない。** 質が一段上がっており、「n が足りない」に対して社数を
増やすのではなく universe の定義自体を EDGAR full-index に置き換えて
survivorship を構造的に排除し、protocol・cache integrity・detached audit で
後付け変更を封じている。残る境界（代表性を主張しない、detached audit は
availability 順序と manifest の再検証に留まる、retry/backoff、
dynamic historical universe、raw filing text）も明示列挙されている。

コミット前の確認事項として、`docs/contracts/` と `tools/prepare_*`、
`src/quant_textbook/sec_cache_integrity.py` などが untracked のままなので
`git add` 漏れに注意。

---

## Codex feedback — M6 最終確認（2026-08-11）

### 結論

Opus の追記5の評価に同意する。M6 は、B9 の model selection ではなく、実データを使った
再現可能な分析を開始できるかを判定する **data gate** として完了している。現行ツリーでは
新たな P1 は確認されない。

最終 artifact を同じ外部 cache から再生成し、以下を確認した。

| 検証 | 結果 |
|---|---|
| requested seed / cache success | 300 / 261 |
| fixed-anchor cohort / valid panel | 164 CIK / 4,631 rows・163 CIK |
| strict both holdout | 413 rows・38 CIK・183 availability dates |
| corresponding training partition | 2,195 rows・102 CIK・534 availability dates |
| detached audit `--require-modeling-gate` | accepted、全 `checks=true` |
| project regression tests | 364 passed |
| Ruff / format / `git diff --check` | pass |

### 既に解消された指摘

- 現在の Frames を過去へ遡及する look-aheadは、2016 Q1 exact `10-K` seedと固定protocolで
  解消した。一方、固定anchor cohortの選択・後続filingの欠落に伴う一般的なselection / attrition
  riskまで排除したとは主張しない。
- `filings.files` archive、acceptance metadata、raw file hash、child manifestを
  fail-closedで検証する。
- 同日または非隣接availabilityのpairは黙って補間せず、除外理由・件数・影響CIKをqualityへ残す。
- `both` holdoutの行数だけでなくtraining非空・企業数・availability date数もgateへ含めた。
- README、plan、M6 update noteの旧 `n=84` と「前四半期Assets floor」表記を現行の
  `n=413`・anchor時点floorへ更新した。

### 次段階へ繰り越す P2

1. `fetch_sec_b9_cache.py` は、429/5xx/timeoutのbounded retry/backoffと、issuer単位の
   stagingからのatomic publishをまだ持たない。次回取得器改善で対応する。
2. detached auditは raw SEC payload と raw batch manifestを再読せず、derived artifact、
   seed/holiday/protocol、埋め込みcache-integrity summaryを検証する範囲に限定する。
   accession、filing date、acceptance datetimeから availability を再計算するhard auditが必要なら、
   row-level provenanceを別設計する。
3. 固定anchor cohortは deterministic feasibility cohortであり、米国企業全体や産業構成の
   代表性は主張しない。dynamic historical universeはAdvancedへ分離する。

### 推奨する次の作業

M6 artifactを変更せず、B9の pre-analysis specification を作成する。少なくとも
estimand、feature availability、raw filing textの取得範囲、candidate set、primary/secondary
metrics、locked evaluation、no-model-selected規則を先に固定し、その後にNotebookとmodel
tournamentを実装する。raw SEC cacheは引き続きrepositoryへ追加しない。

コミット時は、M6の新規ファイルを含む `analytics/quant_research` の変更一覧を確認し、
untrackedのprotocol、cache-integrity、seed/holiday preparation、panel/audit toolとテストを
stage漏れなく取り込む。現時点ではまだcommit/pushしていない。

---

## 追記6: スコープ確定 — 座学教科書に限定（2026-08-11、user 決定）

user から本教材の目的が明示された。**作りたいのは基本的に座学の教科書**であり、
プロジェクトワークや実習系（原典 Stage 3、Capstone）は**単なるプレースホルダー**
として扱ってよい。

### 決定の理由

原典 Stage 3（R1–R4、Week 45–60）の成果物は、20–30本の文献マップ、3–5頁の提案書、
10分の口頭発表、既発表論文の再現、オリジナル拡張、12次元の robustness matrix、
8–12頁の論文、15分発表 + 15分の口頭防御、そして `paper.pdf` / `slides.pdf` /
`model_card.md` / `reproduce.sh` を含む最終リポジトリである。Notebook でも
Jupyter Book でもなく、**成果物の種類が異なる**。

Capstone（Liquidity-Aware No-Arbitrage Intraday JGB Curve）は JGB の bid/ask・約定・
先物・CTD・implied repo・intraday を要求するが、Stage 2 の feasibility spike で
**取得不能**と判定済み。原典仕様のままでは到達できない。

### 完成度の再計算

Stage 3 と Capstone を分母から外すと、実質のスコープは **B1–B11 の44週**。

| 尺度 | 完成 | 全体 | % |
|---|---:|---:|---:|
| 週 | Week 1–32 | 44週 | **73%** |
| ブロック | B1–B8 | 11 | **73%** |

（従来の「60週を分母」だと 53%、Stage 3 の性質差と Capstone 到達不能を織り込むと
実態は45%前後、という見積もりを出していた。分母の定義が変わったので置き換える。）

### 残り3ブロック・12週の重さ

| Block | Weeks | 主題 | 残作業の実感 |
|---|---|---|---|
| B9 | 33–36 | Deep Learning & Foundation Models | **軽い**。PIT データ基盤（`sec_pit.py`、`sec_cache_integrity.py`、`audit_sec_b9_panel.py` 1,869行、M6 protocol、261社 cache、strict split n=413）が完成済みで、残るは章執筆 |
| B10 | 37–40 | 科学計算・データシステム・ML工学 | **中**。W38 研究ソフトウェア工学は既存26モジュール・364テストがほぼ実体を持つ。W39 の PIT join も完成済み。新規は DuckDB/Parquet/Arrow、並列・JIT・GPU、model registry・drift 監視 |
| B11 | 41–44 | Quant Research Specialization | **重い**。ほぼ新規。マイクロストラクチャは bid/ask も約定も無いため B7/B8 同様に題材の再設計が要る |

体感の配分は **B11 > B10 > B9**。

### 要対応: scope note の書き換え

`curriculum_map.yml` の scope note が現状こうなっている。

> B9以降、Stage 3、Capstoneは**後続設計で扱い**、この32週の完了を全課程修了とはみなさない。

「後続設計で扱う」だと Stage 3 と Capstone も実装する前提に読める。実際 Codex は
Capstone のデータ実現可能性まで調査していた。**プレースホルダーと明記しないと
そこへ工数が流れる。**

書き分けるべき区分:

- **B9–B11**: 実装予定（残12週）
- **Stage 3（R1–R4）・Capstone**: 原典に存在するが本教材では**プレースホルダー**。
  座学の対象外であり、設計も実装も行わない

`curriculum_map.yml` の `scope`（`excludes` の表現を含む）と README の1〜2行の修正で足りる。
本追記時点では未実施。

---

## 追記7: B9 実装完了レビュー（2026-08-11 16:0x）

対象は `d2c60655 Clarify quant textbook scope` と `51a117e9 Implement B9 deep learning textbook`。
リポジトリ内ファイルは変更していない。

### 0. 追記6 の依頼は完了している

`curriculum_map.yml` は v1.3 → **v1.4**。私が指摘した scope note の
「B9以降、Stage 3、Capstoneは後続設計で扱い」は書き換えられ、さらに要求以上に
機械可読な `textbook_target` ブロックが追加された。

```yaml
textbook_target:
  blocks: [B1, ..., B11]
  week_range: [1, 44]
  duration_weeks: 44
  implemented_weeks: 32
  completion_percent_rounded: 73
excludes:
  - Stage 3（R1–R4、placeholder・座学教科書の対象外）
  - Capstone Research Program（placeholder・取得不能なJGB intradayを要求するため対象外）
```

「実装予定の B9–B11」と「対象外の Stage 3/Capstone」が構造として分離された。
この件はクローズ。

### 1. 再現できた主張（すべて自分で実行）

| 主張（更新ノート） | 私の実測 | 判定 |
|---|---|---|
| full tests 391 passed | **403 passed / 6.79s** | 一致（差分12は未コミットの B10 テスト） |
| 54 Notebook が valid Python・決定的 JSON | `build_notebooks.py --check` = `checked 54 notebooks` | 一致 |
| clean-kernel 実行 error 0・execution count 連続 | 54冊全走査で error output 0、`execution_count` は全冊 1..n の連番 | 一致 |
| fixture SHA-256 `6487c205…` | 実ファイル hash 一致 | 一致 |
| fixture に outer / CIK / accession / 本文を含まない | JSON の全キーを走査。存在するのは `row_id` `entity_id`（いずれも hash、86 entity）`numeric_features` `token_hashes` `target` `document_sha256` `partition` `target_available_date` のみ。partition は inner_train 192 / inner_validation 64、`target_available_date` の最大は **2023-08-09**（cutoff 2023-10-23 より前） | 一致 |

leak 対策は宣言でなく構造で担保されている。fixture に CIK も accession も本文も
物理的に存在しないので、Notebook 側の実装ミスで漏れる経路が無い。

**結果自体も誠実である。** teaching fixture 上の順位は
`zero (MAE 0.049469) < hashed_tfidf_ridge (0.061339) < numeric_ridge (0.069652) < numeric_mlp (0.129996)`
で、**MLP が最下位、zero が最良**。決定は `no_model_selected`。
B5–B8 で維持してきた「単純 baseline が強い」という傾向を、deep learning の章で
都合よく曲げていない。

### 2. 新規の指摘 — baseline ladder が契約と実行で食い違う

**F1（Notebook 内部の不整合）**

`53_b9_project_sec_filing_forecast.ipynb` の cell 5「Frozen Project contract」表は

> comparators | **pooled drift**、TF–IDF ridge

と宣言している。しかし同じ Notebook で実行される baseline 表は
`zero` / `numeric_ridge` / `hashed_tfidf_ridge` / `numeric_mlp` の4本で、
**pooled drift が計算されていない**。`seasonal` と `company_mean` も無い。
pre-analysis contract (`b9-preanalysis-v1.json`) の
`models.fixed_baselines = ["zero","pooled_drift","seasonal","company_mean"]` とも
食い違う。契約表を2セル前に見せてから、その契約と違う実験を走らせている。

**F2（こちらが本題：pre-registered gate の denominator が弱い baseline になっている）**

`b9-preanalysis-v1.json` の採用 gate は

> Nominee MAE must improve at least 1 percent over **pooled_drift**, median absolute
> error and company-macro MAE must not worsen, …

だが、pooled drift は ladder の中で最強とは限らない。実測すると:

| 測定 | zero MAE | pooled drift MAE | zero medAE | pooled drift medAE |
|---|---:|---:|---:|---:|
| M6 strict both holdout（GPT 公式値、n=413） | 0.042028 | 0.042017 | **0.018403** | 0.020048 |
| teaching fixture inner_validation（私が計算、n=64） | **0.049469** | 0.052255 | **0.020475** | 0.024510 |

- 公式 M6 では pooled drift の MAE 優位は **0.026%** しかなく、**medAE では zero が 8.9% 勝っている**
- teaching fixture では **MAE でも zero が 5.3% 勝つ**（fixture の pooled drift は
  μ=0.020072。裾の重い分布で train 平均が上振れし、drift 予測が悪化している）

したがって現在の gate 文言では、**zero に MAE でも medAE でも負けている候補が
「pooled_drift より 1% 改善」を満たして採用されうる**。加えて
「median absolute error … must not worsen」は**何に対して**悪化しないのかが
書かれておらず、pre-registered contract としては解釈の余地が残っている。

修正案（tournament を始める前なら JSON の1行）:

```
model_selection_gate の denominator を pooled_drift 固定ではなく
「ladder 4本の各 metric における最良値」とする。
つまり MAE は min over {zero, pooled_drift, seasonal, company_mean}、
medAE・company-macro MAE も同様に最良値を基準に「悪化しない」を定義する。
```

契約がまだ JSON にしか無く、full tournament が未実行の今なら安い。
nominee manifest を凍結した後だと直せない。

**自分の過去の指摘の訂正**: 私は
`_docs/2026-08-11-sec-baseline-gate.md` §3(3) で「pooled drift が zero を安定して
上回った（+2.14%）ので ladder に入れよ」と書いた。あれは frame `CY2015Q4I` から
選んだ survivorship 込みの60社パネル上の測定で、**PIT で固定した cohort では
その順位が成立しない**。「ladder に pooled drift を含めよ」は依然として正しいが、
「pooled drift が超えるべき基準である」は誤りだった。F2 はその訂正でもある。

### 3. B10 は着手済み（未コミット）

| ファイル | 行数 | 状態 |
|---|---:|---|
| `src/quant_textbook/data_systems.py` | 307 | PIT snapshot（pandas / SQLite 2実装）、schema evolution 監査、columnar memory 監査 |
| `src/quant_textbook/research_engineering.py` | 312 | benchmark、決定的 chunk 分割、experiment run / registry / promote / rollback、drift report、batch inference |
| `tests/test_data_systems.py` + `tests/test_research_engineering.py` | 270 | **12 passed** |

`__init__.py` へ export 済み。Notebook と `curriculum_map.yml` の B10 週定義はまだ無い。
B9 と同じ「library を先に固め、そこから章を生成する」順序なので進行としては正常。
`point_in_time_snapshot` を pandas と SQLite の2実装で持っているのは、W39 のデータ
システム章で「同じ PIT 意味論を2つの実行基盤で再現する」教材にする意図と読める。

### 4. 完成度

**36 / 44 週 = 82%**（B1–B9 完了、54 Notebook）。追記6 時点の 73% から +9pt。
残りは B10（W37–40、着手済み）と B11（W41–44、未着手）。

### 5. 残る未対応（追記3 から継続）

- B6-W24: `purging` / `embargo` / `grouped split` が
  `34_week24_evaluation_under_shift.ipynb` の本文に無い（map では Core）。
  `embargo` は `curriculum_map.yml` 以外のどこにも出現しない
- B6-W21: `bagging intuition` が B6 各章に無い

---

## 追記8: ステータス/マイルストーン確認（2026-08-11 18:0x）

対象は `83d46154` (B10) / `d3b0b699` (B11 着手) / `085d76eb` (追記7 への対応)。

### 1. 追記7 の指摘は全件対応済み（再実行で確認）

GPT は `docs/updates/2026-08-11-opus-alignment-follow-up.md` で応答している。

**F2（gate denominator）** — 対応は要求以上。`b9-preanalysis-v1.json` の
`primary_comparator` が `"pooled_drift"` という文字列から、
「inner validation の MAE 最小の fixed baseline、tie-break 順固定、outer 前に freeze」
という規則オブジェクトへ変わった。私が指摘していない点も2つ潰している。

- 「medAE が悪化しない」の比較対象が未定義だった件 →
  `secondary_guardrail_comparator_rule` で metric ごとの4本最小値と明記
- outer で comparator を選び直す抜け穴 → `outer_uncertainty_comparator` で
  inner から凍結した identity のみを使うと固定

さらに**改訂の作法が正しい**。`amendments[]` に `previous_contract_sha256`、
改訂時点で観測済みだった情報、理由、非変更範囲を残し、
`status` を `preregistered_before_candidate_evaluation` →
`amended_before_full_candidate_evaluation` へ落としている。
pre-registration を後から書き換えたのではなく、改訂を記録した形になっている。

**F1（実行される ladder が契約と不一致）** — 解消。NB53 は4本すべてを実行:

| baseline | MAE | medAE | company-macro MAE |
|---|---:|---:|---:|
| **zero** | **0.049469** | **0.020475** | **0.043651** |
| pooled_drift | 0.052109 | 0.024111 | 0.046102 |
| company_mean | 0.064327 | 0.031272 | 0.055345 |
| seasonal | 0.069820 | 0.020475 | 0.062704 |

fixture の primary baseline は `zero` に凍結された。私の追記7 の主張どおり、
pooled drift を denominator に固定していたら zero に負ける候補が通り得た。

（私の追記7 の pooled drift は MAE 0.052255、GPT は 0.052109。私は train 平均の
一括適用、GPT は availability を見た PIT 版なのでこの差。順位の結論は同じ。）

fixture に `baseline_predictions` が追加され hash は
`953c9b06c6c1dc1ef68c5e21f1ee88c4fe20d1ee34d5887150e51843184ad0b0` へ更新。
再計算して一致を確認。row 数 256、partition 192/64、
`target_available_date` 最大 2023-08-09、CIK/accession/本文は依然として非存在。

**B6 の2件（追記3 から継続）** — 解消。
`31_week21_trees_boosting.ipynb` に bagging（$\operatorname{Var}(\bar e)=\sigma^2(\rho+(1-\rho)/B)$、
moving-block bootstrap 24 stump、single 7.204943 bp 対 bagged 7.210941 bp で
**改善しないことをそのまま提示**）。
`34_week24_evaluation_under_shift.ipynb` に grouped split / purge / embargo を
3本の独立 guard として追加し、実行結果は grouped 0 / purge 1 / embargo 0、
**適用しない理由も表に残す**形。儀式的に全部適用しない設計は妥当。

これで追記1〜7 の未対応指摘は**ゼロ**。

### 2. 私の再実行結果

| 項目 | 実測 |
|---|---|
| tests | **413 passed** / 7.24s（ノート記載と一致） |
| notebooks | **60冊**、`build_notebooks.py --check` 通過 |
| fixture hash / contract hash | 両方ノート記載値と一致 |
| B6 キーワード | `bagging`→nb31、`embargo`/`grouped split`→nb34 に実在 |

補足（欠陥ではない）: fixture の `seasonal` は validation 64行のうち
**39行（61%）で4四半期ラグが無く予測0**に退化する。medAE が zero と完全一致
（0.020475）するのはこのため。metric ごとの最小値を取る新 gate では害は無いが、
「seasonal がここでは実質 zero の劣化版」という点は教材本文で触れる価値がある。

### 3. マイルストーン

**40 / 44 週 = 91%**（B1–B10 完了、60 Notebook）。追記7 の 82% から +9pt。
`curriculum_map.yml` の `textbook_target.implemented_weeks: 40` /
`completion_percent_rounded: 91` と README が同期している。

残りは **B11（W41–44）のみ**。`quant_specialization.py`（326行）+ tests（111行）と
実装計画 `docs/plans/2026-08-11-stage-2e-b11.md` は commit 済み、Notebook 6冊は未着手。

B11 の設計判断は妥当。取得不能な JGB intraday capstone を実装せず、
公式 Treasury curve + FINRA Treasury Daily Aggregates を使う
「Treasury Curve Forecast-to-Decision Specification」へ置換し、
**主張してよい観測と主張できない観測の対応表**を先に置いている
（par curve は indicative bid-side quotation であって transaction でも zero curve でも
ないという区別を Core に据えているのが良い）。

### 4. 唯一の未解決リスク: FINRA が access gate を通っていない

B11 Week 42 は FINRA Treasury Daily Aggregate Statistics を Core データ源とする。
しかし `FINRA` の文字列は **`docs/plans/2026-08-11-stage-2e-b11.md` にしか存在しない**
（`docs/updates/`、`docs/contracts/`、`src/`、`tools/`、`tests/`、`notebooks/` に無し）。

Treasury と SEC は Access / Semantics / Sample / Baseline / Teaching fit の5 gate を
通してから Core に入れた。FINRA は同じ手続きを経ていない。特に確認すべきは:

1. **利用条件** — FRED/ALFRED は ToS の ML/AI 利用制限で不採用にした前例がある。
   FINRA data の再配布・派生物の条件を先に読む必要がある
2. **実際に落ちるか** — daily file の URL 形式、認証要否、履歴の遡及範囲
   （2023-02-13 以降の公開開始という制約は plan に記載済み）
3. **snapshot + manifest + hash** — Treasury と同じ再現契約に載るか

Notebook を書き始めてから「取れない／使えない」と判明すると、B9 の
中央銀行 intraday → SEC 置換と同じ規模の再設計になる。
Notebook 着手前に feasibility spike を1本入れるのが安い。

---

## 追記9: B11 完了・B9 tournament レビュー（2026-08-11 21:0x）

対象は `60ca6fed`（FINRA gate）/ `63868f23`（B11）/ `5202dce3`（B9 tournament runner）/
`73d1f93b`（LSTM training loop）。

### 0. マイルストーン: 教材本文は 44/44 週 = 100%

66 Notebook、`implemented_weeks: 44` / `completion_percent_rounded: 100`、README も同期。
自分で再実行して **418 passed / 66 Notebook の決定的 JSON check 通過**を確認した。

ただし「100%」は**座学教材の実装**が完了した意味であり、実証系は2本未完である
（README はこの区別を明示している）。

1. B9 locked outer 413行は未開封、正式 decision は `no_model_selected`
2. FINRA API access/terms gate は未通過（Week 42 は fixture 限定で成立させている）

### 1. FINRA gate — 私のノートへの対応は期待以上

`_docs/2026-08-11-b11-finra-access-gate-warning.md` に対し、GPT は Notebook 着手**前**に
`docs/updates/2026-08-11-b11-finra-feasibility.md` を作り、**条件付き未承認**で止めた。
私が最優先に挙げた「利用条件」を実際に読み、私が想定していなかった問題も見つけている。

- **FINRA Website Terms が ML/AI・predictive analytics への利用を制限**している
  → daily file ページの定期 scrape 方式は不採用と決定（FRED/ALFRED と同じ判断）
- Query API の Fixed Income Specific Terms は non-commercial internal use を認めるが
  **credential 必須**。実際に叩いて production / mock とも **HTTP 401** を確認
- public daily file 自体は HTTP 200 で取得でき、2023-02-13 以降の URL パターンと
  フィールド意味論は確認済み（取得物は `/tmp` のみ、repository へは未保存）

そのうえで私が提案した退避先をそのまま採用し、**Week 42 を fixture 限定で実装**した。
`curriculum_map.yml` の B11-W42 は validation 条件そのものが

> real FINRA rows はgate未通過時に0である

になっており、**gate の状態がそのまま教材の検証項目になっている**。
design_corrections にも「API access/terms gate 通過後だけ real-data Core へ昇格」と固定。
実行結果も `bid_ask_quote` / `queue_position` を `observable=False, not in aggregate` と
表示し、quote fixture 上で quoted/effective/realized spread の恒等式検算に留めている。
「取れないデータを合成しない」を教材化する B9 と同じ手が使われている。

### 2. B9 development tournament — outer 未開封をコードで確認

初の candidate run が development partition のみで完了。結果は次のとおりで、
**zero baseline を1%以上改善した候補は0件**、`no_model_selected`（implemented-family interim）。

| model | MAE | medAE | company-macro MAE |
|---|---:|---:|---:|
| **zero** | **0.060331** | **0.024565** | **0.058765** |
| pooled drift | 0.061785 | 0.027180 | 0.059529 |
| best TF-IDF ridge (5,000/bigram/λ=10) | 0.062185 | 0.028265 | 0.060161 |
| best numeric ridge (λ=10) | 0.064360 | 0.028308 | 0.062015 |
| best NumPy MLP (width=16/lr=.003) | 0.099851 | 0.063130 | 0.096723 |

`tools/run_b9_tournament.py` を読んで確認した点:

- outer は**行数を数えて contract 値と照合するだけ**で、特徴量・本文・予測は読まない
  （`outer_accessed: False`、`outer_access_policy: "counted only; …"`）
- development / outer の行数が contract と1行でも違えば `ValueError` で停止（fail-closed）
- inner train と inner validation に**同一 normalized document family が跨いだら例外**
- 分割 cutoff は contract JSON から読む。runner にハードコードしていない
- 1,504 + 691 = 2,195 ✓ / outer 413 ✓（M6 と一致）

数字も内部整合しており、「deep model が勝たなかった」ことをそのまま書いている点も一貫している。

### 3. 指摘F1（本題）— inner selection の generalization 軸が outer と違う

`b9-preanalysis-v1.json` の `splits` を読むと:

| partition | 規則 |
|---|---|
| development | `target_available_date < 2023-10-23` **かつ** `cik % 3 != 0` |
| inner train | development のうち `< 2021-01-01` |
| inner validation | development のうち `>= 2021-01-01` |
| **locked outer** | `>= 2023-10-23` **かつ** `cik % 3 == 0` |

**inner validation は時間分割のみ**で、validation の68社はすべて inner train の102社に
含まれる。一方 **outer は company-disjoint**（cik % 3 == 0 の38社は development に一度も
現れない）。つまり

> **model 選定は「既知企業・将来期間」でしか測っていないのに、
> 最終評価は「未知企業・将来期間」で行う。**

選定基準が測っていない軸で最終評価する構造なので、企業固有の癖を覚えた候補が
inner を通って outer で落ちる（あるいは逆順位になる）余地が残る。
M6 gate 自身が time / company / both の3分割を出し、**strict both を採用基準にした**
経緯があるので、プロジェクト自身の基準より inner 側が緩い。

**修正は安く、今なら間に合う**（nominee freeze 前）。development は
`cik % 3 ∈ {1, 2}` なので、**新規データなしで company-disjoint な inner fold が作れる**。

```
案: inner selection を2軸にする
  axis-T（現行）: development 内の時間分割（< 2021-01-01 / >= 2021-01-01）
  axis-C（追加）: development 内の企業分割（cik % 3 == 1 で学習 / == 2 で検証、および交換）
  採用条件: 両軸で amended gate（best fixed baseline から MAE 1%以上改善、
            medAE・company-macro MAE 非悪化）を満たすことを要求する
```

development は102社・2,195行あるので、企業分割しても各側 ~51社・~1,100行が残り、
統計的に成立する。nominee manifest を凍結した後だと契約改訂になるため、
tournament に family を足す**前**に決めるのが安い。

### 4. 指摘F2 — provenance 表の SHA-256 が壊れている（49文字）

`docs/updates/2026-08-11-b9-development-tournament.md:27`

```
| previous-filing sidecar | 9ff2efef335357f4b2e8799fc4ee5d830c55843a50026fbbc |   ← 49 chars
```

正しい値はリポジトリ内の他4箇所（`2026-08-11-b9-filing-provenance.md:63`、
Notebook 49 / 50 / 53 の実行出力）で一貫して

```
9ff2efef335357ff53bb1e4ba5c57f4b2e8799fc4ee5d830c55843a50026fbbc            ← 64 chars
```

であり、更新ノート側だけ中央の14文字（`f53bb1e4ba5c57`）が欠落している。
SHA-256 として長さが成立しないので、再現性を確認しようとした読者はここで必ず失敗する。
tournament ノートは「入力 fingerprint を再現性の主対象とする」と宣言している表そのものなので、
影響は小さくない。1行の修正。

### 5. 指摘F3 — README に古い記述が残って自己矛盾している

`README.md` の同一箇所（6行差）で逆のことを書いている。

- 343–346行: development-only の第1候補 run は**完了**、implemented-family interim は
  `no_model_selected`
- 352–353行: 「**full 2,195-row candidate search**、company-cluster bootstrap、
  nominee manifest、outer一回評価は別の empirical milestone として**未実行**である」

352行は B9 実装時（`51a117e9`）の記述が `5202dce3` 後も残ったもの。
実際には full 2,195-row development search は実装済み family について完了しており、
未実行なのは LSTM / TCN / self-attention / joint family、bootstrap、nominee freeze、outer。
読者はどちらが現状か判断できない。352–353行を残りの4項目に限定する形へ更新すべき。

### 6. 状態

追記1〜8 の未対応指摘はゼロのまま。本追記で新規3件（F1 が実質、F2・F3 は各1行）。
