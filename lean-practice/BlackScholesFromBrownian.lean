import BrownianMotion.Gaussian.BrownianMotion
import MathFin.Models.BlackScholes.PDEFromFeynmanKac
import MathFin.Models.BlackScholes.Market
import MathFin.Models.BlackScholes.BlackScholesSDE
import MathFin.Models.BlackScholes.BlackScholesSelfFinancing
import MathFin.Probability.Brownian.Ito.ItoSquaringIdentity
import MathFin.Probability.Brownian.QuadraticVariationL2

/-!
# ブラウン運動からブラック・ショールズ方程式まで

連続時間の株価は、BrownianMotion が構成したブラウン運動を使って定義する。
MathFin の伊藤積分、ギルサノフの定理、熱核の定理を利用する。
時間変数は満期までの時間 `τ = T - t` なので、方程式の時間微分は `-Vτ` になる。
-/

open MeasureTheory ProbabilityTheory Filter Set
open MathFin MathFin.Contracts MathFin.Contracts.BlackScholes
open MathFin.ItoIntegralL2 MathFin.ItoIntegralLocalised
open scoped NNReal Topology

namespace LeanPractice.BlackScholes

set_option autoImplicit false

/-- 一定係数の場合、同じブラウン運動による値動きがほとんど確実に一致すれば、
ドリフトと拡散係数がそれぞれ一致する。 -/
theorem brownian_affine_coefficients_unique {T : ℝ≥0} (hT : 0 < T)
    {drift₁ drift₂ diffusion₁ diffusion₂ : ℝ}
    (h : ∀ᵐ ω ∂gaussianLimit,
      drift₁ * (T : ℝ) + diffusion₁ * brownian T ω =
      drift₂ * (T : ℝ) + diffusion₂ * brownian T ω) :
    drift₁ = drift₂ ∧ diffusion₁ = diffusion₂ := by
  have hDiffusion : diffusion₁ = diffusion₂ := by
    by_contra hne
    let x := (drift₂ - drift₁) * (T : ℝ) / (diffusion₁ - diffusion₂)
    have hAtX : ∀ᵐ ω ∂gaussianLimit, brownian T ω = x := by
      filter_upwards [h] with ω hω
      apply (eq_div_iff (sub_ne_zero.mpr hne)).2
      linear_combination hω
    -- 分散が正の正規分布では、どの1点に対しても確率はゼロ。
    have hNoAtom : gaussianLimit (brownian T ⁻¹' {x}) = 0 := by
      rw [← Measure.map_apply (measurable_brownian T) (measurableSet_singleton x),
        hasLaw_brownian_eval.map_eq]
      exact (gaussianReal_absolutelyContinuous 0 hT.ne') (measure_singleton x)
    have hAvoidX : ∀ᵐ ω ∂gaussianLimit, brownian T ω ≠ x := by
      rw [ae_iff]
      simpa [Set.preimage] using hNoAtom
    obtain ⟨ω, hAt, hAvoid⟩ := (hAtX.and hAvoidX).exists
    exact hAvoid hAt
  obtain ⟨ω, hω⟩ := h.exists
  have hTReal : (T : ℝ) ≠ 0 := by exact_mod_cast hT.ne'
  have hDrift : drift₁ * (T : ℝ) = drift₂ * (T : ℝ) := by
    rw [hDiffusion] at hω
    exact add_right_cancel hω
  exact ⟨mul_right_cancel₀ hTReal hDrift, hDiffusion⟩

/-- 区間ごとの左端の値にブラウン運動の増分を掛けた和。 -/
noncomputable def brownianLeftSum (T : ℝ≥0) (n : ℕ) (ω : ℝ≥0 → ℝ) : ℝ :=
  ∑ k ∈ Finset.range n, brownian (unifPart T n k) ω *
    (brownian (unifPart T n (k + 1)) ω - brownian (unifPart T n k) ω)

/-- 二乗の伊藤公式。左端和は `(W_T² - W_0² - T) / 2` に平均二乗で収束する。 -/
theorem ito_squared_on_canonical_brownian (T : ℝ≥0) :
    Tendsto (fun n : ℕ ↦ ∫ ω,
      (brownianLeftSum T n ω - (brownian T ω ^ 2 - brownian 0 ω ^ 2 - (T : ℝ)) / 2) ^ 2
        ∂gaussianLimit) atTop (𝓝 0) := by
  have hQV := MathFin.QuadraticVariationL2.tendsto_qv
    isBrownianReal_brownian.toIsPreBrownianReal measurable_brownian T
  have hQuarter := hQV.const_mul (1 / 4 : ℝ)
  simp only [mul_zero] at hQuarter
  refine hQuarter.congr' ?_
  filter_upwards [eventually_gt_atTop (0 : ℕ)] with n hn
  rw [← integral_const_mul]
  refine integral_congr_ae (ae_of_all _ fun ω ↦ ?_)
  let qv := ∑ k ∈ Finset.range n,
    (brownian (unifPart T n (k + 1)) ω - brownian (unifPart T n k) ω) ^ 2
  -- 有限分割で二乗の差を展開し、隣り合う項を消去した等式を使う。
  have hSquare : brownian T ω ^ 2 - brownian 0 ω ^ 2 =
      2 * brownianLeftSum T n ω + qv := by
    simpa [brownianLeftSum, qv, unifPart_zero, unifPart_self T hn.ne'] using
      discrete_squaring_identity n (fun k ↦ brownian (unifPart T n k) ω)
  have hError : brownianLeftSum T n ω -
      (brownian T ω ^ 2 - brownian 0 ω ^ 2 - (T : ℝ)) / 2 =
      ((T : ℝ) - qv) / 2 := by
    linarith only [hSquare]
  change (1 / 4 : ℝ) * (qv - (T : ℝ)) ^ 2 =
    (brownianLeftSum T n ω - (brownian T ω ^ 2 - brownian 0 ω ^ 2 - (T : ℝ)) / 2) ^ 2
  rw [hError]
  ring

/-- 構成したブラウン運動から得た幾何ブラウン運動は、株価の確率微分方程式を満たす。 -/
theorem canonical_stock_solves_sde (S₀ drift σ : ℝ) (T : ℝ≥0) :
    ∀ᵐ ω ∂gaussianLimit, ∀ t ∈ Icc (0 : ℝ≥0) T,
      pathAssets S₀ drift σ brownian () t ω =
        S₀ + (∫ s in Ioc 0 t, drift * pathAssets S₀ drift σ brownian () s ω ∂timeMeasure)
          + predItoIntegral (μ := gaussianLimit) T measurable_brownian
            (isStronglyPredictable_diffusion_pathAssets
              measurable_brownian continuous_brownian S₀ drift σ) t ω :=
  pathAssets_solves_sde isBrownianReal_brownian.toIsPreBrownianReal measurable_brownian
    continuous_brownian T S₀ drift σ

/-- 現実測度のドリフトを `drift` とする市場において、同値な価格付け測度の下で
ヨーロピアン・コールの割引ペイオフを評価する。 -/
noncomputable def callValueFromMarket (K r σ drift S τ : ℝ) : ℝ :=
  (market gaussianLimit measurable_brownian S drift r σ).price
    (constGirsanovMeasure isBrownianReal_brownian.toIsPreBrownianReal measurable_brownian
      ((drift - r) / σ) τ.toNNReal)
    (europeanCall K τ.toNNReal)

/-- ブラック・ショールズ市場の有限個の取引時点で、上流の無裁定定理を適用する。 -/
theorem canonical_market_no_arbitrage {S drift r σ : ℝ} (hσ : σ ≠ 0)
    {dates : ℕ → ℝ≥0} (hDates : Monotone dates) (n : ℕ) :
    (market gaussianLimit measurable_brownian S drift r σ).NoArbitrage hDates n :=
  noArbitrage_market isBrownianReal_brownian.toIsPreBrownianReal measurable_brownian
    hσ hDates (H := dates n) le_rfl

/-- 満期ペイオフの割引期待値は、正規分布を使う価格式 `bsV` に等しい。 -/
theorem callValueFromMarket_eq_bsV {K r σ drift S τ : ℝ}
    (hK : 0 < K) (hσ : 0 < σ) (hS : 0 < S) (hτ : 0 < τ) :
    callValueFromMarket K r σ drift S τ = bsV K r σ S τ := by
  have hTime := Real.coe_toNNReal τ hτ.le
  have hT : 0 < (τ.toNNReal : ℝ) := by simpa only [hTime] using hτ
  simpa only [callValueFromMarket, bsV, hTime, neg_mul] using
    price_europeanCall_constGirsanovMeasure
      isBrownianReal_brownian.toIsPreBrownianReal measurable_brownian
      (S_0 := S) (m := drift) (r := r) (T := τ.toNNReal) (H := τ.toNNReal)
      le_rfl hS hK hσ hT

/-- 市場で評価したコール価格の偏微分が実際に存在し、ブラック・ショールズ方程式を
満たす。株価についての1階微分はデルタ `Φ(d₁)` になる。 -/
theorem call_satisfies_pde_from_market {K r σ drift S τ : ℝ}
    (hK : 0 < K) (hσ : 0 < σ) (hS : 0 < S) (hτ : 0 < τ) :
    ∃ Vτ VS VSS : ℝ,
      HasDerivAt (fun u ↦ callValueFromMarket K r σ drift S u) Vτ τ ∧
      HasDerivAt (fun s ↦ callValueFromMarket K r σ drift s τ) VS S ∧
      HasDerivAt (deriv fun s ↦ callValueFromMarket K r σ drift s τ) VSS S ∧
      -Vτ + (1 / 2) * σ ^ 2 * S ^ 2 * VSS + r * S * VS
        - r * callValueFromMarket K r σ drift S τ = 0 ∧
      VS = Phi (bsd1 S K r σ τ) := by
  obtain ⟨Vτ, VS, VSS, hVτ, hVS, hVSS, hPDE, _, hDelta, _⟩ :=
    bsV_satisfies_bs_pde_via_feynmanKac (r := r) hK hσ hS hτ
  -- 正の株価・残存期間で価格が一致するので、その近傍で微分も一致する。
  have hTimeEq :
      (fun u ↦ callValueFromMarket K r σ drift S u) =ᶠ[𝓝 τ] fun u ↦ bsV K r σ S u :=
    (eventually_gt_nhds hτ).mono fun _ hu ↦ callValueFromMarket_eq_bsV hK hσ hS hu
  have hSpotEq (s : ℝ) (hs : 0 < s) :
      (fun x ↦ callValueFromMarket K r σ drift x τ) =ᶠ[𝓝 s] fun x ↦ bsV K r σ x τ :=
    (eventually_gt_nhds hs).mono fun _ hx ↦ callValueFromMarket_eq_bsV hK hσ hx hτ
  have hDeltaEq :
      (deriv fun s ↦ callValueFromMarket K r σ drift s τ) =ᶠ[𝓝 S]
        (deriv fun s ↦ bsV K r σ s τ) :=
    (eventually_gt_nhds hS).mono fun s hs ↦ (hSpotEq s hs).deriv_eq
  refine ⟨Vτ, VS, VSS, hVτ.congr_of_eventuallyEq hTimeEq,
    hVS.congr_of_eventuallyEq (hSpotEq S hS), hVSS.congr_of_eventuallyEq hDeltaEq, ?_, hDelta⟩
  rw [callValueFromMarket_eq_bsV hK hσ hS hτ]
  exact hPDE

/-- 市場の価格から始めたデルタ・ヘッジは、満期前の任意の `T'` まで自己資金調達である。
株価の経路は、価格付け測度でのドリフト `r` で表す。 -/
theorem call_market_value_self_financing {S₀ K r σ drift : ℝ}
    (hS₀ : 0 < S₀) (hK : 0 < K) (hσ : 0 < σ) {T T' : ℝ≥0} (hT' : T' < T) :
    ∀ᵐ ω ∂gaussianLimit, ∀ t ∈ Icc (0 : ℝ≥0) T',
      callValueFromMarket K r σ drift (pathAssets S₀ r σ brownian () t ω) ((T : ℝ) - t) =
        callValueFromMarket K r σ drift S₀ T
          + ((∫ s in Ioc 0 t, hedgeDelta K r σ S₀ T brownian s ω *
                (r * pathAssets S₀ r σ brownian () s ω) ∂timeMeasure)
              + predItoIntegral (μ := gaussianLimit) T' measurable_brownian
                (hedgeGain_isStronglyPredictable measurable_brownian continuous_brownian
                  K r σ S₀ T) t ω)
          + ∫ s in Ioc 0 t, r * hedgeBank K r σ S₀ T brownian s ω ∂timeMeasure := by
  have hT'Nonneg : (0 : ℝ≥0) ≤ T' := zero_le
  have hT : 0 < (T : ℝ) := by exact_mod_cast lt_of_le_of_lt hT'Nonneg hT'
  have hInitial :
      callValueFromMarket K r σ drift S₀ T =
        (europeanCall K T).value gaussianLimit (fun u _ ↦ Real.exp (-r * u))
          (pathAssets S₀ r σ brownian) :=
    (callValueFromMarket_eq_bsV hK hσ hS₀ hT).trans
      (value_europeanCall_pathAssets isBrownianReal_brownian.toIsPreBrownianReal hT
        hS₀ hK hσ).symm
  filter_upwards [europeanCall_selfFinancing isBrownianReal_brownian.toIsPreBrownianReal
    measurable_brownian continuous_brownian hT hS₀ hK hσ T' hT'] with ω hω
  intro t ht
  have hSpot : 0 < pathAssets S₀ r σ brownian () t ω := mul_pos hS₀ (Real.exp_pos _)
  have hRemaining : 0 < (T : ℝ) - t := sub_pos.mpr (by
    exact_mod_cast lt_of_le_of_lt ht.2 hT')
  rw [callValueFromMarket_eq_bsV hK hσ hSpot hRemaining, hInitial]
  exact hω t ht

/-- 満期に近づくと、市場で評価したコール価格は各経路のペイオフに収束する。 -/
theorem call_market_value_tendsto_payoff {S₀ K r σ drift : ℝ}
    (hS₀ : 0 < S₀) (hK : 0 < K) (hσ : 0 < σ) (T : ℝ≥0) (ω : ℝ≥0 → ℝ) :
    Tendsto (fun t : ℝ≥0 ↦
      callValueFromMarket K r σ drift (pathAssets S₀ r σ brownian () t ω) ((T : ℝ) - t))
      (𝓝[<] T) (𝓝 (max (pathAssets S₀ r σ brownian () T ω - K) 0)) := by
  have hPayoff := tendsto_bsV_gbm_payoff (r := r) T hK hσ hS₀
    ((continuous_brownian ω).continuousAt (x := T))
  refine hPayoff.congr' ?_
  filter_upwards [self_mem_nhdsWithin (s := Iio T)] with t ht
  have hSpot : 0 < pathAssets S₀ r σ brownian () t ω := mul_pos hS₀ (Real.exp_pos _)
  have hRemaining : 0 < (T : ℝ) - t := sub_pos.mpr (NNReal.coe_lt_coe.mpr ht)
  exact (callValueFromMarket_eq_bsV hK hσ hSpot hRemaining).symm

end LeanPractice.BlackScholes
