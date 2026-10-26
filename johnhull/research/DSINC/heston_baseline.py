"""Pinned upstream Heston DSINC / finite-difference code: loading, branch counting, comparison.

The two upstream solvers (``dsinc_pricer.py``, ``fd_adi_pricer.py``) are kept byte for byte in
``upstream/`` and are only loaded by file path after their sha256 and size match
``upstream_manifest.json``.  ``benchmark.py`` is stored for provenance and is never imported (it
runs a benchmark on import).  Nothing here touches ``sys.path``.

The upstream may not be edited, so :func:`observed_classes` subclasses the two solvers and copies
the control flow of the methods that clip, floor or fall back.  Every line the audit adds to a
copied method ends in ``# audit``; without those lines the method is the upstream's (``_safe`` is
an instance method here, where the upstream's is static, so that it can count), so the prices are
the upstream's own.  The added lines count the branches taken and keep the raw value before each
floor.  ``certified`` is always ``False``: this module audits the upstream and does not endorse it.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import numbers
import sys
import time
from pathlib import Path
from types import ModuleType
from typing import Literal

import numpy as np
import scipy.sparse as sp
from hullkit._dsinc_types import PutContract, VarianceModel
from scipy.optimize import brentq
from scipy.sparse.linalg import splu

HERE = Path(__file__).resolve().parent
UPSTREAM_DIR = HERE / "upstream"
MANIFEST = HERE / "upstream_manifest.json"

# The numerical (non-model) parameters each upstream class accepts; the model comes from the case.
DSINC_SETTINGS = ("Nv", "Nt", "Nom", "om_max", "mode")
FD_SETTINGS = ("N", "m1", "B", "Smax_mult", "Vmax", "theta_mcs", "policy", "rho_AM", "pp_maxiter")
COUNT_KEYS = (
    "clip_low",
    "clip_high",
    "exact_zero",
    "local_bracket",
    "wide_scan",
    "min_residual",
    "safe_nan",
    "cf_nonfinite",
    "european_floor",
)
STOP_REASONS = ("tolerance", "active_set_stable", "maxiter")
# fd_adi_pricer.py's module docstring calls policy=0 the default, but the class default is 1.
FD_DOCSTRING_POLICY_DEFAULT = 0

_LOADED: dict[tuple[Path, str], ModuleType] = {}
_OBSERVED: dict[tuple[type, type], tuple[type, type]] = {}


def load_upstream(name: Literal["dsinc_pricer", "fd_adi_pricer"]) -> ModuleType:
    """Return the pinned upstream module ``name``, loaded by file path after the sha256 check.

    ``benchmark`` is refused because ``benchmark.py`` runs its benchmark on import; any other
    name is refused too.  A file whose bytes differ from ``upstream_manifest.json`` raises
    ValueError naming the sha256 and size.  Loaded modules are cached by (path, sha256).
    """
    if name == "benchmark":
        raise ValueError("benchmark.py is never imported (it runs a benchmark on import)")
    if name not in ("dsinc_pricer", "fd_adi_pricer"):
        raise ValueError(f"unknown upstream module {name!r}: use 'dsinc_pricer' or 'fd_adi_pricer'")
    path = UPSTREAM_DIR / f"{name}.py"
    data = path.read_bytes()
    pinned = json.loads(MANIFEST.read_text())["files"][path.name]
    digest = hashlib.sha256(data).hexdigest()
    if digest != pinned["sha256"] or len(data) != pinned["bytes"]:
        raise ValueError(
            f"{path} does not match upstream_manifest.json: sha256 {digest} ({len(data)} bytes), "
            f"pinned sha256 {pinned['sha256']} ({pinned['bytes']} bytes)"
        )
    if (path, digest) not in _LOADED:
        spec = importlib.util.spec_from_file_location(f"dsinc_upstream_{name}", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(spec.name, None)
            raise
        _LOADED[(path, digest)] = module
    return _LOADED[(path, digest)]


class _DSINCAudit:
    """Counting overrides, put ahead of the pinned ``DSINCPut`` in the observed class.

    The audit attributes carry no annotation: the upstream ``__init__`` accepts exactly the
    annotated class attributes as parameters.
    """

    def __init__(self, params=None):
        self._reset_audit()
        super().__init__(params)

    def _reset_audit(self):
        """Zero the counters and the raw values; ``price()`` starts from this state."""
        self.counts = dict.fromkeys(COUNT_KEYS, 0)
        self.extremes = {"european_min_raw": None}
        self.final = {"european_raw": None, "eep_raw": None, "american_raw": None}
        self.post_processing = []
        self._european_last = None

    def _safe(self, f, x):
        try:
            v = f(x)
            if not np.isfinite(v):  # audit
                self.counts["safe_nan"] += 1  # audit
            return v if np.isfinite(v) else np.nan
        except Exception:
            self.counts["safe_nan"] += 1  # audit
            return np.nan

    def _solve_boundary(self, res, x0):
        # Bracketing root-find warm-started at x0: expand a two-sided bracket about x0 (sqrt(2)
        # growth) and bisect the first sign change; a wide scan over [log(1e-4), 0.02] is the
        # fallback.  Confined to the put-sensible range x* <= ~0.05.
        lo_lim, hi_lim = np.log(1e-6), 0.05
        unclipped = x0  # audit
        x0 = float(np.clip(x0, lo_lim, hi_lim))
        self.counts["clip_low"] += int(x0 > unclipped)  # audit
        self.counts["clip_high"] += int(x0 < unclipped)  # audit
        f0 = self._safe(res, x0)
        if np.isfinite(f0) and f0 == 0:
            self.counts["exact_zero"] += 1  # audit
            return x0
        if np.isfinite(f0):
            dx = (abs(x0) / 50.0) if x0 != 0 else (1.0 / 50.0)
            a = b = x0
            fb = f0
            for _ in range(100):
                dx *= np.sqrt(2.0)
                a = x0 - dx
                fa = self._safe(res, a)
                if np.isfinite(fa) and (fa > 0) != (fb > 0):
                    self.counts["local_bracket"] += 1  # audit
                    return brentq(res, a, b, xtol=1e-12)
                b = x0 + dx
                fb = self._safe(res, b)
                if np.isfinite(fa) and np.isfinite(fb) and (fa > 0) != (fb > 0):
                    self.counts["local_bracket"] += 1  # audit
                    return brentq(res, a, b, xtol=1e-12)
                if a < lo_lim and b > hi_lim:
                    break
        xs = np.linspace(np.log(1e-4), 0.02, 60)
        rv = np.array([self._safe(res, xi) for xi in xs])
        ok = np.isfinite(rv)
        idx = np.where(ok[:-1] & ok[1:] & (rv[:-1] * rv[1:] < 0))[0]
        if idx.size:
            s = idx[0]
            self.counts["wide_scan"] += 1  # audit
            return brentq(res, xs[s], xs[s + 1], xtol=1e-12)
        rv = np.where(ok, np.abs(rv), np.inf)
        self.counts["min_residual"] += 1  # audit
        return float(xs[int(np.argmin(rv))])

    def _heston_cf(self, u, tau, v):
        """Marginal Heston characteristic function in x=log(S_T/K) at maturity tau, variance v."""
        kappa, theta, s, rho = self.kappa, self.theta, self.sigma, self.rho
        a = kappa * theta
        b = kappa
        i = 1j
        bb = rho * s * i * u - b
        s2 = s**2
        d = np.sqrt(bb**2 + s2 * (i * u + u**2))
        lam2 = -bb - d
        lam1 = -bb + d
        g = lam2 / lam1
        bad = np.abs(lam1) < 1e-12
        if np.any(bad):
            g = g.copy()
            g[bad] = 1 - 2 * d[bad] / (lam1[bad] + 1e-12)
        edt = np.exp(-d * tau)
        C = (a / s2) * (lam2 * tau - 2 * np.log((1 - g * edt) / (1 - g)))
        D = (1 - edt) / (1 - g * edt) * (b - rho * s * i * u - d) / s2
        cf = np.exp(i * u * ((self.rd - self.rf) * tau) + C + D * v)
        self.counts["cf_nonfinite"] += int(np.count_nonzero(~np.isfinite(cf)))  # audit
        cf[~np.isfinite(cf)] = 0.0
        return cf

    def _european_value(self, x, coeffs):
        """European put at log-moneyness x from precomputed coefficients (intrinsic if tau~0)."""
        if coeffs is None:
            self._european_last = None  # audit
            return max(self.K * (1 - np.exp(x)), 0.0)
        a, freqs, cfU, DF = coeffs
        val = DF * np.sum(np.real(cfU * np.exp(1j * freqs * (x - a))))
        self._european_last = float(val)  # audit
        lowest = self.extremes["european_min_raw"]  # audit
        if lowest is None or val < lowest:  # audit
            self.extremes["european_min_raw"] = float(val)  # audit
        if val < 0.0:  # audit
            self.counts["european_floor"] += 1  # audit
        return max(val, 0.0)

    def _final_eep(self, xstar):
        Nt, K, wc, wq = self.Nt, self.K, self.wc, self.wq
        tt, v0, x0 = self.tt, self.v0, self.x0
        rd, rf, mu1, kappa, rtx = self.rd, self.rf, self.mu1, self.kappa, self.rtx
        Wt = self._trapw(tt)
        EEP = 0.0
        for iu in range(1, Nt):
            tau = tt[iu]
            L = iu
            Du = np.exp(-rd * tau)
            E1, F1, E2, F2, e1, e2 = self._segcoef(xstar[iu, :], L)
            wm0 = self._WM0[L] if self.partial else np.ones(self.M)
            acc = np.sum(wm0 * (e1 * np.exp(E1 + F1 * v0) - e2 * np.exp(E2 + F2 * v0)), axis=1)
            mu0 = x0 + (rd - rf) * tau - mu1 * v0 - kappa * rtx * tau
            term = np.exp(1j * wc * mu0) * acc
            EEP += Du * Wt[iu] * (1.0 / (2 * np.pi)) * np.real(np.sum(wq * term))
        self.final["eep_raw"] = float(K * EEP)  # audit
        if K * EEP < 0.0:  # audit
            self.post_processing.append("eep_floor")  # audit
        return max(K * EEP, 0.0)

    def price(self):
        """Return (PE, PA, EEP): European put, American put, early-exercise premium."""
        self._reset_audit()  # audit
        self.EEP = self._backward_solve()
        self._european_last = None  # audit
        self.PE = self._european_value(self.x0, self._european_coeffs(self.v0, self.T))
        self.final["european_raw"] = self._european_last  # audit
        if self._european_last is not None and self._european_last < 0.0:  # audit
            self.post_processing.append("european_floor")  # audit
        self.final["american_raw"] = float(self.PE + self.EEP)  # audit
        if self.K - self.S > self.PE + self.EEP:  # audit
            self.post_processing.append("american_floor")  # audit
        self.PA = max(self.PE + self.EEP, self.K - self.S)
        return self.PE, self.PA, self.EEP


class _FDAudit:
    """Counting override, put ahead of the pinned ``HestonFDSolver`` in the observed class."""

    def __init__(self, params=None):
        self.policy_stop_reasons = dict.fromkeys(STOP_REASONS, 0)
        self.policy_solves = 0
        super().__init__(params)

    def _policy_iteration(self, u, Yhat1, Pi_AM_iter):
        """Penalized policy iteration for the A2-implicit stage until the active set stabilizes."""
        dt, th = self.dt, self.theta_mcs
        Ibig, A2, phi = self.Ibig, self.A2, self.phi
        rho_AM = self.rho_AM
        n_dof = self.mi * self.mj

        rhs_const = (Ibig - th * dt * A2).dot(u)
        U_iter_km1 = u
        U_iter = u
        reason = "maxiter"  # audit
        for _k in range(1, self.pp_maxiter + 1):
            Pk1 = sp.diags(Pi_AM_iter, 0, format="csc")
            M_pen = (Ibig - th * dt * A2 + rho_AM * Pk1).tocsc()
            rhs = Yhat1 + rhs_const + rho_AM * (Pk1.dot(phi))
            self.policy_solves += 1  # audit
            U_iter = splu(M_pen).solve(rhs)
            Pi_AM_new = np.zeros(n_dof)
            Pi_AM_new[(phi - U_iter) > 0] = 1
            crit = np.max(np.abs(U_iter - U_iter_km1) / np.maximum(1.0, np.abs(U_iter)))
            if crit < self.pp_tol or np.all(Pi_AM_new == Pi_AM_iter):
                reason = "tolerance" if crit < self.pp_tol else "active_set_stable"  # audit
                break
            Pi_AM_iter = Pi_AM_new
            U_iter_km1 = U_iter
        self.policy_stop_reasons[reason] += 1  # audit
        return U_iter, Pi_AM_iter


def observed_classes() -> tuple[type, type]:
    """Return ``(ObservedDSINCPut, ObservedFDSolver)``, built once per loaded upstream pair.

    Both subclass the pinned classes, return the upstream's values and add the audit attributes
    ``counts``, ``extremes``, ``final`` and ``post_processing`` (DSINC) and ``policy_stop_reasons``
    and ``policy_solves`` (FD).
    """
    put = load_upstream("dsinc_pricer").DSINCPut
    solver = load_upstream("fd_adi_pricer").HestonFDSolver
    if (put, solver) not in _OBSERVED:

        class ObservedDSINCPut(_DSINCAudit, put):
            """The pinned ``DSINCPut`` that counts its clips, floors and fallbacks."""

        class ObservedFDSolver(_FDAudit, solver):
            """The pinned ``HestonFDSolver`` that counts why its penalty iterations stop."""

        _OBSERVED[(put, solver)] = (ObservedDSINCPut, ObservedFDSolver)
    return _OBSERVED[(put, solver)]


def _spot(value) -> float:
    """Return the spot as a float; it must be a finite real number > 0."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
        raise ValueError(f"S must be a finite real number, got {value!r}")
    if value <= 0:
        raise ValueError(f"S must be > 0, got {value!r}")
    return float(value)


def _settings(label: str, given: dict | None, allowed: tuple[str, ...]) -> dict:
    """Return a copy of the numerical settings; model parameters must come from the case."""
    given = dict(given or {})
    unknown = sorted(set(given) - set(allowed))
    if unknown:
        raise ValueError(f"{label} may only set {allowed}, got {unknown}")
    return given


def _differences(reference: dict, dsinc: dict, fd: dict) -> dict:
    """Return solver price minus reference value, per solver and reference key."""
    out = {"dsinc": {}, "fd": {}}
    for key, value in reference.items():
        style = key.rsplit("_", 1)[-1]
        if style not in ("european", "american"):
            raise ValueError(f"reference key {key!r} must end in 'european' or 'american'")
        out["dsinc"][key] = dsinc[style] - float(value)
        out["fd"][key] = fd[style] - float(value)
    return out


def run_heston_baseline(
    case: dict, *, dsinc_settings: dict | None = None, fd_settings: dict | None = None
) -> dict:
    """Price one Heston put case with the pinned DSINC and FD solvers and compare to its reference.

    ``case`` holds ``S, K, T, rd, rf, theta, xi, rho, v0, kappa`` (``xi`` is the vol-of-variance,
    passed to DSINC as ``sigma``), optionally ``case_id`` and ``reference``.  The inputs are
    validated first (``PutContract``, ``VarianceModel`` and ``S > 0``; ``rd <= rf`` and ``T = 0``
    raise ValueError, because the upstream would price them silently or wrongly).
    ``dsinc_settings`` and ``fd_settings`` override the upstream numerical parameters only.

    Returns JSON-ready values: ``case_id``, ``inputs``, ``dsinc`` and ``fd`` (the parameters
    passed to the upstream, the effective settings, the prices, the audit counters and the
    seconds), ``reference``, ``differences`` (solver minus reference, per solver and reference
    key) and ``certified``, which is always False.
    """
    contract = PutContract(case["K"], case["T"], case["rd"], case["rf"])
    model = VarianceModel(
        "heston", case["kappa"], case["theta"], case["xi"], case["rho"], case["v0"]
    )
    spot = _spot(case["S"])
    if contract.expiry == 0.0:
        raise ValueError("T must be > 0: the upstream solvers return NaN or a wrong value at T = 0")
    dsinc_settings = _settings("dsinc_settings", dsinc_settings, DSINC_SETTINGS)
    fd_settings = _settings("fd_settings", fd_settings, FD_SETTINGS)
    reference = dict(case.get("reference") or {})
    observed_dsinc, observed_fd = observed_classes()

    dsinc_parameters = {
        "S": spot,
        "K": contract.strike,
        "T": contract.expiry,
        "rd": contract.domestic_rate,
        "rf": contract.foreign_rate,
        "theta": model.theta,
        "sigma": model.xi,
        "rho": model.rho,
        "v0": model.v0,
        "kappa": model.kappa,
    } | dsinc_settings
    started = time.perf_counter()
    put = observed_dsinc(dsinc_parameters)
    dsinc_init = time.perf_counter() - started
    started = time.perf_counter()
    european, american, eep = put.price()
    dsinc_price = time.perf_counter() - started
    dsinc = {
        "parameters": dict(dsinc_parameters),
        "settings": {name: getattr(put, name) for name in (*DSINC_SETTINGS, "chi")},
        "european": float(european),
        "american": float(american),
        "eep": float(eep),
        "final": dict(put.final),
        "counts": dict(put.counts),
        "extremes": dict(put.extremes),
        "post_processing": list(put.post_processing),
        "seconds": {"init": dsinc_init, "price": dsinc_price},
    }

    fd_parameters = {
        "K": contract.strike,
        "T2": contract.expiry,
        "rd": contract.domestic_rate,
        "rf": contract.foreign_rate,
        "theta": model.theta,
        "xi": model.xi,
        "rho": model.rho,
        "kappa": model.kappa,
    } | fd_settings
    started = time.perf_counter()
    solver = observed_fd(fd_parameters)
    fd_init = time.perf_counter() - started
    started = time.perf_counter()
    fd_european = solver.price(spot, model.v0, 0)
    fd_european_seconds = time.perf_counter() - started
    started = time.perf_counter()
    fd_american = solver.price(spot, model.v0, 1)
    fd_american_seconds = time.perf_counter() - started
    fd = {
        "parameters": dict(fd_parameters),
        "settings": {name: getattr(solver, name) for name in FD_SETTINGS},
        "docstring_policy_default": FD_DOCSTRING_POLICY_DEFAULT,
        "european": float(fd_european),
        "american": float(fd_american),
        "policy_stop_reasons": dict(solver.policy_stop_reasons),
        "policy_solves": solver.policy_solves,
        "seconds": {
            "init": fd_init,
            "european": fd_european_seconds,
            "american": fd_american_seconds,
        },
    }

    return {
        "case_id": case.get("case_id"),
        "inputs": {
            "S": spot,
            "K": contract.strike,
            "T": contract.expiry,
            "rd": contract.domestic_rate,
            "rf": contract.foreign_rate,
            "theta": model.theta,
            "xi": model.xi,
            "rho": model.rho,
            "v0": model.v0,
            "kappa": model.kappa,
        },
        "dsinc": dsinc,
        "fd": fd,
        "reference": reference,
        "differences": _differences(reference, dsinc, fd),
        "certified": False,
    }
