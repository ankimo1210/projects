"""Decision rules of the DSINC American-put reproduction.

Pure functions on stored results: the runner keeps every solver record, calls these on them and the
freeze fixes the thresholds they receive.  Nothing here reads a file, the clock or a global that
changes, and nothing clips, repairs or substitutes a value.  A result that is missing (None) or
non-finite fails the check it enters (``select_level``, ``paper_match``) and a root that failed
fails the boundary gate; arguments that cannot be interpreted (wrong shapes, a non-finite price or
ladder array where one is required) raise ValueError.  Prices are per unit strike (price/K) and
spots are S/K.

* Finite-difference reference (design 5/6, deviation D-3): ``order_from_levels`` fits the observed
  order on the actual step sizes, ``axis_convergence`` judges one refinement axis,
  ``fd_reference`` adds the finest-level correction of every axis to the base grid and
  ``reference_verdict`` demands every axis and the domain test.
* Level choice (``select_level``): the coarse side of the first S0/S1 pair that passes the
  adjacent, independent and sensitivity checks; S2 is only a neighbour.
* Boundary (``boundary_gate``, deviations D-1 and D-4), bounds, the paper's printed values, cost
  estimates, the reproduction label and the central-difference Delta.
"""

import math
from itertools import pairwise

import numpy as np
from hullkit._dsinc_types import BOUNDARY_STATUS
from scipy.optimize import brentq

LEVELS = ("S0", "S1", "S2")  # coarse to fine; S0 and S1 are the candidates, S2 only checks S1
QUANTITIES = ("european", "american", "eep")  # every level, reference and sensitivity carries these
ORDER_BRACKET = (0.25, 8.0)  # the orders order_from_levels searches
FD_SHIFT_SLACK = 1e-9  # cells; the FD time-step check fails above fd_shift_cells + this
ROOT_FOUND = (
    BOUNDARY_STATUS["single"],
    BOUNDARY_STATUS["multiple_crossings"],
    BOUNDARY_STATUS["terminal"],
)


def _floats(name: str, value: object, ndim: int, *, finite: bool = True) -> np.ndarray:
    """Return ``value`` as a float array with ``ndim`` dimensions, finite unless ``finite`` is off."""
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a numeric array, got {value!r}") from None
    if array.ndim != ndim:
        raise ValueError(f"{name} must have {ndim} dimension(s), got shape {array.shape}")
    if finite and not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite")
    return array


def _positive(name: str, value: object) -> float:
    """Return ``value`` as a finite float > 0."""
    number = _floats(name, value, 0)
    if not number > 0.0:
        raise ValueError(f"{name} must be > 0, got {value!r}")
    return float(number)


def order_from_levels(h: np.ndarray, values: np.ndarray) -> float | None:
    """Observed convergence order p of three levels, fitted on their actual step sizes.

    With v_i = v + C h_i^p the differences satisfy (h1^p - h2^p)/(h2^p - h3^p) = d12/d23 where
    d12 = v1 - v2 and d23 = v2 - v3.  ``h`` are the three step sizes, positive and strictly
    decreasing, and ``values`` the three values of one quantity.  The ratio is solved for p in
    [0.25, 8] with ``brentq``; the left side increases strictly with p, so the root is unique.
    Returns None when the ratio is not positive (a difference vanishes or the sign flips) or no p in
    the bracket fits.
    """
    steps = _floats("h", h, 1)
    levels = _floats("values", values, 1)
    if steps.size != 3 or levels.size != 3:
        raise ValueError(
            f"three levels are needed, got {steps.size} step sizes and {levels.size} values"
        )
    if not steps[0] > steps[1] > steps[2] > 0.0:
        raise ValueError(f"h must be positive and strictly decreasing, got {h!r}")
    d12, d23 = levels[0] - levels[1], levels[1] - levels[2]
    if d12 == 0.0 or d23 == 0.0 or (d12 > 0.0) != (d23 > 0.0):
        return None
    ratio = d12 / d23
    up, down = math.log(steps[0] / steps[1]), math.log(steps[2] / steps[1])

    def gap(p: float) -> float:
        """(h1^p - h2^p)/(h2^p - h3^p) - ratio, written with expm1 so small p stays accurate."""
        return math.expm1(p * up) / -math.expm1(p * down) - ratio

    low, high = ORDER_BRACKET
    at_low, at_high = gap(low), gap(high)
    if (at_low > 0.0 and at_high > 0.0) or (at_low < 0.0 and at_high < 0.0):
        return None
    return float(brentq(gap, low, high))


def axis_convergence(h: np.ndarray, values: np.ndarray, thresholds: dict) -> dict:
    """Judge one refinement axis of the independent FD reference (deviation D-3).

    ``values`` is (n_levels, n_quantities), coarse to fine, and ``h`` the actual step size of each
    level (strictly decreasing); at least three levels are needed.  ``final_change`` is
    max|v[-1] - v[-2]| over the quantities and ``previous_change`` max|v[-2] - v[-3]|.  The status is

    * ``final_change_too_large`` if final_change > reference_final_change;
    * ``below_resolution`` (converged) if final_change <= reference_resolution;
    * otherwise, for every quantity whose last change exceeds the resolution, the last change must
      be smaller than the previous one (else ``not_contracting``) and the order fitted on the last
      three levels must lie in reference_order_range (else ``order_out_of_range``; an order that
      cannot be fitted is out of range); everything satisfied is ``converged``.

    Returns ``{status, converged, final_change, previous_change, orders}`` where ``orders`` holds,
    per quantity, the order of the last three levels (None when none fits).
    """
    steps = _floats("h", h, 1)
    ladder = _floats("values", values, 2)
    if ladder.size == 0 or steps.size < 3 or ladder.shape[0] != steps.size:
        raise ValueError(
            f"need >= 3 levels and one step size each, got h {steps.shape} and values {ladder.shape}"
        )
    if not (steps[0] > 0.0 and np.all(np.diff(steps) < 0.0)):
        raise ValueError(f"h must be positive and strictly decreasing, got {h!r}")
    tol = thresholds["reference_final_change"]
    resolution = thresholds["reference_resolution"]
    low, high = thresholds["reference_order_range"]
    last = np.abs(ladder[-1] - ladder[-2])
    before = np.abs(ladder[-2] - ladder[-3])
    orders = [order_from_levels(steps[-3:], ladder[-3:, j]) for j in range(ladder.shape[1])]
    final_change = float(last.max())
    if final_change > tol:
        status = "final_change_too_large"
    elif final_change <= resolution:
        status = "below_resolution"
    else:
        active = last > resolution
        if not np.all(last[active] < before[active]):
            status = "not_contracting"
        elif not all(
            order is not None and low <= order <= high
            for order, judged in zip(orders, active, strict=True)
            if judged
        ):
            status = "order_out_of_range"
        else:
            status = "converged"
    return {
        "status": status,
        "converged": status in ("converged", "below_resolution"),
        "final_change": final_change,
        "previous_change": float(before.max()),
        "orders": orders,
    }


def fd_reference(base: np.ndarray, finest: dict[str, np.ndarray]) -> np.ndarray:
    """Reference value P_B + sum over the axes of (P_axis - P_B) (deviation D-3).

    ``base`` is the price of the base grid and ``finest`` maps each refinement axis to the price at
    its finest level with the other axes at the base grid.  The arrays share one shape; the result
    is a new array of that shape.
    """
    anchor = _floats("base", base, np.ndim(base))
    if not finest:
        raise ValueError("finest must name at least one axis")
    correction = np.zeros_like(anchor)
    for axis, value in finest.items():
        array = _floats(f"finest[{axis!r}]", value, anchor.ndim)
        if array.shape != anchor.shape:
            raise ValueError(f"finest[{axis!r}] has shape {array.shape}, base has {anchor.shape}")
        correction += array - anchor
    return anchor + correction


def reference_verdict(axes: dict[str, dict], domain_change: float, thresholds: dict) -> dict:
    """The reference is converged only if every axis converged and the domain change is small.

    ``axes`` maps each axis to its ``axis_convergence`` result and ``domain_change`` is the largest
    |price change| when the x domain is widened at fixed step.  Returns ``{converged, reasons}``;
    each reason is ``<axis>:<status>`` or a domain-change code, and ``domain_change`` must be finite
    and at most reference_final_change.
    """
    if not axes:
        raise ValueError("axes must name at least one refinement axis")
    reasons = [
        f"{axis}:{result.get('status', 'not_converged')}"
        for axis, result in axes.items()
        if not result["converged"]
    ]
    if not math.isfinite(domain_change):
        reasons.append("domain_change_not_finite")
    elif abs(domain_change) > thresholds["reference_final_change"]:
        reasons.append("domain_change_too_large")
    return {"converged": not reasons, "reasons": reasons}


def _largest_difference(first: dict | None, second: dict | None) -> float | None:
    """Largest |first - second| over all spots and the three quantities, or None without a valid pair.

    None (a missing result) and non-finite values give None, which every check treats as failed.
    """
    if first is None or second is None:
        return None
    worst = 0.0
    for quantity in QUANTITIES:
        a = np.asarray(first[quantity], dtype=float)
        b = np.asarray(second[quantity], dtype=float)
        if a.shape != b.shape:
            raise ValueError(f"{quantity} shapes differ: {a.shape} and {b.shape}")
        gap = np.abs(a - b)
        if not np.all(np.isfinite(gap)):
            return None
        worst = max(worst, float(gap.max()))
    return worst


def select_level(
    levels: dict[str, dict[str, np.ndarray]],
    reference: dict[str, np.ndarray],
    sensitivities: dict[str, dict[str, dict[str, np.ndarray]] | None],
    thresholds: dict,
) -> dict:
    """Adopt the coarse side of the first passing S0/S1 pair (S2 is only a neighbour).

    ``levels`` maps S0, S1, S2 to {european, american, eep} -> prices at the spots; ``reference``
    has the same quantities; ``sensitivities[level]`` maps each sensitivity name to the prices of
    that variant of the level (None for a variant that produced no prices), or is None (or empty)
    when the level's sensitivities were not run.  Candidates are judged in the order S0, S1, each
    against the next level.  A candidate passes when, over every spot and quantity, the largest
    |level - next level| is <= ``adjacent``, the largest |level - reference| is <= ``independent``
    and the largest |variant - level| of every sensitivity is <= ``sensitivity``.  A missing result
    (None, or a non-finite price) fails the check it enters.  The first passing candidate is
    adopted.  Otherwise the status is ``not_achieved_budget`` if some candidate passed the adjacent
    and independent checks but its sensitivities were not run, else ``not_achieved``.

    Returns ``{adopted, status, checks}``; ``checks[level]`` holds ``adjacent``, ``independent`` and
    ``sensitivity`` (the largest differences, None if unavailable), the per-variant
    ``sensitivities`` (None if not run), ``passed`` and ``pending`` (adjacent and independent
    passed, sensitivities not run).
    """
    checks: dict[str, dict] = {}
    adopted = None
    for name, partner in pairwise(LEVELS):
        own = levels.get(name)
        adjacent = _largest_difference(own, levels.get(partner))
        independent = _largest_difference(own, reference)
        variants = sensitivities.get(name)
        if variants:
            per_variant = {
                key: _largest_difference(prices, own) for key, prices in variants.items()
            }
            known = list(per_variant.values())
            sensitivity = None if None in known else max(known)
        else:
            per_variant, sensitivity = None, None
        near = adjacent is not None and adjacent <= thresholds["adjacent"]
        close = independent is not None and independent <= thresholds["independent"]
        calm = sensitivity is not None and sensitivity <= thresholds["sensitivity"]
        checks[name] = {
            "adjacent": adjacent,
            "independent": independent,
            "sensitivity": sensitivity,
            "sensitivities": per_variant,
            "passed": bool(near and close and calm),
            "pending": bool(near and close and per_variant is None),
        }
        if adopted is None and checks[name]["passed"]:
            adopted = name
    if adopted is not None:
        status = "adopted"
    elif any(check["pending"] for check in checks.values()):
        status = "not_achieved_budget"
    else:
        status = "not_achieved"
    return {"adopted": adopted, "status": status, "checks": checks}


def _inside(values: np.ndarray, window: list[float]) -> np.ndarray:
    """Boolean mask of the entries of ``values`` in the closed interval ``window``."""
    low, high = window
    return (values >= low) & (values <= high)


def _edge_at(rows: np.ndarray, grid: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Linear interpolation of each row of ``rows`` (defined on ascending ``grid``) at ``points``.

    NaN where a neighbouring grid value is NaN or the point lies outside the grid; nothing is
    extrapolated.
    """
    k = np.clip(np.searchsorted(grid, points, side="right") - 1, 0, grid.size - 2)
    weight = (points - grid[k]) / (grid[k + 1] - grid[k])
    edge = rows[:, k] + weight * (rows[:, k + 1] - rows[:, k])
    edge[:, (points < grid[0]) | (points > grid[-1])] = np.nan
    return edge


def _fd_shift(
    primary: np.ndarray, check: np.ndarray, fd_z: np.ndarray, dx: float, thresholds: dict
) -> tuple[float | None, bool]:
    """Largest contact-edge shift, in cells, between the primary FD and the check FD in the window.

    The check has half the time steps, so it is compared with the even steps of the primary at the
    check's steps with t/T in the time window and the FD zeta nodes with v in the variance window.
    Returns ``(shift or None, confirmed)``: not confirmed if a node has contact in only one of the
    two or nothing could be compared.
    """
    n_check = check.shape[0] - 1
    rows = np.flatnonzero(_inside(np.arange(n_check + 1) / n_check, thresholds["time_window"]))
    cols = np.flatnonzero(_inside(np.exp(fd_z), thresholds["variance_window"]))
    a = primary[::2][np.ix_(rows, cols)]
    b = check[np.ix_(rows, cols)]
    finite_a, finite_b = np.isfinite(a), np.isfinite(b)
    both = finite_a & finite_b
    if not both.any():
        return None, False
    shift = float(np.abs(a - b)[both].max()) / dx
    return shift, not np.any(finite_a != finite_b)


def boundary_gate(
    *,
    spectral_log_var: np.ndarray,
    spectral_boundary: np.ndarray,
    spectral_status: np.ndarray,
    fd_log_var: np.ndarray,
    fd_primary: np.ndarray,
    fd_check: np.ndarray,
    fd_dx: float,
    fd_x_bounds: tuple[float, float],
    thresholds: dict,
    max_root_residual: float | None = None,
) -> dict:
    """Compare the spectral exercise boundary with the dedicated fine-time FD (deviations D-1, D-4).

    ``spectral_boundary`` and ``spectral_status`` are (N_spec + 1, n_var) by calendar row n
    (t = n T/N_spec) on ``spectral_log_var``; ``fd_primary`` is (N_fd + 1, n_var_fd) with the
    largest contact x per zeta row (NaN without contact) by calendar row k (t = k T/N_fd) on
    ``fd_log_var``; ``fd_check`` has half the time steps of ``fd_primary``.  ``thresholds`` is the
    protocol's boundary block.

    The targets are the spectral nodes with t/T in ``time_window`` and v in ``variance_window`` at
    the common times, where n N_fd is divisible by N_spec.  The FD edge is interpolated linearly in
    zeta onto the node and the bracket is [edge, edge + dx].  A target whose edge is NaN, or whose
    bracket or spectral boundary lies within ``edge_cells`` cells of an x end, is masked as
    ``geometry_invalid``; the deviation of the others is max(0, lo - x*, x* - hi) in cells of dx.

    ``fail`` if any spectral node in the window has status multiple_crossings (D-1), or no root
    (any status but single, multiple_crossings, terminal, or a non-finite x*; the solver records
    maxiter when a root misses |R| <= root_residual_tol, and masks never hide it), or, when
    ``max_root_residual`` (the largest |R| at the roots, as the spectral solve's diagnostics record
    it) is given, a value that is not finite or above ``root_residual`` (reason
    ``root_residual_exceeds_limit``; None leaves this criterion off), or a deviation above
    ``max_cells`` cells, or the FD is not confirmed: the largest edge shift against ``fd_check``
    exceeds ``fd_shift_cells`` (plus 1e-9) or a node has contact in only one grid.  Otherwise
    ``unsupported`` if there is no target or the valid share of the targets is below ``coverage``,
    else ``pass``.

    Returns ``{status, coverage, valid, targets, max_deviation_cells, fd_shift_cells,
    multiple_in_window, reasons}``; the two cell values are None when nothing was compared.
    """
    spec_z = _floats("spectral_log_var", spectral_log_var, 1)
    fd_z = _floats("fd_log_var", fd_log_var, 1)
    x_star = _floats("spectral_boundary", spectral_boundary, 2, finite=False)
    status = np.asarray(spectral_status)
    primary = _floats("fd_primary", fd_primary, 2, finite=False)
    check = _floats("fd_check", fd_check, 2, finite=False)
    dx = _positive("fd_dx", fd_dx)
    x_min, x_max = (float(bound) for bound in fd_x_bounds)
    n_spec, n_fd = x_star.shape[0] - 1, primary.shape[0] - 1
    if status.shape != x_star.shape or x_star.shape[1] != spec_z.size:
        raise ValueError("spectral boundary, status and log-variance grid must agree in shape")
    if primary.shape[1] != fd_z.size or check.shape[1] != fd_z.size or fd_z.size < 2:
        raise ValueError("FD edges and a FD log-variance grid of >= 2 nodes must agree in shape")
    if n_spec < 1 or n_fd < 2 or n_fd % 2 or check.shape[0] - 1 != n_fd // 2:
        raise ValueError(
            "need N_spec >= 1 and a check FD with half the time steps of an even primary"
        )
    if not (np.all(np.diff(spec_z) > 0.0) and np.all(np.diff(fd_z) > 0.0)):
        raise ValueError("log-variance grids must be strictly ascending")

    rows = np.flatnonzero(_inside(np.arange(n_spec + 1) / n_spec, thresholds["time_window"]))
    cols = np.flatnonzero(_inside(np.exp(spec_z), thresholds["variance_window"]))
    window = np.ix_(rows, cols)
    multiple_in_window = int(
        np.count_nonzero(status[window] == BOUNDARY_STATUS["multiple_crossings"])
    )
    root_failures = int(
        np.count_nonzero(~np.isin(status[window], ROOT_FOUND) | ~np.isfinite(x_star[window]))
    )

    common = rows[(rows * n_fd) % n_spec == 0]
    targets = common.size * cols.size
    valid, masked, max_deviation = 0, False, None
    if targets:
        edge = _edge_at(primary[common * n_fd // n_spec], fd_z, spec_z[cols])
        star = x_star[np.ix_(common, cols)]
        margin = thresholds["edge_cells"] * dx
        geometry_invalid = (
            ~np.isfinite(edge)
            | (edge - x_min <= margin)
            | (x_max - (edge + dx) <= margin)
            | (star - x_min <= margin)
            | (x_max - star <= margin)
        )
        usable = ~geometry_invalid & np.isfinite(star)
        masked, valid = bool(geometry_invalid.any()), int(np.count_nonzero(usable))
        if valid:
            outside = np.maximum(0.0, np.maximum(edge - star, star - (edge + dx)))
            max_deviation = float(outside[usable].max()) / dx
    coverage = valid / targets if targets else 0.0
    thin = targets == 0 or coverage < thresholds["coverage"]
    fd_shift, confirmed = _fd_shift(primary, check, fd_z, dx, thresholds)

    failures = []
    if multiple_in_window:
        failures.append("multiple_crossings_in_window")
    if root_failures:
        failures.append("root_failure_in_window")
    if max_root_residual is not None:
        residual = float(_floats("max_root_residual", max_root_residual, 0, finite=False))
        if not (math.isfinite(residual) and residual <= thresholds["root_residual"]):
            failures.append("root_residual_exceeds_limit")
    if max_deviation is not None and max_deviation > thresholds["max_cells"]:
        failures.append("deviation_exceeds_limit")
    if fd_shift is not None and fd_shift > thresholds["fd_shift_cells"] + FD_SHIFT_SLACK:
        failures.append("fd_shift_exceeds_limit")
    if not confirmed:
        failures.append("fd_unconfirmed")
    reasons = list(failures)
    if masked:
        reasons.append("geometry_invalid")
    if targets == 0:
        reasons.append("no_targets")
    elif thin:
        reasons.append("coverage_below_minimum")
    verdict = "fail" if failures else "unsupported" if thin else "pass"
    return {
        "status": verdict,
        "coverage": float(coverage),
        "valid": valid,
        "targets": int(targets),
        "max_deviation_cells": max_deviation,
        "fd_shift_cells": fd_shift,
        "multiple_in_window": multiple_in_window,
        "reasons": reasons,
    }


def bounds_check(
    european: np.ndarray, american: np.ndarray, spots: np.ndarray, contract: dict, tol: float
) -> dict:
    """Raw no-arbitrage margins of European and American put prices, per unit strike.

    ``spots`` is S/K, the prices are price/K and ``contract`` carries domestic_rate, foreign_rate
    and expiry.  Three margins must not fall below -``tol``: American - European, American - payoff
    (max(1 - S/K, 0)) and European - lower, where the European lower bound is
    max(e^{-rd T} - S e^{-rf T}, 0); two must not exceed ``tol``: American - 1 (the strike bound)
    and European - e^{-rd T}.  The violating extreme of each is reported raw
    (``american_minus_european_min``, ``american_minus_payoff_min``, ``european_minus_lower_min``,
    ``american_minus_strike_max``, ``european_minus_upper_max``) with the spot where it occurs (the
    same key plus ``_spot``).  ``pass`` is True when none violates by more than ``tol``.
    """
    eu = _floats("european", european, 1)
    am = _floats("american", american, 1)
    s = _floats("spots", spots, 1)
    if not eu.shape == am.shape == s.shape:
        raise ValueError(
            f"european {eu.shape}, american {am.shape} and spots {s.shape} must share a shape"
        )
    slack = float(_floats("tol", tol, 0))
    if slack < 0.0:
        raise ValueError(f"tol must be >= 0, got {tol!r}")
    discount = math.exp(-contract["domestic_rate"] * contract["expiry"])
    carry = math.exp(-contract["foreign_rate"] * contract["expiry"])
    floors = {
        "american_minus_european_min": am - eu,
        "american_minus_payoff_min": am - np.maximum(1.0 - s, 0.0),
        "european_minus_lower_min": eu - np.maximum(discount - s * carry, 0.0),
    }
    ceilings = {"american_minus_strike_max": am - 1.0, "european_minus_upper_max": eu - discount}
    report: dict = {}
    passed = True
    for key, margin in floors.items():
        at = int(np.argmin(margin))
        report[key], report[f"{key}_spot"] = float(margin[at]), float(s[at])
        passed = passed and bool(margin[at] >= -slack)
    for key, margin in ceilings.items():
        at = int(np.argmax(margin))
        report[key], report[f"{key}_spot"] = float(margin[at]), float(s[at])
        passed = passed and bool(margin[at] <= slack)
    return {"pass": passed} | report


def paper_match(values: dict, anchors: dict, tol: float) -> dict:
    """Compare the spectral values with the printed ones: |value - printed| <= tol, no relaxation.

    ``anchors`` maps a name to the printed value(s) (a number or a list) or to "not_available",
    which is counted and not compared; ``values`` maps the same names to the computed value(s),
    in price/K.  A missing or non-finite computed value fails its anchor.  At least one anchor
    must be comparable.  Returns ``{pass, status, failed, not_available, differences}`` with
    status ``pass`` or ``paper_mismatch`` and ``differences`` = computed - printed per compared
    anchor (None when nothing finite was computed).
    """
    failed, not_available, differences = [], [], {}
    for name, printed in anchors.items():
        if isinstance(printed, str):
            if printed != "not_available":
                raise ValueError(
                    f"anchor {name!r}: expected numbers or 'not_available', got {printed!r}"
                )
            not_available.append(name)
            continue
        target = np.asarray(printed, dtype=float)
        got = values.get(name)
        computed = None if got is None else np.asarray(got, dtype=float)
        if computed is not None and computed.shape != target.shape:
            raise ValueError(
                f"anchor {name!r}: computed shape {computed.shape}, printed shape {target.shape}"
            )
        if computed is None or not np.all(np.isfinite(computed)):
            failed.append(name)
            differences[name] = None
            continue
        gap = computed - target
        differences[name] = gap.tolist()
        if not np.all(np.abs(gap) <= tol):
            failed.append(name)
    if len(not_available) == len(anchors):
        raise ValueError("no printed value to compare")
    return {
        "pass": not failed,
        "status": "paper_mismatch" if failed else "pass",
        "failed": failed,
        "not_available": not_available,
        "differences": differences,
    }


def estimate_seconds(method: str, measured: dict | None, job: dict, factor: float) -> dict:
    """Wall-time estimate of a job from a measured one (design 6), times the safety ``factor``.

    ``spectral``: factor (setup w v^3 + solve t w v^2 s) with w, v, t the ratios job/measured of
    n_omega, n_var, n_time and s = measured scan_spacing / job scan_spacing (the scan has that
    many times more points).  ``fd``: factor (setup r_setup + solve r_solve) with r_setup the
    ratio of nodes x bandwidth^2 and r_solve the ratio of n_time x nodes x bandwidth.  With every
    ratio 1 this is factor (setup + solve).  ``measured`` holds setup_seconds, solve_seconds and
    the sizes above; None gives status ``unmeasured`` and no seconds.  Returns
    ``{status, seconds, formula, coefficients}`` with status ``estimated`` or ``unmeasured``.
    """
    formulas = {
        "spectral": "factor * (setup_seconds * w * v**3 + solve_seconds * t * w * v**2 * s)",
        "fd": "factor * (setup_seconds * r_setup + solve_seconds * r_solve)",
    }
    if method not in formulas:
        raise ValueError(f"method must be one of {tuple(formulas)}, got {method!r}")
    if measured is None:
        return {
            "status": "unmeasured",
            "seconds": None,
            "formula": formulas[method],
            "coefficients": None,
        }
    scale = _positive("factor", factor)
    setup = float(_floats("setup_seconds", measured["setup_seconds"], 0))
    solve = float(_floats("solve_seconds", measured["solve_seconds"], 0))
    if setup < 0.0 or solve < 0.0:
        raise ValueError("measured setup_seconds and solve_seconds must be >= 0")

    def ratio(key: str) -> float:
        """job[key] / measured[key]."""
        return _positive(f"job {key}", job[key]) / _positive(f"measured {key}", measured[key])

    if method == "spectral":
        w, v, t = ratio("n_omega"), ratio("n_var"), ratio("n_time")
        s = _positive("measured scan_spacing", measured["scan_spacing"]) / _positive(
            "job scan_spacing", job["scan_spacing"]
        )
        seconds = scale * (setup * w * v**3 + solve * t * w * v**2 * s)
        terms = {"w": w, "v": v, "t": t, "s": s}
    else:
        r_setup = ratio("nodes") * ratio("bandwidth") ** 2
        r_solve = ratio("n_time") * ratio("nodes") * ratio("bandwidth")
        seconds = scale * (setup * r_setup + solve * r_solve)
        terms = {"r_setup": r_setup, "r_solve": r_solve}
    coefficients = {"factor": scale, "setup_seconds": setup, "solve_seconds": solve} | terms
    return {
        "status": "estimated",
        "seconds": float(seconds),
        "formula": formulas[method],
        "coefficients": coefficients,
    }


def reproduction_label(paper: dict, validated: dict[str, dict]) -> str:
    """``reproduced``, ``constrained`` or ``not_reproduced`` from the paper gate and the maturities.

    ``paper["pass"]`` is the paper_match verdict and ``validated`` maps each maturity to
    ``{"price": bool, "boundary": status}``.  ``reproduced``: the paper gate passes and every
    maturity has price True and boundary ``pass``.  ``constrained``: the paper gate passes and some
    maturity has price True.  Anything else is ``not_reproduced``.
    """
    if not paper["pass"]:
        return "not_reproduced"
    entries = list(validated.values())
    if entries and all(bool(entry["price"]) and entry["boundary"] == "pass" for entry in entries):
        return "reproduced"
    if any(bool(entry["price"]) for entry in entries):
        return "constrained"
    return "not_reproduced"


def deltas(up: np.ndarray, down: np.ndarray, bump: float) -> np.ndarray:
    """Central-difference Delta (up - down) / (2 bump) from prices at S/K + bump and S/K - bump."""
    high = _floats("up", up, np.ndim(up))
    low = _floats("down", down, np.ndim(down))
    if high.shape != low.shape:
        raise ValueError(f"up {high.shape} and down {low.shape} must share a shape")
    return (high - low) / (2.0 * _positive("bump", bump))
