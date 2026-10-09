"""Build three RB-F06 figures from saved, checked Hagan-map observations only."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent
ARTIFACT_ENV = "JOHNHULL_SABR_IDENTIFIABILITY_ARTIFACTS_DIR"
SOURCE_ENV = "JOHNHULL_SABR_IDENTIFIABILITY_SOURCE_DIR"

LOAD = r"""import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
from IPython.display import Markdown, display
from hullkit import nbplot

get_ipython().run_line_magic("matplotlib", "inline")
plt = nbplot.setup()
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": False})

def resolve_directory(variable, filename):
    supplied = os.environ.get(variable)
    candidates = [Path(supplied)] if supplied else [Path.cwd()]
    if not supplied:
        candidates += [parent / "johnhull/research/RB-F06"
                       for parent in [Path.cwd(), *Path.cwd().parents]]
    for candidate in candidates:
        if (candidate / filename).is_file():
            return candidate
    raise FileNotFoundError("Saved RB-F06 data/source missing; set " + variable)

artifact_dir = resolve_directory("JOHNHULL_SABR_IDENTIFIABILITY_ARTIFACTS_DIR", "reference.json")
source_dir = resolve_directory("JOHNHULL_SABR_IDENTIFIABILITY_SOURCE_DIR", "build_reference.py")
spec = importlib.util.spec_from_file_location("rbf06_notebook_saved_loader", source_dir / "build_reference.py")
loader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = loader
spec.loader.exec_module(loader)

def artifact_forbidden(*args, **kwargs):
    raise RuntimeError("Artifact-only guard: RNG, optimization and fresh work are forbidden")

# Install before saved checking: the kernel may read/revalue but must not draw or fit.
import scipy.optimize as _optimizer
artifact_guard_rng = ["default_rng", "RandomState", "SeedSequence", "seed", "rand", "randn",
                      "random", "random_sample", "normal", "standard_normal", "uniform",
                      "poisson", "choice", "permutation", "shuffle"]
artifact_guard_optimizer = ["least_squares", "minimize", "differential_evolution",
                            "dual_annealing", "basinhopping"]
for _name in artifact_guard_rng:
    setattr(np.random, _name, artifact_forbidden)
for _name in artifact_guard_optimizer:
    setattr(_optimizer, _name, artifact_forbidden)
if hasattr(loader, "core"):
    loader.core.fit_smile = artifact_forbidden
    if hasattr(loader.core, "least_squares"):
        loader.core.least_squares = artifact_forbidden
for _name in ["run_study", "_fresh"]:
    if hasattr(loader, _name):
        setattr(loader, _name, artifact_forbidden)
print("Artifact guard active before saved checking:",
      len(artifact_guard_rng), "RNG entries and", len(artifact_guard_optimizer), "optimizer entries")
record, arrays = loader.load_result(artifact_dir)
if record["phase"] not in {"main", "fixture"}:
    raise ValueError("pilot has no held-out study and cannot populate this notebook")
checked = loader.check_record(record, arrays, fresh=False)
if checked.get("passed") is not True:
    raise ValueError("Saved RB-F06 checker failed")
summary = loader.module("analytics").summarize(record, arrays)
protocol = record["protocol"]
phase = record["phase"]
axis_names = ["a", "rho", "nu"]
groups = list(protocol["groups"])
truths = protocol["truths"]
rep = protocol["representative_noisy_rep"]
dataset_map = {(d["truth_index"], d["group"], d["rep"]): d for d in record["datasets"]}
row_map = {r["dataset_id"]: r for r in summary["per_dataset"]}
cells = summary["cells"]
cell_map = {(c["truth_index"], c["group"]): c for c in cells}
identities = [(ti, group) for ti in range(len(truths)) for group in groups]
labels = [truths[ti]["name"] + "\n" + group for ti, group in identities]
positions = np.arange(len(identities))
representatives = [dataset_map.get((ti, group, rep)) for ti, group in identities]

def number(value):
    return "unknown" if value is None else f"{value:.5g}"

def table(headers, rows):
    def clean(value):
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
    lines += ["| " + " | ".join(clean(value) for value in row) + " |" for row in rows]
    display(Markdown("\n".join(lines)))

def finish_figure(fig, title, note):
    fig.suptitle(title + " | " + phase + " | saved artifact only", fontsize=12)
    fig.text(.5, .012, note, ha="center", va="bottom", fontsize=9)
    fig.tight_layout(rect=(0, .07, 1, .945))
    display(fig)
    plt.close(fig)

def chosen_fit(dataset):
    if dataset is None:
        return None
    fid = row_map[dataset["dataset_id"]]["best_converged"]
    return next((fit for fit in dataset["fits"] if fit["fit_id"] == fid), None)

def tick_cells(ax):
    ax.set_xticks(positions, labels, fontsize=8)
    ax.grid(axis="y", alpha=.2)

print("Saved-artifact phase:", phase, "| numerical checker:", checked["passed"])
print("fixture / 未受入: 表示配線の確認専用。" if phase == "fixture"
      else "保存された主実験です。独立研究受入の正本はREADME/REVIEWで確認してください。")
print("record teaching_acceptance:", record["teaching_acceptance"],
      "| independent research acceptance is separate from this numerical checker.")
print("Approximate Hagan IV map only; exact SABR prices/dynamics are not validated.")
print("No RNG, optimizer, training, network, or fresh calculation is run in this notebook.")
print("theta=(a,rho,nu), a=alpha/F**(1-beta); u=theta/parameter_scale:",
      protocol["parameter_scale"], "| IV noise scale:", protocol["noise_scale"])
print("Frozen representative noisy repetition:", rep,
      "| pointwise chi-square descriptive reference:", number(protocol["profile_threshold"]))
print("Boundary/nonidentification LR coverage is unverified. This is not a joint confidence envelope.")
print("Finite visited profiles do not explore all interiors: unexplored gaps may contain extra crossings.")
print("Original dataset slots:", len(record["datasets"]),
      "| noisy slots:", sum(d["rep"] >= 0 for d in record["datasets"]),
      "| recorded seed slots:", len(protocol["seed_ledger"]))
table(["cost item", "recorded value"], [[key, number(record["costs"].get(key))]
      for key in ["solver_calls", "exceptions", "evaluation_count_unknown",
                  "attempt_seconds", "solver_seconds", "diagnostic_seconds"]])
print("Recorded attempt/solver/diagnostic times are nested, not additive independent categories.")
print("Runtime invocation seconds:", number(record["runtime"].get("invocation_seconds")),
      "| scope:", record["runtime"].get("cost_scope"))
print("Saved analytics attempts:", summary["cost_totals"]["attempts"],
      "| failed:", summary["cost_totals"]["failed"],
      "| boundary attempts:", summary["cost_totals"]["boundary_attempts"])
"""

FIGURE_1 = r"""fig, axes = plt.subplots(len(truths), len(groups), figsize=(15, 8.5), squeeze=False)
profile_table = []
for ti, truth in enumerate(truths):
    for gi, group in enumerate(groups):
        ax = axes[ti, gi]
        dataset = dataset_map.get((ti, group, rep))
        if dataset is None:
            ax.set_axis_off()
            ax.text(.5, .5, "missing representative dataset\n" + truth["name"] + " / " + group,
                    ha="center", va="center", transform=ax.transAxes)
            continue
        row = row_map[dataset["dataset_id"]]
        curve = next((c for c in dataset["curves"] if c["axis"] == 2), None)
        baseline = row["best_q"]
        ax.set_title(truth["name"] + " / " + group + "\n" + row["support"]["status"])
        if curve is None or baseline is None:
            ax.text(.5, .5, "missing curve / no converged baseline",
                    ha="center", transform=ax.transAxes)
            continue
        point_map = {p["point_id"]: p for p in dataset["profile_points"]}
        points = sorted([point_map[pid] for pid in curve["point_ids"]], key=lambda p: p["value"])
        x = [point["value"] for point in points]
        profile_q = [point["q"] - baseline if point["success"] and point["q"] is not None
                     and np.isfinite(point["q"]) else np.nan for point in points]
        slice_q = [np.nan if point["slice_q"] is None else point["slice_q"] - baseline for point in points]
        ax.plot(x, profile_q, "o-", markersize=4, label="profile: nuisance re-fit")
        ax.plot(x, slice_q, "s--", markersize=3, label="slice: nuisance fixed")
        ax.axhline(curve["threshold"], color="tab:red", linestyle=":",
                   label="pointwise descriptive reference")
        ax.axhline(0, color=".6", linewidth=.7)
        ax.axvline(truth["theta"][2], color="tab:green", linestyle="--", label="synthetic true nu")
        for bound in [protocol["bounds"][0][2], protocol["bounds"][1][2]]:
            ax.axvline(bound, color=".5", linewidth=.7)
        failed_x = [value for value, q in zip(x, profile_q, strict=True) if not np.isfinite(q)]
        if failed_x:
            ax.scatter(failed_x, [.04]*len(failed_x), transform=ax.get_xaxis_transform(),
                       marker="x", color="black", label="failed / unknown (gap)")
        segments = curve["segments"]
        ax.text(.03, .97, "bound censor L/U: " + str(segments.get("lower_censored")) + "/"
                + str(segments.get("upper_censored")) + "\nunknown brackets: "
                + str(len(segments.get("unknown_brackets", []))),
                transform=ax.transAxes, va="top", fontsize=8)
        ax.set_yscale("symlog", linthresh=1.)
        ax.set_xlabel("nu (fixed profile coordinate)")
        ax.set_ylabel("Q - best converged unrestricted Q")
        ax.legend(fontsize=7, loc="best")
        ax.grid(axis="y", alpha=.2)
finish_figure(fig, "1. Profileとslice：固定代表repのnu比較",
              "NaN breaks failed profiles. Unsupported datasets retained. Pointwise reference; unexplored gaps remain.")
for dataset in record["datasets"]:
    for curve in dataset["curves"]:
        point_map = {p["point_id"]: p for p in dataset["profile_points"]}
        points = [point_map[pid] for pid in curve["point_ids"]]
        segments = curve["segments"]
        profile_table.append([
            truths[dataset["truth_index"]]["name"], dataset["group"], dataset["rep"],
            axis_names[curve["axis"]], row_map[dataset["dataset_id"]]["support"]["status"],
            len(points), sum(not p["success"] or p["q"] is None for p in points),
            segments.get("observed_components", "unknown"),
            str(segments.get("lower_censored")) + "/" + str(segments.get("upper_censored")),
            len(segments.get("unknown_brackets", [])), number(curve["threshold"]),
        ])
table(["truth", "group", "rep", "axis", "support", "visited points", "failed/unknown",
       "sampled components (ΔQ-only)", "bound censor L/U", "unknown brackets", "reference delta Q"], profile_table)
print("表は全curve・全3軸を収録します。sampled componentsは区間全体の支持を保証しません。")
print("Noiseless curve/table: ΔQ-only sampled components; noiseless same-fit price visits additionally require max IV residual<=1e-9.")
print("Noisy curves use pointwise descriptive chi-square reference; noiseless curves use their separate tiny delta-Q tolerance.")
print("Missing curve stays missing. A feasible slice can remain finite when the profile optimizer fails.")
"""

FIGURE_2 = r"""fig, axes = plt.subplots(2, 2, figsize=(15, 9))
sv = np.full((len(identities), 3), np.nan)
projection = np.full_like(sv, np.nan)
stability_table = []
for index, dataset in enumerate(representatives):
    fit = chosen_fit(dataset)
    if fit is None:
        for ax in [axes[0, 0], axes[1, 0]]:
            ax.text(index, .02, "missing", transform=ax.get_xaxis_transform(),
                    rotation=90, fontsize=7)
        continue
    keys = fit["array_keys"]
    sv[index] = arrays[keys["singular_values"]]
    vectors = arrays[keys["right_vectors"]]
    # The entire numerical nullspace is basis invariant when rank<3.
    subspace = vectors[fit["rank"]:] if fit["rank"] < 3 else vectors[-1:]
    projection[index] = np.sum(subspace**2, axis=0)
    stability = fit.get("numerical_stability")
    if stability is not None:
        step_jacobians = np.asarray(arrays[fit["stability_jacobians_key"]], dtype=float)
        if step_jacobians.ndim != 3 or len(step_jacobians) != len(protocol["jacobian_steps_u"]):
            raise ValueError("Saved stability Jacobian steps do not match the protocol")
        middle_jacobian = step_jacobians[len(step_jacobians)//2]
        middle_norm = max(float(np.linalg.norm(middle_jacobian, 2)), np.finfo(float).tiny)
        relative_changes_by_step = [float(np.linalg.norm(j-middle_jacobian, 2))/middle_norm
                                    for j in step_jacobians]
        axes[0, 1].plot(protocol["jacobian_steps_u"], relative_changes_by_step,
                        "o-", label=labels[index].replace("\n", " / "))
        axes[1, 1].plot(protocol["jacobian_steps_u"], stability["direction_projector_changes"],
                        "o-", label=labels[index].replace("\n", " / "))
    stability_table.append([
        labels[index].replace("\n", "/"), fit["rank"], number(fit["condition"]),
        "unknown" if stability is None else stability["status"],
        "unknown" if stability is None else stability["ranks"],
        "unknown" if stability is None else number(stability["relative_matrix_change"]),
        "unknown" if stability is None else number(stability["smallest_nonzero_to_estimated_error"]),
        np.asarray(arrays[keys["boundary_flags"]]).tolist(),
    ])
for axis, marker in enumerate(["o", "s", "^"]):
    axes[0, 0].plot(positions, sv[:, axis], marker, linestyle="none", label="s" + str(axis+1))
    axes[1, 0].bar(positions + (axis-1)*.23, projection[:, axis], width=.23,
                    label="projection on " + axis_names[axis])
axes[0, 0].set_yscale("symlog", linthresh=1e-8)
axes[0, 0].set_title("Scaled J = d(IV/noise)/du; zeros retained")
axes[0, 0].set_ylabel("Singular values (dimensionless)")
axes[1, 0].set_title("Nullspace projector if rank<3; weakest direction otherwise")
axes[1, 0].set_ylabel("Diagonal of direction/subspace projector")
axes[1, 0].set_ylim(-.02, 1.05)
for ax in [axes[0, 0], axes[1, 0]]:
    tick_cells(ax)
    ax.legend(fontsize=8)
for ax, title, ylabel in [
    (axes[0, 1], "Saved per-step Jacobian perturbation", "||J_h - J_middle||2 / ||J_middle||2"),
    (axes[1, 1], "Saved right-subspace step perturbation", "Projector change (operator norm)")]:
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=1e-9)
    ax.set_title(title)
    ax.set_xlabel("Step h in scaled coordinate u")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=.2)
    if ax.lines:
        ax.legend(fontsize=8)
    else:
        ax.text(.5, .5, "missing stability diagnostics", transform=ax.transAxes, ha="center")
finish_figure(fig, "2. Scaled SVDと弱方向の数値安定性",
              "Step perturbations estimate numerical uncertainty, not structural/global identification.")
table(["truth/group", "numerical rank", "scaled condition", "step stability", "ranks by step",
       "maximum relative change (scalar)", "smallest nonzero SV / estimated error",
       "boundary flags a/rho/nu"], stability_table)
print("図の3点は保存済みJacobian行列から各stepの相対差を計算した表示値です。")
print("summary relative_matrix_changeは3点の最大値1個で、数値安定性の判定に使うscalarです。")
print("右特異ベクトルの符号は同定しません。欠損rankではnullspace全体のprojectorを表示します。")
print("rank<2では単一の弱方向は一意ではありません。scaled conditionのunknownを有限値へ置換しません。")
print("安定な数値推定もglobal identificationの証明ではありません。nu=0境界とtiny-positive nuを区別します。")
"""

FIGURE_3 = r"""fig, axes = plt.subplots(2, 3, figsize=(16, 9))
width_medians, width_maxima, range_missing, range_unsupported = [], [], [], []
count_rows, holdout_rows = [], []
for index, (ti, group) in enumerate(identities):
    rows = [r for r in summary["per_dataset"] if (r["truth_index"], r["group"]) == (ti, group)
            and r["rep"] >= 0]
    solved = [r for r in rows if r["theta"] is not None]
    offsets = np.linspace(-.13, .13, len(solved)) if solved else []
    for axis in range(3):
        ax = axes[0, axis]
        if solved:
            ax.scatter(index + offsets, [row["theta"][axis] for row in solved],
                       s=24, color="tab:blue", alpha=.75, label="noisy best converged" if index == 0 else None)
        ax.scatter([index], [truths[ti]["theta"][axis]], marker="x", color="tab:green", s=55,
                   label="synthetic truth" if index == 0 else None)
        if not rows:
            ax.text(index, .03, "missing dataset",
                    rotation=90, transform=ax.get_xaxis_transform(), fontsize=7)
        elif len(solved) < len(rows):
            ax.text(index, .03, f"missing {len(rows)-len(solved)}/{len(rows)}",
                    rotation=90, transform=ax.get_xaxis_transform(), fontsize=7)
    ranges = [row["sampled_price_range"] for row in rows if row["sampled_price_range"] is not None]
    maxima = [max(item["width"]) for item in ranges]
    width_medians.append(float(np.median(maxima)) if maxima else np.nan)
    width_maxima.append(max(maxima) if maxima else np.nan)
    range_missing.append(len(rows)-len(ranges))
    range_unsupported.append(sum(item["support_status"] == "unsupported" for item in ranges))
    cell = cell_map.get((ti, group))
    if cell is not None:
        flags = 0
        for row in rows:
            dataset = next(d for d in record["datasets"] if d["dataset_id"] == row["dataset_id"])
            fit = chosen_fit(dataset)
            if fit is not None:
                key = fit["array_keys"]["boundary_flags"]
                flags += int(np.any(arrays[key]))
        count_rows.append([
            labels[index].replace("\n", "/"), cell["original_noisy_slots"], cell["converged_noisy_slots"],
            cell["unsupported_noisy_slots"], cell["jacobian_unresolved_slots"], flags,
            range_missing[-1], range_unsupported[-1], number(cell["max_holdout_iv_error"]),
            number(cell["max_holdout_price_error"]),
        ])
    for strike_index, log_moneyness in enumerate(protocol["holdout_log_moneyness"]):
        holdout_rows.append([
            labels[index].replace("\n", "/"), number(log_moneyness), protocol["holdout_kind"][strike_index],
            len(ranges), len(rows), number(max((item["width"][strike_index] for item in ranges), default=None)),
        ])
for axis in range(3):
    ax = axes[0, axis]
    for bound in [protocol["bounds"][0][axis], protocol["bounds"][1][axis]]:
        ax.axhline(bound, color=".5", linestyle=":", linewidth=.8)
    ax.set_title("Noisy best-converged " + axis_names[axis] + " (all original reps)")
    ax.set_ylabel(axis_names[axis] + " fitted coordinate")
    tick_cells(ax)
    if axis == 0:
        ax.legend(fontsize=8, loc="best")
axes[1, 0].bar(positions-.18, width_medians, .36, label="median per-run max strike width")
axes[1, 0].bar(positions+.18, width_maxima, .36, label="maximum visited width")
zero_positions = [index for index, value in enumerate(width_maxima) if value == 0]
if zero_positions:
    axes[1, 0].plot(zero_positions, [0]*len(zero_positions), "o", color="black",
                    clip_on=False, label="zero visited width")
finite_widths = [value for value in width_maxima if np.isfinite(value)]
axes[1, 0].set_ylim(0, max(finite_widths)*1.2 if finite_widths and max(finite_widths) > 0 else 1.)
if finite_widths and all(value == 0 for value in finite_widths):
    axes[1, 0].text(.5, .55, "Observed visited width = 0\n"
                    + str(len(finite_widths)) + " cells with saved finite ranges",
                    transform=axes[1, 0].transAxes, ha="center")
axes[1, 0].set_title("Holdout price spread of finite converged visits")
axes[1, 0].set_ylabel("Price width (currency; NOT confidence interval)")
for index, (missing, unsupported) in enumerate(zip(range_missing, range_unsupported, strict=True)):
    axes[1, 0].text(index, .02, f"missing={missing}\nunsupported={unsupported}",
                    transform=axes[1, 0].get_xaxis_transform(), ha="center", fontsize=7, rotation=90)
axes[1, 0].legend(fontsize=7, loc="upper left")
tick_cells(axes[1, 0])
for offset, key, label in [
    (-.28, "original_noisy_slots", "original noisy slots"),
    (-.09, "converged_noisy_slots", "converged"),
    (.09, "unsupported_noisy_slots", "unsupported"),
    (.28, "jacobian_unresolved_slots", "numerical unresolved")]:
    values = [cell_map.get(identity, {}).get(key, np.nan) for identity in identities]
    axes[1, 1].bar(positions+offset, values, width=.18, label=label)
axes[1, 1].set_title("Original denominators and outcomes (counts overlap)")
axes[1, 1].set_ylabel("Dataset slots")
axes[1, 1].legend(fontsize=7)
tick_cells(axes[1, 1])
bottom = np.zeros(3)
for key, color in [("included", "tab:blue"), ("excluded", "tab:orange"), ("unknown", "tab:gray")]:
    values = np.array([sum(cell["pointwise_inclusion"][axis][key] for cell in cells) for axis in range(3)])
    axes[1, 2].bar(np.arange(3), values, bottom=bottom, label=key, color=color)
    bottom += values
axes[1, 2].set_xticks(np.arange(3), axis_names)
axes[1, 2].set_title("Truth-point inclusion: descriptive pointwise reference")
axes[1, 2].set_ylabel("Original noisy slots (unknown retained)")
axes[1, 2].legend(fontsize=8)
axes[1, 2].grid(axis="y", alpha=.2)
finish_figure(fig, "3. Noise反復・holdout価格幅・元の分母",
              "Finite visited price ranges are not a joint confidence envelope or a 95% price interval.")
table(["truth/group", "original noisy", "converged", "unsupported", "J unresolved", "best on bound",
       "range missing", "range unsupported", "max best-fit IV error", "max best-fit price error"], count_rows)
table(["truth/group", "holdout log(K/F)", "kind", "runs with visited range", "original runs",
       "maximum visited price width (currency)"], holdout_rows)
inclusion_rows = []
for cell in cells:
    for axis, outcome in enumerate(cell["pointwise_inclusion"]):
        inclusion_rows.append([
            cell["truth_name"] + "/" + cell["group"], axis_names[axis], outcome["denominator"],
            outcome["included"], outcome["excluded"], outcome["unknown"],
            outcome["original_rate_bounds"], outcome["known_denominator"],
            number(outcome["known_rate"]), outcome["known_wilson95"],
        ])
table(["truth/group", "axis", "original denominator", "included", "excluded", "unknown",
       "original fraction bounds", "known denominator", "known-only rate", "known-only Wilson uncertainty"], inclusion_rows)
print("Pointwise inclusion is descriptive; known-only Wilson uncertainty is not certified LR coverage.")
print("範囲はfinite converged visitsのmin/maxです。未訪問の解やunsupportedの状態を消しません。")
print("Holdout IV/価格誤差は同じHagan近似mapに対する合成実験です。exact SABRや実市場への外的妥当性ではありません。")
"""

LIMITS = r"""## 解釈と限界

- Haganの漸近IV写像を逆算する合成研究です。exact SABR価格・動学の妥当性を検証しません。
- \(\theta=(a,\rho,\nu)\)、\(a=\alpha/F^{1-\beta}\)。scaled Jacobianはノイズと座標の単位を固定します。
- fixed sliceとnuisanceを再最適化したprofileを分けます。各点の失敗はNaNの切れ目とunknownに残します。
- χ²の閾値はpointwise descriptive referenceです。境界・非識別条件での尤度比の被覆保証は未検証です。
- observed componentsは訪れた点の集計です。noiseless curve/tableのsampled componentsはΔQ-onlyです。noiseless same-fit price visitsにはmax IV residual<=1e-9も必要で、両者は同じフィット集合ではありません。unexplored gapsの内部に追加の交差・支持成分があり得ます。境界打切りも保持します。
- ν=0境界とtiny-positive νを区別し、stepによるSVD/右部分空間の変動を数値不確実性として残します。nullspaceの次元が2以上なら単一の弱方向は一意ではありません。
- parameter scatterは元のnoisy反復を使います。較正失敗、unknown、unsupported、境界、未解決の数値rankを表示します。
- holdout価格幅は有限個の訪問済み解の幅です。not a joint confidence envelope。95%価格区間ではありません。
- known-only inclusion率とWilson不確実性は、unknownを含む元の分母・率の上下限と分けます。certified confidence coverageを主張しません。
- 保存checkerのPASSと独立研究受入は別です。fixtureは表示配線の確認専用で未受入です。
- 費用は保存recordの計測です。attempt/solver/diagnosticは入れ子であり、それらを足して独立総費用にはしません。
- ノートブックでRNG・optimizer・学習・network・fresh実験は実行しません。保存したJSON/NPZだけを読みます。
"""


def _loader(source):
    path = Path(source) / "build_reference.py"
    if not path.is_file():
        raise FileNotFoundError("RB-F06 saved loader missing: " + str(path))
    spec = importlib.util.spec_from_file_location("rbf06_notebook_precheck", path)
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
    return loaded


@contextmanager
def _environment(artifacts, source):
    values = {ARTIFACT_ENV: str(artifacts), SOURCE_ENV: str(source)}
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def build(directory: Path = HERE, output: Path | None = None, *, execute: bool = False) -> Path:
    """Create an artifact-only notebook; numerical checking never runs fresh."""
    artifacts = Path(os.environ.get(ARTIFACT_ENV, directory)).resolve()
    source = Path(os.environ.get(SOURCE_ENV, HERE)).resolve()
    loader = _loader(source)
    record, arrays = loader.load_result(artifacts)
    if record["phase"] not in {"main", "fixture"}:
        raise ValueError("pilot has no held-out study and cannot populate this notebook")
    checked = loader.check_record(record, arrays, fresh=False)
    if checked.get("passed") is not True:
        raise ValueError("Saved RB-F06 checker failed")
    output = Path(output) if output is not None else artifacts / "sabr_identifiability.ipynb"
    output.parent.mkdir(parents=True, exist_ok=True)
    cells = [
        nbformat.v4.new_markdown_cell(
            "# RB-F06：SABR較正の識別可能性\n\n"
            "保存した較正・profile・SVD・holdoutから3図を描きます。"
            "価格の一致、パラメータの識別、数値安定性を分けて読みます。",
            id="rbf06-title",
        ),
        nbformat.v4.new_code_cell(LOAD, id="rbf06-load", metadata={"rbf06_loader": True}),
    ]
    for number, (title, code) in enumerate(
        [
            ("Profileとslice", FIGURE_1),
            ("Scaled SVDと弱方向", FIGURE_2),
            ("Noise反復とholdout価格幅", FIGURE_3),
        ],
        1,
    ):
        cells.extend(
            [
                nbformat.v4.new_markdown_cell(
                    "## " + str(number) + ". " + title, id=f"rbf06-figure-{number}-heading"
                ),
                nbformat.v4.new_code_cell(
                    code, id=f"rbf06-figure-{number}", metadata={"rbf06_figure": number}
                ),
            ]
        )
    cells.append(nbformat.v4.new_markdown_cell(LIMITS, id="rbf06-limits"))
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "rbf06": {"artifact_only": True, "figures": 3},
        },
    )
    if execute:
        with _environment(artifacts, source):
            notebook = NotebookClient(
                notebook,
                timeout=600,
                kernel_name="python3",
                resources={"metadata": {"path": str(output.parent.resolve())}},
            ).execute()
    nbformat.write(notebook, output)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=HERE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    print(build(args.artifacts, args.output, execute=args.execute))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
