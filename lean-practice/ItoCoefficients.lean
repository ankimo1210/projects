import MathFin.Probability.Brownian.AdaptedQuadraticVariation

/-!
# 伊藤過程の分解の一意性

自己資金調達と伊藤の公式から二通りの分解が得られたとき、係数の一致を示すには
確率積分と時間積分の和がゼロなら、それぞれがゼロになることを使う。
以下では、拡散係数が有界かつ経路ごとに連続で、累積ドリフトが時間に関して
一様にリプシッツ連続な場合を証明する。
-/

open MeasureTheory ProbabilityTheory Filter Set
open MathFin MathFin.ItoIntegralL2 MathFin.ItoIntegralCLM MathFin.ItoIntegralProcessGeneral
open scoped NNReal Topology

namespace LeanPractice.Ito

set_option autoImplicit false

/-- ゼロ過程を累積ドリフト `A` と伊藤積分に分けると、拡散係数 `σ` は
時間と確率についてほとんど至る所でゼロになる。累積ドリフトも各時点で
ほとんど確実にゼロになる。 -/
theorem bounded_zero_decomposition {Ω : Type*} [MeasurableSpace Ω]
    {μ : Measure Ω} [IsProbabilityMeasure μ] {B : ℝ≥0 → Ω → ℝ}
    (hB : IsPreBrownianReal B μ) (hMeas : ∀ t, Measurable (B t)) (T : ℝ≥0)
    {A σ : ℝ≥0 → Ω → ℝ} {CDrift CVol : ℝ}
    (hAdapted : ∀ t, StronglyMeasurable[(natFiltration hMeas t : MeasurableSpace Ω)] (σ t))
    (hContinuous : ∀ ω, Continuous (fun t ↦ σ t ω))
    (hBound : ∀ t ω, |σ t ω| ≤ CVol)
    (hLipschitz : ∀ ⦃s t : ℝ≥0⦄, s ≤ t → ∀ ω,
      |A t ω - A s ω| ≤ CDrift * ((t : ℝ) - s))
    (hZero : ∀ t ≤ T, (fun ω ↦ A t ω +
      itoProcessCLM hB T t hMeas (processToLp T hMeas hAdapted hContinuous hBound) ω) =ᵐ[μ] 0) :
    (∀ᵐ ω ∂μ, ∀ᵐ s ∂timeMeasureHorizon T, σ s ω = 0)
      ∧ (∀ t ≤ T, A t =ᵐ[μ] 0) := by
  have hPredictable := isStronglyPredictable_of_bdd_adapted_cont hMeas hAdapted hContinuous
  have hProductMeasurable : Measurable (Function.uncurry σ) :=
    (hPredictable.mono (natFiltration hMeas).predictable_le_prod).measurable
  have hSquareIntegrable :
      Integrable (fun z : ℝ≥0 × Ω ↦ σ z.1 z.2 ^ 2) ((timeMeasureHorizon T).prod μ) :=
    (integrable_const (CVol ^ 2)).mono' (hProductMeasurable.pow_const (2 : ℕ)).aestronglyMeasurable
      (ae_of_all _ fun z ↦ by
        rw [Real.norm_eq_abs, abs_pow]
        exact pow_le_pow_left₀ (abs_nonneg _) (hBound z.1 z.2) _)

  -- ゼロ過程の二次変動はゼロ。極限の一意性から、σ² の積分の期待値もゼロ。
  have hQV := MathFin.AdaptedQuadraticVariation.tendsto_qv_adapted hB T hMeas
    hAdapted hContinuous hBound (X := fun _ _ ↦ 0) (X₀ := fun _ ↦ 0) hLipschitz
    (fun t ht ↦ by
      filter_upwards [hZero t ht] with ω hω
      simpa only [zero_add, Pi.zero_apply] using hω.symm)
  have hAbs (ω : Ω) :
      |∫ s in Ioc 0 T, σ s ω ^ 2 ∂timeMeasure| = ∫ s in Ioc 0 T, σ s ω ^ 2 ∂timeMeasure :=
    abs_of_nonneg (integral_nonneg (fun s ↦ sq_nonneg (σ s ω)))
  have hLimit : Tendsto (fun _ : ℕ ↦ ∫ ω, ∫ s, σ s ω ^ 2 ∂timeMeasureHorizon T ∂μ)
      atTop (𝓝 0) := by
    simpa [timeMeasureHorizon, hAbs] using hQV
  have hEnergyZero : ∫ ω, ∫ s, σ s ω ^ 2 ∂timeMeasureHorizon T ∂μ = 0 :=
    tendsto_nhds_unique tendsto_const_nhds hLimit
  have hPathEnergyZero := (integral_eq_zero_iff_of_nonneg
    (fun ω ↦ integral_nonneg (fun s ↦ sq_nonneg (σ s ω)))
    hSquareIntegrable.integral_prod_right).mp hEnergyZero

  -- 非負の関数の積分がゼロなので、σ の値もほとんど至る所でゼロ。
  have hDiffusionZero : ∀ᵐ ω ∂μ, ∀ᵐ s ∂timeMeasureHorizon T, σ s ω = 0 := by
    filter_upwards [hPathEnergyZero, hSquareIntegrable.prod_left_ae] with ω hEnergy hIntegrable
    have hSquareZero := (integral_eq_zero_iff_of_nonneg
      (fun s ↦ sq_nonneg (σ s ω)) hIntegrable).mp hEnergy
    filter_upwards [hSquareZero] with s hs
    simpa using hs

  -- 拡散係数の L² 同値類がゼロなら伊藤積分もゼロなので、残る A が消える。
  have hSwapped : (fun z : Ω × ℝ≥0 ↦ σ z.2 z.1) =ᵐ[μ.prod (timeMeasureHorizon T)] 0 :=
    (Measure.ae_prod_iff_ae_ae
      (measurableSet_eq_fun (hProductMeasurable.comp measurable_swap) measurable_const)).mpr
      hDiffusionZero
  have hProductZero : Function.uncurry σ =ᵐ[(timeMeasureHorizon T).prod μ] 0 :=
    Measure.measurePreserving_swap.quasiMeasurePreserving.ae hSwapped
  have hTrimZero : Function.uncurry σ =ᵐ[trimMeasure (μ := μ) T hMeas] 0 :=
    (StronglyMeasurable.ae_eq_trim_iff (natFiltration hMeas).predictable_le_prod
      hPredictable stronglyMeasurable_const).mpr hProductZero
  have hLpZero : processToLp (μ := μ) T hMeas hAdapted hContinuous hBound = 0 :=
    Lp.ext ((processToLp_coeFn T hMeas hAdapted hContinuous hBound).trans
      (hTrimZero.trans (Lp.coeFn_zero ℝ 2 _).symm))
  refine ⟨hDiffusionZero, fun t ht ↦ ?_⟩
  have hIntegralZero :
      (itoProcessCLM hB T t hMeas (processToLp T hMeas hAdapted hContinuous hBound) : Ω → ℝ)
        =ᵐ[μ] 0 := by
    rw [hLpZero, map_zero]
    exact Lp.coeFn_zero ℝ 2 _
  filter_upwards [hZero t ht, hIntegralZero] with ω hω hIntegral
  simpa only [hIntegral, Pi.zero_apply, add_zero] using hω

end LeanPractice.Ito
