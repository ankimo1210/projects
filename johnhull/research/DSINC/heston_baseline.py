"""Observe the pinned Heston code without certifying its numerical accuracy.

MIT upstream helper bodies are retained arithmetically in observer subclasses.
The unmodified originals and their license live in upstream/. Never import the
upstream benchmark: it starts numerical work at import time.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict
from functools import lru_cache
from numbers import Integral, Real
from pathlib import Path
from time import perf_counter

import numpy as np
import scipy.sparse as sp
from scipy.optimize import brentq
from scipy.sparse.linalg import splu

ROOT = Path(__file__).resolve().parent


def verify_upstream(directory=None):
    """Reject altered source bytes before any dynamically loaded upstream code."""
    directory = ROOT / "upstream" if directory is None else Path(directory)
    manifest = json.loads((ROOT / "upstream_manifest.json").read_text())
    for name, expected in manifest["files"].items():
        raw = (directory / name).read_bytes()
        sha256 = hashlib.sha256(raw).hexdigest()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        if sha256 != expected["sha256"] or blob != expected["git_blob"]:
            raise ValueError(f"upstream hash mismatch: {name}")


def _load(name):
    spec = importlib.util.spec_from_file_location(
        "_dsinc_fixed_" + name, ROOT / "upstream" / (name + ".py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def upstream_classes():
    """Load the two fixed modules by path, without modifying sys.path."""
    verify_upstream()
    return _load("dsinc_pricer").DSINCPut, _load("fd_adi_pricer").HestonFDSolver


def _number(value):
    value = float(value)
    return value if np.isfinite(value) else None


@lru_cache(maxsize=1)
def audited_classes():
    """Return arithmetic-preserving observers for the two upstream solvers."""
    raw_ds, raw_fd = upstream_classes()

    class AuditedDSINC(raw_ds):
        def __init__(self, params=None):
            self.audit = []
            self.phase_seconds = {}
            super().__init__(params)

        def _safe(self, f, x):
            try:
                value = f(x)
                if np.isfinite(value):
                    return value
                self.audit.append({"code": "root_nonfinite", "x": _number(x)})
            except Exception as error:
                self.audit.append({"code": "root_exception", "x": _number(x), "error": str(error)})
            return np.nan

        def _solve_boundary(self, res, x0):
            lo_lim, hi_lim = np.log(1e-6), 0.05
            clipped = float(np.clip(x0, lo_lim, hi_lim))
            if clipped != x0:
                self.audit.append({"code": "predictor_clip", "raw": _number(x0), "value": clipped})
            x0 = clipped

            def finish(value, branch, finite_samples=None):
                residual = self._safe(res, value)
                self.audit.append(
                    {
                        "code": "boundary",
                        "branch": branch,
                        "value": float(value),
                        "residual": _number(residual),
                        "success": bool(branch != "min_residual" and np.isfinite(residual)),
                        "finite_samples": finite_samples,
                    }
                )
                return value

            f0 = self._safe(res, x0)
            if np.isfinite(f0) and f0 == 0:
                return finish(x0, "predictor_exact")
            if np.isfinite(f0):
                dx = abs(x0) / 50 if x0 != 0 else 1 / 50
                a = b = x0
                fb = f0
                for _ in range(100):
                    dx *= np.sqrt(2.0)
                    a = x0 - dx
                    fa = self._safe(res, a)
                    if np.isfinite(fa) and (fa > 0) != (fb > 0):
                        return finish(brentq(res, a, b, xtol=1e-12), "local_brentq")
                    b = x0 + dx
                    fb = self._safe(res, b)
                    if np.isfinite(fa) and np.isfinite(fb) and (fa > 0) != (fb > 0):
                        return finish(brentq(res, a, b, xtol=1e-12), "local_brentq")
                    if a < lo_lim and b > hi_lim:
                        break
            xs = np.linspace(np.log(1e-4), 0.02, 60)
            rv = np.array([self._safe(res, x) for x in xs])
            ok = np.isfinite(rv)
            idx = np.where(ok[:-1] & ok[1:] & (rv[:-1] * rv[1:] < 0))[0]
            if idx.size:
                s = idx[0]
                return finish(brentq(res, xs[s], xs[s + 1], xtol=1e-12), "wide_scan", int(ok.sum()))
            rv = np.where(ok, np.abs(rv), np.inf)
            return finish(float(xs[int(np.argmin(rv))]), "min_residual", int(ok.sum()))

        def _heston_cf(self, u, tau, v):
            kappa, theta, s, rho = self.kappa, self.theta, self.sigma, self.rho
            a, b, i = kappa * theta, kappa, 1j
            bb, s2 = rho * s * i * u - b, s**2
            d = np.sqrt(bb**2 + s2 * (i * u + u**2))
            lam2, lam1 = -bb - d, -bb + d
            g = lam2 / lam1
            bad = np.abs(lam1) < 1e-12
            if np.any(bad):
                g = g.copy()
                g[bad] = 1 - 2 * d[bad] / (lam1[bad] + 1e-12)
            edt = np.exp(-d * tau)
            c = (a / s2) * (lam2 * tau - 2 * np.log((1 - g * edt) / (1 - g)))
            dd = (1 - edt) / (1 - g * edt) * (b - rho * s * i * u - d) / s2
            cf = np.exp(i * u * ((self.rd - self.rf) * tau) + c + dd * v)
            bad = ~np.isfinite(cf)
            if np.any(bad):
                self.audit.append({"code": "cf_nonfinite_replaced", "count": int(bad.sum())})
            cf[bad] = 0.0
            return cf

        def _european_value(self, x, coeffs):
            if coeffs is None:
                return max(self.K * (1 - np.exp(x)), 0.0)
            a, freqs, cf_u, df = coeffs
            raw = df * np.sum(np.real(cf_u * np.exp(1j * freqs * (x - a))))
            value = max(raw, 0.0)
            if raw < 0 or not np.isfinite(raw):
                self.audit.append(
                    {"code": "european_floor", "raw": _number(raw), "value": _number(value)}
                )
            return value

        def _final_eep(self, xstar):
            nt, strike, wc, wq = self.Nt, self.K, self.wc, self.wq
            tt, v0, x0 = self.tt, self.v0, self.x0
            rd, mu1, kappa, rtx = self.rd, self.mu1, self.kappa, self.rtx
            weights = self._trapw(tt)
            eep = 0.0
            for iu in range(1, nt):
                tau = tt[iu]
                e1, f1, e2, f2, w1, w2 = self._segcoef(xstar[iu, :], iu)
                wm0 = self._WM0[iu] if self.partial else np.ones(self.M)
                acc = np.sum(wm0 * (w1 * np.exp(e1 + f1 * v0) - w2 * np.exp(e2 + f2 * v0)), axis=1)
                mu0 = x0 + (rd - self.rf) * tau - mu1 * v0 - kappa * rtx * tau
                term = np.exp(1j * wc * mu0) * acc
                eep += np.exp(-rd * tau) * weights[iu] / (2 * np.pi) * np.real(np.sum(wq * term))
            raw = strike * eep
            value = max(raw, 0.0)
            if raw < 0 or not np.isfinite(raw):
                self.audit.append(
                    {"code": "eep_floor", "raw": _number(raw), "value": _number(value)}
                )
            return value

        def price(self):
            started = perf_counter()
            self.EEP = self._backward_solve()
            self.phase_seconds["american_seconds"] = perf_counter() - started
            started = perf_counter()
            self.PE = self._european_value(self.x0, self._european_coeffs(self.v0, self.T))
            self.phase_seconds["european_seconds"] = perf_counter() - started
            raw = self.PE + self.EEP
            self.PA = max(raw, self.K - self.S)
            if self.PA != raw:
                self.audit.append(
                    {
                        "code": "american_intrinsic_floor",
                        "raw": _number(raw),
                        "value": _number(self.PA),
                    }
                )
            return self.PE, self.PA, self.EEP

    class AuditedFD(raw_fd):
        def __init__(self, params=None):
            self.audit = []
            super().__init__(params)

        def _policy_iteration(self, u, yhat1, active):
            dt, th = self.dt, self.theta_mcs
            identity, a2, phi = self.Ibig, self.A2, self.phi
            rho_am = self.rho_AM
            n_dof = self.mi * self.mj
            rhs_const = (identity - th * dt * a2).dot(u)
            old = current = u
            converged = False
            for _iteration in range(1, self.pp_maxiter + 1):
                penalty = sp.diags(active, 0, format="csc")
                matrix = (identity - th * dt * a2 + rho_am * penalty).tocsc()
                rhs = yhat1 + rhs_const + rho_am * penalty.dot(phi)
                current = splu(matrix).solve(rhs)
                new_active = np.zeros(n_dof)
                new_active[(phi - current) > 0] = 1
                criterion = np.max(np.abs(current - old) / np.maximum(1.0, np.abs(current)))
                if criterion < self.pp_tol or np.all(new_active == active):
                    converged = True
                    break
                active = new_active
                old = current
            self.audit.append(
                {
                    "code": "penalty_iteration",
                    "iterations": _iteration,
                    "converged": bool(converged),
                    "criterion": _number(criterion),
                }
            )
            return current, active

    return AuditedDSINC, AuditedFD


def _settings(obj):
    keys = {key for cls in type(obj).__mro__ for key in getattr(cls, "__annotations__", {})}
    return {key: getattr(obj, key) for key in sorted(keys)}


def _numerical_settings(settings, allowed):
    if set(settings) - allowed:
        raise ValueError("settings may only override known numerical controls")
    integer_minima = {"Nv": 2, "Nt": 2, "Nom": 2, "N": 1, "m1": 4, "pp_maxiter": 1}
    for key, value in settings.items():
        if key == "mode":
            if value not in ("partial", "full"):
                raise ValueError("unknown DSINC mode")
            continue
        if key == "Nt" and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
            raise ValueError("numerical settings must be finite real values")
        if key in integer_minima and (
            not isinstance(value, Integral) or value < integer_minima[key]
        ):
            raise ValueError(f"invalid grid/iteration count: {key}")
        if key == "policy" and value not in (0, 1):
            raise ValueError("policy must be zero or one")
        if key in ("om_max", "Vmax", "rho_AM") and value <= 0:
            raise ValueError(f"{key} must be positive")
        if key == "Smax_mult" and value <= 1:
            raise ValueError("Smax_mult must exceed one")
        if key == "B" and value < 0:
            raise ValueError("B must be nonnegative")
        if key == "theta_mcs" and not 0 < value <= 1:
            raise ValueError("theta_mcs must lie in (0,1]")
    return dict(settings)


def run_heston_baseline(contract, model, spots, *, dsinc_settings, fd_settings):
    """Return un-certified observations, original settings, corrections, and costs."""
    verify_upstream()
    if model.kind != "heston":
        raise ValueError("upstream baseline only supports Heston")
    spots = np.asarray(spots, dtype=float)
    if spots.ndim != 1 or not spots.size or np.any(~np.isfinite(spots)) or np.any(spots <= 0):
        raise ValueError("spots must be a nonempty positive finite vector")
    ds_controls = _numerical_settings(dsinc_settings, {"Nv", "Nt", "Nom", "om_max", "mode"})
    fd_controls = _numerical_settings(
        fd_settings,
        {"N", "m1", "B", "Smax_mult", "Vmax", "theta_mcs", "policy", "rho_AM", "pp_maxiter"},
    )
    if fd_controls.get("Vmax", 5.0) < model.v0:
        raise ValueError("v0 is outside the upstream FD grid")
    if fd_controls.get("B", 0.0) >= contract.strike:
        raise ValueError("B must lie below the strike")
    if (
        min(spots) < fd_controls.get("B", 0.0)
        or max(spots) > fd_controls.get("Smax_mult", 8.0) * contract.strike
    ):
        raise ValueError("spot is outside the upstream FD grid")
    started = perf_counter()
    report = {
        "contract": asdict(contract),
        "model": asdict(model),
        "accepted": False,
        "spots": [],
        "timings": {},
    }
    if contract.expiry == 0:
        for spot in spots:
            payoff = float(max(contract.strike - spot, 0.0))
            report["spots"].append(
                {
                    "spot": float(spot),
                    "dsinc": {"values": [payoff, payoff, 0.0]},
                    "fd": {"values": [payoff, payoff]},
                    "boundary_status": "not_applicable",
                }
            )
        report["timings"]["total_seconds"] = perf_counter() - started
        return report
    ds_class, fd_class = audited_classes()
    common = dict(
        K=contract.strike,
        rd=contract.domestic_rate,
        rf=contract.foreign_rate,
        theta=model.theta,
        rho=model.rho,
        kappa=model.kappa,
    )
    before = perf_counter()
    fd = fd_class(dict(**common, T2=contract.expiry, xi=model.xi, **fd_controls))
    fd_time = {"setup_seconds": perf_counter() - before}
    for style, name in ((0, "european_seconds"), (1, "american_seconds")):
        before = perf_counter()
        fd.solve(style)
        fd_time[name] = perf_counter() - before
    for spot in spots:
        before = perf_counter()
        ds = ds_class(
            dict(
                **common,
                S=float(spot),
                T=contract.expiry,
                sigma=model.xi,
                v0=model.v0,
                **ds_controls,
            )
        )
        ds_time = {"setup_seconds": perf_counter() - before}
        values = ds.price()
        ds_time.update(ds.phase_seconds, query_seconds=None)
        before = perf_counter()
        fd_values = [fd.price(float(spot), model.v0, 0), fd.price(float(spot), model.v0, 1)]
        query_time = perf_counter() - before
        report["spots"].append(
            {
                "spot": float(spot),
                "dsinc": {
                    "values": [_number(v) for v in values],
                    "settings": _settings(ds),
                    "audit": ds.audit,
                    "timings": ds_time,
                },
                "fd": {
                    "values": [_number(v) for v in fd_values],
                    "settings": _settings(fd),
                    "audit": fd.audit,
                    "timings": dict(fd_time, query_seconds=query_time),
                },
            }
        )
    report["timings"]["total_seconds"] = perf_counter() - started
    return report
