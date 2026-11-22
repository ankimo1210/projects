import BrownianMotion.Gaussian.BrownianMotion
import MathFin.Models.BlackScholes.BlackScholesHedge
import MathFin.Probability.Brownian.BrownianExpMoment

/-!
# ヨーロピアン・コールの満期までの複製

割引後の株価を使い、デルタ・ヘッジの確率積分を満期まで構成する。
価格付け測度として `gaussianLimit` を使い、株価のドリフトを無リスク金利 `r` とする。
-/

open MeasureTheory ProbabilityTheory Filter Set
open MathFin
open MathFin.ItoIntegralL2 MathFin.ItoIntegralCLM MathFin.ItoIntegralLocalised
open MathFin.ItoIntegralProcessGeneral MathFin.ItoIntegralProcessContinuousModification
open MathFin.ItoIntegralPredictable
open scoped NNReal Topology InnerProductSpace

namespace LeanPractice.BlackScholes

set_option autoImplicit false

local notation "BrownianPath" => (ℝ≥0 → ℝ)

private theorem discounted_stock_eq (S₀ r σ : ℝ) (t : ℝ≥0) (ω : BrownianPath) :
    Real.exp (-(r * (t : ℝ))) * gbmValue S₀ r σ t (brownian t ω) =
      gbmValue S₀ 0 σ t (brownian t ω) := by
  unfold gbmValue
  rw [mul_left_comm, ← Real.exp_add]
  congr 2
  ring

/-- 価格付け測度における割引株価の二次モーメントは `S₀² exp(σ²t)`。 -/
theorem expected_discounted_stock_square (S₀ σ : ℝ) (t : ℝ≥0) :
    (∫ ω, gbmValue S₀ 0 σ t (brownian t ω) ^ 2 ∂gaussianLimit) =
      S₀ ^ 2 * Real.exp (σ ^ 2 * (t : ℝ)) := by
  calc
    _ = (∫ ω, (S₀ ^ 2 * Real.exp (-(σ ^ 2 * (t : ℝ)))) *
        Real.exp ((2 * σ) * brownian t ω) ∂gaussianLimit) := by
      apply integral_congr_ae
      refine ae_of_all _ fun ω ↦ ?_
      dsimp only
      unfold gbmValue
      rw [mul_pow, ← Real.exp_nat_mul, mul_assoc, ← Real.exp_add]
      congr 2
      push_cast
      ring
    _ = _ := by
      rw [integral_const_mul,
        integral_exp_mul_eval isBrownianReal_brownian.toIsPreBrownianReal t (2 * σ),
        mul_assoc, ← Real.exp_add]
      congr 2
      ring

private theorem memLp_discounted_stock (S₀ σ : ℝ) (T : ℝ≥0) :
    MemLp (fun z : ℝ≥0 × BrownianPath ↦ gbmValue S₀ 0 σ z.1 (brownian z.1 z.2))
      2 ((timeMeasureHorizon T).prod gaussianLimit) := by
  have hPred := isStronglyPredictable_comp_path measurable_brownian continuous_brownian
    (h := fun t x ↦ gbmValue S₀ 0 σ t x) (by unfold gbmValue; fun_prop)
  have hMeas := (hPred.mono (natFiltration measurable_brownian).predictable_le_prod).measurable
  apply (memLp_two_iff_integrable_sq hMeas.aestronglyMeasurable).2
  refine (integrable_prod_iff (hMeas.pow_const (2 : ℕ)).aestronglyMeasurable).2 ⟨?_, ?_⟩
  · refine ae_of_all _ fun t ↦ ?_
    have hSlice := (memLp_exp_mul_eval isBrownianReal_brownian.toIsPreBrownianReal t σ).const_mul
      (S₀ * Real.exp (-(σ ^ 2 / 2) * (t : ℝ)))
    have hSliceSq := (memLp_two_iff_integrable_sq hSlice.aestronglyMeasurable).mp hSlice
    refine hSliceSq.congr (ae_of_all _ fun ω ↦ ?_)
    change (S₀ * Real.exp (-(σ ^ 2 / 2) * (t : ℝ)) * Real.exp (σ * brownian t ω)) ^ 2 =
      gbmValue S₀ 0 σ t (brownian t ω) ^ 2
    unfold gbmValue
    rw [mul_assoc, ← Real.exp_add, zero_sub]
  · have hNormIntegral (t : ℝ≥0) :
        (∫ ω, ‖gbmValue S₀ 0 σ t (brownian t ω) ^ 2‖ ∂gaussianLimit) =
          S₀ ^ 2 * Real.exp (σ ^ 2 * (t : ℝ)) := by
      rw [← expected_discounted_stock_square]
      exact integral_congr_ae (ae_of_all _ fun ω ↦ Real.norm_of_nonneg (sq_nonneg _))
    change Integrable (fun t : ℝ≥0 ↦
      ∫ ω, ‖gbmValue S₀ 0 σ t (brownian t ω) ^ 2‖ ∂gaussianLimit) (timeMeasureHorizon T)
    simp_rw [hNormIntegral]
    refine (integrable_const (S₀ ^ 2 * Real.exp (σ ^ 2 * (T : ℝ)))).mono' (by fun_prop) ?_
    have hWindow : ∀ᵐ t ∂timeMeasureHorizon T, t ∈ Ioc 0 T :=
      ae_restrict_mem measurableSet_Ioc
    filter_upwards [hWindow] with t ht
    rw [Real.norm_of_nonneg (by positivity)]
    gcongr
    exact NNReal.coe_le_coe.mpr ht.2

/-- デルタは `0 ≤ Φ(d₁) ≤ 1` なので、割引株価の二次モーメントで
デルタ・ヘッジの被積分関数を満期まで評価できる。 -/
theorem call_hedge_integrand_memLp (K r σ S₀ : ℝ) (T : ℝ≥0) :
    MemLp (Function.uncurry fun (t : ℝ≥0) (ω : BrownianPath) ↦
      deltaHedgeIntegrand K r σ S₀ T t (brownian t ω))
      2 (trimMeasure (μ := gaussianLimit) T measurable_brownian) := by
  have hPred := deltaHedgeIntegrand_isStronglyPredictable
    measurable_brownian continuous_brownian K r σ S₀ T
  have hLe := (natFiltration measurable_brownian).predictable_le_prod
  have hProduct :
      MemLp (Function.uncurry fun (t : ℝ≥0) (ω : BrownianPath) ↦
        deltaHedgeIntegrand K r σ S₀ T t (brownian t ω))
        2 ((timeMeasureHorizon T).prod gaussianLimit) := by
    refine ((memLp_discounted_stock S₀ σ T).const_mul σ).mono
      (hPred.mono hLe).aestronglyMeasurable (ae_of_all _ fun z ↦ ?_)
    change ‖deltaHedgeIntegrand K r σ S₀ T z.1 (brownian z.1 z.2)‖ ≤
      ‖σ * gbmValue S₀ 0 σ z.1 (brownian z.1 z.2)‖
    unfold deltaHedgeIntegrand
    rw [discounted_stock_eq, norm_mul, Real.norm_of_nonneg (Phi_nonneg _)]
    exact mul_le_of_le_one_right (norm_nonneg _) (Phi_le_one _)
  unfold MemLp trimMeasure
  rw [eLpNorm_trim hLe hPred]
  exact hProduct.eLpNorm_lt_top

/-- 満期までの L² 空間に入れた、割引デルタ・ヘッジの被積分関数。 -/
noncomputable def callHedgeIntegrand (K r σ S₀ : ℝ) (T : ℝ≥0) :
    Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian) :=
  (call_hedge_integrand_memLp K r σ S₀ T).toLp
    (Function.uncurry fun (t : ℝ≥0) (ω : BrownianPath) ↦
      deltaHedgeIntegrand K r σ S₀ T t (brownian t ω))

/-- 切り詰めた予測可能過程の L² 同値類は、元の過程の L² 同値類に収束する。 -/
private theorem tendsto_clipped_integrands {Ω : Type*} [MeasurableSpace Ω]
    {μ : Measure Ω} [IsProbabilityMeasure μ] {B H : ℝ≥0 → Ω → ℝ}
    (T : ℝ≥0) (hMeas : ∀ t, Measurable (B t))
    (hPredictable : IsStronglyPredictable (natFiltration hMeas) H)
    (hL2 : MemLp (Function.uncurry H) 2 (trimMeasure (μ := μ) T hMeas)) :
    Tendsto (fun n : ℕ ↦ processToLpPredictable (μ := μ) T hMeas
      (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H))
      atTop (𝓝 (hL2.toLp (Function.uncurry H))) := by
  let ν := trimMeasure (μ := μ) T hMeas
  let squaredError (n : ℕ) (z : ℝ≥0 × Ω) : ℝ := (clip n H z.1 z.2 - H z.1 z.2) ^ 2
  have hBoundIntegrable : Integrable (fun z : ℝ≥0 × Ω ↦ 4 * H z.1 z.2 ^ 2) ν :=
    ((memLp_two_iff_integrable_sq hL2.aestronglyMeasurable).mp hL2).const_mul 4
  have hDominated (n : ℕ) : ∀ᵐ z ∂ν, ‖squaredError n z‖ ≤ 4 * H z.1 z.2 ^ 2 := by
    refine ae_of_all _ fun z ↦ ?_
    have hClipBound : |clip n H z.1 z.2| ≤ |H z.1 z.2| := by
      by_cases hn : |H z.1 z.2| ≤ (n : ℝ)
      · rw [clip_eq_self hn]
      · exact (abs_clip_le n H z.1 z.2).trans (le_of_not_ge hn)
    have hErrorBound : |clip n H z.1 z.2 - H z.1 z.2| ≤ 2 * |H z.1 z.2| := by
      calc
        _ ≤ |clip n H z.1 z.2| + |H z.1 z.2| := abs_sub _ _
        _ ≤ _ := by linarith only [hClipBound]
    change ‖(clip n H z.1 z.2 - H z.1 z.2) ^ 2‖ ≤ _
    rw [Real.norm_of_nonneg (sq_nonneg _), ← sq_abs (clip n H z.1 z.2 - H z.1 z.2)]
    calc
      _ ≤ (2 * |H z.1 z.2|) ^ 2 := pow_le_pow_left₀ (abs_nonneg _) hErrorBound _
      _ = _ := by rw [mul_pow, sq_abs]; ring
  have hLimit : ∀ᵐ z ∂ν, Tendsto (fun n ↦ squaredError n z) atTop (𝓝 0) := by
    refine ae_of_all _ fun z ↦ ?_
    obtain ⟨N, hN⟩ := exists_nat_ge |H z.1 z.2|
    refine tendsto_const_nhds.congr' ?_
    filter_upwards [eventually_ge_atTop N] with n hn
    simp [squaredError, clip_eq_self (hN.trans (Nat.cast_le.mpr hn))]
  have hMeasurable (n : ℕ) :
      StronglyMeasurable[(natFiltration hMeas).predictable] (squaredError n) :=
    ((clip_isStronglyPredictable hMeas hPredictable n).sub hPredictable).pow 2
  have hSquareLimit : Tendsto (fun n ↦ ∫ z, squaredError n z ∂ν) atTop (𝓝 0) := by
    have h := tendsto_integral_of_dominated_convergence
      (fun z : ℝ≥0 × Ω ↦ 4 * H z.1 z.2 ^ 2)
      (F := squaredError) (f := fun _ ↦ 0) (fun n ↦ (hMeasurable n).aestronglyMeasurable)
      hBoundIntegrable hDominated hLimit
    simpa only [integral_zero] using h
  let clippedLp (n : ℕ) := processToLpPredictable (μ := μ) T hMeas
    (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H)
  let φ := hL2.toLp (Function.uncurry H)
  have hNormSq (n : ℕ) : ‖clippedLp n - φ‖ ^ 2 = ∫ z, squaredError n z ∂ν := by
    rw [← real_inner_self_eq_norm_sq, L2.inner_def]
    refine integral_congr_ae ?_
    filter_upwards [Lp.coeFn_sub (clippedLp n) φ,
      processToLpPredictable_coeFn (μ := μ) T hMeas
        (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H),
      hL2.coeFn_toLp] with z hz hClip hOrig
    rw [hz, Pi.sub_apply]
    change ⟪clippedLp n z - φ z, clippedLp n z - φ z⟫_ℝ = squaredError n z
    rw [real_inner_self_eq_norm_sq, Real.norm_eq_abs, sq_abs, hClip, hOrig]
    rfl
  change Tendsto clippedLp atTop (𝓝 φ)
  rw [tendsto_iff_norm_sub_tendsto_zero]
  simp_rw [← hNormSq] at hSquareLimit
  simpa only [Real.sqrt_sq_eq_abs, abs_norm, Real.sqrt_zero] using hSquareLimit.sqrt

/-- 短い区間で使った局所化した伊藤積分は、同じ時刻で満期までの L² 積分と一致する。 -/
private theorem predItoIntegral_eq_l2 {Ω : Type*} [MeasurableSpace Ω]
    {μ : Measure Ω} [IsProbabilityMeasure μ] {B H : ℝ≥0 → Ω → ℝ}
    (hB : IsPreBrownianReal B μ) (hMeas : ∀ t, Measurable (B t))
    (hBcont : ∀ ω, Continuous (fun s ↦ B s ω)) {T t : ℝ≥0} (ht : t ≤ T)
    (hPredictable : IsStronglyPredictable (natFiltration hMeas) H)
    (hPaths : ∀ᵐ ω ∂μ, ContinuousOn (fun s ↦ H s ω) (Icc 0 t))
    (hL2 : MemLp (Function.uncurry H) 2 (trimMeasure (μ := μ) T hMeas)) :
    predItoIntegral (μ := μ) t hMeas hPredictable t =ᵐ[μ]
      (itoProcessCLM hB T t hMeas (hL2.toLp (Function.uncurry H)) : Ω → ℝ) := by
  let φ (n : ℕ) := processToLpPredictable (μ := μ) T hMeas
    (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H)
  have hClip (n : ℕ) : clipPredMod (μ := μ) t hMeas hPredictable n t =ᵐ[μ]
      (itoProcessCLM hB T t hMeas (φ n) : Ω → ℝ) := by
    have hMod := itoContinuousMod_modification hB t hMeas hBcont
      (processToLpPredictable (μ := μ) t hMeas
        (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H)) le_rfl
    rw [itoProcessCLM_terminal_eq hB t hMeas,
      ← itoProcessCLM_processToLpPredictable hB T hMeas ht
        (clip_isStronglyPredictable hMeas hPredictable n) (abs_clip_le n H)] at hMod
    exact hMod
  have hLimitLp : Tendsto (fun n ↦ itoProcessCLM hB T t hMeas (φ n)) atTop
      (𝓝 (itoProcessCLM hB T t hMeas (hL2.toLp (Function.uncurry H)))) :=
    ((itoProcessCLM hB T t hMeas).continuous.tendsto _).comp
      (tendsto_clipped_integrands T hMeas hPredictable hL2)
  have hLimitInMeasure := (tendstoInMeasure_of_tendsto_Lp hLimitLp).congr_left
    (fun n ↦ (hClip n).symm)
  have hLimitPath : TendstoInMeasure μ (fun n ↦ clipPredMod (μ := μ) t hMeas hPredictable n t)
      atTop (predItoIntegral (μ := μ) t hMeas hPredictable t) := by
    refine tendstoInMeasure_of_tendsto_ae (fun n ↦
      (Lp.memLp (itoProcessCLM hB T t hMeas (φ n))).aestronglyMeasurable.congr
        (hClip n).symm) ?_
    filter_upwards [ae_predItoIntegral_eq hB t hMeas hBcont hPredictable hPaths, hPaths]
      with ω hEq hCont
    refine tendsto_const_nhds.congr' ?_
    filter_upwards [eventually_ge_atTop (denseLevel t (fun s ↦ H s ω))] with n hn
    exact hEq n t ⟨zero_le, le_rfl⟩
      (fun s hs ↦ (abs_le_denseLevel hCont s hs).trans (Nat.cast_le.mpr hn))
  exact tendstoInMeasure_ae_unique hLimitPath hLimitInMeasure

/-- 時刻 `t` までの割引デルタ・ヘッジ損益を L² 確率変数として表す。 -/
noncomputable def callHedgeGain (K r σ S₀ : ℝ) (T t : ℝ≥0) : Lp ℝ 2 gaussianLimit :=
  itoProcessCLM isBrownianReal_brownian.toIsPreBrownianReal T t measurable_brownian
    (callHedgeIntegrand K r σ S₀ T)

/-- ヘッジ損益は、満期を含めて平均二乗で連続である。 -/
theorem continuous_call_hedge_gain (K r σ S₀ : ℝ) (T : ℝ≥0) :
    Continuous (callHedgeGain K r σ S₀ T) :=
  itoIntegralProcessGen_l2_continuous isBrownianReal_brownian.toIsPreBrownianReal T
    measurable_brownian (callHedgeIntegrand K r σ S₀ T)

/-- 満期前のデルタ・ヘッジを、満期まで定義した L² 伊藤積分で表す。 -/
theorem discounted_call_hedge_before_maturity {K r σ S₀ : ℝ} {T t : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (ht : t < T) :
    (fun ω ↦ discountedCallBrownian K r σ S₀ T t (brownian t ω)) =ᵐ[gaussianLimit]
      fun ω ↦ bsV K r σ S₀ T + callHedgeGain K r σ S₀ T t ω := by
  have htReal : (t : ℝ) < (T : ℝ) := NNReal.coe_lt_coe.mpr ht
  have hPredictable := deltaHedgeIntegrand_isStronglyPredictable
    measurable_brownian continuous_brownian K r σ S₀ T
  have hPaths : ∀ᵐ ω ∂gaussianLimit, ContinuousOn (fun s : ℝ≥0 ↦
      deltaHedgeIntegrand K r σ S₀ T s (brownian s ω)) (Icc 0 t) := by
    refine ae_of_all _ fun ω ↦ ?_
    have hCap := continuous_deltaHedgeIntegrand_comp (r := r) hK hσ hS₀
      (contDiff_timeCap 1).continuous (timeCap_lt htReal)
    refine ((hCap.comp (NNReal.continuous_coe.prodMk (continuous_brownian ω))).continuousOn
      ).congr fun s hs ↦ ?_
    change deltaHedgeIntegrand K r σ S₀ T s (brownian s ω) =
      deltaHedgeIntegrand K r σ S₀ T (timeCap (t : ℝ) T s) (brownian s ω)
    rw [timeCap_of_le htReal (NNReal.coe_le_coe.mpr hs.2)]
  have hRep := bs_delta_hedge_replication (r := r) isBrownianReal_brownian.toIsPreBrownianReal
    measurable_brownian continuous_brownian hK hσ hS₀ t htReal
  have hL2 := predItoIntegral_eq_l2 isBrownianReal_brownian.toIsPreBrownianReal
    measurable_brownian continuous_brownian ht.le hPredictable hPaths
    (call_hedge_integrand_memLp K r σ S₀ T)
  filter_upwards [hRep, hL2] with ω hRepPath hGain
  exact (hRepPath t ⟨zero_le, le_rfl⟩).trans (congrArg (bsV K r σ S₀ T + ·) hGain)

/-- 満期に受け取るコールのペイオフを時刻 0 の単位で割り引く。 -/
noncomputable def discountedCallPayoff (K r σ S₀ : ℝ) (T : ℝ≥0) (ω : BrownianPath) : ℝ :=
  Real.exp (-(r * (T : ℝ))) * max (gbmValue S₀ r σ T (brownian T ω) - K) 0

/-- 満期ペイオフを複製する。満期前の等式を可算個の時刻で使い、確率積分の連続な版と
コール価格の満期極限を、同じ経路で比較する。 -/
theorem call_discounted_payoff_replication {K r σ S₀ : ℝ} {T : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (hT : 0 < T) :
    discountedCallPayoff K r σ S₀ T =ᵐ[gaussianLimit]
      fun ω ↦ bsV K r σ S₀ T + callHedgeGain K r σ S₀ T T ω := by
  obtain ⟨times, _, hTimes, hTends⟩ :=
    (dense_univ : Dense (univ : Set ℝ≥0)).exists_seq_strictMono_tendsto_of_lt hT
  let gain := itoContinuousMod T measurable_brownian (callHedgeIntegrand K r σ S₀ T)
  have hMod {t : ℝ≥0} (ht : t ≤ T) :
      gain t =ᵐ[gaussianLimit] (callHedgeGain K r σ S₀ T t : BrownianPath → ℝ) :=
    itoContinuousMod_modification isBrownianReal_brownian.toIsPreBrownianReal
      T measurable_brownian continuous_brownian (callHedgeIntegrand K r σ S₀ T) ht
  have hBefore : ∀ᵐ ω ∂gaussianLimit, ∀ n : ℕ,
      discountedCallBrownian K r σ S₀ T (times n) (brownian (times n) ω) =
        bsV K r σ S₀ T + gain (times n) ω := by
    refine ae_all_iff.2 fun n ↦ ?_
    have ht := (hTimes n).1.2
    filter_upwards [discounted_call_hedge_before_maturity hK hσ hS₀ ht, hMod ht.le]
      with ω hEq hGain
    exact hEq.trans (congrArg (bsV K r σ S₀ T + ·) hGain.symm)
  have hContinuity : ∀ᵐ ω ∂gaussianLimit, ContinuousOn (fun t ↦ gain t ω) (Icc 0 T) :=
    itoContinuousMod_continuousOn isBrownianReal_brownian.toIsPreBrownianReal
      T measurable_brownian continuous_brownian (callHedgeIntegrand K r σ S₀ T)
  filter_upwards [hBefore, hContinuity, hMod le_rfl] with ω hEq hCont hTerminal
  have hLeft : Tendsto times atTop (𝓝[<] T) :=
    tendsto_nhdsWithin_iff.2 ⟨hTends, Eventually.of_forall fun n ↦ (hTimes n).1.2⟩
  have hClosed : Tendsto times atTop (𝓝[Icc 0 T] T) :=
    tendsto_nhdsWithin_iff.2 ⟨hTends, Eventually.of_forall fun n ↦
      ⟨zero_le, (hTimes n).1.2.le⟩⟩
  have hDiscount : Continuous (fun s : ℝ≥0 ↦ Real.exp (-(r * (s : ℝ)))) := by fun_prop
  have hPriceLimit : Tendsto (fun s : ℝ≥0 ↦
      discountedCallBrownian K r σ S₀ T s (brownian s ω)) (𝓝[<] T)
      (𝓝 (discountedCallPayoff K r σ S₀ T ω)) :=
    ((hDiscount.tendsto T).mono_left nhdsWithin_le_nhds).mul
      (tendsto_bsV_gbm_payoff (r := r) T hK hσ hS₀ (continuous_brownian ω).continuousAt)
  have hGainLimit := ((hCont T ⟨zero_le, le_rfl⟩).tendsto.comp hClosed).const_add
    (bsV K r σ S₀ T)
  exact (tendsto_nhds_unique (hPriceLimit.comp hLeft) (hGainLimit.congr fun n ↦ (hEq n).symm)
    ).trans (congrArg (bsV K r σ S₀ T + ·) hTerminal)

/-- 満期までの株取引の割引損益を与える伊藤積分。被積分関数は、保有株数と
割引株価の拡散係数の積である。 -/
noncomputable def stockGainAtMaturity (T : ℝ≥0) :
    Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian) →L[ℝ] Lp ℝ 2 gaussianLimit :=
  itoIntegralCLM isBrownianReal_brownian.toIsPreBrownianReal T measurable_brownian

/-- 複製ポートフォリオの初期費用は、満期ペイオフの割引期待値に等しい。 -/
theorem call_replication_cost_eq_discounted_expectation {K r σ S₀ : ℝ} {T : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (hT : 0 < T) :
    bsV K r σ S₀ T = ∫ ω, discountedCallPayoff K r σ S₀ T ω ∂gaussianLimit := by
  have hRep := call_discounted_payoff_replication (r := r) hK hσ hS₀ hT
  rw [callHedgeGain, itoProcessCLM_terminal_eq isBrownianReal_brownian.toIsPreBrownianReal] at hRep
  let gain := stockGainAtMaturity T (callHedgeIntegrand K r σ S₀ T)
  have hMeanZero : (∫ ω, gain ω ∂gaussianLimit) = 0 :=
    integral_itoIntegralCLM isBrownianReal_brownian.toIsPreBrownianReal T measurable_brownian
      (callHedgeIntegrand K r σ S₀ T)
  calc
    _ = (∫ ω, bsV K r σ S₀ T + gain ω ∂gaussianLimit) := by
      rw [integral_add (integrable_const _) ((Lp.memLp gain).integrable (by norm_num)), hMeanZero]
      simp
    _ = _ := (integral_congr_ae hRep).symm

/-- 満期前の割引複製価値は、その時刻までのブラウン運動で条件づけた割引ペイオフの期待値。 -/
theorem discounted_call_eq_condExp_of_payoff {K r σ S₀ : ℝ} {T t : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (ht : t < T) :
    (fun ω ↦ discountedCallBrownian K r σ S₀ T t (brownian t ω)) =ᵐ[gaussianLimit]
      gaussianLimit[discountedCallPayoff K r σ S₀ T | natFiltration measurable_brownian t] := by
  have hT : 0 < T := lt_of_le_of_lt zero_le ht
  let initial := bsV K r σ S₀ T
  let gain := callHedgeGain K r σ S₀ T
  let info := natFiltration measurable_brownian t
  have hCond := condExp_add (μ := gaussianLimit) (f := fun _ : BrownianPath ↦ initial)
    (integrable_const _) ((Lp.memLp (gain T)).integrable (by norm_num)) info
  rw [condExp_const ((natFiltration measurable_brownian).le t)] at hCond
  have hMart := itoIntegralProcessGen_isMartingale isBrownianReal_brownian.toIsPreBrownianReal
    T measurable_brownian (callHedgeIntegrand K r σ S₀ T) ht.le
  have hExpected : gaussianLimit[discountedCallPayoff K r σ S₀ T | info] =ᵐ[gaussianLimit]
      fun ω ↦ initial + gain t ω := by
    refine (condExp_congr_ae (call_discounted_payoff_replication (r := r) hK hσ hS₀ hT)).trans
      (hCond.trans ?_)
    filter_upwards [hMart] with ω hω
    exact congrArg (initial + ·) hω
  exact (discounted_call_hedge_before_maturity hK hσ hS₀ ht).trans hExpected.symm

/-- 価格 `quote` でコールを `position` 枚買い、満期まで保有する。
代金は無リスク口座から調達し、株取引の割引損益を加えると、自己資金ゼロでの
満期の割引損益になる。負の `position` はコールの売りを表す。 -/
noncomputable def callTradeTerminalGain (K r σ S₀ : ℝ) (T : ℝ≥0) (quote position : ℝ)
    (stock : Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian))
    (ω : BrownianPath) : ℝ :=
  stockGainAtMaturity T stock ω + position * (discountedCallPayoff K r σ S₀ T ω - quote)

/-- L² の株取引とコールの売買を許す。自己資金ゼロから満期損益がほとんど確実に
非負なら、その損益はほとんど確実にゼロである価格を無裁定と呼ぶ。 -/
def NoArbitrageAtCallQuote (K r σ S₀ : ℝ) (T : ℝ≥0) (quote : ℝ) : Prop :=
  ∀ (position : ℝ) (stock : Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian)),
    (∀ᵐ ω ∂gaussianLimit, 0 ≤ callTradeTerminalGain K r σ S₀ T quote position stock ω) →
    callTradeTerminalGain K r σ S₀ T quote position stock =ᵐ[gaussianLimit] 0

private theorem call_trade_gain_eq_stock_gain_add_price_difference {K r σ S₀ : ℝ} {T : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (hT : 0 < T) (quote position : ℝ)
    (stock : Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian)) :
    callTradeTerminalGain K r σ S₀ T quote position stock =ᵐ[gaussianLimit]
      fun ω ↦ stockGainAtMaturity T (stock + position • callHedgeIntegrand K r σ S₀ T) ω
        + position * (bsV K r σ S₀ T - quote) := by
  have hRep := call_discounted_payoff_replication (r := r) hK hσ hS₀ hT
  rw [callHedgeGain, itoProcessCLM_terminal_eq isBrownianReal_brownian.toIsPreBrownianReal] at hRep
  let hedgeGain := stockGainAtMaturity T (callHedgeIntegrand K r σ S₀ T)
  filter_upwards [hRep, Lp.coeFn_add (stockGainAtMaturity T stock) (position • hedgeGain),
    Lp.coeFn_smul position hedgeGain] with ω hPayoff hAdd hScale
  change discountedCallPayoff K r σ S₀ T ω = bsV K r σ S₀ T + hedgeGain ω at hPayoff
  unfold callTradeTerminalGain
  rw [map_add, map_smul, hAdd, Pi.add_apply, hScale, Pi.smul_apply, smul_eq_mul, hPayoff]
  ring

/-- コールが複製費用より安ければ買い、高ければ売る。逆向きのヘッジを組むと、
満期ペイオフが相殺され、正の割引損益が確実に残る。 -/
theorem call_quote_mispricing_gives_arbitrage {K r σ S₀ quote : ℝ} {T : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (hT : 0 < T)
    (hQuote : quote ≠ bsV K r σ S₀ T) :
    ∃ (position : ℝ) (stock : Lp ℝ 2 (trimMeasure (μ := gaussianLimit) T measurable_brownian)),
      ∀ᵐ ω ∂gaussianLimit, 0 < callTradeTerminalGain K r σ S₀ T quote position stock ω := by
  let position := bsV K r σ S₀ T - quote
  let stock := -(position • callHedgeIntegrand K r σ S₀ T)
  have hGain := call_trade_gain_eq_stock_gain_add_price_difference (r := r) hK hσ hS₀ hT quote position stock
  have hCancel : stock + position • callHedgeIntegrand K r σ S₀ T = 0 := neg_add_cancel _
  rw [hCancel, map_zero] at hGain
  refine ⟨position, stock, ?_⟩
  filter_upwards [hGain, Lp.coeFn_zero ℝ 2 gaussianLimit] with ω hω hZero
  rw [hω, hZero, Pi.zero_apply, zero_add]
  exact mul_self_pos.mpr (sub_ne_zero.mpr hQuote.symm)

/-- L² の株取引と満期まで保有するコールが取引可能な市場で、
無裁定となるコール価格は割引期待値に等しい価格だけである。 -/
theorem arbitrageFree_call_quote_iff {K r σ S₀ quote : ℝ} {T : ℝ≥0}
    (hK : 0 < K) (hσ : 0 < σ) (hS₀ : 0 < S₀) (hT : 0 < T) :
    NoArbitrageAtCallQuote K r σ S₀ T quote ↔
      quote = ∫ ω, discountedCallPayoff K r σ S₀ T ω ∂gaussianLimit := by
  rw [← call_replication_cost_eq_discounted_expectation hK hσ hS₀ hT]
  constructor
  · intro hFree
    by_contra hWrong
    obtain ⟨position, stock, hPositive⟩ := call_quote_mispricing_gives_arbitrage hK hσ hS₀ hT hWrong
    have hZero := hFree position stock (hPositive.mono fun _ h ↦ h.le)
    obtain ⟨ω, hPos, hω⟩ := (hPositive.and hZero).exists
    exact hPos.ne' hω
  · rintro rfl position stock hNonneg
    let combined := stock + position • callHedgeIntegrand K r σ S₀ T
    let gain := stockGainAtMaturity T combined
    have hEq : callTradeTerminalGain K r σ S₀ T (bsV K r σ S₀ T) position stock
        =ᵐ[gaussianLimit] (gain : BrownianPath → ℝ) := by
      simpa only [sub_self, mul_zero, add_zero] using
        call_trade_gain_eq_stock_gain_add_price_difference (r := r) hK hσ hS₀ hT (bsV K r σ S₀ T) position stock
    refine hEq.trans ((integral_eq_zero_iff_of_nonneg_ae ?_
      ((Lp.memLp gain).integrable (by norm_num))).mp
      (integral_itoIntegralCLM isBrownianReal_brownian.toIsPreBrownianReal T measurable_brownian combined))
    filter_upwards [hNonneg, hEq] with ω hNonnegω hEqω
    rwa [← hEqω]

end LeanPractice.BlackScholes
