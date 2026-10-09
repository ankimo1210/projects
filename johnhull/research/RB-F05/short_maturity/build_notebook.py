"""Build three short-call figures by replaying saved study artifacts only."""

from __future__ import annotations

import argparse
import os
from contextlib import contextmanager
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent
ARTIFACT_ENV = "JOHNHULL_SHORT_MATURITY_ARTIFACTS_DIR"
SOURCE_ENV = "JOHNHULL_SHORT_MATURITY_SOURCE_DIR"

LOAD = r"""import importlib.util
import os
import sys
from pathlib import Path
from collections import Counter

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
        candidates += [parent / "johnhull/research/RB-F05/short_maturity"
                       for parent in [Path.cwd(), *Path.cwd().parents]]
    for candidate in candidates:
        if (candidate / filename).is_file():
            return candidate
    raise FileNotFoundError("Saved short-maturity evidence missing; set " + variable)

artifact_dir = resolve_directory("JOHNHULL_SHORT_MATURITY_ARTIFACTS_DIR", "reference.json")
source_dir = resolve_directory("JOHNHULL_SHORT_MATURITY_SOURCE_DIR", "build_reference.py")
spec = importlib.util.spec_from_file_location("short_notebook_saved_loader", source_dir / "build_reference.py")
loader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = loader
spec.loader.exec_module(loader)

# Import libraries before disabling sampling; no model is constructed or trained.
import scipy.optimize as _optimizer
import urllib.request as _url
import http.client as _http
import hullkit
_workspace = Path(hullkit.__file__).resolve().parents[4]
_deep_src = _workspace / "deep_hedge_price/src"
if _deep_src.is_dir():
    sys.path.insert(0, str(_deep_src))
try:
    import torch as _torch
    from deep_hedge_price import _short_maturity_dml as _learner
except ImportError:
    _torch = _learner = None

def artifact_forbidden(*args, **kwargs):
    raise RuntimeError("Artifact-only guard: sampling, training, optimization and network forbidden")

# SeedSequence is allowed solely for reserved-ledger provenance validation.
# No Generator/RandomState or sampling entry point is available to this notebook.
artifact_guard_rng = ["default_rng", "RandomState", "seed", "rand", "randn", "random",
                      "random_sample", "normal", "standard_normal", "uniform", "poisson",
                      "choice", "permutation", "shuffle"]
for _name in artifact_guard_rng:
    setattr(np.random, _name, artifact_forbidden)
for _name in ["least_squares", "minimize", "differential_evolution", "dual_annealing", "basinhopping"]:
    setattr(_optimizer, _name, artifact_forbidden)
for _name in ["run_study", "_initial_weights"]:
    if hasattr(loader, _name):
        setattr(loader, _name, artifact_forbidden)
if hasattr(loader, "core"):
    loader.core.compact_teacher = artifact_forbidden
if _learner is not None:
    _learner.train = artifact_forbidden
if _torch is not None:
    _torch.manual_seed = artifact_forbidden
    _torch.seed = artifact_forbidden
    _torch.optim.Adam.step = artifact_forbidden
    _torch.optim.SGD.step = artifact_forbidden
    _torch.nn.init.kaiming_uniform_ = artifact_forbidden
_url.urlopen = artifact_forbidden
_http.HTTPConnection.request = artifact_forbidden
print("Artifact-only guard installed before numerical checking; no RNG, optimizer, training or network.")

record, arrays = loader.load_result(artifact_dir)
checked = loader.check_record(record, arrays)
if checked.get("passed") is not True:
    raise ValueError("Saved short-maturity numerical checker did not pass")
analytics = loader.module("analytics")
protocol = record["protocol"]
strike = protocol["contract"]["strike"]
mode = record["mode"]
test = record["datasets"]["test"]
test_inputs = arrays[test["inputs_key"]]
truth = arrays[test["oracle_key"]]
independent = arrays[test["independent_key"]]
fits = record["fits"]
scale = np.array([1., 1., strike])
units = ["C (currency)", "Delta (currency/spot)", "K Gamma (K currency/spot^2)"]

def number(value):
    return "unknown" if value is None or not np.isfinite(value) else f"{value:.5g}"

def vector(value):
    return "unknown" if value is None else ", ".join(number(x) for x in value)

def table(headers, rows):
    def clean(value):
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
    lines += ["| " + " | ".join(clean(x) for x in row) + " |" for row in rows]
    display(Markdown("\n".join(lines)))

def finish_figure(fig, title, note):
    fig.suptitle(title + " | " + mode + " | saved artifact only", fontsize=12)
    fig.text(.5, .015, note, ha="center", va="bottom", fontsize=8)
    fig.tight_layout(rect=(0, .075, 1, .95))
    display(fig)
    plt.close(fig)

def fit_label(fit):
    stats = fit["stats"]
    return (fit["id"] + " / seed " + str(stats["seed"]) + " / "
            + ("Delta-DML" if fit["dml"] else "price-only") + " / " + stats["status"])

print("mode:", mode, "| fixture:", bool(record.get("fixture", mode != "main")))
print("original test rows:", test["original_count"])
print("original fit slots:", len(fits))
print("numerical replay:", checked["passed"], "| independent research acceptance:", record["accepted"],
      "| teaching acceptance:", record["teaching_acceptance"])
print("smoke/fixture output checks display wiring only; it is not performance or acceptance evidence."
      if mode != "main" else "Saved main evidence; independent acceptance is recorded separately.")
print("Synthetic same-day session, conditioned jump teacher, unconstrained raw NN; no official SPX fit.")
print("Price/Delta target one price function. Physical Gamma is a diagnostic; no Gamma training claim.")
print("All original rows/paired seeds remain, including failures and undefined expiry Greeks.")
"""

FIGURE_1 = r"""teacher_rows = []
teacher_tables = []
for split in ["train", "validation"]:
    dataset = record["datasets"][split]
    inputs = arrays[dataset["inputs_key"]]
    target = arrays[dataset["oracle_key"]]
    teachers = dataset["teachers"]
    for i, teacher in enumerate(teachers):
        teacher_rows.append((split, inputs[i], target[i], teacher,
                             arrays[teacher["keys"]["mean"]], arrays[teacher["keys"]["se"]]))
    teacher_tables.append([split, dataset["original_count"], len(teachers),
                           sum(t["reserved_sample_count"] for t in teachers),
                           sum(t["count"] for t in teachers),
                           sum(t["actual_random_draws"] for t in teachers),
                           sum(t["precision_ready"] for t in teachers),
                           dict(Counter(t["status"] for t in teachers))])
fig, axes = plt.subplots(2, 2, figsize=(13, 8))
for j, ax in enumerate(axes.flat[:3]):
    for event, color in [(0, "tab:blue"), (1, "tab:orange")]:
        rows = [row for row in teacher_rows if row[1][2] == event]
        if not rows:
            continue
        minutes = np.array([row[1][1]/60 for row in rows])
        standard_error = np.array([row[5][j]*scale[j] for row in rows])
        error = np.array([abs(row[4][j]-row[2][j])*scale[j] for row in rows])
        ax.scatter(minutes, standard_error, marker="o", facecolors="none", edgecolors=color,
                   label=f"event={event}: teacher SE")
        ax.scatter(minutes, error, marker="x", color=color,
                   label=f"event={event}: absolute true error")
    ax.set(xscale="log", yscale="symlog", xlabel="remaining minutes", ylabel=units[j],
           title=units[j] + ": original conditioned teacher rows")
    ax.grid(alpha=.2)
    ax.legend(fontsize=7)
ax = axes.flat[3]
for status in sorted({row[3]["status"] for row in teacher_rows}):
    rows = [row for row in teacher_rows if row[3]["status"] == status]
    ax.scatter([row[1][1]/60 for row in rows], [row[3]["active_count"] for row in rows],
               marker="x" if status == "analytic_deterministic" else "o", label=status)
ax.axhline(protocol["pilot"]["minimum_active_count"], linestyle=":", color="tab:red", label="rare-event diagnostic minimum")
ax.set(xscale="log", xlabel="remaining minutes", ylabel="observed nonzero Poisson counts",
       title="Rare counts; analytic slots observe zero MC draws")
ax.grid(alpha=.2)
ax.legend(fontsize=7)
finish_figure(fig, "1. Conditioned teacher precision and rare-event evidence",
              "Original N includes zeros; rare-event flags retain mean/SE. Analytic no-event reserved N is not observed MC.")
table(["split", "original rows", "teacher slots", "reserved N", "observed MC N", "actual random draws", "ready slots", "all statuses"], teacher_tables)
print("Teacher SE is an estimate; rare_event_unobserved/unresolved is not evidence of zero true error.")
"""

FIGURE_2 = r"""fig, axes = plt.subplots(3, 2, figsize=(14, 10))
raw_summary = []
for fit in fits:
    raw = arrays[fit["predictions"]["test"]["raw_key"]]
    color = plt.rcParams["axes.prop_cycle"].by_key()["color"][fit["pair_id"] % 10]
    marker = "x" if fit["dml"] else "o"
    label = fit_label(fit)
    for j in range(3):
        axes[j, 0].scatter(np.log(test_inputs[:, 0]/strike), raw[:, j]*scale[j],
                           color=color, marker=marker, s=25, alpha=.75, label=label)
        axes[j, 1].scatter(test_inputs[:, 1]/60, abs(raw[:, j]-truth[:, j])*scale[j],
                           color=color, marker=marker, s=25, alpha=.75, label=label)
    summary = analytics.error_summary(raw, truth, strike=strike)
    stats = fit["stats"]
    raw_summary.append([fit["id"], stats["seed"], "Delta-DML" if fit["dml"] else "price-only",
                        stats["status"], stats.get("reason"), stats["updates"], stats["batch_attempts"],
                        summary["original_count"], summary["failed_rows"], vector(summary["rmse"]),
                        vector(summary["p99"]), vector(summary["max"])])
for j in range(3):
    axes[j, 0].scatter(np.log(test_inputs[:, 0]/strike), independent[:, j]*scale[j],
                       color="black", marker="_", s=70, label="independent reference")
    axes[j, 0].set(xlabel="log(S/K)", ylabel=units[j], title="Raw outputs: all paired seeds")
    axes[j, 1].set(xscale="log", yscale="symlog", xlabel="remaining minutes",
                  ylabel="absolute error: " + units[j], title="Raw errors: all original test rows")
    for ax in axes[j]:
        ax.grid(alpha=.2)
axes[0, 0].legend(fontsize=6, loc="best")
finish_figure(fig, "2. Raw NN price, Delta and physical Gamma",
              "Raw and routed-safe outputs are distinct. Failed rows create gaps, not zero errors; full-roster metrics become unknown.")
table(["fit", "seed", "method", "status", "reason", "updates", "batch attempts", "original N", "failed rows",
       "RMSE C/Delta/KGamma", "p99 C/Delta/KGamma", "max C/Delta/KGamma"], raw_summary)
diagnostic_rows = []
for fit in fits:
    diagnostic = fit["diagnostics"]
    routes = arrays[diagnostic["routes_key"]]
    safe = arrays[diagnostic["safe_key"]]
    diagnostic_rows.append([fit["id"], diagnostic["original_count"], dict(Counter(str(x) for x in routes)),
                            int(np.isfinite(safe[:, 0]).sum()), int(np.isfinite(safe[:, 1:]).all(axis=1).sum())])
table(["fit", "original contract diagnostic N", "all routes", "defined safe prices", "defined ordinary Greeks"], diagnostic_rows)
print("expiry_undefined_atm: price is defined; ordinary Greeks: unknown (Delta/Gamma NaN, reason retained).")
print("Invalid contracts remain invalid; fallback output does not certify the accuracy of raw NN Greeks.")
bucket_rows = []
for fit in fits:
    for route, key in [("raw", "test_buckets"), ("safe", "safe_test_buckets")]:
        for bucket in fit.get(key, []):
            bucket_rows.append([fit["id"], route, bucket["event"], bucket["minutes"], bucket["geometry"],
                                bucket["original_count"], bucket["failed_rows"], vector(bucket["rmse"]),
                                vector(bucket["p99"]), vector(bucket["max"])])
if bucket_rows:
    table(["fit", "raw/safe", "event", "minutes", "geometry", "original N", "failed rows",
           "RMSE C/Delta/KGamma", "p99 C/Delta/KGamma", "max C/Delta/KGamma"], bucket_rows)
else:
    print("Per-time/event/ATM bucket roster: fixture absent; no invented bucket results.")
"""

FIGURE_3 = r"""methods = [("core_mixture", truth), ("hermite", arrays[record["hermite"]["predictions"]["test"]])]
methods += [(fit["id"] + "/raw", arrays[fit["predictions"]["test"]["raw_key"]]) for fit in fits]
comparison = [(name, analytics.error_summary(prediction, independent, strike=strike)) for name, prediction in methods]
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
positions = np.arange(len(comparison))
for j, label in enumerate(units):
    axes[0, 0].scatter(positions, [np.nan if row["max"] is None else row["max"][j] for _, row in comparison],
                       label="max error: " + label)
axes[0, 0].set_xticks(positions, [name for name, _ in comparison], rotation=35, ha="right", fontsize=7)
axes[0, 0].set(yscale="symlog", ylabel="absolute error (distinct units; see table)", title="Strong baselines and all raw NN fits")
axes[0, 0].legend(fontsize=7)
online = {}
for timing in record["timing"]:
    # These are stored whole-call observations; no evaluation is timed in this notebook.
    key = (timing["method"], timing["batch_size"])
    online.setdefault(key, []).append(np.median(arrays[timing["seconds_key"]])/timing["batch_size"])
timing_keys = sorted(online)
axes[0, 1].barh(np.arange(len(timing_keys)), [np.median(online[key]) for key in timing_keys])
axes[0, 1].set_yticks(np.arange(len(timing_keys)), [name + f" / batch {batch}" for name, batch in timing_keys], fontsize=7)
axes[0, 1].set(xscale="log", xlabel="saved median seconds per query", title="Online time; includes returned C/Delta/Gamma")
totals = analytics.expense_totals(record["expenses"])
categories = sorted(totals["categories"])
axes[1, 0].barh(np.arange(len(categories)), [totals["categories"][key] for key in categories])
axes[1, 0].set_yticks(np.arange(len(categories)), categories, fontsize=7)
axes[1, 0].set(xlabel="measured seconds (uniquely charged)", title="Research main-only work; cold costs are separate")
axes[1, 1].set_axis_off()
costs = record["costs"]
pending = totals["pending_ids"]
receipt = loader.serialization_receipt(artifact_dir, record) if hasattr(loader, "serialization_receipt") else None
pending_text = "\n".join(pending) or "none"
lines = ["main-only measured: " + number(costs.get("main_only_s")) + " s",
         "cold pipeline: " + number(costs.get("cold_pipeline_s")) + " s",
         "fresh replay: " + number(costs.get("fresh_s")) + " s",
         "pending receipt IDs:\n" + pending_text,
         "serialization receipt: " + ("unknown" if receipt is None else
             "pending=" + str(receipt.get("pending")) + "; " + number(receipt.get("seconds")) + " s"),
         "equal-accuracy cold payback: unknown",
         "standard accelerator adoption: " + str(record.get("standard_accelerator_adoption", "unknown")),
         "Numerical replay, teaching and independent acceptance are separate."]
axes[1, 1].text(0, 1, "\n\n".join(lines), transform=axes[1, 1].transAxes, va="top", fontsize=9,
                wrap=True)
for ax in axes.flat[:3]:
    ax.grid(axis="x" if ax is not axes[0, 0] else "y", alpha=.2)
finish_figure(fig, "3. Accuracy, strong baselines and measured work",
              "Online speed alone is not equivalent-accuracy evidence. Unknown cold/startup costs are never replaced by zero.")
table(["method", "original test N", "failed rows", "RMSE C/Delta/KGamma", "p99 C/Delta/KGamma", "max C/Delta/KGamma"],
      [[name, row["original_count"], row["failed_rows"], vector(row["rmse"]), vector(row["p99"]), vector(row["max"])]
      for name, row in comparison])
print("Frozen accuracy targets (descriptive, no new adoption decision):", protocol["accuracy"])
table(["expense ID", "category", "charged", "measured seconds", "scope"],
      [[row["id"], row["category"], row["charged"], number(row["seconds"]), row.get("scope", "unknown")]
       for row in record["expenses"]])
print("Pending cold/import/archive/pilot/fresh costs:", pending)
print("cold payback and standard adoption: unknown until complete equal-accuracy measurements and independent review.")
"""

END = """## 読み方と限界

これは保存済み JSON/NPZ の表示です。乱数生成・較正・学習・ネットワークアクセスは実行しません。
数値再検算、教材の表示確認、独立研究受入、標準加速器への採用は別の判断です。

- 条件付き教師は元のゼロ事象を含む全 IID 分母で集計します。予約件数を実際の MC 件数と呼びません。
- 個票の価格・Delta を期待値の上限でクリップしていません。rare-event 未観測は誤差ゼロの証拠ではありません。
- raw NN と安全経路を分けます。満期 ATM の通常 Delta/Gamma は未定義、無効契約は無効のままです。
- Gamma は物理 Gamma の診断であり、Gamma 学習や実市場の 0DTE 較正を主張しません。
- 失敗した学習・非有限値は元の分母に残り、全分母の誤差を unknown と表示します。
- smoke/fixture は配線の検証だけです。速度比較には精度同等性、cold 費用、未測定費用の解消が必要です。

出典はこの保存物の `protocol` と `source_registry`、正式仕様
`2026-10-09-short-maturity-dml-design.md`、計画 `2026-10-09-short-maturity-dml.md` です。
"""


@contextmanager
def _environment(artifacts, source):
    previous = {name: os.environ.get(name) for name in [ARTIFACT_ENV, SOURCE_ENV]}
    os.environ[ARTIFACT_ENV] = str(artifacts)
    os.environ[SOURCE_ENV] = str(source)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def build(artifacts=HERE, output=None, *, source=HERE, execute=False):
    """Create an artifact-only notebook; execute only against supplied evidence."""
    artifacts, source = Path(artifacts).resolve(), Path(source).resolve()
    for path in [
        artifacts / "reference.json",
        artifacts / "reference.npz",
        source / "build_reference.py",
    ]:
        if not path.is_file():
            raise FileNotFoundError(path)
    output = Path(output or artifacts / "short_maturity_dml.ipynb").resolve()
    cells = []
    for identifier, kind, text in [
        (
            "title",
            "markdown",
            "# RB-F05: 短期・同日満期 DML\n\n保存済み証跡から教師・raw NN・強い基準器を比較します。",
        ),
        ("load", "code", LOAD),
        ("teacher", "code", FIGURE_1),
        ("raw", "code", FIGURE_2),
        ("cost", "code", FIGURE_3),
        ("limits", "markdown", END),
    ]:
        factory = nbformat.v4.new_code_cell if kind == "code" else nbformat.v4.new_markdown_cell
        cells.append(factory(text, id="rbf05-short-" + identifier))
    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "rbf05_short": {"artifact_only": True, "figures": 3},
        },
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if execute:
        with _environment(artifacts, source):
            NotebookClient(
                notebook,
                timeout=600,
                kernel_name="python3",
                resources={"metadata": {"path": str(output.parent)}},
            ).execute()
    nbformat.write(notebook, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=HERE)
    parser.add_argument("--source", type=Path, default=HERE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(build(args.artifacts, args.output, source=args.source, execute=args.execute))


if __name__ == "__main__":
    main()
