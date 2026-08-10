"""Builder for notebook 22: research software and numerical contracts."""

from nbkit import code, md

cells = [
    md(r"""
# 22. Week 16 — 研究ソフトウェアと数値契約

> 速いNotebookではなく、入力、勾配、許容誤差、再生成手順を第三者が監査できる小さな研究componentを作る。

## 学習目標

- 数値関数のinput、output、invariant、failure、toleranceを契約として書く
- Big-O、vectorization、array layout、sparse matrix、hash lookupを実測と結び付ける
- analytic gradient、forward-mode automatic differentiation、finite differenceを区別して照合する
- deterministicなproperty-style testと個別edge-case testを作る
- correctness test、performance benchmark、profilingを別の証拠として保存する
- configuration、seed、environment、input fingerprintを持つartifactをclean processで再生成する

## 前提知識

- B1のfloating-point error、conditioning、pure function
- Week 13–15のconvex QP、KKT residual、gradient-based algorithm
- Python function、NumPy array、SciPy sparse matrix、計算量の基本

本章は新しいdependencyを追加しない。automatic differentiationは教育用に演算を限定したdual numberを実装する。finite differenceやcomplex-stepをADと呼ばない。
"""),
    code("""
import cProfile
import hashlib
import importlib.metadata as importlib_metadata
import io
import json
import platform
import pstats
import subprocess
import sys
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from scipy import sparse

from quant_textbook.convex import QuadraticProgram, solve_quadratic_program
from quant_textbook.curves import weighted_rmse
from quant_textbook.optimization import finite_difference_gradient_audit

pio.renderers.default = "notebook_connected"
RANDOM_SEED = 20260810
NOTEBOOK_ID = 22
TASK_IDS = {
    "complexity": 1,
    "sparse": 2,
    "gradient": 3,
    "properties": 4,
    "artifact": 5,
}


def task_rng(task_name, *coordinates):
    entropy = [
        RANDOM_SEED,
        NOTEBOOK_ID,
        TASK_IDS[task_name],
        *(int(coordinate) for coordinate in coordinates),
    ]
    return np.random.default_rng(np.random.SeedSequence(entropy))
"""),
    md(r"""
## 1. Notebookからcomponentへ境界を引く

探索用cellの状態をAPIへ持ち込まない。最小componentは次の契約を持つ。

| Contract | 必須記述 | 失敗時の動作 |
|---|---|---|
| input | shape、dtype、有限性、単位、順序 | `ValueError`等で早く止める |
| output | shape、単位、immutabilityの要否 | 不完全な値をsuccessとして返さない |
| invariant | symmetry、PSD、feasibility、再現性 | raw residualと判定を分離する |
| tolerance | absolute / relative scale、float precision | 根拠とともにconfigurationへ保存する |
| resource | expected complexity、memory、iteration budget | correctness failureとtimeoutを区別する |

experiment configurationはlibrary codeのglobal variableに埋め込まず、呼び出し側から渡す。plotやmemoはpure numerical functionの責務にしない。
"""),
    md(r"""
## 2. Big-Oは入力scaleと演算を指定する

| Operation | Expected time | Extra memory | 注意点 |
|---|---:|---:|---|
| dense matrix-vector, $A\in\mathbb{R}^{m\times n}$ | $O(mn)$ | $O(m+n)$ | layoutとBLASで定数が変わる |
| sparse matrix-vector with `nnz` entries | $O(\mathrm{nnz})$ | $O(\mathrm{nnz}+m+n)$ | dense conversionは利点を失う |
| dense linear solve | $O(n^3)$ | $O(n^2)$ | structureを使えば異なる |
| hash lookup | expected $O(1)$ | $O(n)$ table | worst caseやhash costを隠さない |
| list membership | $O(n)$ | $O(1)$ | small $n$では定数が支配する |

Big-Oはwall-clock timeの予言ではない。hardware、thread数、cache、array layout、problem sparsityを記録して初めてbenchmarkを解釈できる。
"""),
    code("""
def benchmark(function, *, repeats=7, warmups=2):
    for _ in range(warmups):
        function()
    durations = np.empty(repeats, dtype=float)
    for repeat in range(repeats):
        started = time.perf_counter()
        function()
        durations[repeat] = time.perf_counter() - started
    return {
        "median_ms": 1.0e3 * float(np.median(durations)),
        "iqr_ms": 1.0e3
        * float(np.quantile(durations, 0.75) - np.quantile(durations, 0.25)),
        "minimum_ms": 1.0e3 * float(durations.min()),
        "repeats": repeats,
    }


def weighted_sum_loop(values, weights):
    total = 0.0
    for value, weight in zip(values, weights, strict=True):
        total += value * weight
    return total


def weighted_sum_vectorized(values, weights):
    return float(values @ weights)


complexity_rng = task_rng("complexity")
vector_size = 150_000
benchmark_values = complexity_rng.normal(size=vector_size)
benchmark_weights = complexity_rng.normal(size=vector_size)

loop_value = weighted_sum_loop(benchmark_values, benchmark_weights)
vectorized_value = weighted_sum_vectorized(benchmark_values, benchmark_weights)
agreement_scale = 1.0 + abs(loop_value) + abs(vectorized_value)
relative_agreement = abs(loop_value - vectorized_value) / agreement_scale
assert relative_agreement < 1.0e-12

vectorization_benchmark = pd.DataFrame(
    [
        {"implementation": "Python loop", **benchmark(lambda: weighted_sum_loop(benchmark_values, benchmark_weights), repeats=5)},
        {"implementation": "NumPy vectorized", **benchmark(lambda: weighted_sum_vectorized(benchmark_values, benchmark_weights), repeats=7)},
    ]
)
display(vectorization_benchmark.round(4))
print("relative result disagreement:", relative_agreement)
"""),
    md(r"""
値の一致を先にtestし、その後にtimeを測った。timingへpass/fail assertionを置かない。共有runnerでは負荷やthread設定が変わるため、performance regressionには専用environmentと履歴baselineが必要である。
"""),
    md(r"""
## 3. sparse、layout、hashは万能な高速化ではない

sparse matrixはzeroを保存しない利点を持つが、index情報と間接参照のcostも持つ。densityを明示し、同じmatrix-vector productをdense表現と照合する。
"""),
    code("""
sparse_rng = task_rng("sparse")
matrix_size = 1_000
matrix_density = 0.004
sparse_matrix = sparse.random(
    matrix_size,
    matrix_size,
    density=matrix_density,
    format="csr",
    random_state=sparse_rng,
    data_rvs=lambda size: sparse_rng.normal(size=size),
)
dense_matrix = sparse_matrix.toarray()
matrix_vector = sparse_rng.normal(size=matrix_size)

sparse_product = sparse_matrix @ matrix_vector
dense_product = dense_matrix @ matrix_vector
np.testing.assert_allclose(sparse_product, dense_product, rtol=1.0e-11, atol=1.0e-11)

dense_bytes = dense_matrix.nbytes
sparse_bytes = (
    sparse_matrix.data.nbytes
    + sparse_matrix.indices.nbytes
    + sparse_matrix.indptr.nbytes
)
sparse_benchmark = pd.DataFrame(
    [
        {
            "representation": "dense",
            "stored_megabytes": dense_bytes / 1.0e6,
            **benchmark(lambda: dense_matrix @ matrix_vector),
        },
        {
            "representation": "CSR sparse",
            "stored_megabytes": sparse_bytes / 1.0e6,
            **benchmark(lambda: sparse_matrix @ matrix_vector),
        },
    ]
)
display(sparse_benchmark.round(4))
print("realized density:", sparse_matrix.nnz / dense_matrix.size)
"""),
    code("""
layout_rng = task_rng("complexity", 2)
layout_base = layout_rng.normal(size=(700, 240))
c_layout = np.array(layout_base, order="C")
f_layout = np.array(layout_base, order="F")
layout_weights = layout_rng.normal(size=700)

c_result = layout_weights @ c_layout
f_result = layout_weights @ f_layout
np.testing.assert_allclose(c_result, f_result, rtol=1.0e-13, atol=1.0e-13)

layout_table = pd.DataFrame(
    [
        {
            "layout": "C contiguous",
            "C_contiguous": c_layout.flags.c_contiguous,
            "F_contiguous": c_layout.flags.f_contiguous,
            **benchmark(lambda: layout_weights @ c_layout),
        },
        {
            "layout": "F contiguous",
            "C_contiguous": f_layout.flags.c_contiguous,
            "F_contiguous": f_layout.flags.f_contiguous,
            **benchmark(lambda: layout_weights @ f_layout),
        },
    ]
)
display(layout_table.round(4))
"""),
    code("""
lookup_keys = [f"bond-{index:05d}" for index in range(20_000)]
lookup_table = {key: index for index, key in enumerate(lookup_keys)}
lookup_queries = lookup_keys[::97]


def list_lookup_checksum():
    return sum(lookup_keys.index(key) for key in lookup_queries)


def hash_lookup_checksum():
    return sum(lookup_table[key] for key in lookup_queries)


assert list_lookup_checksum() == hash_lookup_checksum()
lookup_benchmark = pd.DataFrame(
    [
        {"container": "list scan", **benchmark(list_lookup_checksum, repeats=5)},
        {"container": "dict hash", **benchmark(hash_lookup_checksum, repeats=7)},
    ]
)
display(lookup_benchmark.round(4))
"""),
    md(r"""
この実測は現在のsize、density、hardwareに条件付けられる。`sparse is faster`、`F order is faster`のような無条件の結論は出さない。hash tableのlookupはexpected $O(1)$であり、順序付きrange queryやworst-case保証とは別である。
"""),
    md(r"""
## 4. restricted forward-mode AD

dual number $(v,\dot v)$ は値と接線を持つ。加法と積について

$$
(a,\dot a)+(b,\dot b)=(a+b,\dot a+\dot b),
$$

$$
(a,\dot a)(b,\dot b)=(ab,a\dot b+b\dot a)
$$

と演算を伝播すれば、input tangentを単位basisにした一回の評価でscalar outputのgradientを得られる。これはchain ruleをprogram executionへ適用するforward-mode ADである。

以下は加減乗除だけを扱う教材実装である。NumPy ufunc、branch、sparse operationを一般に微分するproduction AD engineではない。
"""),
    code("""
@dataclass(frozen=True)
class Dual:
    value: float
    tangent: np.ndarray

    def _coerce(self, other):
        if isinstance(other, Dual):
            if other.tangent.shape != self.tangent.shape:
                raise ValueError("dual tangents must have matching shapes")
            return other
        return Dual(float(other), np.zeros_like(self.tangent))

    def __add__(self, other):
        other = self._coerce(other)
        return Dual(self.value + other.value, self.tangent + other.tangent)

    __radd__ = __add__

    def __neg__(self):
        return Dual(-self.value, -self.tangent)

    def __sub__(self, other):
        return self + (-self._coerce(other))

    def __rsub__(self, other):
        return self._coerce(other) + (-self)

    def __mul__(self, other):
        other = self._coerce(other)
        return Dual(
            self.value * other.value,
            self.tangent * other.value + self.value * other.tangent,
        )

    __rmul__ = __mul__

    def __truediv__(self, other):
        other = self._coerce(other)
        if other.value == 0.0:
            raise ZeroDivisionError("dual division by zero")
        return Dual(
            self.value / other.value,
            (self.tangent * other.value - self.value * other.tangent)
            / other.value**2,
        )

    def __rtruediv__(self, other):
        return self._coerce(other) / self


def quadratic_expression(inputs, hessian, linear_term):
    total = inputs[0] * 0.0
    for row in range(len(inputs)):
        hessian_product = inputs[0] * 0.0
        for column in range(len(inputs)):
            hessian_product += hessian[row, column] * inputs[column]
        total += 0.5 * inputs[row] * hessian_product
        total += linear_term[row] * inputs[row]
    return total


def forward_ad_quadratic(point, hessian, linear_term):
    point = np.asarray(point, dtype=float)
    identity = np.eye(point.size)
    dual_inputs = [
        Dual(float(point[index]), identity[index]) for index in range(point.size)
    ]
    result = quadratic_expression(dual_inputs, hessian, linear_term)
    return result.value, result.tangent


def central_difference_gradient(function, point, relative_step):
    point = np.asarray(point, dtype=float)
    steps = relative_step * np.maximum(1.0, np.abs(point))
    gradient = np.empty_like(point)
    for index, step in enumerate(steps):
        direction = np.zeros_like(point)
        direction[index] = step
        gradient[index] = (
            function(point + direction) - function(point - direction)
        ) / (2.0 * step)
    return gradient
"""),
    code("""
gradient_rng = task_rng("gradient")
gradient_dimension = 5
gradient_factor = gradient_rng.normal(size=(gradient_dimension, gradient_dimension))
gradient_hessian = gradient_factor.T @ gradient_factor + 0.4 * np.eye(gradient_dimension)
gradient_linear = gradient_rng.normal(size=gradient_dimension)
gradient_point = gradient_rng.normal(size=gradient_dimension)


def gradient_objective(point):
    return float(
        0.5 * point @ gradient_hessian @ point + gradient_linear @ point
    )


analytic_gradient = gradient_hessian @ gradient_point + gradient_linear
ad_value, ad_gradient = forward_ad_quadratic(
    gradient_point,
    gradient_hessian,
    gradient_linear,
)
fd_relative_step = np.finfo(float).eps ** (1.0 / 3.0)
finite_difference_gradient = central_difference_gradient(
    gradient_objective,
    gradient_point,
    fd_relative_step,
)

gradient_audit = pd.DataFrame(
    {
        "coordinate": np.arange(gradient_dimension),
        "analytic": analytic_gradient,
        "forward_mode_AD": ad_gradient,
        "central_finite_difference": finite_difference_gradient,
        "AD_absolute_error": np.abs(ad_gradient - analytic_gradient),
        "FD_absolute_error": np.abs(finite_difference_gradient - analytic_gradient),
    }
)
display(gradient_audit)
print("objective agreement:", abs(ad_value - gradient_objective(gradient_point)))
assert np.max(np.abs(ad_gradient - analytic_gradient)) < 1.0e-12
assert np.max(np.abs(finite_difference_gradient - analytic_gradient)) < 1.0e-6
"""),
    md(r"""
ADにもfloating-point arithmeticの丸めはあるが、差分stepのtruncation / cancellation trade-offはない。finite differenceは独立な監査手段として有用であり、ADの別名ではない。
"""),
    code("""
step_grid = np.logspace(-12, -2, 31)
finite_difference_errors = []
for relative_step in step_grid:
    estimate = central_difference_gradient(
        gradient_objective,
        gradient_point,
        relative_step,
    )
    finite_difference_errors.append(
        np.linalg.norm(estimate - analytic_gradient, ord=np.inf)
    )

fig = go.Figure()
fig.add_scatter(
    x=step_grid,
    y=finite_difference_errors,
    mode="lines+markers",
    name="Central finite difference",
)
fig.add_hline(
    y=max(np.linalg.norm(ad_gradient - analytic_gradient, ord=np.inf), np.finfo(float).eps),
    line_dash="dash",
    annotation_text="Forward AD error floor",
)
fig.update_xaxes(type="log")
fig.update_yaxes(type="log")
fig.update_layout(
    title="Finite-difference error depends on the step size",
    xaxis_title="Relative step",
    yaxis_title="Infinity-norm gradient error",
    template="plotly_white",
)
fig.show()
"""),
    md(r"""
### Reusable package slice: gradient audit

Notebook内のdual numberはforward-mode ADの仕組みを見せる教材実装である。一方、再利用するcomponentは`finite_difference_gradient_audit`で、入力検証、複数stepのcentral difference、step instability、cancellationを一つのpure resultへ返す。analytic / AD一致と、analytic / package finite-difference一致を別々に検査し、finite differenceをADとは呼ばない。
"""),
    code("""
package_gradient_audit = finite_difference_gradient_audit(
    gradient_objective,
    lambda point: gradient_hessian @ point + gradient_linear,
    gradient_point,
    relative_step=fd_relative_step,
    absolute_tolerance=1.0e-7,
    relative_tolerance=1.0e-5,
)
package_step_errors = np.max(
    np.abs(
        package_gradient_audit.finite_difference_gradients
        - package_gradient_audit.analytic_gradient[None, :]
    ),
    axis=1,
)
package_gradient_table = pd.DataFrame(
    {
        "relative_step": package_gradient_audit.relative_steps,
        "maximum_absolute_error": package_step_errors,
    }
)
display(package_gradient_table)
print("package verdict:", package_gradient_audit.passed)
print("step instability:", package_gradient_audit.step_instability)
print("cancellation detected:", package_gradient_audit.cancellation_detected)
print("diagnostic:", package_gradient_audit.diagnostic)
assert package_gradient_audit.passed
assert not package_gradient_audit.cancellation_detected
np.testing.assert_allclose(
    package_gradient_audit.analytic_gradient,
    ad_gradient,
    rtol=1.0e-12,
    atol=1.0e-12,
)
"""),
    md(r"""
### B1 curve fitterの共通pure API

B1 curve fitterで繰り返すprice / yield residual集計をNotebook内で再実装せず、既存の`quant_textbook.curves.weighted_rmse`へ接続する。known-answer caseとinvalid weight contractをここで実行し、plotやglobal stateを持たないpure functionとして検査する。
"""),
    code("""
curve_metric_actual = np.array([100.0, 101.0, 99.0])
curve_metric_predicted = np.array([99.0, 100.0, 101.0])
curve_metric_weights = np.array([1.0, 2.0, 1.0])
curve_metric_expected = np.sqrt(7.0 / 4.0)
curve_metric_observed = weighted_rmse(
    curve_metric_actual,
    curve_metric_predicted,
    curve_metric_weights,
)
np.testing.assert_allclose(
    curve_metric_observed,
    curve_metric_expected,
    rtol=0.0,
    atol=1.0e-15,
)
print("B1 pure weighted-RMSE known answer:", curve_metric_observed)
"""),
    md(r"""
## 5. toleranceを数値契約にする

値の比較は

$$
|x-\tilde x|\le \mathrm{atol}+\mathrm{rtol}|\tilde x|
$$

のようにabsoluteとrelative termを分ける。`atol`はzero付近の単位scale、`rtol`は代表値に対する相対誤差を表す。solver residualではさらにconstraint row、objective、multiplierのscaleを無次元化する。

float64のmachine epsilonは丸めのscaleであり、すべてのalgorithmの許容誤差そのものではない。conditioning、反復停止、data precisionが誤差を増幅する。well-scaledな小問題に$100\sqrt{\epsilon_{\rm mach}}$を使う場合も、普遍定数ではなく教材gateの選択として記録する。
"""),
    code("""
FLOAT64_EPSILON = np.finfo(float).eps
TEACHING_RELATIVE_TOLERANCE = 100.0 * np.sqrt(FLOAT64_EPSILON)

numerical_contract = pd.DataFrame(
    [
        {
            "item": "quadratic input",
            "invariant": "finite vector, symmetric PSD Hessian, matching shapes",
            "tolerance": "PSD scale times O(n * machine epsilon)",
            "failure": "reject before solve",
        },
        {
            "item": "gradient audit",
            "invariant": "analytic and independent method agree",
            "tolerance": "method, point, and step specific",
            "failure": "do not benchmark optimizer",
        },
        {
            "item": "KKT audit",
            "invariant": "four residual families and gap",
            "tolerance": "dimensionless after term scaling",
            "failure": "optimizer success is insufficient",
        },
        {
            "item": "benchmark",
            "invariant": "same inputs and outputs",
            "tolerance": "no wall-clock correctness gate",
            "failure": "record environment and rerun",
        },
    ]
)
display(numerical_contract)
print("float64 epsilon:", FLOAT64_EPSILON)
print("illustrative dimensionless gate:", TEACHING_RELATIVE_TOLERANCE)
"""),
    md(r"""
## 6. deterministic property-style tests

特定の一例だけでなく、seed固定の複数caseに同じpropertyを適用する。Hypothesis等を使わないため、これはproperty-based testing frameworkではなくdeterministicなproperty-style loopである。

検査するpropertyは、quadratic gradientのanalytic / AD / finite-difference一致と、PSD quadraticのJensen inequalityである。case IDとseed contractを残すため失敗を再現できる。
"""),
    code("""
property_rows = []
for case_id, dimension in enumerate(range(2, 9)):
    case_rng = task_rng("properties", case_id)
    factor = case_rng.normal(size=(dimension, dimension))
    hessian = factor.T @ factor + 0.2 * np.eye(dimension)
    linear = case_rng.normal(size=dimension)
    point = case_rng.normal(size=dimension)
    left_point = case_rng.normal(size=dimension)
    right_point = case_rng.normal(size=dimension)
    mixture_weight = case_rng.uniform()

    def case_objective(candidate):
        return float(0.5 * candidate @ hessian @ candidate + linear @ candidate)

    expected_gradient = hessian @ point + linear
    _, automatic_gradient = forward_ad_quadratic(point, hessian, linear)
    difference_gradient = central_difference_gradient(
        case_objective,
        point,
        np.finfo(float).eps ** (1.0 / 3.0),
    )
    mixture = mixture_weight * left_point + (1.0 - mixture_weight) * right_point
    jensen_slack = (
        mixture_weight * case_objective(left_point)
        + (1.0 - mixture_weight) * case_objective(right_point)
        - case_objective(mixture)
    )
    ad_error = np.linalg.norm(automatic_gradient - expected_gradient, ord=np.inf)
    fd_error = np.linalg.norm(difference_gradient - expected_gradient, ord=np.inf)
    passed = ad_error < 1.0e-11 and fd_error < 2.0e-6 and jensen_slack >= -1.0e-11
    property_rows.append(
        {
            "case_id": case_id,
            "dimension": dimension,
            "AD_error": ad_error,
            "FD_error": fd_error,
            "Jensen_slack": jensen_slack,
            "passed": passed,
        }
    )

property_results = pd.DataFrame(property_rows)
display(property_results)
assert property_results["passed"].all()
"""),
    md(r"""
### Explicit unit / edge-case tableとsimple QP test

edge caseはrandom generationへ期待せず個別に実行する。empty vector、NaN、shape mismatch、grossly non-symmetric Hessian、zero denominator、inconsistent boundを期待するexception型まで固定する。さらに、解析解のあるsmall QPを実際のpackage solverへ通し、optimizer status、raw constraint、全KKT familyを自動testする。random caseが通ってもcontract外入力の扱いは証明されない。
"""),
    code("""
def expected_exception(case_id, operation, expected_type):
    try:
        operation()
    except expected_type as error:
        return {
            "case_id": case_id,
            "expected": expected_type.__name__,
            "observed": type(error).__name__,
            "passed": True,
        }
    except Exception as error:
        return {
            "case_id": case_id,
            "expected": expected_type.__name__,
            "observed": type(error).__name__,
            "passed": False,
        }
    return {
        "case_id": case_id,
        "expected": expected_type.__name__,
        "observed": "no exception",
        "passed": False,
    }


edge_case_rows = [
    expected_exception(
        "empty point",
        lambda: finite_difference_gradient_audit(
            lambda point: float(point @ point),
            lambda point: 2.0 * point,
            np.array([]),
        ),
        ValueError,
    ),
    expected_exception(
        "NaN point",
        lambda: finite_difference_gradient_audit(
            lambda point: float(point @ point),
            lambda point: 2.0 * point,
            np.array([np.nan]),
        ),
        ValueError,
    ),
    expected_exception(
        "gradient shape mismatch",
        lambda: finite_difference_gradient_audit(
            lambda point: float(point @ point),
            lambda point: np.ones(point.size + 1),
            np.array([1.0]),
        ),
        ValueError,
    ),
    expected_exception(
        "non-symmetric Hessian",
        lambda: QuadraticProgram(
            P=np.array([[1.0, 1.0], [0.0, 1.0]]),
            q=np.zeros(2),
        ),
        ValueError,
    ),
    expected_exception(
        "dual zero denominator",
        lambda: Dual(1.0, np.array([1.0])) / 0.0,
        ZeroDivisionError,
    ),
    expected_exception(
        "inconsistent bounds",
        lambda: QuadraticProgram(
            P=np.eye(1),
            q=np.zeros(1),
            lower_bounds=np.array([1.0]),
            upper_bounds=np.array([0.0]),
        ),
        ValueError,
    ),
    expected_exception(
        "curve metric zero total weight",
        lambda: weighted_rmse(
            np.array([1.0, 2.0]),
            np.array([1.0, 2.0]),
            np.zeros(2),
        ),
        ValueError,
    ),
]

cancellation_audit = finite_difference_gradient_audit(
    lambda point: float(1.0e30 + point[0]),
    lambda point: np.ones_like(point),
    np.array([0.0]),
)
edge_case_rows.append(
    {
        "case_id": "absorbed finite-difference probes",
        "expected": "cancellation verdict",
        "observed": cancellation_audit.diagnostic,
        "passed": (
            cancellation_audit.cancellation_detected
            and not cancellation_audit.passed
        ),
    }
)
edge_case_results = pd.DataFrame(edge_case_rows)
display(edge_case_results)
assert edge_case_results["passed"].all()
"""),
    code("""
# min 0.5 ||x - (2, 2)||^2 subject to x >= 0 and x_1 + x_2 <= 1.
# The constant term is omitted, and the unique analytic solution is (0.5, 0.5).
package_qp = QuadraticProgram(
    P=np.eye(2),
    q=np.array([-2.0, -2.0]),
    G=np.array([[1.0, 1.0]]),
    h=np.array([1.0]),
    lower_bounds=np.zeros(2),
    variable_units=("unitless", "unitless"),
    inequality_units=("unitless",),
    name="week16_contract_qp",
)
package_qp_solution = solve_quadratic_program(
    package_qp,
    initial=np.array([0.2, 0.3]),
    method="SLSQP",
)
package_qp_expected = np.array([0.5, 0.5])
package_qp_kkt = package_qp_solution.diagnostics.kkt
raw_inequality_violation = max(
    float(np.max(package_qp.G @ package_qp_solution.x - package_qp.h)),
    0.0,
)
raw_lower_bound_violation = max(
    float(np.max(package_qp.lower_bounds - package_qp_solution.x)),
    0.0,
)
qp_contract_tests = pd.DataFrame(
    [
        {
            "test": "optimizer termination",
            "value": package_qp_solution.diagnostics.optimizer_success,
            "threshold": True,
            "passed": package_qp_solution.diagnostics.optimizer_success,
        },
        {
            "test": "analytic solution infinity error",
            "value": np.linalg.norm(
                package_qp_solution.x - package_qp_expected,
                ord=np.inf,
            ),
            "threshold": 1.0e-8,
            "passed": np.allclose(
                package_qp_solution.x,
                package_qp_expected,
                rtol=0.0,
                atol=1.0e-8,
            ),
        },
        {
            "test": "raw inequality violation",
            "value": raw_inequality_violation,
            "threshold": 1.0e-12,
            "passed": raw_inequality_violation <= 1.0e-12,
        },
        {
            "test": "raw lower-bound violation",
            "value": raw_lower_bound_violation,
            "threshold": 1.0e-12,
            "passed": raw_lower_bound_violation <= 1.0e-12,
        },
        {
            "test": "all normalized KKT families",
            "value": max(
                package_qp_kkt.stationarity,
                package_qp_kkt.primal_inequality,
                package_qp_kkt.primal_equality,
                package_qp_kkt.primal_bounds,
                package_qp_kkt.dual_feasibility,
                package_qp_kkt.complementarity,
                package_qp_kkt.duality_gap,
            ),
            "threshold": package_qp_kkt.tolerance,
            "passed": package_qp_kkt.passed,
        },
    ]
)
display(qp_contract_tests)
assert qp_contract_tests["passed"].all()
assert package_qp_solution.success

tested_package_slice = pd.DataFrame(
    [
        {
            "package API": "curves.weighted_rmse",
            "evidence": "known answer + zero-total-weight rejection",
            "passed": (
                np.isclose(
                    curve_metric_observed,
                    curve_metric_expected,
                    rtol=0.0,
                    atol=1.0e-15,
                )
                and edge_case_results.loc[
                    edge_case_results["case_id"]
                    == "curve metric zero total weight",
                    "passed",
                ].item()
            ),
        },
        {
            "package API": "optimization.finite_difference_gradient_audit",
            "evidence": "step sweep + cancellation / invalid-input cases",
            "passed": (
                package_gradient_audit.passed
                and cancellation_audit.cancellation_detected
            ),
        },
        {
            "package API": "convex.solve_quadratic_program",
            "evidence": "analytic solution + raw constraints + every KKT family",
            "passed": package_qp_solution.success,
        },
    ]
)
display(tested_package_slice)
assert tested_package_slice["passed"].all()
"""),
    md(r"""
## 7. profilingは遅い箇所を限定する

profileはalgorithm complexityの証明ではない。同じ入力の繰り返しについてcall countとcumulative timeを記録し、上位だけを表示する。
"""),
    code("""
profiler = cProfile.Profile()
profiler.enable()
for _ in range(40):
    weighted_sum_vectorized(benchmark_values, benchmark_weights)
profiler.disable()

profile_stream = io.StringIO()
pstats.Stats(profiler, stream=profile_stream).strip_dirs().sort_stats("cumulative").print_stats(8)
print(profile_stream.getvalue())
"""),
    md(r"""
正しさを確認するunit testは高速でdeterministicに保つ。benchmarkとprofileはperformance artifactとして分離し、CIの共有machineでwall-clock thresholdをcorrectness gateにしない。
"""),
    md(r"""
## 8. provenanceとclean-process artifact

artifactには結果だけでなく、configuration、論理seed、library version、platform、input fingerprint、再生成commandを含める。fingerprintはsourceの真正性や意味の正しさを保証しないが、同じbytesを入力したかを監査できる。
"""),
    code("""
artifact_rng = task_rng("artifact")
artifact_input = artifact_rng.normal(size=32).astype("<f8")
artifact_value = float(np.mean(artifact_input**2))
artifact_input_hash = hashlib.sha256(artifact_input.tobytes()).hexdigest()

environment_metadata = {
    "python": platform.python_version(),
    "numpy": importlib_metadata.version("numpy"),
    "scipy": importlib_metadata.version("scipy"),
    "plotly": importlib_metadata.version("plotly"),
    "platform": platform.platform(),
}
artifact_configuration = {
    "root_seed": RANDOM_SEED,
    "notebook_id": NOTEBOOK_ID,
    "task_id": TASK_IDS["artifact"],
    "size": int(artifact_input.size),
    "dtype": str(artifact_input.dtype),
}

research_artifact = {
    "configuration": artifact_configuration,
    "input_sha256": artifact_input_hash,
    "mean_square": artifact_value,
    "environment": environment_metadata,
}
print(json.dumps(research_artifact, ensure_ascii=False, indent=2))
"""),
    md(r"""
上のversionはこの実行artifactのprovenanceであり、互換性範囲全体の試験結果ではない。教材が参照するSciPy 1.13 APIの下限は別environment / CIで実行して初めて検証できる。このNotebookをより新しいSciPyで一度実行しただけなら「1.13でも実行済み」とは主張しない。
"""),
    code("""
clean_script = f'''\
import hashlib
import json
import numpy as np

rng = np.random.default_rng(
    np.random.SeedSequence([{RANDOM_SEED}, {NOTEBOOK_ID}, {TASK_IDS["artifact"]}])
)
values = rng.normal(size=32).astype("<f8")
print(json.dumps({{
    "input_sha256": hashlib.sha256(values.tobytes()).hexdigest(),
    "mean_square": float(np.mean(values**2)),
}}))
'''
clean_command = [sys.executable, "-c", clean_script]
clean_result = subprocess.run(
    clean_command,
    check=True,
    capture_output=True,
    text=True,
)
clean_artifact = json.loads(clean_result.stdout)

assert clean_artifact["input_sha256"] == research_artifact["input_sha256"]
np.testing.assert_allclose(
    clean_artifact["mean_square"],
    research_artifact["mean_square"],
    rtol=0.0,
    atol=0.0,
)
print("clean-process fingerprint match:", clean_artifact["input_sha256"])
print("reproduction command shape:", ["<python>", "-c"], "<recorded Python script>")
"""),
    md(r"""
child processは現在のNotebook namespaceを継承せず、seedとcodeだけから同じartifactを再生成した。production artifactではinline scriptではなくversion管理されたmodule / CLI、input URI、commit、lockfileまたはenvironment exportを記録する。
"""),
    md(r"""
## 9. Core / Advancedと75点gate

**Core**はB1共通metricのpure API、explicit configuration、analytic / AD / finite-difference audit、package QPのconstraint / KKT test、deterministic test、benchmark metadata、clean-process再生成までである。

**Advanced**はfull-featured AD framework、Hypothesisによるshrinking、continuous benchmark、differentiable optimization、large sparse profilingである。Advancedを使わなくてもCoreの契約は省略しない。

| Category | Points | 必須証拠 |
|---|---:|---|
| Mathematical understanding | 25 | complexityとerror sourceの区別 |
| Implementation and testing | 30 | tested package API、gradient audit、edge case、QP / KKT |
| Experimental design | 30 | correctnessとbenchmarkの分離、metadata |
| Explanation and memo | 15 | contract、failure、reproduction command |

合計75点以上に加え、package gradient audit、explicit edge-case table、QP constraint / KKT test、deterministic rerun、clean-process artifactが欠けていないことを必須gateにする。速いという主張だけでは合格しない。
"""),
    md(r"""
## 10. 失敗モード

- Notebook globalを暗黙に読む関数をlibraryへ移す
- NaNやshape mismatchをsolverへ渡して不明瞭なfailureにする
- finite differenceまたはcomplex-stepをautomatic differentiationと呼ぶ
- 一つのpointだけでgradientを照合する
- `np.finfo(float).eps`を全てのabsolute toleranceへ直接使う
- random testのseed、case ID、失敗入力を保存しない
- wall-clock timeへunit-test assertionを置く
- sparse matrixを測らず常に高速・省memoryと主張する
- fingerprintをdata qualityまたはprovenance全体の証明とみなす
- warm Notebook stateでだけartifactを再生成する
"""),
    md(r"""
## 11. 段階別演習

### 基礎

1. 価格vectorを返す関数のshape、単位、有限性contractを書け。
2. forward finite differenceとcentral finite differenceのtruncation orderを導出せよ。
3. list lookupとdict lookupを同じquery setで照合せよ。

### 標準

4. dual numberへpowerまたはexponential ruleを一つ追加し、analytic gradientと照合せよ。
5. gradient checkのstep gridをfloat32へ変え、error curveの移動を説明せよ。
6. sparse densityを$0.1\%$から$50\%$まで変え、memoryとtimeを別々にplotせよ。
7. edge-case tableの各failureを小さなunit testへ落とせ。

### 研究

8. benchmark artifactへCPU、thread設定、commit、input hashを追加せよ。
9. **Advanced:** production AD frameworkのreverse modeと本章のforward modeを、input / output次元から比較せよ。
"""),
    md(r"""
## 12. Exit Criteria

- [ ] input / output / invariant / tolerance / failureを数値契約として書ける
- [ ] correctness testとperformance benchmarkを別artifactにできる
- [ ] forward-mode ADとfinite differenceを区別してgradientを照合できる
- [ ] reusable gradient auditとQP solverを実codeで呼び、failure / constraint / KKTをtestできる
- [ ] deterministic property-style testと明示的edge caseを使い分けられる
- [ ] sparse、layout、hashの実測を条件付きで解釈できる
- [ ] configuration、environment、fingerprint、commandを保存できる
- [ ] clean processでNotebook stateに依存せず同じartifactを再生成できる
"""),
    md(r"""
## 13. 出典

- [Griewank and Walther, *Evaluating Derivatives*](https://epubs.siam.org/doi/book/10.1137/1.9780898717761) — forward / reverse automatic differentiationの原典的体系
- [SciPy `check_grad`](https://docs.scipy.org/doc/scipy-1.13.0/reference/generated/scipy.optimize.check_grad.html) — forward finite differenceとのgradient照合を行う1.13公式API
- [SciPy sparse arrays](https://docs.scipy.org/doc/scipy-1.13.0/reference/sparse.html) — sparse representationとlinear algebraの公式reference
- [NumPy `assert_allclose`](https://numpy.org/doc/stable/reference/generated/numpy.testing.assert_allclose.html) — `atol + rtol * abs(desired)`の公式比較契約
- [Python `timeit`](https://docs.python.org/3/library/timeit.html) — small code timingと繰り返しに関する公式documentation
- [Python `cProfile`](https://docs.python.org/3/library/profile.html) — deterministic profilerの公式documentation

次章では、この数値契約をdiscount-factor QPへ適用し、B1の価格curveを制約、KKT、LOO、memoまで含む再現可能なprojectへ拡張する。
"""),
]
