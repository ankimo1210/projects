"""Draw the three DSINC figures from the saved results of a main run.

Only ``results.json`` and the arrays it points to are read; nothing is solved or re-judged here.
``results.json`` is saved with sorted keys, so no order is taken from a saved dict: the lines and
rows are put in their order here (the ladders of the cost figure, the protocol order of the
sensitivities).

* ``price_error_cost.png``: the largest price difference to the FD reference against the solver
  time, for the spectral levels S0, S1, S2 and the finite-difference x grids (the base grid, then
  481, 961 and 1921 nodes), log-log, price/K.
* ``exercise_boundary.png``: the exercise boundary of the judged spectral level against the FD
  bracket of the dedicated fine-time run, with the masked nodes and the failure counts.
* ``refinement_stability.png``: the difference of every sensitivity, of the next level and of the
  FD reference from a level's base solve, with the limits of the gates.  A check that ran but gave
  no price is a grey cross on the left edge, named with its job status; sensitivities that were
  not run have no marker and are named in the legend only.

Usage: ``python plot.py --results RUN/results.json --output DIR``.
"""

import argparse
import json
import math
import re
import sys
import textwrap
from pathlib import Path

import numpy as np
from hullkit._dsinc_types import BOUNDARY_STATUS, FAILURE_CODES
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, LogLocator, NullLocator

BLUE, ORANGE, GREEN, RED, GRAY = "#1f77b4", "#d95f02", "#1b9e77", "#c0392b", "#555555"
EXPIRY_COLORS = (BLUE, ORANGE)
# Variances the boundary is drawn at: the grid node nearest to each value (the label gives the node).
VARIANCE_COLORS = ((0.01, GREEN), (0.04, BLUE), (0.16, ORANGE))
DISPLAY_FLOOR = 1e-10  # smaller differences are drawn on the left edge of the stability figure
LOG_TICKS = (1.0, 2.0, 3.0, 5.0)  # labelled ticks of a log axis, times each power of ten
NO_PRICE = {"color": GRAY, "ms": 9, "mew": 2}  # the grey cross of a check that gave no price
# The sensitivities in the order of protocol.json (spectral.sensitivities): the rows of the
# stability figure.  A saved results.json lists them alphabetically.
SENSITIVITIES = (
    "crossing_lower", "time_x2", "time_x2_cutoff_x2", "var_next", "points_plus4", "cutoff_x2",
    "chi_0.25", "chi_0.75", "domain_expand", "offset_plus_half", "offset_minus_half",
)  # fmt: skip


def _tick_text(value: float, _position: int | None = None) -> str:
    """A tick value without zero padding of the exponent: 0.5, 20, 2e-6."""
    text = f"{value:g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        text = f"{mantissa}e{int(exponent)}"
    return text


def _label_log_axis(axis) -> None:
    """Label a log axis at 1, 2, 3 and 5 times each power of ten, so that values can be read off."""
    axis.set_major_locator(LogLocator(base=10.0, subs=LOG_TICKS))
    axis.set_minor_locator(NullLocator())
    axis.set_major_formatter(FuncFormatter(_tick_text))


def _new_figure(width: float, height: float) -> Figure:
    """Return an empty figure on the Agg canvas, with room under it for the footnote."""
    figure = Figure(figsize=(width, height), layout="constrained")
    FigureCanvasAgg(figure)
    figure.get_layout_engine().set(rect=(0.0, 0.04, 1.0, 0.96))
    return figure


def _footnote(figure: Figure, verdicts: dict) -> None:
    """Write the job accounting and the reproduction label under the figure."""
    accounting = verdicts["accounting"]
    counts = ", ".join(f"{n} {name}" for name, n in sorted(accounting["status_counts"].items()))
    figure.text(
        0.01,
        0.01,
        f"{accounting['jobs']} jobs ({counts}); reproduction label: {verdicts['reproduction_label']}.",
        fontsize=7.5,
        color=GRAY,
        va="bottom",
    )


def _by_expiry(table: dict) -> list[tuple[str, dict]]:
    """The entries of an expiry-keyed table in ascending order of expiry."""
    return sorted(table.items(), key=lambda item: float(item[0]))


def _solver_seconds(row: dict) -> float:
    """The setup and solve seconds of a cost row (what was not measured counts as zero)."""
    return (row["setup_seconds"] or 0.0) + (row["solve_seconds"] or 0.0)


def _numbered(rows: dict, pattern: str) -> dict:
    """The rows whose name matches ``pattern`` (one group of digits), by ascending number."""
    numbers = {name: int(m.group(1)) for name in rows if (m := re.fullmatch(pattern, name))}
    return {name: rows[name] for name in sorted(numbers, key=numbers.__getitem__)}


def _ladders(costs: dict) -> tuple[dict, dict]:
    """The cost rows of one expiry as two ladders, coarse to fine, in the order a line is drawn.

    The spectral levels come as S0, S1, S2 and the FD x grids as the base grid, then by the number
    of x nodes (481, 961, 1921).  The dicts of a saved ``results.json`` are in key order, which
    would join the x grids as base, 1921, 481, 961.
    """
    base = {name: row for name, row in costs["fd"].items() if name == "independent-base"}
    return (
        _numbered(costs["spectral"], r"S(\d+)"),
        base | _numbered(costs["fd"], r"independent-x(\d+)"),
    )


def _price_error_cost(verdicts: dict, limits: dict) -> Figure:
    """Price error against solver time: the spectral levels and the FD x grids, per expiry."""
    figure = _new_figure(8.4, 5.6)
    ax = figure.subplots()
    marked = False
    for index, (expiry, costs) in enumerate(_by_expiry(verdicts["costs"])):
        color = EXPIRY_COLORS[index % len(EXPIRY_COLORS)]
        levels, x_grids = _ladders(costs)
        for family, rows, marker, line in (
            ("spectral", levels, "o", "-"),
            ("FD x grid", x_grids, "s", "--"),
        ):
            points = [
                (_solver_seconds(row), row["error"], name)
                for name, row in rows.items()
                if row["error"] and _solver_seconds(row) > 0.0  # a log axis cannot show zero
            ]
            if not points:
                continue
            seconds, errors, names = zip(*points, strict=True)
            face = color if family == "spectral" else "white"
            ax.plot(
                seconds,
                errors,
                marker + line,
                color=color,
                mfc=face,
                label=f"{family}, T = {expiry}",
            )
            for x, y, name in points:
                ax.annotate(
                    name.removeprefix("independent-"),
                    (x, y),
                    textcoords="offset points",
                    xytext=(5, 5),
                    fontsize=7.5,
                    color=color,
                )
            adopted = verdicts["selections"][expiry]["adopted"]
            if family == "spectral" and adopted in names:
                at = names.index(adopted)
                ax.plot(
                    [seconds[at]],
                    [errors[at]],
                    "o",
                    ms=15,
                    mfc="none",
                    mec=GREEN,
                    mew=2,
                    label=None if marked else "adopted level",
                )
                marked = True
    for key, label, line in (
        ("independent", "independent limit", "--"),
        ("adjacent", "adjacent and sensitivity limit", ":"),
    ):
        ax.axhline(limits[key], color=GRAY, ls=line, lw=1)
        ax.text(
            0.005,
            limits[key],
            f"{label} {_tick_text(limits[key])}",
            transform=ax.get_yaxis_transform(),
            ha="left",
            va="bottom",
            fontsize=8,
            color=GRAY,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    _label_log_axis(ax.xaxis)
    _label_log_axis(ax.yaxis)
    ax.set_xlabel("solver time, setup + solve [s]")
    ax.set_ylabel("max |price - FD reference| / K   (European, American, EEP)")
    ax.set_title("Price error against cost at S/K = 0.9, 1.0, 1.1")
    ax.grid(True, which="major", alpha=0.25)
    if ax.get_legend_handles_labels()[0]:  # nothing is drawn when no error could be measured
        ax.legend(fontsize=8, loc="best")
    _footnote(figure, verdicts)
    return figure


def _edge_at_variance(edge: np.ndarray, log_var: np.ndarray, point: float) -> np.ndarray:
    """The FD contact edge of every time row at ``point`` (zeta), linear in zeta, NaN if a node is."""
    k = int(np.clip(np.searchsorted(log_var, point, side="right") - 1, 0, log_var.size - 2))
    weight = (point - log_var[k]) / (log_var[k + 1] - log_var[k])
    return edge[:, k] + weight * (edge[:, k + 1] - edge[:, k])


def _status_counts(status: np.ndarray) -> tuple[int, int]:
    """Return the number of multiple-crossing nodes and of root failures in a status array."""
    multiple = int(np.count_nonzero(status == BOUNDARY_STATUS["multiple_crossings"]))
    return multiple, int(np.count_nonzero(np.isin(status, sorted(FAILURE_CODES))))


def _cells(value: float | None, limit: float) -> str:
    """A cell count with its limit, or n/a when nothing was compared."""
    return "n/a" if value is None else f"{value:.2f} cells (limit {limit:g})"


def _boundary_panel(
    ax, expiry: str, entry: dict, adopted: str | None, rules: dict, root: Path
) -> None:
    """Draw one expiry: the spectral boundary, the FD brackets, masked nodes and the failure counts."""
    level = entry["level"]
    if entry["status"] == "unavailable":
        ax.text(
            0.5,
            0.5,
            "boundary gate not run:\n" + "\n".join(entry["reasons"]),
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=8,
        )
        ax.set_title(f"T = {expiry}: {level}")
        return
    with np.load(root / entry["arrays"]["spectral"]) as stored:
        star, spectral_z, status = (
            stored[name] for name in ("log_boundary", "log_variances", "boundary_status")
        )
    with np.load(root / entry["arrays"]["fd_primary"]) as stored:
        edge, fd_z = stored["contact_edge"], stored["log_variances"]
    geometry = entry["geometry"]
    dx, (x_min, x_max) = geometry["fd_dx"], geometry["fd_x_bounds"]
    margin = geometry["edge_cells"] * dx
    n_spec, n_fd = star.shape[0] - 1, edge.shape[0] - 1
    t_spec, t_fd = np.arange(n_spec + 1) / n_spec, np.arange(n_fd + 1) / n_fd
    low, high = geometry["time_window"]
    window = np.flatnonzero((t_spec >= low) & (t_spec <= high))
    common = window[(window * n_fd) % n_spec == 0]  # the rows the gate can compare with the FD
    ax.axvspan(low, high, color="0.93", zorder=0, label="gate window in t / T")
    masked_label = "masked node (geometry_invalid)"
    multiple_label = "multiple crossings (topmost kept)"
    for v, color in VARIANCE_COLORS:
        column = int(np.argmin(np.abs(spectral_z - math.log(v))))
        node = math.exp(float(spectral_z[column]))  # the grid node that is drawn, not v itself
        mine = star[:, column]
        fd_low = _edge_at_variance(edge, fd_z, float(spectral_z[column]))
        ax.fill_between(t_fd, np.exp(fd_low), np.exp(fd_low + dx), color=color, alpha=0.4, lw=0)
        label = f"spectral, v ≈ {node:.4f} (node nearest {v:g})"
        ax.plot(t_spec, np.exp(mine), color=color, lw=1.4, label=label)
        fd_here, own = fd_low[common * n_fd // n_spec], mine[common]
        masked = (
            ~np.isfinite(fd_here)
            | (fd_here - x_min <= margin)
            | (x_max - (fd_here + dx) <= margin)
            | (own - x_min <= margin)
            | (x_max - own <= margin)
        ) & np.isfinite(own)
        if masked.any():
            ax.plot(
                t_spec[common][masked],
                np.exp(own[masked]),
                "x",
                color=RED,
                ms=5,
                mew=1.2,
                label=masked_label,
            )
            masked_label = None
        several = status[window, column] == BOUNDARY_STATUS["multiple_crossings"]
        if several.any():
            ax.plot(
                t_spec[window][several],
                np.exp(mine[window][several]),
                "^",
                color=color,
                mec="black",
                ms=5,
                label=multiple_label,
            )
            multiple_label = None
    ax.fill_between([], [], [], color=GRAY, alpha=0.4, lw=0, label="FD bracket [edge, edge + dx]")
    variances = np.exp(spectral_z)
    inside = np.flatnonzero(
        (variances >= geometry["variance_window"][0])
        & (variances <= geometry["variance_window"][1])
    )
    in_window, whole = _status_counts(status[np.ix_(window, inside)]), _status_counts(status)
    lines = [
        f"gate: {entry['status']};  coverage {100 * entry['coverage']:.1f}% ({entry['valid']} of "
        f"{entry['targets']} nodes, minimum {100 * rules['coverage']:.0f}%)",
        f"max deviation {_cells(entry['max_deviation_cells'], rules['max_cells'])};  "
        f"FD step shift {_cells(entry['fd_shift_cells'], rules['fd_shift_cells'])}",
        f"in the window: {in_window[0]} multiple crossings, {in_window[1]} root failures;  "
        f"whole grid: {whole[0]} and {whole[1]}",
    ]
    if entry["reasons"]:
        lines.append(textwrap.fill("reasons: " + ", ".join(entry["reasons"]), 78))
    ax.text(
        0.98,
        0.02,
        "\n".join(lines),
        transform=ax.transAxes,
        fontsize=7.5,
        va="bottom",
        ha="right",
        bbox={"boxstyle": "round", "fc": "white", "ec": "0.7", "alpha": 0.92},
    )
    ax.set_xlabel("t / T")
    ax.set_ylabel("exercise boundary S* / K")
    shown = "adopted" if adopted == level else "not adopted"
    ax.set_title(f"T = {expiry}: {level} ({shown}) against the fine-time FD")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7.5, loc="upper left", framealpha=0.92)


def _exercise_boundary(verdicts: dict, rules: dict, root: Path) -> Figure:
    """The exercise boundary of the judged level against the FD bracket, one panel per expiry."""
    expiries = _by_expiry(verdicts["boundary"])
    figure = _new_figure(7.0 * len(expiries), 5.8)
    axes = figure.subplots(1, len(expiries), squeeze=False)[0]
    for ax, (expiry, entry) in zip(axes, expiries, strict=True):
        adopted = verdicts["selections"][expiry]["adopted"]
        _boundary_panel(ax, expiry, entry, adopted, rules, root)
    _footnote(figure, verdicts)
    return figure


def _refinement_stability(verdicts: dict, limits: dict) -> Figure:
    """The difference of every sensitivity, of the next level and of the reference, with the limits."""
    expiries = _by_expiry(verdicts["selections"])
    checks = [check for _, selection in expiries for check in selection["checks"].values()]
    present = {name for check in checks for name in check["sensitivities"] or {}}
    names = [name for name in SENSITIVITIES if name in present]
    names += sorted(present - set(names))  # a sensitivity the protocol does not list goes last
    rows = [(name, "sensitivity") for name in names]
    rows += [("next level (adjacent)", "adjacent"), ("FD reference (independent)", "independent")]
    figure = _new_figure(6.6 * len(expiries), 6.0)
    axes = figure.subplots(1, len(expiries), squeeze=False)[0]
    values = [
        value
        for check in checks
        for value in (
            check["adjacent"],
            check["independent"],
            *(check["sensitivities"] or {}).values(),
        )
        if value is not None
    ]
    right = max([1e-4, *(3 * value for value in values)])
    statuses = {  # why a job that ran gave no price, by job id
        entry["job_id"]: entry["status"] for entry in verdicts["accounting"].get("not_ok", [])
    }
    for ax, (expiry, selection) in zip(axes, expiries, strict=True):
        for position, (_, kind) in enumerate(rows):  # one dashed line over the rows of a limit
            ax.plot(
                [limits[kind]] * 2,
                [position - 0.5, position + 0.5],
                color=GRAY,
                ls="--",
                lw=1,
                label="limit of the row" if position == 0 else None,
            )
        failed: dict[str, None] = {}  # why a check has no price, in order of appearance
        for level, marker, color, shift in (("S0", "o", BLUE, -0.12), ("S1", "s", ORANGE, 0.12)):
            check = selection["checks"][level]
            found = (check["sensitivities"] or {}) | {
                "next level (adjacent)": check["adjacent"],
                "FD reference (independent)": check["independent"],
            }
            ax.plot([], [], marker, color=color, label=f"{level} base solve")
            if not check["sensitivities"]:  # not run: nothing is drawn, only the legend says so
                ax.plot([], [], " ", label=f"{level} sensitivities not run")
            for position, (name, kind) in enumerate(rows):
                if name not in found:
                    continue
                value = found[name]
                if value is None:  # it ran but gave no price: a grey cross on the left edge
                    status = statuses.get(f"spectral-{level}-{name}-T{expiry}")
                    failed[f"no price ({status})" if status else "no value"] = None
                    ax.plot([DISPLAY_FLOOR], [position + shift], "x", clip_on=False, **NO_PRICE)
                    continue
                x, y = max(value, DISPLAY_FLOOR), position + shift
                ax.plot(
                    [x],
                    [y],
                    marker,
                    color=color,
                    ms=7,
                    clip_on=False,
                    mfc=color if value > DISPLAY_FLOOR else "white",
                )
                if value > limits[kind]:
                    ax.plot([x], [y], "o", mfc="none", mec=RED, ms=13, mew=1.5, clip_on=False)
        ax.plot([], [], "o", mfc="none", mec=RED, ms=10, mew=1.5, label="above its limit")
        ax.plot([], [], "o", mfc="white", mec=GRAY, label=f"at most {DISPLAY_FLOOR:g}, on the edge")
        for text in failed:
            ax.plot([], [], "x", label=text, **NO_PRICE)
        ax.set_xscale("log")
        ax.set_xlim(DISPLAY_FLOOR, right)
        ax.set_ylim(len(rows) + 2.0, -0.5)  # the empty rows below hold the legend
        ax.set_yticks(range(len(rows)), [name for name, _ in rows], fontsize=8)
        ax.set_xlabel("max |difference| / K")
        if selection["adopted"]:
            ax.set_title(f"T = {expiry}: adopted {selection['adopted']}")
        else:
            ax.set_title(f"T = {expiry}: none adopted ({selection['status']})")
        ax.grid(True, axis="x", which="both", alpha=0.25)
        ax.legend(fontsize=7.5, loc="lower left", ncol=2, framealpha=0.92)
    _footnote(figure, verdicts)
    return figure


def draw(results_path: Path, out_dir: Path) -> list[Path]:
    """Draw the three figures of a main run into ``out_dir`` and return their paths.

    ``results_path`` is the ``results.json`` of the run; the arrays it points to are read from the
    same directory.  The files are ``price_error_cost.png``, ``exercise_boundary.png`` and
    ``refinement_stability.png``.  ValueError unless the results are those of a main run.
    """
    results_path = Path(results_path)
    results = json.loads(results_path.read_text())
    if results["phase"] != "main":
        raise ValueError(
            f"the figures need a main run, these results are of phase {results['phase']!r}"
        )
    verdicts, limits = results["verdicts"], results["thresholds"]
    figures = {
        "price_error_cost.png": _price_error_cost(verdicts, limits),
        "exercise_boundary.png": _exercise_boundary(
            verdicts, limits["boundary"], results_path.parent
        ),
        "refinement_stability.png": _refinement_stability(verdicts, limits),
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, figure in figures.items():
        figure.savefig(out_dir / name, dpi=150)
        paths.append(out_dir / name)
    return paths


FAILED_SENSITIVITIES = ("crossing_lower", "time_x2")  # the S1 variants without a price at T = 1
COSTS = (("S0", 3.9e-6, 3.8, 1.2), ("S1", 4.4e-6, 11.1, 6.7), ("S2", 4.9e-6, 29.8, 22.4))  # fmt: skip
X_GRIDS = (("base", 8.0e-5, 0.2, 0.5), ("x481", 2.5e-5, 0.6, 1.4), ("x961", 7.0e-6, 1.4, 3.0), ("x1921", 1.5e-6, 3.1, 5.6))  # fmt: skip


def _synthetic_boundary(tmp: Path, expiry: float, multiple: int) -> dict:
    """Write the arrays of a made-up boundary at ``expiry`` and return its gate entry."""
    spectral_z = np.linspace(math.log(2e-4), math.log(2.0), 160)
    fd_z = np.linspace(math.log(1e-5), math.log(8.0), 101)
    dx, n_spec, n_fd = 0.0025, int(200 * expiry), int(1200 * expiry)
    left_spec, left_fd = 1.0 - np.arange(n_spec + 1) / n_spec, 1.0 - np.arange(n_fd + 1) / n_fd
    star = -1.3 * np.sqrt(expiry * np.outer(left_spec, np.exp(spectral_z)))
    edge = np.floor(-1.3 * np.sqrt(expiry * np.outer(left_fd, np.exp(fd_z))) / dx) * dx
    edge[-1] = np.nan  # no contact at maturity
    edge[int(0.1 * n_fd) : int(0.35 * n_fd), np.searchsorted(fd_z, math.log(0.01))] = np.nan
    status = np.zeros(star.shape, dtype=np.int8)
    status[-1], status[:, 0] = BOUNDARY_STATUS["terminal"], BOUNDARY_STATUS["maxiter"]
    column, first = int(np.argmin(np.abs(spectral_z - math.log(0.16)))), n_spec // 2
    status[first : first + multiple, column] = BOUNDARY_STATUS["multiple_crossings"]
    paths = {
        "spectral": f"arrays/synthetic-spectral-T{expiry}.npz",
        "fd_primary": f"arrays/synthetic-fd-T{expiry}.npz",
    }
    np.savez_compressed(
        tmp / paths["spectral"], log_boundary=star, log_variances=spectral_z, boundary_status=status
    )
    np.savez_compressed(tmp / paths["fd_primary"], contact_edge=edge, log_variances=fd_z)
    return {
        "status": "fail" if multiple else "pass",
        "level": "S0",
        "coverage": 0.97,
        "valid": 3770,
        "targets": 3888,
        "max_deviation_cells": 1.03,
        "fd_shift_cells": 1.0,
        "multiple_in_window": multiple,
        "reasons": [*(["multiple_crossings_in_window"] if multiple else []), "geometry_invalid"],
        "geometry": {
            "fd_dx": dx,
            "fd_x_bounds": [-1.2, 1.2],
            "edge_cells": 4,
            "time_window": [0.1, 0.9],
            "variance_window": [0.01, 0.16],
        },
        "arrays": paths,
    }


def synthetic_results(tmp: Path) -> Path:
    """Write a minimal main ``results.json`` and its arrays under ``tmp`` and return its path.

    The numbers are made up (a square-root boundary, a few differences and times): they exercise
    the figure code, with masked nodes, multiple crossings, a sensitivity above its limit, two S1
    variants that gave no price and S1 sensitivities that were not run, and say nothing about a
    real run.
    """
    tmp = Path(tmp)
    (tmp / "arrays").mkdir(parents=True, exist_ok=True)
    verdicts: dict = {"selections": {}, "costs": {}, "boundary": {}}
    for scale, expiry in enumerate((0.5, 1.0), start=1):
        sensitivities = {name: 1e-6 * scale * (i % 4 + 0.5) for i, name in enumerate(SENSITIVITIES)}
        sensitivities |= {"crossing_lower": 0.0, "chi_0.75": 3e-6 * scale * scale}
        adopted = "S0" if scale == 1 else None
        key = str(expiry)
        s1_sensitivities = None  # the S1 variants run only where S0 does not pass
        if scale == 2:
            s1_sensitivities = {n: 2e-6 * (i % 3 + 0.5) for i, n in enumerate(SENSITIVITIES)}
            s1_sensitivities |= dict.fromkeys(FAILED_SENSITIVITIES)
        s0 = {
            "adjacent": 1.6e-6 * scale,
            "independent": 3.9e-6 * scale,
            "sensitivity": max(sensitivities.values()),
            "sensitivities": sensitivities,
            "passed": scale == 1,
            "pending": False,
        }
        s1 = {
            "adjacent": 6.0e-7,
            "independent": 4.4e-6,
            "sensitivity": None,
            "sensitivities": s1_sensitivities,
            "passed": False,
            "pending": scale == 1,
        }
        verdicts["selections"][key] = {
            "adopted": adopted,
            "status": "adopted" if adopted else "not_achieved",
            "checks": {"S0": s0, "S1": s1},
        }
        verdicts["costs"][key] = {
            "spectral": {
                level: {
                    "error": error,
                    "setup_seconds": scale * setup,
                    "solve_seconds": scale * solve,
                }
                for level, error, setup, solve in COSTS
            },
            "fd": {
                f"independent-{name}": {
                    "error": error * scale,
                    "setup_seconds": setup,
                    "solve_seconds": solve,
                }
                for name, error, setup, solve in X_GRIDS
            },
            "timing": {},
        }
        verdicts["boundary"][key] = _synthetic_boundary(tmp, expiry, 3 * (scale - 1))
    verdicts |= {
        "accounting": {
            "jobs": 88,
            "status_counts": {"ok": 58, "not_run_condition": 28, "pricing_failure": 2},
            "not_ok": [
                {
                    "job_id": f"spectral-S1-{name}-T1.0",
                    "reason": "made up",
                    "status": "pricing_failure",
                }
                for name in FAILED_SENSITIVITIES
            ],
        },
        "reproduction_label": "synthetic",
    }
    results = {
        "schema": "DSINC-results-v1",
        "phase": "main",
        "thresholds": {
            "adjacent": 5e-6,
            "sensitivity": 5e-6,
            "independent": 2e-5,
            "boundary": {"coverage": 0.9, "max_cells": 2.0, "fd_shift_cells": 1.0},
        },
        "verdicts": verdicts,
    }
    path = tmp / "results.json"
    path.write_text(json.dumps(results))
    return path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: ``--results FILE --output DIR``."""
    parser = argparse.ArgumentParser(prog="plot.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--results", type=Path, required=True, help="results.json of a main run")
    parser.add_argument("--output", type=Path, required=True, help="directory for the PNG files")
    arguments = parser.parse_args(argv)
    try:
        paths = draw(arguments.results, arguments.output)
    except ValueError as error:
        print(f"plot.py: {error}", file=sys.stderr)
        return 2
    print("\n".join(str(path) for path in paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
