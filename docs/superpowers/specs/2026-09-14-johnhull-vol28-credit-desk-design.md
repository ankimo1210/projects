# johnhull vol 28 — 信用商品評価デスク（Hull Ch.24–25 完全実装）設計

- 日付: 2026-09-14
- ステータス: 実装済み（2026-09-14 release、`main` c7194c5d。許容値は実装時に緩めたものを下に反映）
- 対象: `/home/kazumasa/projects/johnhull`（hullkit 新規 4 モジュール + `xva.py` 拡張 + `volumes/28_credit_desk`）
- ブランチ: `worktree-johnhull-vol28-credit-desk`（git worktree、共有 index 事故の回避）
- 親設計: `docs/superpowers/specs/2026-06-08-johnhull-09-credit-xva-design.md`（vol 09）、
  `docs/superpowers/specs/2026-07-20-johnhull-vol27-risk-desk-design.md`（巻の契約の雛形）
- 背景: vol 09（Hull 11e Ch.9/24/25）は 27 セルに 3 章を圧縮した結果、24.4 の債券価格
  ブートストラップ、24.7 の担保付き CVA、24.9 の CreditMetrics、25.2 の CDS レッグ表と MTM、
  25.4 の固定クーポン/アップフロント、25.5 の CDS フォワード/オプション、25.6/25.10 の
  k-th-to-default、25.10 の合成 CDO（ガウス求積）、25.9–25.10 のコンパウンド/ベース相関、
  25.11 の代替モデルが**説明文のみ**か**ノートブック内の未テスト関数**で終わっている。
  当時の設計書は「md/conceptual only」と明示して範囲外にしたが、その線引きは推奨案の自動適用で
  あり、ROADMAP は章単位で `done` と数えていた。本巻はこれを**節単位**で埋め、Hull 本文に
  印刷された数値例（Example 24.1/24.2/24.4/24.8、Table 24.4、Table 25.1–25.8、
  Example 25.1/25.2/25.3）に固定して検証する。

## 1. 目的と成功基準

**目的:** Hull Ch.24–25（＋Ch.9/24.7 の CVA 実務）の信用商品評価を、教科書の印刷数値に
ピン留めした検証済みコードで再現する教材巻を追加する。

**成功基準:**

1. hullkit に `credit_curve` / `cds` / `credit_portfolio` / `credit_metrics` の 4 モジュールが
   追加され、`xva` に 4 関数が加わる。公開 API docstring 100%、MODEL_INDEX 掲載、
   参照解決を既存 guard tests が保証する。既存 `credit.py` / `copula.py` / `xva.py` の
   既存関数は変更しない（vol 09/16/17 のピンを壊さない）。
2. 下表の Hull ピンが hullkit テストで許容値内に再現される（§3.6）。
3. vol 28 notebook が artifact-only で実行でき、`frontier_acceptance._volume28` が
   コミット済み配列から §4 の 17 チェックを再計算して全 PASS する。
4. 既存の全ゲート（hullkit+report suite・`make hull-artifacts-check` / `hull-notebooks-check` /
   `hull-report` / `hull-book` / `hull-release-check`・ruff）が通る。
5. 検証方針は vol 18–27 と同じ: **PASS = integration・数値恒等式・再現性・教科書ピンのみ**。
   市場予測力・較正品質の承認ではない。

## 2. スコープ

含む（すべて Hull 本文に答え合わせ先がある）:

| Hull 節 | 内容 | 答え合わせ |
|---|---|---|
| 24.4 | スプレッド→平均/フォワードハザード、債券価格からの区分定数ブートストラップ | Ex 24.1（2.5/3.0/3.25% → 3.5/3.75%）、Ex 24.2（λ=2.46/3.48/3.74%） |
| 24.7 | スプレッド由来 q_i、ネッティング、担保付きエクスポージャ（cure period）、特殊ケース式 (24.5) | ネッティング 40→15、Ex 24.4 の 4 ケース 5/0/0/5 |
| 24.9 | CreditMetrics（Table 24.4 推移行列、閾値、1 ファクター相関 MC、信用 VaR） | 閾値 1.2719/2.4089/2.8070、−3.7190/−3.0618/−1.7866、2.9290。Ex 24.8 は既存 `vasicek_credit_var` で $5.13M |
| 25.2 | CDS レッグ分解、パースプレッド、MTM、インプライドハザード、バイナリ CDS | Table 25.1–25.5（4.0728s / 0.0422s / 0.0506 → 123bp、MTM 0.0111、100bp→1.63%、バイナリ 0.0844→205bp） |
| 25.3–25.4 | インデックス、固定クーポン、アップフロント価格、act/360→act/act | Ex 25.1（λ=0.5717%、D=4.447、P=100.27） |
| 25.5 | CDS フォワードスプレッドと CDS オプション（Black 型・knock-out） | 解析恒等式（put–call parity、σ→0 極限）のみ。Hull に数値例なし |
| 25.6, 25.10 | k-th-to-default（条件付き二項→求積） | Ex 25.3（153bp、条件付き中間値付き） |
| 25.8–25.10 | 合成 CDO トランシェ（式 25.1–25.12、Gauss–Hermite M=60） | Ex 25.2（A=4.2846, B=0.0187, C=0.1496 → 348bp、Table 25.7 の条件付き列） |
| 25.9–25.10 | コンパウンド相関・ベース相関・0–X% 期待損失曲線 | Table 25.6（iTraxx 2007-01-31 気配）→ Table 25.8（17.7/7.8/14.0/18.2/23.3%、17.7/28.4/36.5/43.2/60.5%）、λ=0.382% |
| 25.11 | double-t コピュラ（ν=4）、不均質モデル（Andersen–Sidenius–Basu 再帰） | 極限恒等式（ν→∞ でガウスに一致、同質で二項に一致） |

含まない（説明文のみ。理由を併記）:

- KMV EDF への写像（Moody's の非公開データ。距離 DD までは既存 `merton_default_prob` で可）。
- 25.11 のランダム回収率・ランダムファクター負荷、implied copula、動的モデル（Hull に数値例がなく、
  答え合わせが極限しかない。implied copula は最適化問題で本巻の求積 API と別物）。
- ISDA 標準モデル厳密版（実日付・実カレンダー・act/360 の日次累積）。Hull は年/四半期の
  均等グリッドで例題を組んでおり、それに合わせる。
- CDS オプションの Hull–White (2003) 完全版（デフォルト前の knock-out を含む
  forward measure の厳密扱い）。Black 型の市場慣行式に留める。
- 市場データの取得。Table 25.6 の Creditex 気配は教科書に印刷された定数を転記する
  （§6 data policy）。
- vol 09 の改修（core-notebook ゲートの再実行を避ける。接続は ROADMAP/book/導入セルで示す）。

## 3. 成果物

### 3.1 hullkit 新規モジュール（torch-free、numpy/scipy のみ）

既存 `credit.py`（vol 09 ピン）、`copula.py`（vol 16）、`xva.py` の既存関数は**変更しない**。
`xva.py` は関数追加のみ。

#### `credit_curve.py` — ハザード曲線と校正

| API | 内容 |
|---|---|
| `HazardCurve(knots, hazards)` | frozen dataclass。区分定数 λ。`cumulative_hazard(t)` / `survival(t)` / `default_prob(t)` / `default_prob_between(t0, t1)` / `forward_hazard(t)`。knots は狭義単調増加 >0、hazards ≥0、同長。最終 knot 以降は最後の λ で平坦外挿。`from_constant(hazard)` で定数曲線 |
| `average_hazards_from_spreads(spreads, recovery)` | 式 (24.2): λ̄(T)=s(T)/(1−R)。配列対応 |
| `forward_hazards_from_average(tenors, average_hazards)` | 平均→区分定数フォワード（Ex 24.1 の 3.5/3.75%）。`HazardCurve` を返す |
| `risk_free_bond_price(face, coupon_rate, maturity, r, freq)` | 連続複利 r での無リスク債券価格（Ex 24.2 の 102.83/105.52/108.08） |
| `bond_price_from_yield(face, coupon_rate, maturity, yield_cc, freq)` | 利回り（連続複利）→価格（101.33/101.99/102.47） |
| `expected_default_loss_pv(curve, face, coupon_rate, maturity, r, recovery, freq, default_step)` | 6 か月区間の中点デフォルト、損失 = (フォワード無リスク価値 − R·face) の割引（Ex 24.2 の 63.33/60.40） |
| `bootstrap_from_bonds(bond_prices, coupon_rate, maturities, r, recovery, face=100.0, freq=2, default_step=0.5)` | 短い満期から順に λ_i を brentq で解く。`HazardCurve` を返す。診断用に各債券の期待損失 PV も返す `BondBootstrapResult` |
| `bootstrap_from_cds(tenors, spreads, recovery, r, freq=4)` | CDS 気配から区分定数ハザード（vol 09 セル 14 の関数を hullkit 化）。`cds.cds_legs` を使う |

#### `cds.py` — 単一名 CDS

| API | 内容 |
|---|---|
| `CDSLegs(annuity, accrual, protection)` | frozen dataclass。`risky_duration = annuity + accrual`、`par_spread = protection / risky_duration` |
| `cds_legs(curve, recovery, r, maturity, freq=1, binary=False)` | Hull §25.2 の離散レッグ。支払いは期末、デフォルトは各期の中点、アクルーアルは半期分。`curve` は `HazardCurve` または float（定数 λ）。`binary=True` でペイオフ 1（Table 25.5） |
| `cds_par_spread(...)` | `cds_legs(...).par_spread`（Table 25.2–25.4: 123bp） |
| `cds_mtm(contract_spread, curve, recovery, r, maturity, freq=1, side="seller")` | 売り手の価値 = D·s_contract − protection（150bp で 0.0111）、`side="buyer"` は符号反転 |
| `binary_cds_spread(...)` | ペイオフ固定 1 のパースプレッド（205bp） |
| `implied_hazard(spread, recovery, r, maturity, freq=1)` | brentq で定数 λ（100bp→1.63%、Ex 25.1 で 0.5717%） |
| `actual360_to_actual_actual(rate)` | ×365/360（Ex 25.1: 34bp→0.345%、40bp→0.406%） |
| `fixed_coupon_price(spread, coupon, duration)` | P = 100 − 100·D·(s − c)（Ex 25.1: 100.27） |
| `upfront_payment(spread, coupon, duration, notional)` | (100 − P)/100 × notional（負なら売り手が支払う） |
| `cds_forward_spread(curve, recovery, r, start, maturity, freq)` | start から maturity までのレッグを無条件生存確率で評価した比（knock-out 前提） |
| `cds_option(forward_spread, strike, sigma, expiry, risky_annuity, kind="payer")` | Black 型: payer = A[F N(d₁) − K N(d₂)]、receiver = A[K N(−d₂) − F N(−d₁)]。σ→0 で A·max(F−K, 0) |

#### `credit_portfolio.py` — 1 ファクターコピュラの求積評価

| API | 内容 |
|---|---|
| `gauss_hermite_factor(m=60)` | 標準正規期待値用の節点・重み（F=√2·x、w/√π）。Hull Table 25.7 の F_k=±0.2020, −0.6060, −1.0104 と重み 0.1579/0.1342/0.0969 に一致（確認済み） |
| `conditional_default_prob(q, rho, factor)` | 式 (25.5)、ベクトル化 |
| `default_count_pmf(n, q_cond)` | 式 (25.7) の二項 pmf（k=0..n） |
| `tranche_expected_principal(pmf, n, recovery, attach, detach)` | 式 (25.8)。m(x)=「x より大きい最小の整数」の定義を Hull どおりに実装 |
| `TrancheValuation` | frozen dataclass: `payment_times`、`factor_nodes`、`factor_weights`、`expected_principal[k, j]`、`annuity_by_factor`、`accrual_by_factor`、`protection_by_factor`、`annuity`、`accrual`、`protection`、`spread`、`upfront(fixed_spread)` |
| `cdo_tranche_valuation(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq=4, m=60, copula="gaussian", nu=4.0)` | 式 (25.9)–(25.12)。`hazard` が float なら同質（二項）、配列 (n,) なら不均質（ASB 再帰）。`copula="double_t"` で ν 自由度の double-t（§3.1 末尾）。Ex 25.2: A=4.2846, B=0.0187, C=0.1496 → 348bp |
| `cdo_tranche_spread(...)` / `cdo_upfront(..., fixed_spread)` | C/(A+B)、C − s*(A+B) |
| `kth_to_default_valuation(k, n_names, hazard, recovery, r, maturity, rho, freq=1, m=60)` | 条件付き「k 件以上」の確率差で k 番目デフォルトの区間確率、中点決済（Ex 25.3: 0.0629/4.0580s/0.0524s → 153bp、F=−1.0104 の条件付き中間値も返す） |
| `compound_correlation(target, attach, detach, ..., quote_kind="spread" \| "upfront", fixed_spread=0.05)` | brentq で ρ∈(1e-6, 1−1e-6)。Table 25.8 のコンパウンド行 |
| `base_correlations(quotes, attachments, ...)` | Hull の 4 ステップ: コンパウンド相関→各トランシェの C_q→0–a_q の EL 累積→a_q で割って ρ_base を逆算。`BaseCorrelationResult(compound, base, cumulative_expected_loss)` |
| `expected_loss_curve(detachments, base_correlations, ...)` | 0–X% の期待損失 PV（Figure 25.3） |
| `heterogeneous_default_pmf(q_cond)` | Andersen–Sidenius–Basu 再帰: P_k^{(i)} = P_k^{(i−1)}(1−p_i) + P_{k−1}^{(i−1)} p_i。同質入力で二項に一致（≤1e-12） |
| `double_t_factor_quadrature(nu, m)` | F を標準化 t_ν（分散 1）とし、CDF 空間の Gauss–Legendre 節点で F の期待値を近似 |
| `double_t_threshold(q, rho, nu)` | X=√ρF+√(1−ρ)Z（F, Z は標準化 t_ν）の CDF H(x)=E_F[T_std((x−√ρF)/√(1−ρ))] を求積し、H(x*)=q を brentq で解く |
| `double_t_conditional_prob(q, rho, factor, nu)` | T_std((x*−√ρF)/√(1−ρ))。ν→∞（ν=1e6）でガウス版とトランシェスプレッドが ±0.5bp 以内 |

#### `credit_metrics.py` — 格付推移と信用 VaR

| API | 内容 |
|---|---|
| `RATINGS` | `("AAA","AA","A","BBB","BB","B","CCC/C","Default")` |
| `HULL_TABLE_24_4` | 1981–2019 の 1 年推移行列（%、WR 配分済み）を Hull どおり転記 |
| `TransitionMatrix(probabilities)` | 行和 100%（±0.05 の丸め許容）を検証、`as_fraction()`、`multi_period(years)`（行列べき、Technical Note 11）、`default_column()` |
| `rating_thresholds(matrix, initial)` | 列順の累積確率の N⁻¹（AAA: 1.2719/2.4089/2.8070…、BBB: −3.7190/−3.0618/−1.7866…、BBB デフォルト境界 2.9290） |
| `simulate_rating_migrations(matrix, initial_ratings, rho, n_sims, rng)` | 1 ファクターガウスコピュラ x_i=√ρF+√(1−ρ)Z_i で新格付け index (n_sims, n_obligors) |
| `credit_loss_distribution(new_ratings, exposures, recovery, rating_values=None)` | デフォルト損失 = exposure·(1−R)。`rating_values`（格付け→価値比）を与えると格下げ損失（格上げは負の損失）も含む |
| `credit_var(losses, confidence)` / `expected_loss(losses)` | 分位点と平均 |

#### `xva.py` 追加（既存関数は不変）

| API | 内容 |
|---|---|
| `default_probs_from_spreads(times, spreads, recovery)` | Hull §24.7: q_i = exp(−s(t_{i−1})t_{i−1}/(1−R)) − exp(−s(t_i)t_i/(1−R)) |
| `netting_set_exposure(values, netting=True)` | 最後の軸を取引とみなし、`netting=True` で max(Σv,0)、False で Σmax(v,0)（10/30/−25 → 15 vs 40） |
| `collateralized_exposure(value, lagged_value, threshold=0.0)` | 二者間ゼロ閾値の担保規則（Ex 24.4）: 受取担保 C_r=max(V_lag−θ,0)、差入担保 C_p=max(−V_lag−θ,0)、exposure = max(V−C_r,0) + max(C_p−max(−V,0),0)。4 ケース 5/0/0/5 |
| `cva_single_payoff(no_default_value, recovery, default_probs)` | 式 (24.5): (1−R) f_nd Σq_i。閉形式 (1−R) f_nd (1−e^{−λT}) と一致（≤1e-12）、EE_t = f_nd·e^{rt} の一般 `cva`（2000 ステップ格子）と一致（≤1e-5） |

### 3.2 ボリューム `volumes/28_credit_desk/`

vol 27 と同形式（`scripts/build_frontier_notebooks.VOLUME_META[28]` から生成）:

- `build_28_credit_desk_notebook.py`（ラッパー、ruff exclude 対象）
- `credit_desk.ipynb`（artifact-only 実行、教材文は日本語）
- `reference/metrics.json` + `reference/credit_scenarios.npz`
  （`frontier_reference.volume28_reference(seed=20260746)` から
  `build_frontier_artifacts.py --volume 28` が生成、fingerprint 付き）
- `VALIDATION.md`（G10 様式、builder が生成）

`VOLUME_META[28]` の sections（各 1 図）:

| key | 図 | Hull |
|---|---|---|
| `bond_bootstrap_hazard` | 平均 vs フォワードハザード（Ex 24.1）と債券価格ブートストラップ（Ex 24.2） | 24.4 |
| `cds_leg_pv_by_year` | 年ごとの期待支払い・アクルーアル・ペイオフ PV（Table 25.2–25.4） | 25.2 |
| `cds_mtm_vs_contract_spread` | 契約スプレッドに対する MTM（150bp で 0.0111） | 25.2 |
| `fixed_coupon_price_vs_spread` | 気配スプレッドに対するアップフロント価格（Ex 25.1） | 25.4 |
| `cds_option_payer_receiver` | 行使スプレッドに対する payer/receiver 価値と parity | 25.5 |
| `tranche_expected_principal` | E_j(F_k) の時間×ファクター（Table 25.7） | 25.10 |
| `tranche_spread_vs_rho` | 標準トランシェのスプレッド（0–3% はアップフロント）vs ρ | 25.9 |
| `kth_to_default_spread` | k=1..5 のブレークイーブンスプレッド（Ex 25.3 の k=3 を含む） | 25.6/25.10 |
| `implied_correlation_smile` | Table 25.8 のコンパウンド vs ベース相関（Hull 印刷値を重ねる） | 25.10 |
| `expected_loss_curve` | 0–X% の期待損失 PV（Figure 25.3） | 25.10 |
| `double_t_vs_gaussian_spread` | ν=4 と ガウスのトランシェスプレッド比較、ν→∞ 極限 | 25.11 |
| `rating_thresholds` | Table 24.4 由来の閾値（AAA/BBB） | 24.9 |
| `creditmetrics_loss_histogram` | 独立 vs ρ=0.2 の損失分布と信用 VaR | 24.9 |
| `collateral_exposure_cases` | Ex 24.4 の 4 ケースとネッティング効果 | 24.7 |

verification セル: 主要恒等式（123bp、348bp、153bp、Table 25.8 再価格、EL 曲線の凹性、
式 24.5 の一致）をコミット済み配列から再計算。exercises セルに演習 5 問。

### 3.3 reference artifact の配列・指標（抜粋、実装時に確定）

配列: `bond_maturities`, `bond_prices`, `bond_risk_free_prices`, `bond_expected_loss_pv`,
`bond_forward_hazard`, `bond_bootstrap_hazard`, `cds_year`, `cds_survival`, `cds_default_prob`,
`cds_payment_pv`, `cds_accrual_pv`, `cds_payoff_pv`, `cds_contract_spread_grid`, `cds_mtm_seller`,
`index_spread_grid`, `fixed_coupon_price`, `option_strike_grid`, `payer_value`, `receiver_value`,
`tranche_payment_time`, `factor_nodes`, `factor_weights`, `tranche_expected_principal`（M×m）,
`tranche_annuity_by_factor`, `tranche_accrual_by_factor`, `tranche_protection_by_factor`,
`rho_grid`, `tranche_names`, `tranche_attach`, `tranche_detach`, `tranche_spread_vs_rho`,
`kth_order`, `kth_spread`, `kth_conditional_cumulative_prob`, `market_tranche_quote`,
`compound_correlation`, `base_correlation`, `hull_compound_correlation`, `hull_base_correlation`,
`el_curve_x`, `el_curve_value`, `double_t_nu_grid`, `double_t_spread`, `gaussian_spread`,
`transition_matrix`, `threshold_aaa`, `threshold_bbb`, `credit_loss_independent`,
`credit_loss_correlated`, `collateral_case_value`, `collateral_case_lagged`,
`collateral_case_exposure`, `netting_trade_values`。

指標: `cds_par_spread_bp`, `cds_risky_duration`, `cds_protection_pv`, `cds_mtm_seller_150bp`,
`cds_implied_hazard_100bp`, `binary_cds_spread_bp`, `bond_bootstrap_hazard_1/2/3`,
`fixed_coupon_hazard`, `fixed_coupon_duration`, `fixed_coupon_price`, `cdo_mezz_annuity`,
`cdo_mezz_accrual`, `cdo_mezz_protection`, `cdo_mezz_spread_bp`, `cdo_index_hazard`,
`kth3_spread_bp`, `kth3_protection`, `kth3_annuity`, `kth3_accrual`, `itraxx_hazard`,
`base_correlation_max_reprice_error_bp`, `double_t_limit_gap_bp`, `heterogeneous_binomial_gap`,
`creditmetrics_bbb_default_threshold`, `credit_var_independent`, `credit_var_correlated`,
`netting_exposure`, `gross_exposure`, `cva_special_case`, `cva_general_equivalent`。

Hull の印刷値は `hull_*` プレフィクスで配列/指標に併記し、acceptance が差分を検査する。

## 4. Acceptance checks（`frontier_acceptance._volume28`、コミット済み配列から再計算）

| Check | 基準 |
|---|---|
| `cds_par_spread_hull_pin` | 配列（生存確率・割引係数）から再計算した 5Y スプレッドが 123bp ± 0.5bp |
| `cds_mtm_identity` | D·0.015 − protection が指標 `cds_mtm_seller_150bp` と一致（≤1e-10）、値 0.0111 ± 0.0001 |
| `cds_bootstrap_round_trip` | ブートストラップ曲線で市場 CDS 気配を再価格 ≤1e-10 |
| `bond_bootstrap_hull_pin` | λ₁/λ₂/λ₃ が 2.46/3.48/3.74% ± 0.02pt、期待損失 PV が 1.50/3.53/5.61 ± 0.01 |
| `fixed_coupon_price_identity` | 100 − 100·D·(s−c) の再計算が指標と一致、Ex 25.1 の 100.27 ± 0.01 |
| `cds_option_parity` | payer − receiver = A(F − K) ≤1e-10（全行使価格） |
| `cdo_mezz_spread_hull_pin` | 配列 E_j(F_k) と重みから A,B,C を再求積し 348bp ± 1bp、A/B/C が 4.2846/0.0187/0.1496 ± 0.002 |
| `expected_principal_monotone` | E_j(F_k) が j について非増加、F について非減少 |
| `capital_structure_loss_conservation` | Σ_tranche (a_H−a_L)·C_tranche = 0–100% の C（≤1e-8） |
| `kth_to_default_hull_pin_and_ordering` | k=3 が 153bp ± 1bp、スプレッドが k について単調減少 |
| `implied_correlation_reprices_quotes` | コンパウンド相関で Table 25.6 の気配を再価格 ≤0.1bp（0–3% はアップフロント ≤0.01pt） |
| `implied_correlation_hull_pin` | Table 25.8 のコンパウンド/ベース相関 ± 1.0pt（DerivaGem との離散化差を許容、実測値を記録） |
| `base_correlation_curve_shape` | 0–X% 期待損失 PV が X について増加かつ増分逓減 |
| `double_t_gaussian_limit` | ν=1e6 の double-t スプレッド − ガウススプレッド ≤ 0.5bp |
| `heterogeneous_equals_binomial` | 同質入力の ASB 再帰 pmf − 二項 pmf ≤1e-12 |
| `creditmetrics_thresholds_hull_pin` | 閾値 7 値が Hull ± 0.0001、独立 vs ρ=0.2 で信用 VaR（99.9%）が相関側で大きい |
| `netting_collateral_and_cva_special_case` | ネッティング 15 ≤ グロス 40、担保 4 ケース 5/0/0/5、式 (24.5) と閉形式の差 ≤1e-12、一般 `cva`（2000 ステップ格子）との差 ≤1e-5 |

許容値は固定 seed の実測に余裕を持たせて実装時に確定し、VALIDATION.md の表に記録する（慣行）。
Table 25.8 の相関ピンは DerivaGem（30 点×2）との離散化差を含むので、実測差を negative results に
書き、許容値を勝手に広げない（超えたら原因を調べる）。

## 5. 配線・ドキュメント

- `release_manifest.json` に vol 28 エントリ（vol 27 と同形式）: `slug: 28_credit_desk`、
  `notebook: credit_desk.ipynb`、`book_name: 28_credit_desk`、`portal_page: risk_credit`
  （既存ページ「リスクと信用」）、`portal_figures` 4 点
  （`cds_leg_pv_by_year`・`tranche_spread_vs_correlation`・`base_correlation_skew`・
  `creditmetrics_loss_distribution`）、`semantic_sources` に `frontier_reference` + 新規 4 モジュール
  + `xva`、`semantic_tests` に対応テスト、`references` に metrics.json + npz。
  `portal.figures` を 78 → 82 に更新。
- 上限 27 → 28 の更新: `FrontierReference.__post_init__`（`range(21, 29)`）、`_BUILDERS[28]`、
  `build_frontier_reference` のエラー文、`build_frontier_artifacts.FILES[28]` +
  `UNITS_BY_VOLUME[28]`、`build_frontier_notebooks.VOLUME_META[28]`、
  `frontier_acceptance._EVALUATORS[28]` とエラー文、`verify_release.py`（`range(18, 29)`）、
  `test_frontier_reference.py`（`[21, 28]`・seed 規則 `20260718 + volume`）、各 docstring の
  「18--27 / 21--27」表記。
- `report/report_builder/frontier_figures.py` に `_vol28_*` 4 図と `FRONTIER_BUILDERS` 登録、
  `figures.py` の `risk_credit` ページに FigureSpec 4 点（`risk_credit` 8 → 12、合計 82）。
  `report/tests/test_report_build.py` の期待値更新。
- `book/_toc.yml` に `notebooks/28_credit_desk`（vol 26–27 の part に追加）、
  `book/notebooks/28_credit_desk.ipynb` symlink、`book/notebooks/00_overview.md` に 1 行。
- `MODEL_INDEX.md` §6（Risk & credit）に 5 モジュール分の行。
- `ROADMAP.md` に vol 28 行（`| 28 | volumes/28_credit_desk | ... | done |` 形式、
  verify_release が正規表現で照合）と、vol 09 の未実装節が本巻で埋まった旨。
- `README.md` の巻一覧・`make` 説明（18–28）。
- `VALIDATION.md` に vol 28 行（Gate matrix、acceptance 表、Numerical evidence、
  Negative results、Fresh validation record）。
- `docs/DATA_PROVENANCE.md` に「Volume 28 credit-desk reference」節: すべて公開 hullkit API と
  固定 seed `20260746` から生成。**Table 25.6（Creditex、2007-01-31 の iTraxx Europe 中値）と
  Table 24.4（S&P 1981–2019 推移行列）は Hull 11e に印刷された教科書定数を転記したもので、
  ダウンロード・ライセンス付きデータの再配布ではない**と明記。`limitations` にも同文。
- `johnhull/CLAUDE.md` の「vol 18–27」表記を 18–28 に。

## 6. 決めごと

- **data_policy は `synthetic-offline` のまま。** 教科書転記定数は「fixture」であり、
  verify_release の契約（`data_policy == synthetic-offline`）を変えない。
- **Hull の離散化に合わせる。** 年 1 回払い + 年央デフォルト（Table 25.1–25.4、Ex 25.3）、
  四半期払い + 期央デフォルト（Ex 25.1/25.2）、6 か月区間の中点デフォルト（Ex 24.2）。
  ISDA 実日付モデルは範囲外。
- **既存 API の再利用**: 条件付き PD は既存 `credit.gaussian_copula_conditional`（a=√ρ）と
  数値一致をテストで確認するが、ベクトル化版を `credit_portfolio` に持つ。
  Vasicek は既存 `credit.vasicek_credit_var` をそのまま使う。
- **エラー方針**: ρ∈[0,1)、R∈[0,1)、attach<detach≤1、k∈[1,n]、ν>2、行和検証などで
  `ValueError` を明示的に投げる。brentq の括弧が取れない場合も `ValueError`。
- **決定性**: MC は CreditMetrics のみ（固定 seed）。求積系はすべて決定的。

## 7. 検証ゲート（完了条件、すべて worktree の repo root から）

1. `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests`
2. `uv run --no-sync python johnhull/scripts/build_frontier_artifacts.py --volume 28`
3. `uv run --no-sync --package hullkit python johnhull/volumes/28_credit_desk/build_28_credit_desk_notebook.py`
4. `make hull-artifacts-check` / `make hull-notebooks-check`
5. `make hull-report` / `make hull-book`
6. `make hull-release-check`（コミット後に `HULL_RELEASE_FLAGS=--require-tracked`）
7. `uv run --no-sync ruff check johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts johnhull/report/report_builder johnhull/report/tests`
8. `make hull-core-notebooks-check` は vol 09 を触らないので不要だが、`credit.py` に手を入れないことを
   `git diff --stat` で確認する。

## 8. 実装順（writing-plans の入力）

1. `credit_curve.py` + テスト（Ex 24.1/24.2 ピン）
2. `cds.py` + テスト（Table 25.1–25.5、Ex 25.1、option parity）
3. `credit_portfolio.py` + テスト（Ex 25.2/25.3、Table 25.8、double-t 極限、ASB 恒等式）
4. `credit_metrics.py` + テスト（Table 24.4 閾値、MC の決定性と相関効果）
5. `xva.py` 追加 + テスト（ネッティング/担保/式 24.5）
6. `MODEL_INDEX.md` 更新（guard tests が緑になる）
7. `frontier_reference.volume28_reference` + `test_frontier_reference` 追加
8. `frontier_acceptance._volume28` + artifact builder 配線 + artifact 生成
9. `VOLUME_META[28]` + notebook 生成 + VALIDATION.md
10. portal 図 4 点 + report tests + book/manifest/ROADMAP/README/DATA_PROVENANCE/VALIDATION
11. 全ゲート実行、コミット
