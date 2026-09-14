# johnhull 全節監査（2026-09-14）

Hull 11e（Global Edition）の全 306 節と、vol 13–28 の成果物を読み直した棚卸し。
「何が実装済みか」「意図的に先送りしたもの」「今できるもの」を、コードの現状と照らして整理する。

## 前提と方法

- **対象の状態:** `main` の `cae1cd84`（2026-09-14）。vol 28 の `c7194c5d` を含む。
- **節の一覧:** `johnhull/options, futures and other derivatives 11th.pdf` の PDF アウトライン。番号付き 299 節と付録 7 本。
  - Summary / Further Reading / Practice Questions は除外した。
  - 節番号は GE 版で、US 版とはずれる。
- **監査の進め方:** 8 系統を読み取り専用で並列に監査した。
  - 読んだもの: spec・plan・`PROGRESS.md`・巻別 `VALIDATION.md`・ノートの builder・hullkit のソースとテスト。
  - 判定の根拠: `grep` と、scratchpad でのプローブ実行。
  - 監査中はファイルを変更していない。
- **パス:** すべて repo ルート（`/home/kazumasa/projects`）からの相対パス。
- **記号:**
  - ✅: 監査後、メインセッションで実物を再確認したもの。
  - 無印: 監査エージェントの報告（根拠は `grep` / プローブ）。未再確認。
- **実行可否:**
  - `now`: オフラインで、印刷値・恒等式・極限・再計算のどれかで検証できる。
  - `decision`: 公開 API の出力か release 契約が変わる。
  - `blocked`: 外部要因がある。
- **規模の目安:**
  - S: 数時間以内
  - M: 半日〜2 日
  - L: 数日以上、または新しい巻
- **節の分類:**
  - code: hullkit のシンボルとテストがある
  - code*: hullkit にシンボルとテストはあるが、その節のノートから参照されていない（後続巻で実装されたもの）
  - nb: ノート builder の中で計算しているだけ
  - md: 説明文だけ
  - absent: どこにも言及がない
  - qual: 定性的な節で、計算対象がない

## 0. 要約

- **節単位のカバレッジは「全 37 章カバー」より薄い。**
  - 計算対象 243 節の内訳: code 107（code* を含む）、nb 54、md 47、absent 35。
  - 残り 63 節は qual。
  - 章単位の「全章カバー」は成り立つが、節単位では 82 節（md+absent）に計算がない。
  - この集計は、レビュー（§10）で見つかった分類の不整合を抜き取りで直した後の値。節別台帳からの再集計はまだしていないので、数節の増減はあり得る。
- **code の節でも、Hull の印刷値ではほぼ固定していない。**
  - テストの多くは合成値で固定されている。
  - 第 13 章は US 版の値（r=12%）で固定している。
  - 監査で試した印刷値は、既存関数でほぼ再現できた。印刷値でテストを固定する作業は、コストが低く効果が大きい。
- **実物で確認した欠陥が 11 件ある（§2）。** 内容は、計算の誤り・常に PASS する検査・古い出力。
- **「acceptance はコミット済み配列から再計算する」という主張は、どの巻でも全面的には成り立たない。**
  - 配列からの検査と保存値への依存は、巻ごとに混在している。vol 27–28 は再計算を拡充したが、原始入力（hazard、損失標本など）からの独立検証は全面的ではない。
  - メモリ内で入力を変えて `evaluate_acceptance` を呼ぶと、vol 28 は `cds_bootstrap_hazard` や `cds_survival` を全 0 にしても 17/17 PASS、vol 27 は `gpd_losses` を全 0 にしても 14/14 PASS のまま。一方 vol 22 の `variance_clock` や vol 26 の元本・YoY 配列を壊すと FAIL する（§10）。
  - 検査の種類は、形状・有限性の検査、保存結果の再集計、原始入力からの再価格・再推定に分けて記録する必要がある。
  - vol 19–28 の JSON の改ざんは、原則として `make hull-artifacts-check` の再構築で検出できる。ただし vol 21 の計測値（speedup、対応する acceptance の observed、NPZ の companion hash、timing 配列）は比較から明示的に除外されている（`johnhull/scripts/verify_frontier_artifacts.py:23-46`）。
- **外部要因で止まっているものは少ない（§8）。**

## 1. 節カバレッジ

### 1.1 巻別

| 巻（章） | 節 | code | nb | md | absent | qual |
|---|---:|---:|---:|---:|---:|---:|
| 01（13, 14） | 21 | 17 | 1 | 2 | 0 | 1 |
| 02（10, 11, 12, 17, 18） | 41 | 12 | 7 | 6 | 6 | 10 |
| 03（19） | 15 | 10 | 1 | 0 | 1 | 3 |
| 旧 `notebooks/bsm_chapter15`（15） | 13 | 6 | 6 | 0 | 1 | 0 |
| 04（2–6） | 49 | 10 | 12 | 6 | 2 | 19 |
| 05（20, 23） | 16 | 6 | 6 | 1 | 1 | 2 |
| 06（21, 27） | 16 | 7 | 2 | 5 | 2 | 0 |
| 07（7, 34） | 19 | 2 | 4 | 7 | 1 | 5 |
| 08（22） | 9 | 5 | 2 | 1 | 0 | 1 |
| 09 + 28（9, 24, 25） | 24 | 15 | 1 | 5 | 1 | 2 |
| 10（26, 28） | 25 | 8 | 3 | 3 | 11 | 0 |
| 11（29, 30） | 8 | 4 | 1 | 1 | 2 | 0 |
| 旧 `interest_rate_models`（31–33） | 15 | 3 | 3 | 2 | 5 | 2 |
| 12（1, 8, 16, 35, 36, 37） | 35 | 2 | 5 | 8 | 2 | 18 |
| **計** | **306** | **107** | **54** | **47** | **35** | **63** |

判定の粒度は監査系統ごとに少し差がある。後の巻で実装された節は code* として code 列に数える（§4.2 → `rfr:compounded_rfr`、§3.4 → `weather:optimal_basis_hedge`、§6.3 → `rfr:compounded_rfr`、§28.1 → `sde:girsanov_weights`）。レビューで見つかった不整合は次のとおり直した（§10）。
- vol 12 の行は合計が 34 だった。§1.2 の nb（1.3、8.1、16.4、35.4、36.5）に合わせて nb を 5 にした。
- §3.4・§6.3・§28.1 を nb から code* に、§7.2 を absent から md に（`volumes/07_swaps/build_swaps_notebook.py:277-282` に OIS の説明がある）、§36.4 を qual から absent に（GE p.806-807 に Schwartz–Moon の確率過程と MC 手順があり、実装は 0 件）変えた。
- 分類（実装の有無）と印刷値の再現可否は別の項目として扱う。節 ID・分類・実装シンボル・テスト・ノート・判定理由を持つ節別台帳は未作成で、巻表と章表はまだ手集計。

### 1.2 章別

`*` は部分的な実装。節番号が監査で特定できなかった章は件数だけを書いた。

| 章 | 節 | code | nb | md | absent | qual |
|---|---:|---|---|---|---|---|
| 1 | 10 | — | 1.3 | 1.5, 1.7–1.9 | — | 5 節 |
| 2 | 11 | — | 2.4 | 2.11 | — | 9 節 |
| 3 | 7 | 3.4*（`weather:optimal_basis_hedge`、乱数データのノートからは未参照） | 3.5 | 3.1, 3.3 | 3.6, 付録 CAPM | 3.2 |
| 4 | 12 | 4.2*（vol 23）, 4.4, 4.6–4.11 | — | 4.5 | — | 4.1, 4.3, 4.12 |
| 5 | 14 | — | 5.4, 5.5, 5.7, 5.9–5.12 | 5.6, 5.14 | — | 5.1–5.3, 5.8, 5.13 |
| 6 | 5 | 6.3*（3M SOFR 決済は vol 23 の `rfr:compounded_rfr`。式 (6.2) の延長や SOFR スタブは FR-03） | 6.1, 6.2, 6.4 | — | — | 6.5 |
| 7 | 13 | 7.6, 7.9 | 7.1, 7.7 | 7.2（OIS の説明のみ、Table 7.3 は FR-01）, 7.5, 7.8, 7.13 | 7.10 | 7.3, 7.4, 7.11, 7.12 |
| 8 | 4 | — | 8.1 | — | — | 3 節 |
| 9 | 4 | 9.1, 9.2* | — | 9.3, 9.4 | — | — |
| 10 | 12 | 1 | 1 | 1 | 1 | 8 |
| 11 | 7 | 2 | 3 | 0 | 1 | 1 |
| 12 | 5 | 3 | 2 | 0 | 0 | 0 |
| 13 | 12 | 10 | 1 | 0 | 0 | 1 |
| 14 | 9 | 7 | 0 | 2 | 0 | 0 |
| 15 | 13 | 6 | 6 | 0 | 1 | 0 |
| 16 | 5 | — | 16.4 | — | — | 4 節 |
| 17 | 6 | 3 | 1 | 2 | 0 | 0 |
| 18 | 11 | 3 | 0 | 3 | 4 | 1 |
| 19 | 15 | 10 | 1 | 0 | 1 | 3 |
| 20 | 9 | 20.1 | 20.2–20.5, 20A | 20.6 | 20.8 | 20.7 |
| 21 | 8 | 21.1, 21.2, 21.6–21.8 | 21.4 | 21.5 | 21.3 | — |
| 22 | 9 | 22.1–22.4, 22.8（vol 27） | 22.5, 22.6 | 22.9 | — | 22.7 |
| 23 | 7 | 23.2, 23.3, 23.5–23.7 | 23.1 | — | — | 23.4 |
| 24 | 9 | 24.2*, 24.4, 24.6, 24.7*, 24.8*, 24.9* | — | 24.5 | — | 2 節 |
| 25 | 11 | 25.2, 25.4–25.6, 25.9*–25.11* | 25.8 | 25.1, 25.3 | 25.7 | — |
| 26 | 17 | 26.4, 26.9–26.11, 26.13, 26.14 | 26.16 | 26.1 | 26.2, 26.3, 26.5–26.8, 26.12, 26.15, 26.17 | — |
| 27 | 8 | 27.2（vol 14）, 27.8 | 27.1 | 27.3–27.6 | 27.7 | — |
| 28 | 8 | 28.1*（vol 13 の `sde:girsanov_weights`）, 28.7 | 28.3, 28.4 | 28.6, 28.8 | 28.2, 28.5 | — |
| 29 | 4 | 29.1–29.3 | — | — | 29.4 | — |
| 30 | 4 | 30.1 | 30.3 | 30.2 | 付録 | — |
| 31 | 5 | — | 31.2（テストなし） | 31.1 | 31.3–31.5 | — |
| 32 | 7 | 32.1*（HW1F のみ）, 32.2, 32.6 | 32.3 | — | 32.4, 32.5 | 32.7 |
| 33 | 3 | — | 33.1 | 33.2 | — | 33.3 |
| 34 | 6 | — | 34.2, 34.3 | 34.1, 34.4, 34.5 | — | 34.6 |
| 35 | 8 | 35.5（vol 25）, 35.7* | 35.4 | 35.6 | 35.8 | 3 節 |
| 36 | 5 | — | 36.5 | 36.1–36.3 | 36.4（Schwartz–Moon。計算手順はあるがパラメータ σ(t)・η(t) が本文にない、CR-23） | — |
| 37 | 3 | — | — | — | — | 3 節 |

穴が大きい章:
- Ch 26: 9 節が absent。
- Ch 31–33: 金利ツリーも LMM もない。
- Ch 5–6: nb だけで、印刷値の固定がない。
- Ch 8 / 16 / 35 / 36: 数値例にほぼコードがない。

## 2. 確認済みの欠陥（✅）

> 2026-09-14 に D9 以外を修正済み。対応 commit は §11。

| # | 場所 | 内容 | 再確認の方法 | 規模 |
|---|---|---|---|---|
| D1 | `johnhull/hullkit/src/hullkit/rates.py:149` | `bootstrap_zero_curve` は、最初の商品が満期 0.5 年超のゼロクーポン債だと `ValueError: array of sample points is empty` で落ちる。coupon=0 でも `zero_interp` を空の曲線で呼んでいるため。既存テスト（`test_rates.py:105-118`）はこの入力を通らない。 | `bootstrap_zero_curve([(1.0, 0, 97.8)])` で再現した。 | S |
| D2 | `johnhull/hullkit/src/hullkit/swaps.py:44-66` | `irs_value_bonds` / `irs_value_fras` は初回期間を 0 起点の差分で数える。そのため途中から評価するスワップ（期中評価）を誤る。`accrual_to_next` は変動側にしか効かない。 | Hull Ex 7.1 の入力（名目 100、固定 3% 半年払い、支払 0.2/0.7/1.2 年、連続複利ゼロ金利 2.8/3.2/3.4%、次回変動 2.516%（半年複利、Hull の丸め値）、`curve=(times, zeros)`）で、受け固定の価値（名目と同じ単位）は次のとおり。既定引数: bonds = fras = −0.43639。`accrual_to_next=0.5` を渡した bonds = −1.18697。固定クーポンをすべて半年分（1.5）として直接評価すると −0.29200 で、Hull の −0.292（支払固定なら +0.292）に一致する。再現コードは §10。 | S（引数追加は公開 API への追加） |
| D3 | `johnhull/hullkit/src/hullkit/frontier_reference.py:447-448`（vol 22） | 予定イベントの分散 3.5e-4 を、ジャンプ強度 λ·dt への加算（期待ジャンプ回数）として注入している。ジャンプ幅は mean −0.05・std 0.10 なので E[Y²]=0.0125。実際に増える分散は約 4.4e-6 で、意図した値の約 1/80。一方、expiry 検査（`:486-487`）は 3.5e-4 をそのまま使っている。 | コードと `zero_dte.sv_jump_teacher` の既定値を読んで確認した。 | S |
| D4 | vol 21（`johnhull/hullkit/src/hullkit/spx_vix.py:465-472`） | Greek RMSE 25.36 は delta と gamma を混ぜた RMSE になっている。NPZ の値は、`teacher_gamma` が ±4.4e-7（ほぼ 0）、`surrogate_gamma` が 35.507 の定数。指標は実質的に gamma の差だけを見ている。 | `reference/*.npz` の配列を読んで確認した。 | S（指標の定義変更は decision） |
| D5 | `johnhull/hullkit/src/hullkit/frontier_reference.py:941-946`（vol 23） | Hagan 教師グリッドが、満期 [1, 5, 10] と α [0.010, 0.020, 0.040] を `zip` で対にしている。そのため long-maturity 診断と high-vol 診断が同じ行を選び、RMSE が一致する（26.2144）。 | コードで確認した。 | S |
| D6 | `johnhull/hullkit/src/hullkit/frontier_reference.py:2015-2037`（vol 26） | ①`unhedged_normalized_risk=[1,1]` と `hedged_normalized_risk=[0,0]` が固定配列で、`synthetic_hedge_decomposition`（`frontier_acceptance.py:1118-1128`）は名前と固定値しか見ないので常に PASS する。②`floor_decomposition_error` は `adjusted_clean_price = raw + floor`（`:1942`）と同じ式（`:1975`）の差で、定義上 0。`floor_payoff_decomposition`（`:1089-1094`）は自己照合になっている。③`principal_floor_redemption_only=True` と `measure_treatment="nominal_payment_forward"` はリテラルだが、それを読む検査は coupon 誤差・元本配列・YoY 比率差も見る（`:1077-1105`）。リテラルを保ったまま配列を壊すと FAIL するので、「常に PASS」ではない。 | コードで確認した。③は `jgbi_floored_principal[-1]` を unfloored に合わせる、`yoy_jy_ratio` を deterministic に合わせる、の 2 通りでそれぞれ FAIL することを実行して確認した。 | S–M |
| D7 | `johnhull/interest_rate_models/build_ir_models_notebook.py:2014-2019` | HJM と BGM/LMM の「当てはめ」は `mzr.copy()` と `rmse_table[...] = 0.0` の代入だけ。同じノートの LMM 節は Black キャップレットのスライダー（`:1474-1485`）で、LMM のシミュレーションはない。 | コードで確認した。 | S |
| D8 | vol 21 / vol 27 | コミット済みのノート出力と巻別 `VALIDATION.md` が `metrics.json` より古い。vol 21 は `surrogate_speedup_1024` が 914.29、metrics は 781.91。vol 27 は `alloc_normal_var` が 77.53、metrics は 68.81（8c3d4c97 で artifact だけ再生成）。`make hull-notebooks-check` は一時ディレクトリで実行するだけで、コミット済みの出力と照合しない。 | ipynb の出力、`VALIDATION.md`、`metrics.json` を突き合わせた。 | S（再生成）＋ S（照合ゲート） |
| D9 | Jupyter Book（`johnhull/book/_config.yml:6-9`） | `execute_notebooks: "off"` の理由は「実行済み出力をコミット済み」。しかし vol 01–12 と `interest_rate_models/ir_models.ipynb` の 13 冊は実行回数 0・出力 0 でコミットされていて、book ページにはコードしか出ない。vol 13–16 の出力は `application/vnd.plotly.v1+json` だけで、静的 book では描画されない。 | 全 ipynb の出力数を数えた（旧 bsm と vol 13–17 だけ出力がある）。 | M（方式は decision、§7） |
| D10 | `johnhull/hullkit/tests/test_trees.py:9-19` | 第 13 章の固定値が US 版（r=12%: 0.633 / 1.2823）。手元の GE 版は r=4% で f=0.545（p.288-291）、Fig 13.4 は 0.9497。`volumes/01_foundations/PROGRESS.md:12-14` の「GE 準拠」とも食い違う。 | PDF の本文で確認した。 | S |
| D11 | vol 28（2026-09-14 の作業） | ①ランダム回収率・ランダム因子負荷・implied copula・動的モデル・KMV EDF を「documentation only / 説明のみ」と記録したが、vol 28 のノート（`build_frontier_notebooks.py` の `VOLUME_META[28]`）にも vol 09/16 にも説明文がない。②spec（`docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md:46`）が対象とした Ex 24.8（$5.13M）を固定するテストがない。`test_credit.py:53-62` にあるのは合成パラメータの単調性と閉形式一致で、印刷値は未固定。③`volumes/28_credit_desk/VALIDATION.md:95` と `johnhull/VALIDATION.md:264-265` の記述は「Black 型の市場慣行式を使い、**完全版の** Hull–White (2003) の knock-out 扱いは未実装」で、spec :49・:62-63（forward measure の厳密な扱いを除外）とも整合している。`cds.cds_option` は Black 型の knock-out 式（`cds.py:187-199`）なので、記述は逆ではない。ただし「完全版」との相違点（何が未対応か）が文書に書かれていないので、明確化が要る。knock-out しない版の追加は独立した拡張候補（CR-13）。 | `grep` と docstring で確認した。③は初版で「記述が逆」としていたが、レビュー（§10）で訂正した。 | S |

## 3. 監査報告の数値・設計上の問題（未再確認）

| # | 巻 | 内容 | 根拠 | 実行可否 / 規模 |
|---|---|---|---|---|
| R1 | 19 | rBergomi のカーネルは右端点リーマン和なのに、補償項は連続時間の t^{2H} を使っている。離散分散 / t^{2H} = 0.533 で、12 step の E[v_T]/ξ0 = 0.915–0.942。既存テストは η=0 しか見ていない。 | `johnhull/hullkit/src/hullkit/surrogate_data.py:319-324`、`johnhull/hullkit/tests/test_surrogate_data.py:120` | decision（既定出力が変わる。scheme 引数を足すなら now）/ S–M |
| R2 | 20 | Log-HAR の再変換バイアス。exp(E[log]) を平均の予測に使っている。train だけで smearing すると QLIKE が h1 3.545→1.414、h5 0.888→0.690、h21 0.163→0.141 になる（EWMA は 1.316 / 0.458 / 0.053）。 | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:880` | decision（10 モデル集合が `frontier_acceptance.py:301-312` で固定）/ S |
| R3 | 20 | 予測からヘッジへの経路が退化している。パスもヘッジも予測ボラで作るので、予測誤差が P&L に入らない。モデル別・ホライズン別の経済指標もない。 | `deep_hedge_price/src/deep_hedge_price/hedge_capstone.py:91-98` | decision（`strategy_order` 固定）/ M |
| R4 | 22 | Poisson 乱数の消費量が経路ごとに違うため、共通乱数が崩れる（240–300 分の区間で経路の対応 0%）。 | `johnhull/hullkit/src/hullkit/zero_dte.py:357-361` | decision（同じ seed で出力が変わる）/ S |
| R5 | 22 | 14:00 の強度 bump が event 群と non-event 群の両方に入っている。そのため non-event RMSE（0.0225）が event RMSE（0.0116）より大きい。expiry 曲線は手置き。 | `johnhull/hullkit/src/hullkit/frontier_reference.py:425,493` | now / S |
| R6 | 24 | 「dynamic fee は gross LVR を減らさない」は実験結果ではなく構成上の恒等式。手数料なしの裁定終点を使い、fixed と dynamic に同じ reserves と価格を渡している。 | `johnhull/hullkit/src/hullkit/amm.py:101-108,145-147`、`frontier_reference.py:1290-1301` | now（新関数）/ M |
| R7 | 18 | OOD で価格予測が崩れる（MAE 1.606、最大 261.9。polynomial は 0.025）。この数値は git 管理外のローカル評価結果にしかない。 | `deep_hedge_price/scripts/export_johnhull_pricing_reference.py:216-236` | now / S |
| R8 | 21 | サロゲート価格の 7/24 が負、delta の 5/24 が負。サロゲートに hard check をかけていない。 | `johnhull/hullkit/src/hullkit/spx_vix.py:318-340` | now / S |
| R9 | 27 | `tail_risk.mean_excess` に入力検証がない。NaN を黙って除外し、2 次元入力を平坦化する。 | `johnhull/hullkit/src/hullkit/tail_risk.py:264-278`（`_validate_finite_1d` は `:56`） | now / S |
| R10 | 旧 ir_models | 「HJM implied caplet vol」は実際には短期金利の正規 vol で、対数正規の BGM vol と同じ軸で比べている。 | `johnhull/interest_rate_models/build_ir_models_notebook.py:1537-1552` | now / S |
| R11 | 03 | Table 19.1 / 19.4 のヘッジ性能は、Δt ≥ 1 週なら ±0.02 で一致する。0.5 週と 0.25 週は 0.137 / 0.098 で、印刷値は 0.16 / 0.13。Hull は利息と割引を除外し、実装は割引込み。乖離の原因は特定できていない。 | `johnhull/hullkit/src/hullkit/hedging.py:3-8` | decision（コスト規約か許容幅）/ M |

## 4. 未対応項目（open）

「0 件」は、`johnhull/hullkit/src`・`johnhull/volumes/*/build_*.py`・`johnhull/interest_rate_models`・`deep_hedge_price/src` を複数の表記ゆれで `grep` した結果。
「印刷値」は、監査のプローブで既存関数か小さな試作による再現を確認した値。

### 4.1 先物・金利・スワップ（Ch 2–7, 34 / vol 04, 07）

- D1（`bootstrap_zero_curve`）と D2（期中評価のスワップ）は §2 を参照。
- vol 04 はすでに 46 セルある。full-coverage spec（`docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md:87`）のソフト上限 35 を超えている。FR-02〜09 をノートに足すなら、巻を分けるか、vol 28 型の節単位の巻を作る必要がある。

| id | § | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| FR-01 | 7.2 | OIS ゼロカーブ（パー債・四半期払い・反復解） | 0 件。既存の bootstrap は半年払い固定 | now（新シンボル） | S–M | Table 7.3 の 6 点が小数 4 桁で一致 |
| FR-02 | 6.1–6.2 | 日付からの act/act・30/360、T-bill 表示、32nds、転換係数、受渡額、Ex 6.2 | `volumes/04_futures_forwards_rates/build_futures_rates_notebook.py:524-532,557-567`（日数・CF を手入力） | now | M | 2.6957 / 2.7111 / 157.14 / 4.0、CF 1.4623 / 1.2199、168.60、71.79 |
| FR-03 | 6.3 | 式 (6.2) による先物ゼロ延長（Ex 6.4）、SOFR スタブ（Ex 6.5）、1M SOFR 算術平均、Ex 6.3 | spec 04:69、`volumes/04_futures_forwards_rates/PROGRESS.md:25` | now | S | 2.916% / 3.033%、2.75%、$502,500（2.01% 相当） |
| FR-04 | 3.4 | Table 3.2 実データでの最小分散ヘッジ比率、式 (3.3)、tailing | builder :153-160 は乱数データ、spec :70 で範囲外 | now | S | σ_F 0.0313 / σ_S 0.0263（ddof=1）/ ρ 0.928、N* 37 / 32.23 / 30.70。`hullkit.weather:optimal_basis_hedge`（h*=0.7777）を流用可 |
| FR-05 | 3.5–3.6, 付録 | Table 3.4、stock picking、stack & roll、CAPM | spec :70、PROGRESS 04:25 | now | S | 5,096,187（±1）、20.95 枚 / $62,500、1.70、11% |
| FR-06 | 2.4 | Table 2.1 の証拠金台帳（追証は翌日入金） | builder :106-118 は当日補填の合成経路 | now | S | 追証 4,020 / 3,780、累計 −4,620、残高 15,180 |
| FR-07 | 4.6, 4.10 | パーイールド、修正デュレーション・ドルデュレーション | builder :259-263 は出力のみ | now | S | 6.87、D* 2.499、93.978 |
| FR-08 | 5.4–5.11 | Table 5.6 のフォワード価格と価値関数（収入・利回り・保管・FX） | builder :419-452。assert は 40.50 のみ | now | S | 948.79, 886.60, 51.14, 25.77, 2.17, 1,313.07, 0.7206, 484.63 |
| FR-09 | 34.2, 7.9 | Ex 34.1（複利スワップ）、Ex 7.2（フォワード FX 分解） | `volumes/07_swaps/build_swaps_notebook.py:361-371`（独自の例）、:329-335（説明のみ） | now | S | 2.895、0.009182 / 0.009275 / 0.009368 → 0.9629 |
| FR-10 | 7.10, 34.1, 34.4 | クロスカレンシーの固定-変動・変動-変動、元本スケジュール（amortizing・step-up）、エクイティスワップのリセット間評価 | build_swaps_notebook.py:340-351, 410-418。`swaps` の元本はスカラーのみ | now | M | 恒等式のみ（印刷値なし） |
| FR-11 | 34.5 | accrual swap（N(d2*) の二値分解）、cancelable swap | spec 07:63 で md のみ | European は now。Bermudan は金利ツリーが要る（`trees.py` は株式 CRR のみ） | M（Bermudan は L） | RK→∞ の極限、MC、`ir_options:swaption_black` との恒等式 |
| FR-12 | 34.3（Ch 30 と重複） | diff/quanto スワップ、CMS スワップ、タイミング調整（§30.3） | vol 11 の quanto は数値表のみ（`volumes/11_ir_derivatives_market/build_ir_options_notebook.py:450`）、timing は説明のみ（:412） | now | M | ρ=0 で調整ゼロ、MC |
| FR-13 | 6.3 | 先物のコンベクシティ調整 ½σ²t₁t₂ の関数化 | builder :590-599 はチャートのみ | 恒等式なら now。印刷値は Technical Note 1（repo 外）で blocked | S | Ho–Lee の下で `rfr.futures_forward_from_covariance` と照合 |
| FR-14 | vol 04/07 | ライブ Jupyter でのウィジェット操作確認 | PROGRESS 04:15 / 07:15 | blocked（手動確認） | S | — |

### 4.2 オプション基礎（Ch 10–15, 17–19 / vol 01–03、旧 bsm）

- D10（第 13 章の US 版の値での固定）は §2、R11（Table 19.1 / 19.4）は §3 を参照。
- ノート内の assert は pytest では走らず、`make hull-core-notebooks-check`（`johnhull/report/tests/test_core_notebook_gate.py:18-44`）でしか実行されない。

| id | § | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| OP-01 | 19 | `bsm` の Greeks 11 関数と `d1` が T=0 / σ=0 で `ValueError`。混在した配列も丸ごと例外になり、要素ごとに処理する価格関数と非対称 | `johnhull/hullkit/src/hullkit/bsm.py:28-29,131-194`（価格側は :38-128）。例外は `test_bsm.py:79-83` で仕様化済み。`frontier_reference.py:2249-2259` からも呼ばれる | decision（公開挙動の変更、S=K のキンクの規約。先例は `johnhull/notebooks/patch_bsm_nb.py:183-238`） | S–M | σ→0⁺ の極限、call delta − put delta = e^{−qT}、`make hull-artifacts-check` |
| OP-02 | 13.1–13.9 | GE 版の印刷値で固定: 0.545、p=0.5503、p*=0.6266、1.7433 / 0.9497、Δ 0.4358 / 0.7273 / −0.4024、Fig 13.10 の 7.43 | `test_trees.py:9-19`（US 値）、`build_foundations_notebook.py:231,807` | now | S | 印刷値 |
| OP-03 | 13.10–13.11, 17.6 | 7.671 / 7.47 / 6.76、Ex 13.1 53.39、Ex 13.2 0.019、Ex 13.3 2.84 | 値の grep 0 件 | now | S | 印刷値 |
| OP-04 | 15.12, 11.7 | 既知の現金配当（S−PV(D)）、式 (15.25)、Black 近似、式 (11.8)–(11.11) | 0 件。旧ノートの §15.12 は q 利回りの内容（`johnhull/notebooks/bsm_chapter15.ipynb:1907`） | now（関数追加） | M | Ex 15.9（PV 0.9742、d1 0.2020、d2 −0.0102、c=3.67）、D=0 で BSM に一致、近似値 ≥ European |
| OP-05 | 15.4 | Table 15.1 のヒストリカル・ボラティリティと標準誤差 | 旧ノートのローカル関数のみ（bsm_chapter15.ipynb:183） | now | S | 0.01216 / 19.3% / SE 3.1% |
| OP-06 | 19.4 | Table 19.2 / 19.3 の株価パスの決定的リプレイ | `test_hedging.py:19-67` は MC 平均と比率のみ | now | S | 263.3、256.3（印刷 256.6）、Week 9 の 414.5 |
| OP-07 | 19.4, 19.6, 19.8 | Γ 中立化（2,000 / 1,240）、Ex 19.5（400 / 6,000 / 3,240）、ポートフォリオ delta −14,900、Ex 19.3 | 0 件。vol 03 は独自の数値（`build_greeks_notebook.py:496-523`） | now | S | 印刷値 |
| OP-08 | 19.12 | 外国金利 rho、先物オプションの rho（−cT）、先物ヘッジ比 H_F（Ex 19.8） | md のみ（build_greeks_notebook.py:183, 537-538） | now | S | q の FD。Ex 19.8 は 468,422（印刷 468,442 は係数 1.0228 の丸め、7 枚は一致） |
| OP-09 | 19.13 | Ex 19.9（−0.3215 / −0.3679 / −0.2787）、Ex 19.10（122.96 枚） | 図のみ（build_greeks_notebook.py:580-593） | now | S | 印刷値 |
| OP-10 | 12.3 | calendar / diagonal spread、bull put、bear call | spec 02:31-34, 70-72 で md のみ。0 件 | ノートなら now。`payoffs` を多満期にするなら decision | S | 極限の挙動。`STRATEGIES` に足すと `build_options_basics_notebook.py:334-338` の `_N_STRIKES` で KeyError |
| OP-11 | 12.1, BS 12.1, 15.1–15.3, 15.7, 15.11 | Ex 12.1（835.27、σ25% で約 221、r3% で 119 / 217 / 281）、米国型 box（10.00 / 5.44→5.26）、Ex 15.1–15.3、BS 15.1、Ex 15.7（7.04 / 5.87 / 38.83）、IV 1.875→23.5% | `test_volatility.py:8-16` は往復変換のみ | now | S | 印刷値 |
| OP-12 | 15.6 | Ex 15.5、永久デリバティブ（式 15.17）、e^{(σ²−2r)(T−t)}/S | 0 件 | now | S | FD で PDE 残差 ≈ 0 |
| OP-13 | 17.1–17.5 | Table 17.1 / 17.2（K=960）、range forward（K1=1.3000・K2=1.3414 がともに 0.0273）、BS 17.1（169.7）、Ex 17.2 の IV 14.1%、式 (17.10) と implied q。Ex 17.1 を pytest へ移す | ノートのみ（`build_options_basics_notebook.py:563-608`） | now | S | 印刷値 |
| OP-14 | 18.4–18.11 | Ex 18.5（1.04）、上下限と式 (18.2)、Ex 18.7（88.37）、一段木 1.592、米国型の先物オプションと現物オプションの大小、futures-style option（F N(d1)−K N(d2)、p+F0=c+K）。Ex 18.6 を pytest へ移す | 0 件 | now | S | 印刷値、c·e^{rT} の恒等式 |
| OP-15 | 10.4, 10.7, 11.4 | Ex 10.1–10.2（株式分割・株式配当）、Ex 10.3（裸売り証拠金 $4,240 / $3,520 / $5,040）、Ex 11.3（1.68 ≤ P ≤ 2.50） | 暗号資産の `liquidation.py:81` 以外 0 件 | now | S | 印刷値 |
| OP-16 | 14.3, 14.6, 14.8 | Table 14.1 のリプレイ（→111.54）、フォワードへの伊藤の補題、fBM の式 (14.20) | vol 13 にフォワードの例なし、fBM は fGn 版のみ | now | S | 111.54、H=0.5 で min(s,t) |
| OP-17 | spec 03:80 | q≠0 のヘッジシミュレーション | `hedging.py:3-8`、`deep_hedge_price/src/deep_hedge_price/baselines.py:16-29` も q なし | now | S | 平均コスト → `call_price(q)` |
| OP-18 | vol 01–03 | ウィジェット操作確認（PROGRESS 01:11 / 02:13 / 03:14） | — | blocked（手動確認） | S | — |

### 4.3 ボラティリティ・数値計算・VaR（Ch 20–23, 27 / vol 05, 06, 08）

| id | § | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| VN-01 | 20.1, 20.5, 20A, 20.8 | 印刷値で固定する: Ex 20.1（14.5%、put 0.0419）、Table 20.2 の補間（13.7 / 14.525）、Ex 20A.1（g1..g8、面積 0.9985）、Table 20.3 | `test_volatility.py:8-17` は往復変換のみ | now | S | 印刷値。Table 20.3 の K=56 は計算 49.9、印刷 49.0。GE の誤植と思われる（不確実） |
| VN-02 | 20A, 20.4 | `bl_density` を hullkit へ移す（今は `volumes/05_vol_smile_estimation/build_vol_smile_notebook.py:213-217` にインライン）。K/F0 軸と delta 軸の変換も追加 | 0 件 | now（公開 API 追加のため MODEL_INDEX と docstring を同時に更新） | S | Ex 20A.1、ボラ一定なら対数正規密度 |
| VN-03 | 21.1–21.2 | 印刷値で固定する: Ex 21.1（4.49…4.283）、コントロール変量（4.32 / 4.08 / 4.25）、Ex 21.3、Ex 21.4。ツリーの Γ / Θ（Ex 21.2） | `test_trees.py:9-28` は Ch 13 のみ。ツリー Greeks は `trees.py:66` の delta だけ | now | S | 印刷値（試作で 0.034 / −4.30） |
| VN-04 | 21.3, 21.4 | ドル配当の S* ツリー、p=0.5 ツリー、三項ツリーの hullkit 化（今は `volumes/06_numerical_methods/build_numerical_notebook.py:135-160`） | 0 件 | now | S–M | 試作で 4.44 / 4.208 / 4.214 と 0.0026 が一致 |
| VN-05 | 21.5 | 時変の r(t)・q(t)・σ(t) を扱うツリー（式 21.11） | build_numerical_notebook.py:82-83 は md のみ | now | M | パラメータ一定なら `crr_price` と一致 |
| VN-06 | 21.7, 21.8 | 層化抽出とモーメントマッチング、S 格子の FD（Ex 21.10 / 21.11）、PSOR | `fd.py:1-5` は ln S 格子と射影のみ。PSOR は spec 06:74 で範囲外 | now（PSOR は decision） | S / S–M / M | 分散比、印刷値（試作で 4.07 / 3.91 / 4.26） |
| VN-07 | 22.2–22.4 | 印刷値で固定する: Table 22.4（422.291 / 669.391）、BRW の重みと ES 833.2、Table 22.8（14,406.193 / 279.222 / 319.894）、ES 1,687,000 / 421,400、Ex 22.1 の 7.099 | 値の grep 0 件 | now | S | Table 22.8 は丸めた表から計算すると 14,404 になるので、許容 0.02% が要る。MSFT の ES は厳密には 1,685,629 で、誤植の可能性がある（不確実）。p.521 の累積重み 0.004833 は 0.003776 の誤植と判断 |
| VN-08 | 22.2 | stressed VaR/ES の 250 シナリオ規約（VaR は 2 位と 3 位の中点、ES は 0.4c1+0.4c2+0.2c3） | `risk.py:21` は k=⌈(1−α)n⌉。`test_risk.py:62-67` が n=250 で 3 位を固定。vol 27 spec :60 は `risk.py` を変更しないとしている | 新関数なら now、既定変更は decision | S | p.521 の手計算 |
| VN-09 | 22.4, 22.5 | cash-flow mapping、2 次モデル（式 22.8 の cross gamma）、脚注 10 のモーメントと Cornish–Fisher | `volumes/08_risk_var/build_risk_notebook.py:397-402` はポインタのみ。`pnl_explain.py:9-19` は cross gamma を範囲外と明記 | now。印刷値は TN25 / TN10 にしかないので固定は blocked | M | 脚注 10 の式、build_risk_notebook.py:367-392 のデルタ-ガンマ MC |
| VN-10 | 22.9 | PCA による VaR | md のみ（:401） | now | S（表から）/ M（合成データ） | 寄与 87.3% / 95.6% が一致。VaR は 59.3（印刷 59.2、ローディングの丸め） |
| VN-11 | 22.2, 23.5 | 4 指数・501 日の全計算、S&P 500 での推定値（α=0.22636、β=0.74704、λ=0.9182） | Hull のデータが repo にない。`johnhull/docs/DATA_PROVENANCE.md:15` は synthetic-offline 方針 | blocked | — | — |
| VN-12 | 23.6, 23.7 | Table 23.3（26.5…19.5）、Table 23.4（0.90…0.10）、式 23.15、Ex 23.3（ρ=0.6044）、GARCH 共分散、式 23.17 の例（w=[1,1,−1] で −0.6）、PSD チェック関数 | 既存 API で一致。`volatility.py:9-102` に期間構造の関数はない | now（`risk.py:40-46` に PSD 検証を足すなら decision） | S | 印刷値 |
| VN-13 | 23.5 | variance targeting、EWMA の λ の MLE、Ljung–Box。GARCH の初期分散の規約 | 0 件。spec 05:64 は Ljung–Box を md で扱うと約束したが builder に言及なし。`volatility.py:60` は `init=np.var(u)`、Hull は v3=u2²（p.549） | now（初期値の規約は decision） | S–M | Table 23.2 から 2,138 / 12.95、本文は約 2,170 / 13.2（丸めと推定、不確実） |
| VN-14 | 27.1, 27.2 | CEV（非心 χ²）、variance-gamma、Merton 級数、Table 27.1、σ(t) の平均分散（0.255）、Hull–White の混合式 | Merton は build_numerical_notebook.py:411-421 にインライン、CEV / VG は :393 / :395 の表のみ | now | S–M | Table 27.1 の 0.3679 など、`zero_dte.py:303`（vol_of_vol=0）、`heston_cf`（ρ=0） |
| VN-15 | 27.3 | IVF / Dupire（式 27.4） | `vol_surface.py:12-210` は SSVI と凸射影のみ | now（implied tree は L） | M | 局所ボラで MC して入力の IV を再現 |
| VN-16 | 27.4, 27.5 | 転換社債ツリー（Ex 27.1）、Hull–White の代表値平均ツリー | :534-536 はポインタのみ | now | S–M / M | 試作で 107.44、7.17 / 7.77、5.58 / 6.17 が一致 |
| VN-17 | 27.6, 27.7 | バリアツリー（AMM を含む）、2 資産の相関ツリー（Table 27.2 / 27.3） | :535 はポインタ、27.7 は言及なし | now | M | `exotics.barrier_call`（:39）、`exchange_option`（:141） |
| VN-18 | 27.8 | LSM の 8 パス例を公開 API で固定、境界のパラメータ化、Andersen–Broadie の上限 | パスを受け取れる `_lsm_backward` は private（`mc.py:63`）。`lsm_exercise_boundary` のテストは `test_plotly_viz.py:246` だけ | now（上限は M） | S | 0.1144 が一致。境界 0.84 / 0.88 で価値 0.1209（印刷 0.1208） |
| VN-19 | 20 | `implied_vol` はスカラーの Brent 法だけ | `volatility.py:9-21`。ループ呼び出しは `plotly_viz.py:660,824`、`surrogate_data.py:412`。private の Black-76 版が `frontier_reference.py:1447` にある | ベクトル版の追加は now、既存の挙動変更は decision | S–M | 要素ごとにスカラー版と一致 |
| VN-20 | 横断 | 既定 seed が統一されていない（下記） | 統一すると `build_numerical_notebook.py:590-591` の 3SE assert とコミット済み出力が変わる | decision | S | 決定性テスト |

**既定 seed の一覧**（`johnhull/hullkit/src/hullkit/` 配下）

- 42:
  - `mc.py:16,45`
  - 継承先: `mc.py:108,130`、`hedging.py:41,60`、`xva.py:23`
  - `sde.py:33,92`、`hull_white.py:144`、`jarrow_yildirim.py:368,436`、`jgbi.py:352`
- 0:
  - `aad.py:27,41`、`copula.py:28,57`、`heston.py:62`、`mc_advanced.py:61,72`
  - `sabr_normal.py:370,413,491`、`carbon.py:126,214,283`、`weather.py:58,107`、`ppa.py:100`
  - `zero_dte.py:319`、`surrogate_data.py:134,213,230,296,352`、`plotly_viz.py:1290`
- 引数必須: `mc_advanced.py:22,29,45`
- seed なし: `credit_metrics.py:125`（`default_rng()`）。呼び出し側はすべて rng を渡している。
- 巻ごとの固定: `volume21_reference`〜`volume28_reference` は 20260739〜20260746。

**FRTB について**

- Hull Ch 22 の本文にあるのは、ES 97.5% への移行（BS 22.1 p.515、§22.1 p.516、PQ 22.20 p.541）と stressed VaR/ES（§22.2 p.521）だけ。
- liquidity horizon・NMRF・P&L attribution・SA は本文に出てこない。
- したがって ROADMAP の「vol 29 候補」（`johnhull/ROADMAP.md:131-132`）は、Hull の残りではなく Beyond-Hull の新テーマ。Hull に紐づいて残るのは VN-08 だけ。

### 4.4 エキゾチック・金利デリバティブ（Ch 26, 28–33 / vol 10, 11、旧 ir_models）

D7（HJM/BGM の RMSE=0 のハードコード）と R10（HJM vol の単位）は §2・§3 を参照。

| id | § | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| EX-01 | 26, 29, 30, 32 | 既存関数を印刷値で固定する（現状は合成値のみ） | `test_exotics.py:12,71`、`test_ir_options.py:83-102` | now | S | Table 26.1 の 0.31（実測 0.3136）、Ex 26.2 の 8.04、Ex 26.3 の 5.62、Ex 29.1 の 9.49 / 7.97、Ex 29.4 の 2.19、Ex 30.4 の 179.83（CRR N=100 で 179.826）、Table 32.3 の 1.8093 |
| EX-02 | 26.4, 26.9, 26.11 | 対になる関数がない: gap put、バリアプット 4 種と BGK 離散補正、floating lookback put、固定ストライク lookback、r=q の極限 | `exotics.py:15,39,85-91`。`barrier_put` などは 0 件 | now（r=q は `test_exotics.py:128` が raise を固定しているので decision） | S | pdi+pdo=p、Ex 26.1 の 1,896（手計算 1895.69）、Ex 26.2 の put 7.79 |
| EX-03 | 26.2, 26.3, 26.5–26.8, 26.12 | perpetual American、Bermudan、forward start、cliquet、Geske compound、chooser、shout | `perpetual`（暗号資産のみ）、`forward.?start`、`cliquet\|chooser\|shout\|geske` いずれも 0 件 | now | M | chooser のパッケージ恒等式、call-on-call − put-on-call = C − K1·e^{−rT1}、European ≤ Bermudan ≤ American |
| EX-04 | 26.13–26.15 | 離散観測 Asian、観測済み分の K*、average-strike、basket、min/max、American exchange | `exotics.py:121`（連続 TW のみ）。`basket\|rainbow\|stulz` は 0 件 | now | S | Ex 26.3 の 6.00 / 5.70 / 5.63、min+max=U+V、ツリー（S=V/U）= `exchange_option` |
| EX-05 | 26.16, 26.17 | 分散スワップ・ボラスワップ（式 26.6–26.10）、static replication | `volumes/10_exotics_martingales/build_exotics_notebook.py:255-269`（補正項のない近似 strip） | now | S | Ex 26.4 の 0.0621 / 1.69、Ex 26.5 の 0.2484 / 1.82（既存 bsm で一致）、Table 26.1 |
| EX-06 | 28.2, 28.4, 28.8 | フォワード測度とアニュイティ測度、式 (28.35) の数値検証 | build_exotics_notebook.py:376-385 は表のみ | now | S | MC で E^T[S_T]=F |
| EX-07 | 29.1, 29.2 | Ex 29.2、spot vol stripping の関数化、キャップを ZCB プットで表す形、shifted-lognormal の公開 API、後ろ向き RFR の近似 | `volumes/11_ir_derivatives_market/build_ir_options_notebook.py:209-241`、`sabr_normal.py:141`（private） | now（Ex 29.2 は DerivaGem 規約に依存し不確実） | S–M | strip した vol でキャップを再価格、shift→0 で Black、`rfr_options.compounded_rate_option_mc` と比較 |
| EX-08 | 29.4, 32.7 | 金利オプションの bucket delta / vega | `dv01\|bucket\|key.?rate` はスワップのノートのみ（`build_swaps_notebook.py:208-228`） | now | M | bucket の合計 ≈ parallel DV01 |
| EX-09 | 30.1–30.3, 付録 | timing / quanto の関数化、spec が約束した `bond_yield_convexity` | spec 11:25-27、build_ir_options_notebook.py:374-381, 412-460 | now | S | Ex 30.1 の G′=−2.6730・G″=9.8910、Ex 30.2 の 1.00535 / 760.25、Ex 30.3 の 15,260.23 |
| EX-10 | 31.2–31.4 | Vasicek / CIR / RB を hullkit へ昇格、real-world の b*、パラメータ推定 | `johnhull/interest_rate_models/build_ir_models_notebook.py:257-266,1607-1631`。`vasicek` は信用側のみ | now（§31.4 の印刷値は T-bill データがなく blocked） | S | Ex 31.1 の D̂=3.30、合成 OU からのパラメータ回復 |
| EX-11 | 31.5, 32.1, 32.3 | 2 因子 Vasicek（式 31.14）、HW2F のボラティリティ・ハンプ | 0 件 | now | M | C(t,T) を MC と比較、ZCB のマルチンゲール性 |
| EX-12 | 32.2 | Ho–Lee の σ_P、CIR の債券オプション、HW でのキャップ | `hull_white.py:33-34` が a>0 を必須にしている | 新シンボルなら now、検証を緩めるなら decision（`test_hull_white.py:113`） | S | HW の a→0 極限 |
| EX-13 | 32.4, 32.5 | HW / BK 三項ツリー、節点の解析式（32.15–32.17）、American 債券オプション | `trees.py:31` は CRR のみ。trinomial は vol 06 の株式ノートのみ | now | M（HW）/ L（BK＋American） | Fig 32.4 の 0.35、Fig 32.7 のノード（scratch で 3.824 / 6.937 / … / 2.788 を再現）。Table 32.3 のツリー列と Fig 32.9 の 0.672 / 0.703 は規約依存で不確実 |
| EX-14 | 32.6, 33.2 | σ(t) の階段関数での較正、Bermudan swaption | `hull_white.py:249`（a, σ は定数）。`bermudan` は md のみ（`build_swaps_notebook.py:416-417`） | EX-13 の後なら now | M | 行使日 1 回なら Jamshidian と一致 |
| EX-15 | 33.2 | LMM 一式: Λ の算出、MC（33.14 / 33.16）、ratchet / sticky / flexi、スワプション近似（33.18）、PCA | `lmm\|bgm\|libor.?market\|rebonato` のコードは 0 件。旧ノートは Black キャップレットのみ | 実装は now。置き場所は decision（新巻は release_manifest 登録が必要） | L | Ex 33.1 の 19.80 / 15.23（手計算で一致）、MC のキャップレット = Black、Table 33.2 / 33.3 を ±3SE で |
| EX-16 | 33.1, 33.3 | 多因子 HJM、MBS / OAS | `johnhull/interest_rate_models/PROGRESS.md:144-145`。`mortgage\|mbs\|oas` は 0 件 | HJM は now。MBS は印刷値がなく decision | M | P(0,T)=E[e^{−∫r}] |
| EX-17 | 旧 ir_models | PROGRESS の残り（キンクの解説、BK の clip の根本対処、無裁定モデルの残差、CIR の厳密サンプリング、ノート分割、実データ） | `johnhull/interest_rate_models/PROGRESS.md:127-159`、builder :2084 | now。実データは blocked（spec 2026-06-07:130 で synthetic 限定）。分割は book の `31_ir_models` が変わるので decision | S–M | `hw_zcb_option` から Black IV を逆算 |

### 4.5 信用・XVA・定性章（Ch 1, 8, 9, 16, 24, 25, 35–37 / vol 09, 12, 28）

置き場所によって可否が変わる。
- hullkit の単体テストに足すだけなら `now`。
- vol 28 の acceptance に足すと、チェック数 17 の固定（`johnhull/hullkit/tests/test_frontier_reference.py:852`、`johnhull/VALIDATION.md:49`）と artifact の fingerprint が変わるので `decision`。
- vol 09 / 12 の builder を触る場合は、`make hull-core-notebooks-check` の再実行が必要。

| id | § | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| CR-01 | 24.9 | Ex 24.8 Vasicek 信用 VaR を印刷値で固定（D11 ②） | spec :46 が対象と明記。`test_credit.py:53-62` は合成パラメータの単調性と閉形式一致のみ | now | S | V=0.1282 → $5.13M |
| CR-02 | 24.7 | Ex 24.5 / 24.6: 自社信用で割り引く f=f_nd·e^{−(y−y_nd)T}、フォワード CVA の閉形式 | 式 24.5 の特殊ケースのみ（`xva.py:120`） | now | S | 2.91、v₁=92.67、v₂=130.65、CVA 5.77、84.71 |
| CR-03 | 24.8 | Ex 24.7 デフォルト時刻コピュラの閾値と MC | 0 件 | now | S | −2.33 / −1.88 / −1.55 / −1.28 / −1.04、限界頻度が二項 SE 内 |
| CR-04 | 24.2, 24.5, 24.6 | Table 24.1 の PD、λ(7)、Table 24.3、Ex 24.3 の負債価値 | md のみ（`volumes/09_credit_xva/build_credit_notebook.py:110`） | now | S | 0.29 / 4.77 / 7.53%、0.34%、3%、28bp、9.40 |
| CR-05 | 24.7, 9.4 | 担保・cure period 付きネッティングセットの MC CVA、増分 CVA | 規則関数のみ（`xva.py:92-125`） | now | M | cure period→0 で EE→0、netting ≤ gross、ネッティングなしなら増分 = 単体 |
| CR-06 | 24.7 | wrong-way risk | md のみ（build_credit_notebook.py:443、vol 16 :248）。Hull はモデルを示さない | now（モデル選択が必要） | M | 独立の極限で `xva.cva` と一致、依存度に単調 |
| CR-07 | 9.2–9.3 | MVA / KVA / FCA–FBA | 表の md のみ（builder :386）。`xva.fva` は符号テストだけ（`test_xva.py:33`） | now（規約選択） | S–M | 恒等式のみ（印刷値なし） |
| CR-08 | 25.2, 25.3, 25.8, 25.9 | 回収率への感応度（通常 CDS とバイナリ CDS の対比）、指数スプレッド = Σprot/ΣD、合成 CDO の $3M / $14M、二項の 86.74% / 0.0034% | バイナリ CDS 本体（`cds.py:116` の `binary_cds_spread`）と Table 25.5 の 205 bp（`test_cds.py:39-42`）は実装済み。未固定なのは列挙した追加シナリオ。指数の加重コードと $3M / $14M、86.74% の値は 0 件 | now | S×4 | MTM 0.0210→0.0204（R 0.2→0.6）に対しバイナリは 125→250bp。2 社指数は 415.7bp で 505bp 未満だが、Hull の「わずかに下」より差が大きい |
| CR-09 | 25.10 | 非標準トランシェ（4–8%）: 標準気配のベース相関から非標準点へ補間・較正する規約と、その再価格検証 | `expected_loss_curve`（`credit_portfolio.py:507-529`）は任意の detachment と相関を受け取るので、評価 API 自体は既存。未対応なのは補間規約と検証だけ。プローブ（λ=0.02、R=0.4、r=0.03、T=5、125 社、ρ=0.2）で EL_PV(0–8%)−EL_PV(0–4%)=0.013551 と 4–8% トランシェの直接評価 ×0.04 の差は 1.2e-17 | now | S–M | 補間 EL が単調増加かつ凹、標準気配を再価格、EL(0–8)−EL(0–4)=0.04·C |
| CR-10 | 25.11 | ランダム回収率・ランダム因子負荷、implied copula | `frontier_acceptance.py:1924` の否定結果の文以外は 0 件 | now | M×2 | 負荷一定で Gaussian に一致・無条件 PD を保存。Table 25.6（2007）を再価格、重み ≥ 0 で和 1 |
| CR-11 | 25.11 | 動的モデル | 同上 | decision（新巻、印刷値なし） | L | 極限のみ |
| CR-12 | 24.6 脚注 11 | KMV EDF 写像 | distance to default の言及のみ（vol 09 builder :150） | blocked（Moody's の非公開データ） | — | — |
| CR-13 | 25.5（Hull の範囲外） | knock-out しない CDS オプション・インデックス・オプション | `cds.py:187` は knock-out 型の Black 式のみ。Hull p.597 は knock-out のみ記述 | now | M | パリティ、λ→0 で knock-out 版と一致 |
| CR-14 | vol 28 範囲外 | ISDA 標準 CDS モデル | `ISDA` はコード 0 件 | blocked（オフラインの参照テストケースなし） | L | — |
| CR-15 | 9.4 | 増分 XVA の ML サロゲート | サロゲート系に XVA 実装なし | decision（torch 側の `deep_hedge_price` と新しい artifact 契約） | L | MC 教師との誤差帯 |
| CR-16 | 8.1 | Table 8.1（ABS CDO の 2 段ウォーターフォール） | md のみ（`volumes/12_qualitative_summary/build_summary_notebook.py:178`） | now | S | 表の 12 値と 10.25% の閾値 |
| CR-17 | 16.4 | Ex 16.1 / 16.2（権利確定・離職・行使確率つき ESO ツリー） | vol 12 の md のみ | now | S–M | 6.31（プローブ 6.306）、節点 23.67 / 103.56 / 56.44 / 14.97、通常オプション 17.98 |
| CR-18 | 16.4 | 行使倍率モデル（Hull–White 2004） | 0 件 | now | M | 倍率→∞・離職 0 でアメリカン・コールに一致 |
| CR-19 | 35.4, 36.5 | 平均回帰三項ツリーと、その上のリアルオプション | trinomial は vol 06 の株式ノートのみ。`hull_white.py` にツリーなし | now | M | α₁=3.071、α₂=3.099、Ex 35.3 のプット 1.48、プロジェクト −0.54 / 14.46、放棄 1.94、拡張 1.06、E[S]=F |
| CR-20 | 35.4, 35.7, 36.1–36.3, 1.7–1.9 | 閉形式・算術の印刷値固定 | 値の grep 0 件 | now | S（合計 M） | 0.034 / 20.4%、17.729、季節性 35.2 / 32.6、$250,900→$243,400、トレンド除去後 $180,400 / $175,100、4.5355 / $1.3586M、λ=0.075、NPV −11.53（Ch 1 以外はプローブで一致） |
| CR-21 | 35.8 | 回帰ヘッジ Y=a+bP+cT | なし（関連: `ppa.py:258` のヘッジ比グリッド） | now | S | 合成データで b・c を回復、残差分散が減る |
| CR-22 | 35.3–35.4 | Gibson–Schwartz、ジャンプ、Eydeland–Geman、スイング・オプション | 0 件 | GS は now、スイングは decision | M / L | GS 先物の閉形式と MC の一致 |
| CR-23 | 36.4, 25.7 | Schwartz–Moon（Amazon）、TRS | 0 件 | Schwartz–Moon は blocked（σ(t)・η(t) が Hull に不記載）、TRS は decision（式なし） | L / S | — |

### 4.6 深掘り巻・基盤（vol 13–17、Jupyter Book、ポータル、論文コーパス）

- vol 13–17 の主張は大半がコードとテストで裏付けられている。builder とコミット済みノートのセル数（30 / 35 / 22 / 22 / 18）も一致した。
- `johnhull/AGENTS.md` は `CLAUDE.md` への symlink。
- 論文コーパス v2 は Phase 0–10 完了で、未完のフェーズはない。

| id | 巻・領域 | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| DD-01 | book | vol 13–16 の plotly（JSON mimetype 出力 23 件）が静的 book で描画されない（D9） | 2026-07-20 のビルドで `plotly-graph-div`=0。`.venv/lib/python3.12/site-packages/myst_nb/sphinx_.py:354-363` が該当出力を捨てている | decision。①builder に `pio.renderers.default="plotly_mimetype+notebook"` を入れて再実行（plotly.js 4.85MB × 4 巻で repo 約 +19MB）②`myst_nb.mime_renderers` プラグイン＋plotly.min.js の同梱（`release_manifest.json` の `vendored_book_assets` 変更）③CDN は `verify_release.py:631-647` で失敗する④kaleido は未導入 | M | `make hull-book` の div 数、`make hull-release-check` |
| DD-02 | book | vol 01–12 と ir_models の 13 冊が出力なしでコミットされている（D9） | 59e00c4d 以降ずっと出力 0 | decision（出力をコミットするか、book 側で実行するか） | M–L | `make hull-book` |
| DD-03 | book | 見出しレベルの飛び（H1→`###`、5 巻の cell-003） | `johnhull/VALIDATION.md:137-139` の legacy warning 29 件は、plotly 23 件＋見出し 5 件＋1 件と数が合う（推定） | now | S | warning 件数 |
| DD-04 | 13 / 15 | Milstein は vol 13 :239 で「A3 で扱う」と予告したが、どこにもない | `milstein` は vol 13 の本文 1 件のみ | now | S–M | `test_sde`＋core ノートチェック |
| DD-05 | 14 / 15 | Heston キャリブレーションが予告されたまま | `def *calibrat` は SABR・HW・dhp のみ | now | M | 設定値を回復できるか |
| DD-06 | 15 / 17 | 「AAD」と表記しているが adjoint（逆掃引）の実体がない | `johnhull/hullkit/src/hullkit/aad.py:1-7`（"toward AAD"）。reverse-mode は `deep_hedge_price/src/deep_hedge_price/greeks.py:10-14`（torch）のみ | now（numpy で手書き adjoint。表記修正だけなら S） | M | adjoint と bump の一致、torch-free のテスト |
| DD-07 | 15 | LR ベガが未テスト | `test_aad.py:22-28`。プローブで 37.01、解析値 37.52 | now | S | test_aad |
| DD-08 | 13 | EM の収束次数を測っていない | `test_sde.py:44-57` は 1 解像度の平均のみ | now | S | test_sde |
| DD-09 | 15 | RQMC による誤差推定がない（単発の scramble のみ） | — | now | S | test_mc_advanced |
| DD-10 | 16 | t コピュラとテール依存係数 | `student\|t.copula` は vol 28 の double-t のみ | now | S–M | 解析的な λ_U との一致 |
| DD-11 | 17 | capstone のモデルが揃っていない: QMC は GBM σ=0.20 で比較（:196-199）、Δ は COS の差分と GBM pathwise（:124-131）、ベガは未計算、CVA は GBM（σ=√v0）の 1 単位フォワード（:153-156） | `volumes/17_capstone/build_capstone_notebook.py`、`xva.py:23` | md で明記するだけなら now（S）。Heston 整合のパス生成を hullkit に足すなら正本境界の判断が要る（`spx_vix.py:3-5`） | S / M | core ノートチェック |
| DD-12 | 14 / 17 | 例のパラメータが Feller 条件を満たさない（2κθ=0.12 < ξ²=0.36）のに、本文で触れていない | vol 14 :100, :122、vol 17 :66 | now | S | 同上 |
| DD-13 | コーパス | 深掘り巻の出典に検証済みの式がない。P0 は 7 系統のみ。Albrecher・Lord・Broadie–Glasserman・Giles–Glasserman は検証済みの式・claim とも 0、Fang–Oosterlee は式 0。`heston-pricing` の証跡は Heston (1993) の g/d 形を指すが、実装は little-trap 形 | `johnhull/docs/PAPER_CORPUS_V2.md:35-38`、`heston.py:28-35` | PDF がある分は now。Li と Vasicek はリンクのみで PDF も公開許可もなく blocked（`johnhull/references/README.md:80-81`） | M | `make hull-paper-corpus-gold-check` |
| DD-14 | コーパス | `Andersen et al. (2024)` の書誌が特定できない | `johnhull/references/README.md:154-155`、`johnhull/scripts/build_frontier_notebooks.py:121` | blocked（書誌の特定が必要） | S | `make hull-notebooks-check` |
| DD-15 | workspace | `deep_hedge_price/tests`（206 本）が root の testpaths になく、root conftest にも import がない | `pyproject.toml:159-194`、`conftest.py:24-32` | now（`make test` の所要時間は増える） | S | ワークスペース全体の pytest |
| DD-16 | 基盤 | builder とコミット済みノートのズレを検出するテストがない | — | now | S | 新規テスト |
| DD-17 | 基盤 | コミット済みノートの出力・巻別 VALIDATION.md と metrics.json を照合するゲートがない（D8 の再発防止） | `johnhull/scripts/verify_frontier_notebooks.py:32-39` | now | S | vol 21 / 27 で FAIL し、再生成後に PASS |
| DD-18 | MODEL_INDEX | シンボル単位の未掲載（`sabr_greeks`、`sticky_strike_delta`、`xva.forward_exposure`、`expected_negative_exposure`、`copula.portfolio_loss_samples` など 9 件） | `test_model_index.py:22-31` はモジュール単位の検査のみ | now | S | test_model_index |
| DD-19 | release | research track が既定で無効 | `johnhull/ROADMAP.md:81`、`verify_release.py:490-497` | decision（promotion rule） | L | release check |

### 4.7 Beyond-Hull vol 18–22

vol 19–22 の JSON を改ざんすれば、原則として `make hull-artifacts-check` の再構築（`johnhull/scripts/verify_frontier_artifacts.py:63-72`）で検出される。例外は vol 21 の計測値で、speedup・対応する acceptance の observed・NPZ の companion hash は比較前に `<timing-dependent>` に置き換えられ（`:23-30`）、`nested_mc_ms` / `surrogate_ms` は正値かどうかしか見ない（`:33-46`）。静的な検証経路（`johnhull/scripts/verify_release.py:228`）と vol 18 は再構築の対象外。

| 巻 | spec 成果物（充足/総数） | 無効な research track | negative results | 配列から再計算する検査 |
|---|---|---|---|---|
| 18 | 10/13（BS time-value residual の比較なし、OOD の数値が artifact にない、break-even は解析解との比のみ） | Deep BSDE / PINN / DeepONet・FNO / Differential PCA（`research_profiles.json` に未登録） | soft penalty が効かない（weight 0.1 の 1 点のみ、価格 MAE 比 0.9994）、break-even なし、OOD の価格崩壊（R7） | 1/8。artifacts-check の再構築対象外。20 seed の coverage 条件 ∈[0.8,1] は、真の coverage が 90% でも 96% の確率で通る |
| 19 | 8/11（学習済み forward surrogate なし、識別性と noisy quote の分離なし、break-even なし） | VAE / flow / SBI（config のみ）、direct-inverse NN（stub） | soft 曲面の convexity 違反 4 件（最大 3e-6 > 許容 1e-7、教材の反例としては妥当）、累積射影は joint-L2 最適ではない、rBergomi のバイアス（R1） | 0/11（hard report と Pareto は保存フラグを読むだけ） |
| 20 | 8/11（Phase-1 比較、モデル別の経済比較、surface-latent 予測がない） | foundation model（stub）、conditional diffusion（Gaussian 平滑の仮実装、`deep_hedge_price/src/deep_hedge_price/research_models.py:47-67`） | PCA-ridge が EWMA に勝てない、Phase-1 は `not_evaluated`、Log-HAR が h=1 / 21 で EWMA・GARCH に劣後（CI が 0 を含まない）、challenger は hidden 8・5 epoch | 2/12（purge 不等式のみ） |
| 21 | 6/8（共同較正なし、Greek 比較が不成立） | signature / POT（名前のみ） | Greek RMSE 25.36（D4）、人工ターゲット、サロゲートの負の価格と delta（R8） | 0/8 |
| 22 | 5/8（イベント注入の誤り、expiry 検査の曲線は手置き、OOD なし） | DML / PIDE（名前のみ） | synthetic のみ。イベント効果 ≈ +0.001 で SE 0.013 より小さい | 2/6 |

| id | 巻 | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| BA-01 | 20 | Phase-1 policy が未評価。checkpoint はローカルにあるが条件が違う（T=0.119y・30 step・μ=0.05 に対し、capstone は T=1・12 step・drift 0） | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:1124`、`hedge_capstone.py:89-98` | decision（positions と checkpoint の fingerprint を vol 20 の reference に入れる契約）＋同じ条件で再学習（CPU で可） | M | acceptance の評価済み分岐（`johnhull/scripts/frontier_acceptance.py:441-447`） |
| BA-02 | 18 | soft penalty が weight 0.1 の 1 点だけ。break-even は解析解との比・batch ≤ 256 のみで、測ってある COS / MC の latency を使っていない（MLP 256 行で 126.5 ms は計測系を疑う、未確認） | `deep_hedge_price/src/deep_hedge_price/pricing_ablation.py:41`、`pricing_evaluation.py:262` | now（torch CPU、export の再生成が必要） | S–M | weight を振ったときの hard 違反数、COS / MC 対 MLP の中央値±ばらつき |
| BA-03 | 18 | OOD の数値を artifact に入れる（R7）。`volumes/18_ml_surrogates/VALIDATION.md:55` は定性記述のみ | `deep_hedge_price/scripts/export_johnhull_pricing_reference.py:216-236` | now（checkpoint 2d4ba8e38acfa5cc がローカルにある） | S | `pricing_evaluation.json` の `splits.ood` と一致 |
| BA-04 | 18–22 | acceptance が保存値中心で、改ざんテストがない（vol 27 / 28 にはある） | `johnhull/scripts/frontier_acceptance.py:51-100,143-202,546-584,615-633` | decision（metrics.json 内の検査集合が変わる） | S | vol 19 の hard report・Pareto、vol 20 の予測、vol 21 の speedup、vol 22 の event RMSE は NPZ から再現できることをプローブで確認済み。`test_frontier_reference.py:563` と同じ形の改ざんテストを足す |
| BA-05 | 19 | hard repair を joint-L2 射影に置き換える | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:212-214` | now（SLSQP、36 変数） | S | raw との RMSE ≤ 0.003063、hard 違反 0、冪等性 |
| BA-06 | 19 | 学習済み forward surrogate がない（較正は SABR / Hagan 教師を直接使う）。識別性と noisy quote の分離もない | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:391-401` | now | M | `compare_forward_models`、残差ヤコビアンの特異値 |
| BA-07 | 20 | surface-latent ターゲットを保存しているだけで、予測していない | `deep_hedge_price/src/deep_hedge_price/frontier_reference.py:955` | now | S–M | purged fold 上で persistence と ridge の RMSE を比較 |
| BA-08 | 21 | 共同「較正」をしていない。ターゲットは 0.55·PDV + 0.45·AFV の合成、skew は手置き、objective は評価しているだけ | `johnhull/hullkit/src/hullkit/frontier_reference.py:196-205` | decision（`joint_*_rmse` の意味が変わる） | M–L | 自分で生成したターゲットからパラメータを回復 |
| BA-09 | 21 | Greek 指標の修正（D4）とサロゲートへの hard check（R8） | `johnhull/hullkit/src/hullkit/spx_vix.py:318-340,472` | 指標定義は decision、hard check は now | S | delta と gamma を別々の RMSE に、`check_price_bounds` と `check_spot_monotonicity` を適用 |
| BA-10 | 21 | SHA 契約（下記） | `johnhull/scripts/build_frontier_artifacts.py:493-510` | decision | S | vol 28 だけ編集して vol 21 を再生成しなくても PASS |
| BA-11 | 22 | イベント注入の修正（D3）と強度 bump の分離（R5）、乱数ストリームの分離（R4） | `johnhull/hullkit/src/hullkit/frontier_reference.py:425,446-448,486-487`、`zero_dte.py:357-361` | 注入の修正は now（`sv_jump_teacher` は変更不要）、ストリーム分離は decision | S | 対数収益の分散増分が公称値に一致（SE 内）、`SeedSequence.spawn` でパス対応 100% |
| BA-12 | 18–22 | research track はすべて未実装で、runner もない | `johnhull/research_profiles.json:7-13` | DML / PIDE / signature / VAE は now（GPU は任意）。foundation model は重みとライセンスで blocked。実市場での検証はデータライセンスで blocked（`johnhull/docs/DATA_PROVENANCE.md:19-22`） | L | promotion rule（`research_profiles.json:13`） |

**vol 21 の SHA 契約（BA-10）**

- **計算している場所:** `build_frontier_artifacts.py:493-510`。`frontier_reference.py`（vol 21–28 共通、2,879 行）と `spx_vix.py` の、ファイル全体の SHA-256 を `benchmark.sources` に入れている。
- **無関係な編集でも落ちる理由:** 検証側の正規化（`verify_frontier_artifacts.py:23-30`）はタイミング値だけを除外し、`sources` は除外しない。
- **目的も果たしていない:** タイミング値を保存し直すかの判定（`build_frontier_artifacts.py:526-527`）は `sources` を見ない。そのため、古い計測値が新しい digest の下に残る。128d7c7b〜c7194c5d の 6 コミットは、vol 21 の digest 1 行を書き換えただけだった。
- **決定的な配列の検出には要らない:** 数値配列は厳密に比較されている。ただし配列の一致は、計測値を出した実装の来歴（どの source revision・環境で測ったか）までは保証しない。削除するなら、来歴を別に残すかを先に決める。
- **直し方の案:** ①vol 21 の経路だけの digest にする ②計測時の source revision と環境を別フィールドに保持し、通常再生成の digest と区別する（`--refresh-timing` のときだけ更新し、比較から外す）③来歴の保持先を決めたうえで削除する。

### 4.8 Beyond-Hull vol 23–28

「コミット済み配列から再計算する」は vol 27 と vol 28 で拡充されたが、原始入力からの独立検証はそこでも全面的ではない（BB-14、BB-18）。

| 巻 | spec 成果物（充足/総数） | 範囲外（明示） | negative results | 保存値に依存する acceptance |
|---|---|---|---|---|
| 23 | 6/8（SABR の段階比較で free-boundary が明示 shift・MC 教師との比較が gate にない、Hagan の領域別誤差が交絡（D5）） | Deep XVA / SIMM / MVA（`hullkit.xva` へ委譲） | Hagan 最大誤差 60.6 bp（単位は価格×1e4）、free-boundary は外生 shift、MC SE に時間離散化バイアスを含まない | 9 中 5: `daily_compounding_handcheck`、`continuous_limit`、`hagan_diagnostics`（フラグと RMSE>0 のみ）、`nonzero_nu_teacher`、`sabr_model_ladder`（shape と SE>0 のみ） |
| 24 | 6/7（LVR 削減量が構成上 0（R6）） | 無限期間 BSDE、risk-based ADL、AMM-token option（spec では research track だが `research_profiles.json` に未登録） | cascade は合成、dynamic fee は gross LVR を減らさない（構成上の恒等式） | 10 中 4 が保存スカラー（`cashflow_conservation`、`solvency_identity`、`insurance_identity`、`stress_waterfall`）。別の 4 は保存済みの誤差配列を読むだけ |
| 25 | 7/8（価格と発電量の相関に対する感度が ρ=−0.60 の 1 点だけ） | storage real option（名前のみ）、実市場での較正、OOS 検証 | weather / PPA の価値は premium principle に依存 | 9 中 2 がハードコード（`market_completeness`、`carbon_model_ladder` の `True`）、`ppa_cashflow_risk` は保存スカラー |
| 26 | 6/8（`jy_zcis_value` / `jy_yoy_value` にテストなし、ノートのヘッジ分解がスタブで演習なし） | ISDA disruption fallback、実運用の JGBi 決済、G2++ / Bermudan、インフレ smile・cap / floor、確率的 seasonality、JY の実市場 MLE | synthetic、1 因子 Gaussian＋決定論的 seasonality | 11 中 8 が保存スカラーかリテラルを入力に含む。うち `synthetic_hedge_decomposition` は固定配列、`floor_payoff_decomposition` は自己照合で、この 2 つは常に PASS（D6） |
| 27 | 11/12（ノートと VALIDATION.md が 09-02 の artifact と不一致（D8）） | FRTB IMA（vol 29 候補）、統合リスク枠組み、多変量 EVT、cross-gamma / vanna / vomma | synthetic、FHS は EWMA 固定、Basel 表は 250 日表のみ | 14 中 7（BB-15） |
| 28 | acceptance 17/17、配線 9/10（docstring に「18--27」が残る） | ランダム回収率・負荷、implied copula、動的モデル、KMV EDF、ISDA 標準モデルの厳密版 | 教科書から転記した定数、Table 25.8 は小数 1 桁で一致、double-t と ASB は極限でのみ検証 | 17 中 6 が保存値を入力に使う（BB-18） |

| id | 巻 | 項目 | 根拠 | 可否 | 規模 | 検証の手がかり |
|---|---|---|---|---|---|---|
| BB-01 | 23 | free-boundary SABR が shifted SABR の別名になっている（shift 0.030）。MC 教師は shift 0.020 側にしかない | `johnhull/hullkit/src/hullkit/sabr_normal.py:109-138`、`frontier_reference.py:907-937`。`antonov\|endogenous` は免責文 1 件のみ | 既存関数の出力変更は decision、別関数の新設は now | M | β=0 で normal SABR に一致、ρ=0 の AKS 積分と \|F\|^β 型 MC が 3SE 以内 |
| BB-02 | 23 | Hagan の領域別診断を T×α の全組合せで取り直す（D5）。calendar 検査も α の違う行同士を比べている | `frontier_reference.py:941-946`、`johnhull/volumes/23_rfr_post_libor/VALIDATION.md:17-18` | now | S | 満期×α の全組合せグリッドで他条件を固定し、診断マスクが選ぶ行が別であること、配列から再計算した RMSE が保存値と一致することを検査する。「2 つの RMSE が異なる」だけでは偶然の一致を除外できない。26.2144 の単位は価格×1e4 の bp |
| BB-03 | 23 | MC SE に時間離散化バイアスを含まない（積分分散は左端リーマン和） | `sabr_normal.py:453-456`、`frontier_acceptance.py:775`。最悪セルの SE は約 11 bp で、n_steps 48→192→768 で推定値が SE 程度動く | now | S–M | 共通乱数での step-doubling で \|P_n−P_2n\| と SE を比較 |
| BB-04 | 23–25 | gate が保存スカラー・フラグ・リテラルを読んでいる。vol 24 の `solvency_identity_error` は貸借の恒等式ではない | `frontier_acceptance.py:686-749,797-846,909-945`、`frontier_reference.py:1341,1739,1755`。`discrete_accrual` と continuous limit は配列からの再計算が保存値と一致することを確認済み | now | S | 再計算値と保存値の差 ≤ 1e-12、vol 27 と同じ形の改ざんテスト |
| BB-05 | 24 | 手数料帯つきの裁定終点で dynamic fee を評価し直す（R6） | `amm.py:101-108,145-147`、`test_frontier_reference.py:383-386` | now（新関数） | M | f=0 で現行と bit 一致、gross LVR が f に対して非増加 |
| BB-06 | 24 | cascade は単一口座で、最終ステップに 1 回だけ close-out する。ADL はスカラーの容量。spec の research track 3 件が未登録 | `frontier_reference.py:1233-1240`、`liquidation.py:253,283`、`research_profiles.json:6-12` | cascade は now、research track は decision（登録か撤回） | M / L | 各ステップで Σflow=0、単一口座にすれば現行の ledger を再現 |
| BB-07 | 25 | 価格と発電量の相関に対する感度（spec 必須） | `frontier_reference.py:1639`、`docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md:199-200` | now | S | 共通乱数で ρ グリッド、merchant 収入の差 = ΣDF·Cov(S,G) |
| BB-08 | 25 | storage real option（名前のみ） | `research_profiles.json:11` | now（research track なので core gate に影響しない） | M | σ→0 で intrinsic、intrinsic ≤ 価値 ≤ perfect foresight。`hullkit.mc:price_american_lsm` を流用可 |
| BB-09 | 26 | ヘッジ分解を実装し、固定配列と常に PASS する検査を置き換える（D6） | `frontier_reference.py:1942,1975,2015-2037`、`frontier_acceptance.py:1050-1129`、`build_frontier_notebooks.py:219-223` | now | S–M | bump で PV01 と CPI delta。floored[-1] = unfloored[-1] + face·max(1−R_T,0)（100 = 93.346 + 6.654）、diff(floor_analytic) ≥ 0。z=1.4889 / 1.1975 は配列から再計算できる |
| BB-10 | 26 | `jy_zcis_value` / `jy_yoy_value` にテストも内部利用もない。ノートに演習がない（plan 必須）。短い初回クーポンに未対応 | `jarrow_yildirim.py:297,321`、`build_frontier_notebooks.py:307,400`、`docs/superpowers/plans/2026-07-19-johnhull-inflation-jgbi.md:461`、`jgbi.py:161` | now | S | ゼロボラ極限で `zcis_npv` / `yoy_swap_npv` に一致、MC と 3SE 以内 |
| BB-11 | 26 | G2++ / Bermudan、YoY cap / floor と smile、確率的 seasonality | plan :522-524。0 件 | now（API の追加のみ） | 各 M | σ₂=0 で HW1F に一致、行使日 1 回の Bermudan が Jamshidian に一致 |
| BB-12 | 25 / 26 | 実市場での較正と OOS（25）、ISDA fallback・実運用の JGBi 決済・JY の実市場 MLE（26） | `frontier_acceptance.py:1133`、`johnhull/VALIDATION.md:244-250` | blocked（有償の ISDA 定義と実データのライセンス、`verify_release.py:133-134` の synthetic-offline 契約と衝突） | L | — |
| BB-13 | 27 | VALIDATION.md とノート出力の再生成（D8）と、照合ゲート（DD-17） | `johnhull/volumes/27_risk_desk/VALIDATION.md:13,62-76`、`risk_desk.ipynb` セル 6 の出力 | now | S | builder を再実行し、生成物がコミット版と一致 |
| BB-14 | 27 | follow-ups §1 の残り（`fhs_coverage_improvement`、`gpd_parameter_recovery`）と弱い検査。`evt_var` と `euler_additivity_normal` が保存値、z が保存 VaR からの逆算で循環、desk 和が Σpos−Σpos で恒等的に 0、Kupiec を名目 5% と比較（正確なサイズは 7.09%） | `frontier_acceptance.py:1254-1348,1356,1415,1444`（`_norm_ppf_np` は :1497）。HS / FHS の予測・EWMA σ・違反系列は配列から誤差 0 で再計算できる | now | S | 再計算値の差 ≤ 1e-12、book_* = weights @ position_factor_*、Kupiec は正確なサイズと比較 |
| BB-15 | 27 | cross-gamma / vanna / vomma を P&L explain に入れる | `pnl_explain.py:9-19`。`bsm.vanna` / `vomma` は `bsm.py:183,190` に既存 | decision（公開 API の拡張。review-fixes plan :29 は「公開 API を増やさない」） | S–M | 移動幅を半分にしたとき、残差比が約 4 倍から約 8 倍になる |
| BB-16 | 27 | FHS の既定の rescale 先が `sigma[-1]`（artifact は翌日予測を明示的に渡すので影響なし） | `tail_risk.py:103`、`test_tail_risk.py:47`、`frontier_reference.py:2128-2130` | decision（既定の出力が変わる） | S | 明示パスで現行 artifact と bit 一致 |
| BB-17 | 27 | follow-ups §4（ポータルの重複ブロックと未使用の `tags`）、§8 のテスト細目 a / b / d / e | `johnhull/report/report_builder/figures.py:749-761,853-865`、`var_backtest.py:198-201`、`test_risk_allocation.py:100-113`、`risk_allocation.py:89-90` | now | S | ポータルが 12 テーマ / 82 図のまま。n=100・x=3 で yellow 3.40 |
| BB-18 | 28 | acceptance が保存値を入力に使う: CDS レッグは保存 PV 列の足し直し（spec は生存確率と割引から再計算）、CDS ブートストラップは保存済みの再価格スプレッドと市場スプレッドの比較だけで保存 hazard を使わない（spec :211 は標準気配の再価格を要求）、固定クーポンの D、capital structure、base 相関と EL 曲線、double-t、一般 CVA（許容 1e-5） | `frontier_acceptance.py:1565-1568,1592-1606,1630-1639,1715-1834,1899-1918`。実行確認: `cds_bootstrap_hazard` を全 0 にしても、`cds_survival` を全 0 にしても 17/17 PASS で判定辞書も不変（§10）。payment / payoff / accrual は S·DF、(1−R)q·DF_mid、0.5q·DF_mid と誤差 0 | now | S（double-t だけ M） | 既存の `_tranche_legs_np`（:1517）で再価格。hazard・tenor・割引・回収率から気配を再価格し、hazard を変えたら FAIL する検査を足す。チェック名・件数・許容値を保ったまま判定だけ強くできる |
| BB-19 | 27（→29） | FRTB IMA（follow-ups §7） | `johnhull/ROADMAP.md:131-132`。`frtb\|nmrf\|liquidity_horizon\|stressed_es` は docstring と vol 08 の本文のみ | decision（新巻。`verify_release.py:337` の 18..28 固定と manifest の変更） | L | LH カスケードの ES と PLA 統計を、コミット済み P&L から再計算 |

## 5. 先送りしたが、別の巻・モジュールで解決済みのもの

**先物・金利・スワップ**
- §4.2 と §6.3（3M SOFR の決済） → `rfr:compounded_rfr`（`rfr.py:193`、vol 23）。
- 「dual-curve OIS は範囲外」（PROGRESS 07:25-26） → `rfr:MultiCurveScenario` / `collateralized_present_value`（`rfr.py:328,410`）。ただし `swaps` 自体は単一カーブのまま。
- 先物とフォワードの差 → `rfr:futures_forward_from_covariance`（`rfr.py:360`）。テストは符号だけ。
- 「スワプションは vol 11 で」 → `ir_options:swaption_black`（`ir_options.py:66`）と vol 26 の `hull_white:hw_jamshidian_swaption`。CMS の式 (30.1) は `convexity_adjustment`（:76）で一部だけ。
- §7.12 CDS → `credit:cds_spread`（vol 09）と `cds:*`（vol 28）。
- 最小分散ヘッジの汎用関数 → `weather.py:214`（§3.4 からは参照されていない）。
- 実カレンダーでの日数計算 → `rfr.BusinessCalendar`（act/360）と `jgbi:jgbi_accrued_interest` で一部。30/360 と米国債の act/act は未実装。

**オプション基礎**
- vanna / vomma → `bsm.py:183-194`（827ea077）。
- 米国型 Greeks（spec 03:79） → `fd.fd_vanilla`（`test_fd.py:65-74`、vol 06）。
- q 付きの §11.3 / 11.4 → `surrogate_validation.check_price_bounds` / `check_put_call_parity`（vol 18）。
- §14.2 / 14.6 / 付録 14A → `sde.brownian_paths` / `quadratic_variation` / `ito_riemann_sum`（vol 13）。
- §14.5 → `heston.heston_mc_price` に埋め込み。
- §14.8 → 一部だけ（`weather.fractional_noise_autocovariance`、`spx_vix.rough_heston_fractional_kernel`）。
- 三項ツリー → vol 06 のノートのみ（VN-04）。
- §12.5 Breeden–Litzenberger → vol 05 のノートのみ（VN-02）。
- §15.7 → `mc.price_european_mc`。
- §19.14 → `deep_hedge_price` の policy / risks。ただし Hull の目的関数 X+cY とは同一ではない。

**ボラ・数値計算・VaR**
- Heston / SABR（spec 05:61、06:72-73） → `heston.py`、`sabr.py`（vol 14）。
- Sobol QMC と重点サンプリング（06:75） → `mc_advanced.py`（vol 15）。
- 陽解法 FD と安定性 → `fd_advanced.py`（vol 15）。
- MC Greeks → `aad.py`（vol 15）。
- Kupiec・Christoffersen・traffic light（08:55） → `var_backtest.py:104-192`（vol 27）。
- EWMA / GARCH を使う VaR（08:54） → `tail_risk.py`（FHS、EVT / GPD）。
- スマイル整合デルタ（05:65） → `sabr.py:58,70,83`、`sabr_normal.py:266` の `bartlett_delta`。

**エキゾチック・金利**
- HW の解析スワプション（vol 11 PROGRESS:27、ir_models PROGRESS:155） → vol 26 の `hull_white:hw_jamshidian_swaption` と `calibrate_hw1f`。旧ノートには未配線。
- Bachelier → `rfr_options:bachelier_price`（vol 23）。shifted lognormal は private のみ。
- HW の θ(t) と初期カーブへの完全フィット → `hull_white:hw_phi` / `hw_discount_bond`。
- スワプション＝債券オプション（BS 29.2） → `hull_white:HullWhiteSwaption`。
- Girsanov（§28.1） → `sde:girsanov_weights`（vol 13）。
- CPI に限った timing / quanto 型の測度変換 → `jarrow_yildirim:jy_payment_forward_cpi`（汎用形は EX-09）。
- Black-76 の公開関数 → `carbon:black76_price`。
- ボラティリティ・キューブ → 単一スライスの `sabr:calibrate_sabr` のみ。

**信用・XVA**
- CreditMetrics MC、ベース相関、Big-Bang 固定クーポン（vol 09 spec:57-59） → vol 28 の `credit_metrics` / `credit_portfolio` / `cds`。
- vol 09 のノート内 CDS ブートストラップと MC トランシェ → `cds.bootstrap_from_cds`、`cdo_tranche_valuation`、`kth_to_default_valuation`。
- §24.4 債券ブートストラップ → `credit_curve.bootstrap_from_bonds`。
- §25.11 の double-t と不均質モデル → `credit_portfolio`（極限でのみ検証）。
- ネッティング・担保・式 (24.5) → `xva.netting_set_exposure` / `collateralized_exposure` / `cva_single_payoff`（MC 部分は CR-05）。
- EE / PFE / ENE / DVA / FVA → `hullkit.xva`（vol 16）。
- HDD / CDD（vol 12 spec:52） → `weather.degree_day_index` / `weather_contract_premium`（vol 25）。Ex 35.4 は未対応。

**基盤・深掘り**
- nbformat の cell id → 全 30 冊の builder で付与済み（c54491fd）。
- MODEL_INDEX の vol 28 モジュール掲載 → `johnhull/MODEL_INDEX.md:87-91`。
- `johnhull/report/tests` の testpaths 登録 → `pyproject.toml:172`（8c3d4c97）。
- rough vol → 正本は `rough_volatility`（`johnhull/CLAUDE.md:57`）。
- 論文コーパス v1 の OCR 後続課題 → v2 で pass。ただし式は未検証（DD-13）。
- 論文コーパス v2 の全フェーズ完了 → `docs/superpowers/plans/2026-07-22-johnhull-paper-corpus-v2.md:206-221`。

**Beyond-Hull**
- vol 27 follow-ups:
  - §1 Kupiec（複製ごとの超過回数をコミット）→ `frontier_reference.py:2077-2087`、`frontier_acceptance.py:1231-1264`。
  - §3 符号付きの `limit_measure` → `frontier_reference.py:2329`。
  - §5 root conftest → 解決済み。
- vol 27 review-fixes Phase 1–6 → 実施済み（`mean_excess` だけ漏れている、R9）。
- vol 27 plan Phase 1–6 → 公開 20 シンボル・NPZ 56 配列・ポータル 4 図が揃っている。
- vol 26 plan §13 で延期したポータル・book・tracked release → 完了（`johnhull/ROADMAP.md:101-104`）。
- vol 20 Phase-1 の adapter 契約 → `deep_hedge_price/tests/test_frontier_reference.py:203`（評価そのものは BA-01）。
- vol 19 の CPU 較正時間 → `johnhull/VALIDATION.md:59-61`（1743 ms）。
- research track が既定で無効であることの検査 → `verify_release.py:490-500`。

## 6. 文書・成果物の食い違い

✅ 以外は監査報告のまま。

### 6.1 状態の主張が実態より強い

- `johnhull/ROADMAP.md:8,24` は「全 37 章カバー」、`volumes/12_qualitative_summary/build_summary_notebook.py:523-528` は「教科書値でピン済み」「節番号まで突合済み」としている。実際は §1 のとおり節単位で 81 節に計算がない。
- `johnhull/ROADMAP.md:17` の「未実装節は vol 28 で実装」、`johnhull/scripts/build_frontier_notebooks.py:321` の「一つ残らず」、`johnhull/README.md:8-9` → CR-01〜04 と CR-08 が残っている。
- ✅ `johnhull/ROADMAP.md:144-145`、`johnhull/VALIDATION.md:263-265`、`johnhull/volumes/28_credit_desk/VALIDATION.md:94-95` の「説明のみ」と knock-out の記述 → D11。
- 「acceptance はコミット済み配列から再計算する」→ 配列検査と保存値依存が巻ごとに混在し、vol 27–28 でも原始入力からの独立検証は全面的ではない（§0）。該当箇所は `johnhull/CLAUDE.md:31-32`（`johnhull/AGENTS.md` は symlink）、`johnhull/VALIDATION.md:34-35`、`johnhull/scripts/build_frontier_notebooks.py:562` が生成する巻別 VALIDATION の定型文。
- `johnhull/MODEL_INDEX.md` の過大な記述:
  - :64 の「Hull ch.4-6 / Pinned to Hull examples」→ Ch 5–6 の hullkit シンボルはない。
  - :66 の「Hull ch.29 worked examples」→ 固定されているのは Ex 29.3 だけ。
  - :31 の「Table 19.2/19.3 pinned」→ そのテストはない。
  - :58 の「(AAD)」→ DD-06。
- ✅ `johnhull/volumes/01_foundations/PROGRESS.md:12-14` の「GE 準拠」→ 固定値は US 版（D10）。
- ✅ `johnhull/book/_config.yml:6-9` の「実行済み出力をコミット」→ 13 冊は出力なし（D9）。
- vol 13 の builder（:7-8）、vol 14 / 15 / 16 の builder（:7）、`johnhull/book/_config.yml:13-15` の「静的 book で描画される」→ 描画されない。`johnhull/CLAUDE.md:45` の記述が正しい。
- `johnhull/interest_rate_models/PROGRESS.md:61-62` の HJM / BGM「市場に完全フィット」→ ハードコード（D7）。

### 6.2 件数・範囲・日付が古い

- `johnhull/ROADMAP.md`:
  - :22 の hullkit 14 モジュール → 約 50。
  - :43-47 のセル数 21/19/15/15/12 → 30/35/22/22/18。
  - :75-77 の 78 図 / 30 ページ → 82 図 / 31 ページ。直すときは `verify_release.py:474-475` が読む `| n | … | done |` の行形式を壊さないこと。
  - :124 の「13 恒等式」→ 14。
- `johnhull/README.md:10` の「release-candidate」→ リリース・merge 済み。
- 「18–27」のまま → 18–28。該当箇所は `johnhull/MODEL_INDEX.md:11`、`johnhull/report/README.md:8`、`johnhull/report/tests/test_core_notebook_gate.py:3`、`johnhull/docs/DATA_PROVENANCE.md:1,5,7,12`、vol 28 まわりの docstring。
- `johnhull/docs/DATA_PROVENANCE.md` の中身:
  - :53-57 の API 列挙に `swaps` がない。
  - :27 は PDV / AFV / 0DTE を research 扱いにしているが、実際は core（`spx_vix.py:33-38`）。
- `johnhull/report/report_builder/figures.py:9-10` の「as they land」。
- `AGENTS.md:61-64`（ルート）の「report/tests（10 本）が testpaths 未登録」→ 登録済み・15 本。
- `johnhull/VALIDATION.md`:
  - :3 の日付一覧に 09-02 がない。
  - :172 は Kupiec flags の検査を 07-20 の実行に帰属させている（実際は 09-02）。
  - :30-32 の「vol 26–28 は G 番号を持たない」→ 各巻の見出しは G8 / G9 / G10（`build_frontier_notebooks.py:226,317,409`）。vol 26 の G8 は統合 gate の G8 と番号が重なる。
  - :130 は 07-18 の記録なのに「vol 18–27」（8d72a0bc で書き換え）。
  - :239 の point-process track は `research_profiles.json` にない。
  - :18 は OOD を根拠に挙げているが、vol 18 の artifact に OOD の数値はない。
- FRTB の「vol 28 候補」表記（現在は vol 29 候補）が残っている箇所: `johnhull/hullkit/src/hullkit/pnl_explain.py:28-30`、`docs/superpowers/specs/2026-07-20-johnhull-vol27-risk-desk-design.md:11-12,50-51,134`、`docs/superpowers/plans/2026-07-20-johnhull-27-risk-desk.md:34,384,512`、`docs/superpowers/plans/2026-07-20-johnhull-vol27-follow-ups.md:86-90`。
- spec / plan の状態表記:
  - model-library-index design :4 が「実装前」のまま（plan のチェックボックス 32 個も未チェック）。
  - vol 27 spec :4「実装前」・:25「13 項目」、vol 28 spec :4「実装前」。
  - A5 spec :4「コード未着手」・:33「184 tests」。:190-191 は dynamic fee を research track としているが、実際は core。
  - beyond-hull-options spec :12-16 と A5 plan :39-40 が「11 テーマ / 70 図 / 28 ページ」のまま。
  - A5 plan :459 の「research config からのみ実行可能」はチェック済みだが、その config を読むコードがない。
- vol 28 spec の許容値（:143, :210, :224, :225）が gate の値と一致しない（plan :2317, :2432, :2446 で緩めた）。観測された CVA の差 1.53e-10 は spec の基準（≤ 1e-10）なら FAIL になる。
- ✅ vol 21 の `VALIDATION.md:26,40` とノート出力の speedup 914.29（metrics は 781.91）→ D8。
- ローカルの `johnhull/book/_build/html` は 2026-07-20 時点の 30 ページで、vol 28 を含まない。release check はこのディレクトリをそのまま走査する。

### 6.3 PROGRESS.md

- 「nbformat cell ids still missing」→ 解消済み（c54491fd）。該当箇所: 01:25、02:28、03:27、04:27、05:26、07:27、08:27、09:28、10:28、11:28、12:33。
- セル数とテスト数が古い:
  - セル数: 04 の「34」→ 46、07 の「25」→ 33、05 / 06 / 08 の 27 / 29 / 25 → 39 / 39 / 32。
  - テスト数: 04 の「6」→ 10、07 の「6」→ 7、10 の 9 → 14、11 の 6 → 10。
- 延期先の記載が違う:
  - 03:25「vanna / vomma は vol 05 へ延期」→ 実装済み。
  - 05:24「SABR / Heston は vol 06 へ」→ 実際は vol 14。
  - 06:25「quasi-random は md のみ」→ vol 15 で実装。
- 「md only」と書かれているが、実際には記述がない:
  - 09:27 の CreditMetrics → 現在は code。
  - ✅ 10:27 の compound / chooser / cliquet / fixed-strike lookback / Parisian → builder に 0 件。
  - 12:31-32 の Gibson–Schwartz / スイング / 行使倍率 → builder に 0 件。
- ✅ 11:26-27 と spec 11:58-60 の「LMM と HW スワプションは ir_models にある」→ ir_models の LMM 節は Black キャップレットのスライダーだけ。
- calendar spread の「再訪先」が食い違っている: `build_options_basics_notebook.py:397` は vol 03、PROGRESS 02:26-27 は vol 06。実際はどちらにもない（OP-10）。
- `johnhull/interest_rate_models/PROGRESS.md`:
  - :10 の「2365 行・49 セル」→ 2488 行・55 セル。
  - :176 のビルドコマンドにある anaconda の python は、もう存在しない。

### 6.4 MODEL_INDEX の誤参照

- :25 は「旧 ch15 ノートが `hullkit.bsm` を使う」としているが、旧ノートに hullkit の import はない。`test_greeks.py` も記載漏れ。
- :28 は LSM のテストを `test_mc.py` としているが、実際は `test_mc_pricing.py:34-49`。
- :37-38 に `ewma_covariance` と `garch11_long_run` が載っていない。
- :41 は SABR を「Hull ch.20 / vol 05」としているが、実際は §27.2 で、使っているのは vol 14（vol 05 に SABR の記述はない）。
- :42 は free-boundary SABR を Antonov et al. と紐づけているが、実装は明示 shift（BB-01）。
- :167 の「correlation sensitivity」には実体がない（BB-07）。
- :69 は HW を使うノートとして旧 IR ノートを挙げているが、旧 builder は hullkit を import していない。
- :85 は Vasicek を「Hull ch.25」としているが、式 24.10 である。
- :119 は forward surrogate としているが、実体は teacher。:121 の「vol 19, 21-25」は、hullkit 側では 21–28。:201 は vol 19 が rough_volatility の artifact を使うとしているが、実体は hullkit 独自の rBergomi。
- シンボル単位の未掲載が 9 件ある（DD-18）。

### 6.5 ノートや図の本文・引用

- **GE / US の節番号のずれ:**
  - `build_foundations_notebook.py:559` の §14.3 → GE §14.2、:621 の §14.4–14.5 → GE §14.2 / 14.3。
  - `build_options_basics_notebook.py:550` の §17.4 → §17.1。
  - `build_exotics_notebook.py:455` の §28.6 → §28.4。
  - `plotly_viz.py:2268` の Asian §26.12 → §26.13。
  - `build_ir_options_notebook.py:313` の §29.3 → 章末 Summary。
  - `build_summary_notebook.py:381` の §36.1 → §36.2。
  - `copula.py:43` の式 (24.8) → (24.9)。
- `build_exotics_notebook.py:141` は「バリアは 8 種に閉形式」としているが、実装はコール 4 種だけ。
- `build_futures_rates_notebook.py`:
  - :98-125 は「Table 2.1 形式」と書きながら、Hull の数値を再現しない。
  - :421-423 は I=40 で 886.19 となり、Hull（I=39.60 で 886.60）と一致しない。
  - :339 の注記と `rates.py:58` の docstring「continuous rates」は Ex 4.3（半年複利）と矛盾する。注記どおりに変換すると 359,539 になり、テストの 369,246.5 と合わない。
- `build_swaps_notebook.py:416-417` の「Bermudan はツリー / LSM（第 6 冊）」→ 金利用の実装はない。
- `build_numerical_notebook.py`:
  - :537 の「Heston / SABR はポインタのみ」→ vol 14 で実装済み。
  - :82-83 の「時変 r(t), q(t) は第 1・2 冊で実装済み」→ 実装済みなのは定数 q だけ。
- `build_vol_smile_notebook.py:251` の「局所・確率ボラは第 6 冊で」→ vol 06 にあるのは表だけ。
- `build_risk_notebook.py`:
  - :481 の「hullkit.risk は第 9 冊でも使う」→ vol 09 は import していない。
  - :402 の「第 1 冊 ir_models」→ 第 1 冊は 01_foundations。
- `build_credit_notebook.py:112` の「1.3〜17 倍」と :514 の「5〜10 倍」が矛盾している。Table 24.2 の比は 1.2–16.8。
- `build_summary_notebook.py`:
  - :142 のトランシェ境界 5 / 15% は Hull Fig 8.1 の 5 / 20% と違う。検証セル :445-448 もこの値で固定している。
  - :494-513 のモジュール一覧は 14 個のまま。
- vol 16 :51 と vol 17 :143 の「中立 DD」は意図が不明。vol 16 :248 の「ワンウェイ（wrong-way）」は誤訳。
- vol 14 の例のパラメータは Feller 条件を満たさないが、本文で触れていない（DD-12）。
- `johnhull/report/report_builder/figures.py` の図の説明:
  - :538 の「penalty 前後」→ 実データは小さな ablation と penalty_weight 0.0 の本番モデルの比較。
  - :580 の「Transformer」→ 実際に描いているのは PCA-ridge。
  - :608 の「fit」→ 較正はしていない。
  - :657 の「OOD」→ 実際は event と baseline の時間帯別 MAE。
- `johnhull/scripts/build_frontier_artifacts.py:84-85` の単位「per session」→ 実装は年率（`zero_dte.py:170`）。
- vol 23 の「bp」は価格×1e4 で、normal vol の bp ではない（`frontier_reference.py:1035,1059`）。
- vol 24 の NPZ の `liquidation_loss` は、中身が oracle の乖離（`frontier_reference.py:1203,1417`）。
- `pnl_explain.py:6` の「measures は正の量」→ 現在は符号付きの component VaR を渡している。
- テスト:
  - `test_cds.py:69` はテスト名が "between" なのに、assert は両方より大きいことを確認している。
  - `credit.cds_spread`（freq=4）と `cds.cds_par_spread`（freq=1）が重複していて、相互テストがない（プローブでは 1e-15 で一致）。
  - `test_risk.py:18` のコメントは 1,620,140、:22 の assert は 1,620,114。
- spec が約束したが未実装:
  - spec 10 :45 は 15 型の分類・rainbow の md・3 通りのニュメレール比較を予定したが、builder は 7 型・rainbow なし・2 通り。
  - spec 11 :25-27 の `bond_yield_convexity` と :49 のストリッピング検証の assert。
  - spec 04 :69-70 の ED 先物ブートストラップの md と tailing の注記。
- `johnhull/VALIDATION.md:139-140` の同梱 require.js は、それに依存する出力を持つ巻が見当たらず、実質使われていない可能性がある（推定）。

## 7. 判断が必要な事項

| 事項 | 選択肢と影響 | 関連 id |
|---|---|---|
| book の出力方式 | ①core 13 冊を実行して出力をコミット ②book 側で実行 ③plotly は mimetype＋notebook レンダラ（repo 約 +19MB）か、myst-nb プラグイン＋plotly.js 同梱（manifest 変更） | D9, DD-01, DD-02 |
| 既定 seed の統一 | 42 系と 0 系が混在。揃えるとコミット済み出力とノートの 3SE assert が変わる | VN-20 |
| 既定の出力が変わる修正 | bsm Greeks の T=0 / σ=0、rBergomi のスキーム、Log-HAR のモデル集合、vol 21 の Greek 指標、vol 22 の乱数ストリーム、`risk.py` の VaR 規約、GARCH の初期分散、FHS の既定、`hull_white` の a>0 制約、free-boundary SABR | OP-01, R1, R2, BA-09, R4, VN-08, VN-13, BB-16, EX-12, BB-01 |
| acceptance の検査集合の変更 | 検査名・件数・許容値を変える作業（vol 18–22 の改ざんテスト追加）は release 契約の判断が要る。判定だけを強くする作業（vol 23–28 で保存値を配列からの再計算に置き換える）は技術的には今できるが、metrics.json の acceptance ブロックの再生成を伴う | decision: BA-04 / now（再生成を伴う）: BB-04, BB-09, BB-14, BB-18 |
| vol 21 の SHA 契約 | vol 21 の経路だけに絞る / `--refresh-timing` 時のみ更新 / 削除 | BA-10 |
| 大物の置き場所 | Ch 26 一式、金利ツリーと Bermudan、LMM、Ch 2–7 の節単位実装、Ch 35–36 のツリー例。vol 04 は 46 セルでソフト上限 35 を超えているので、vol 28 型の節単位の巻を足すか | EX-02〜05, EX-13〜15, FR-02〜09, CR-19 |
| FRTB IMA（vol 29 候補） | Hull 本文にあるのは ES 97.5% と stressed VaR/ES だけで、残りは Hull 外の新テーマ。`verify_release.py:337` の 18..28 固定と manifest の変更が必要 | BB-19, VN-08 |
| 公開 API の拡張 | P&L explain の cross-gamma 項（review-fixes plan は「公開 API を増やさない」と記載）、`payoffs` の多満期化 | BB-15, OP-10 |
| research track | 未登録トラック（vol 24 の 3 件、vol 18 の 4 件）を登録するか撤回するか。promotion rule の運用 | BB-06, BA-12, DD-19 |
| vol 20 / 21 の評価設計 | Phase-1 policy の評価（再学習＋契約変更）、vol 21 の共同較正 | BA-01, BA-08 |
| 旧ノートの整理 | `ir_models` の分割（book の `31_ir_models` が変わる）、実データの扱い | EX-17 |

## 8. 外部要因でできないもの（blocked）

| 項目 | 理由 | 関連 id |
|---|---|---|
| KMV EDF の写像 | Moody's の非公開データ | CR-12 |
| 実市場での較正・OOS 検証 | ライセンスデータが必要。synthetic-offline 契約（`verify_release.py:133-134`）と衝突 | BB-12, BA-12 |
| Hull 本文の実データでの計算 | 4 指数 501 日、S&P 500 の GARCH 推定、T-bill のデータが repo にない | VN-11, EX-10 |
| Technical Note にしか数値がない例 | TN1 / TN10 / TN25 は PDF の外 | FR-13, VN-09 |
| ISDA 標準 CDS モデル、ISDA fallback | 有償の定義、オフラインの参照テストケースがない | CR-14, BB-12 |
| Schwartz–Moon（Amazon） | σ(t)・η(t) が Hull に記載されていない | CR-23 |
| foundation model | 重みとライセンス | BA-12 |
| 論文コーパスの Li / Vasicek | PDF と公開許可がない | DD-13 |
| `Andersen et al. (2024)` | 書誌が特定できない | DD-14 |
| ウィジェットの操作確認 | ライブ Jupyter での手動確認が必要 | FR-14, OP-18 |

## 9. 推奨順序

1. **確認済み欠陥を直す:** D1〜D8 と D11。変更ごとに必要な判断と検証を先に置く。判断なしで着手できるのは D1・D3・D5・D7・D11。D2 は初回期間の引数（公開 API への追加）、D4 は指標の定義、D6 はヘッジ分解の実装範囲（S–M）を先に決める。D8 は再生成に加えて照合ゲート（2.）が要る。
2. **再発防止:** 出力照合ゲート（DD-17）を足してから、vol 21 / 27 のノートと VALIDATION.md を再生成する（D8）。
3. **既存 PASS の根拠を強くする:** 大型の機能追加より前に、検査名・件数・許容値を保ったまま判定を強められる作業（BB-18 の hazard 再価格、BB-04、BB-09、BB-14）を進める。生成物や fingerprint の更新は別途記録する。指標・閾値・検査集合を変える作業（BA-04、BA-09）は判断事項（§7）。
4. **印刷値でテストを固定する:** OP-02・03・11・13・14、VN-01・03・07・12、EX-01、CR-01〜04・20 など。既存関数のまま、章ごとに S。
5. **文書の一括修正:** §6。
6. **判断事項（§7）を決める:** 特に book の出力方式・大物の置き場所。既定 seed の統一（VN-20）は、それ自体を欠陥修正の前提にしない。
7. **機能追加:** Ch 26 エキゾチック、金利ツリー→Bermudan→LMM、信用の残り（CR-05・09・10・13）、Ch 35–36 のツリー、深掘り巻の予告の回収（DD-04〜06）、BB-07（spec 必須）。

`now` は技術的な実行可否であって、作業の承認ではない。API・仕様・release 契約を変える判断は `decision` 列に分けてある。

## 10. レビュー反映（2026-09-14）

`SECTION_AUDIT_2026-09-14_FEEDBACK.md`（初版 SHA-256 `38c75ca4…`、653 行に対するレビュー）の 7 項目を、次のとおり確認して反映した。

| 項目 | 確認結果 | 反映 |
|---|---|---|
| 1. 節カバレッジ | vol 12 の行和 34 ≠ 35 を確認。§3.4（`weather.py:214-226`、`test_weather.py:66-72`）、§7.2（`build_swaps_notebook.py:277-282`）、§36.4（GE p.806-807 に Schwartz–Moon の確率過程と MC 手順）を確認 | §1.1 の 4 行と合計、§1.2 の 6 行、§0 の集計を修正。code* を定義。節別台帳は未作成 |
| 2. acceptance の二分法 | メモリ内で入力を変えて `evaluate_acceptance` を実行。vol 28: `cds_bootstrap_hazard`=0 → 17/17 PASS、`cds_survival`=0 → 17/17 PASS。vol 27: `gpd_losses`=0 → 14/14 PASS。vol 22: `variance_clock[1]`=−1 → FAIL。vol 26: 元本配列を壊す → `redemption_only_principal_floor` FAIL、YoY 比率をそろえる → `nominal_payment_forward_measure` FAIL。vol 20 の walk-forward 境界の FAIL はレビュー側の結果で、未再確認 | §0、§4.8 の表、BB-18、D6、§6.1、§7 を修正 |
| 3. D11③ | `volumes/28_credit_desk/VALIDATION.md:95`、`johnhull/VALIDATION.md:264-265`、spec :49・:62-63 を再読。「完全版の HW (2003) は未実装」という限定があり、記述は逆ではない。`test_credit.py:60-62` に閉形式一致の assert がある | D11②③、CR-01 を修正 |
| 4. CR-08 / CR-09 | `expected_loss_curve`（`credit_portfolio.py:507-529`）は任意の detachment を受け取る。`binary_cds_spread`（`cds.py:116`）と Table 25.5 の 205 bp 固定（`test_cds.py:39-42`）がある | CR-08、CR-09 を修正 |
| 5. D2 の再現条件 | 既定引数では bonds = fras = −0.43639、`accrual_to_next=0.5` で bonds = −1.18697、直接評価 −0.29200 を再実行で確認 | D2 に条件と符号を明記 |
| 6. vol 21 の例外 | `verify_frontier_artifacts.py:23-46` の正規化を確認 | §0、§4.7 の前置き、BA-10 を修正 |
| 7. 順序と完了条件 | — | §9 を書き直し。BB-02 の完了条件を具体化。`now` と `decision` の意味を明記 |

D2 の再現コード（repo ルートで `uv run --no-sync python`）:

```python
import numpy as np
from hullkit.swaps import irs_value_bonds, irs_value_fras

times = np.array([0.2, 0.7, 1.2])
zeros = np.array([0.028, 0.032, 0.034])
curve = (times, zeros)
args = (100.0, 0.03, times, curve, 0.02516)
print(irs_value_bonds(*args))                      # -0.43639
print(irs_value_fras(*args))                       # -0.43639
print(irs_value_bonds(*args, accrual_to_next=0.5)) # -1.18697
df = np.exp(-times * zeros)
print(1.5 * df.sum() + 100 * df[-1] - 100 * (1 + 0.02516 * 0.5) * df[0])  # -0.29200
```

acceptance の感度プローブ（repo ルートで `PYTHONDONTWRITEBYTECODE=1 uv run --no-sync python -B`）:

```python
import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "johnhull/scripts")
from frontier_acceptance import evaluate_acceptance

ref = Path("johnhull/volumes/28_credit_desk/reference")
metrics = json.loads((ref / "metrics.json").read_text())["metrics"]
with np.load(ref / "credit_scenarios.npz", allow_pickle=False) as stored:
    arrays = {name: stored[name].copy() for name in stored.files}
before = evaluate_acceptance(28, metrics, arrays)
arrays["cds_bootstrap_hazard"][:] = 0.0
after = evaluate_acceptance(28, metrics, arrays)
print(before == after, after["passed"], len(after["checks"]))  # True True 17
```

レビューが未確認とした点（完全版 HW (2003) との金融理論上の同等性、vol 20 の FAIL 条件、全 306 節の再集計）は、この改訂でも未確認のまま。

## 11. 修正状況（2026-09-14、`main` の `90e903ea` までに反映・push 済み）

D9（コア notebook の出力なし）以外の確認済み欠陥を修正した。作業ブランチ `worktree-johnhull-audit-fixes`（base `cae1cd84`）で全ゲート（hullkit+report 917 tests、ruff、`hull-artifacts-check`、`hull-notebooks-check`、`hull-core-notebooks-check`、`hull-report`、`hull-book`、`hull-release-check --require-tracked`）が PASS し、`main` へ fast-forward マージした。マージ後の `main` でもテスト、`hull-artifacts-check`、`hull-release-check --require-tracked` を再実行して PASS。ブランチと worktree は削除済み。

| ID | commit | 変更 | 数値の変化 |
|---|---|---|---|
| D1 | 384b8eff | 利付債でないとき中間キャッシュフローの補間をしない | 1 年ゼロ単独で 2.225% |
| D2 | 3e18d0c2 | `irs_value_bonds` / `irs_value_fras` に `first_accrual` を追加 | Ex 7.1 型の途中評価 −0.292 を両方式で一致 |
| D3 | 2db3e49c | `zero_dte.scheduled_jump_intensity`（λ = 分散 / (dt·E[Y²])）。acceptance に `event_variance_injection`（vol 22: 6→7 checks） | event price MAE 0.0055 → 0.1093 |
| D4＋R8 | c4654c9a | Greek RMSE を delta / gamma に分割。`check_price_bounds`（先物オプション境界）と `check_spot_monotonicity` を教師とサロゲートに適用。`surrogate_hard_checks` 追加（vol 21: 8→9） | delta 5.043 / gamma 35.507（旧 25.36）。サロゲート違反 18/24 行・32 ステップ、教師 0 |
| D5 | 3db10647 | Hagan グリッドを α×T×K の 3×3×9 に。静的裁定は α スライスごと。acceptance が配列から領域 RMSE を再計算 | long 21.4948 / high-vol 19.4385 bp（旧 26.2144 で一致）。worst 60.64 → 65.78 bp |
| D6 | f812e8ef | 5y 実質ゼロ linker＋floor を名目ゼロ債と ZCIS で PV01・CPI delta ヘッジし再評価。floor 恒等式は償還キャッシュフローで検査（check 名・件数は不変） | 残差 0、実質 PV01 −0.0451 → 1.8e-7、シナリオ P&L はヘッジ後に最大 66.6% |
| D7 | 012b305c | HJM / BGM の曲線を初期フォワードから再構築して RMSE を計算 | 丸め誤差のみ |
| D8 | 8580546f | notebook ゲートがコミット済み出力と巻別 VALIDATION.md を照合 | vol 21 / 27 を再生成 |
| D10 | 21eadd03 | Ch.13 ツリーを GE 版（r=4%）と US 版の両方で固定 | — |
| D11 | 90e903ea | vol 28 notebook に「本巻で実装しない節」を追加、`cds_option` の範囲を明記、Ex 24.8 を固定 | 0.128 / $5.13M |

vol 21 は `frontier_reference.py` の SHA 契約のため各変更で再生成した（timing は保持）。

**残り:** D9（core notebook の出力方式、§7 の判断事項）と、§3（未再確認の監査報告。R8 だけは D4 と同時に対応）・§4（open 項目）・§6（文書の食い違い）は未着手。§2 の欠陥表と §9 の推奨順序は監査時点の記述のまま残し、修正済みかどうかはこの節で判断する。
