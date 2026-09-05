"""Smooth zero curves with analytic instantaneous forwards and positive D."""
from __future__ import annotations

import numpy as np
from scipy.interpolate import CubicSpline


class CurveBasis:
    def __init__(self, kind="advanced", horizon=30.0):
        self.kind = kind
        self.horizon = max(30.0, float(horizon))
        if kind == "advanced":
            k = [0, 1 / 12, .25, .5, .75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30]
            if self.horizon > 30:
                k += [self.horizon]
            self.knots = np.array(k)
            self.spline = CubicSpline(np.log1p(self.knots), np.eye(len(k)), axis=0, bc_type="natural")
            self.size = len(k)
        elif kind == "baseline":
            self.size = 3
        else:
            raise ValueError("curve kind must be baseline or advanced")

    def matrix(self, times, derivative=0):
        t = np.atleast_1d(np.asarray(times, dtype=float))
        if np.any(~np.isfinite(t)) or np.any(t < 0):
            raise ValueError("curve times must be finite and nonnegative")
        if self.kind == "advanced":
            x = np.log1p(np.minimum(t, self.horizon))
            b = self.spline(x) if derivative == 0 else self.spline(x, 1) / (1 + np.minimum(t, self.horizon))[:, None]
            beyond = t > self.horizon
            if np.any(beyond):
                u = self.horizon
                bu = self.spline(np.log1p(u))
                du = self.spline(np.log1p(u), 1) / (1 + u)
                fu = bu + u * du
                b[beyond] = fu + (bu - fu) * u / t[beyond, None] if derivative == 0 else -(bu - fu) * u / t[beyond, None]**2
            return b
        # Fixed-tau Nelson-Siegel: three coefficients, tau=2 years.
        x = t / 2
        g = np.empty_like(x)
        gp = np.empty_like(x)
        small = abs(x) < 1e-5
        g[small] = 1 - x[small] / 2 + x[small]**2 / 6 - x[small]**3 / 24
        gp[small] = -0.5 + x[small] / 3 - x[small]**2 / 8
        g[~small] = -np.expm1(-x[~small]) / x[~small]
        gp[~small] = ((x[~small] + 1) * np.exp(-x[~small]) - 1) / x[~small]**2
        if derivative == 0:
            return np.column_stack([np.ones(len(t)), g, g - np.exp(-x)])
        return np.column_stack([np.zeros(len(t)), gp / 2, (gp + np.exp(-x)) / 2])

    def penalty(self):
        if self.kind == "baseline":
            return np.zeros((0, self.size))
        x = np.linspace(0, np.log1p(self.horizon), 241)
        weights = np.full(len(x), (x[-1] - x[0]) / (len(x) - 1))
        weights[[0, -1]] /= 2
        return self.spline(x, 2) * np.sqrt(weights)[:, None]


class ZeroCurve:
    def __init__(self, basis, beta):
        self.basis = basis
        self.beta = np.asarray(beta, dtype=float)

    def zero(self, times):
        return self.basis.matrix(times) @ self.beta * 1e-4

    def discount(self, times):
        t = np.atleast_1d(np.asarray(times, dtype=float))
        e = -self.zero(t) * t
        if np.any(abs(e) > 700):
            raise ValueError("discount exponent outside safe floating-point range")
        return np.exp(e)

    def forward(self, times):
        t = np.atleast_1d(np.asarray(times, dtype=float))
        return self.zero(t) + t * (self.basis.matrix(t, 1) @ self.beta * 1e-4)

    def to_dict(self):
        return {"kind": self.basis.kind, "horizon": self.basis.horizon, "coefficients_basis_points": self.beta.tolist()}
