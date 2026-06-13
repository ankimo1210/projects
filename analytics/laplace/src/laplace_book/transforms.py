"""Laplace transform helpers: symbolic (SymPy) and numeric (quadrature).

The notebooks treat the Laplace transform as a *tool* that moves a function of
time t into a function of the complex frequency s. This module keeps the two
complementary views in one place:

* symbolic  -- ``L`` / ``Linv`` wrap SymPy so the algebra (derivative rule,
  partial fractions) is exact and inspectable;
* numeric   -- ``numeric_laplace`` evaluates F(s) = integral_0^inf f(t)e^{-st} dt
  by quadrature, so we can *see* the transform as an integral and overlay it on
  the symbolic answer.

Math labels in figures are English; the Japanese explanation lives in the
notebook prose (so no Japanese-font setup is needed).
"""

from __future__ import annotations

import math
import warnings

import numpy as np
import sympy as sp
from scipy.integrate import quad

# Canonical symbols shared across the book. ``t`` is the (one-sided) time
# variable, ``s = sigma + i*omega`` the complex frequency.
t = sp.symbols("t", positive=True)
s = sp.symbols("s")


# --------------------------------------------------------------------------- #
# Symbolic transform pair.
# --------------------------------------------------------------------------- #
def L(expr, var=t, svar=s):
    """Forward Laplace transform L{f(t)} -> F(s) (conditions dropped)."""
    return sp.laplace_transform(expr, var, svar, noconds=True)


def Linv(F, svar=s, var=t):
    """Inverse Laplace transform L^{-1}{F(s)} -> f(t).

    The result is usually written with ``Heaviside(t)`` because the one-sided
    transform only constrains f for t >= 0.
    """
    return sp.inverse_laplace_transform(F, svar, var)


def partial_fractions(F, svar=s):
    """Partial-fraction expansion of a rational F(s) -- the key inversion trick."""
    return sp.apart(F, svar)


def verify_derivative_rule(expr, var=t, svar=s) -> bool:
    """Check L{f'} = s F(s) - f(0) symbolically for a concrete f.

    This is *the* property that turns differentiation into multiplication by s
    (and lets initial conditions enter naturally).
    """
    F = L(expr, var, svar)
    lhs = L(sp.diff(expr, var), var, svar)
    rhs = svar * F - expr.subs(var, 0)
    return sp.simplify(lhs - rhs) == 0


# --------------------------------------------------------------------------- #
# Transform table (for display and for round-trip tests).
# --------------------------------------------------------------------------- #
def laplace_pairs():
    """Return analytically-verifiable (f(t), F(s), description) SymPy pairs.

    The impulse delta(t) is intentionally excluded: with ``t`` declared positive,
    SymPy collapses ``DiracDelta(t)`` to 0, and the delta is a distribution best
    handled separately (see ``transform_table_df`` and chapter 05).
    """
    a = sp.symbols("a", positive=True)
    w = sp.symbols("omega", positive=True)
    n = sp.symbols("n", positive=True, integer=True)
    return [
        (sp.Integer(1), 1 / s, "unit step (t>=0)"),
        (t, 1 / s**2, "ramp"),
        (t**n, sp.factorial(n) / s ** (n + 1), "power t^n"),
        (sp.exp(-a * t), 1 / (s + a), "exponential decay"),
        (sp.sin(w * t), w / (s**2 + w**2), "sine"),
        (sp.cos(w * t), s / (s**2 + w**2), "cosine"),
        (sp.exp(-a * t) * sp.sin(w * t), w / ((s + a) ** 2 + w**2), "damped sine"),
        (sp.exp(-a * t) * sp.cos(w * t), (s + a) / ((s + a) ** 2 + w**2), "damped cosine"),
    ]


def transform_table_df():
    """The transform table as a pandas DataFrame of LaTeX strings (for notebooks).

    Adds the impulse pair delta(t) -> 1 as a display-only row (it is a
    distribution, so it is not part of the symbolically-verified ``laplace_pairs``).
    """
    import pandas as pd

    rows = [
        {"f(t)": f"${sp.latex(f)}$", "F(s)": f"${sp.latex(F)}$", "note": note}
        for f, F, note in laplace_pairs()
    ]
    rows.append({"f(t)": r"$\delta(t)$", "F(s)": "$1$", "note": "impulse"})
    return pd.DataFrame(rows)


def verify_pair(f, F, var=t, svar=s) -> bool:
    """True if L{f} simplifies to F (used to test the table entries)."""
    return sp.simplify(L(f, var, svar) - F) == 0


# --------------------------------------------------------------------------- #
# Numeric transform: F(s) as an integral.
# --------------------------------------------------------------------------- #
def numeric_laplace(f, s_value, t_max: float = 200.0, limit: int = 200, warn: bool = True):
    """Evaluate F(s) = integral_0^inf f(t) e^{-st} dt numerically.

    ``f`` is a real-valued Python callable f(t). ``s_value`` may be a complex
    scalar or array. For complex s = sigma + i*omega we split

        e^{-st} = e^{-sigma t} (cos(omega t) - i sin(omega t))

    and integrate g(t) = f(t) e^{-sigma t} against cos / sin. The oscillatory
    pieces use ``scipy.integrate.quad``'s dedicated weighted integrator
    (``weight="cos"/"sin"``), which stays accurate even for large omega where a
    plain quad would alias. Convergence needs sigma to exceed the abscissa of
    convergence of f; if the integrand has not decayed by ``t_max`` (a sign that
    s is outside the region of convergence) a warning is issued.
    """
    scalar = np.ndim(s_value) == 0
    s_arr = np.atleast_1d(np.asarray(s_value, dtype=complex)).ravel()
    out = np.empty(s_arr.shape, dtype=complex)
    for i, sv in enumerate(s_arr):
        sigma, omega = float(sv.real), float(sv.imag)

        def g(x, _sigma=sigma):
            return f(x) * np.exp(-_sigma * x)

        if abs(omega) < 1e-12:
            re, _ = quad(g, 0.0, t_max, limit=limit)
            im = 0.0
        else:
            re, _ = quad(g, 0.0, t_max, weight="cos", wvar=omega, limit=limit)
            im_pos, _ = quad(g, 0.0, t_max, weight="sin", wvar=omega, limit=limit)
            im = -im_pos
        out[i] = complex(re, im)

        if warn:
            env_end = abs(g(t_max))
            env_ref = max(abs(g(0.0)), abs(g(0.5 * t_max)), 1e-300)
            if env_end > 1e-3 * env_ref:
                warnings.warn(
                    f"numeric_laplace: integrand has not decayed at t_max={t_max} for s={sv} "
                    f"(|f e^-st|={env_end:.3g}); result may be inaccurate or s may be outside the ROC.",
                    stacklevel=2,
                )
    return complex(out[0]) if scalar else out.reshape(np.shape(s_value))


# --------------------------------------------------------------------------- #
# Numerical inverse transforms: f(t) from F(s) given only as a callable.
# --------------------------------------------------------------------------- #
def _stehfest_coeffs(N: int) -> np.ndarray:
    """Gaver-Stehfest weights V_1..V_N (N even). 1-indexed; index 0 unused."""
    if N % 2 != 0:
        raise ValueError("Gaver-Stehfest needs an even N")
    half = N // 2
    V = np.zeros(N + 1)
    for k in range(1, N + 1):
        total = 0.0
        for j in range((k + 1) // 2, min(k, half) + 1):
            total += (
                j**half
                * math.factorial(2 * j)
                / (
                    math.factorial(half - j)
                    * math.factorial(j)
                    * math.factorial(j - 1)
                    * math.factorial(k - j)
                    * math.factorial(2 * j - k)
                )
            )
        V[k] = (-1) ** (k + half) * total
    return V


def inverse_laplace_stehfest(F, t, N: int = 14):
    """Numerically invert F(s) at time(s) t via the Gaver-Stehfest algorithm.

    Only samples F on the positive real axis, so it is simple and fast, but it
    is best for smooth, non-oscillatory f(t); it degrades badly on oscillations
    or jumps (a good illustration of why numerical inversion is hard). ``N`` must
    be even (12-16 is the sweet spot in double precision).
    """
    V = _stehfest_coeffs(N)
    ln2 = math.log(2.0)
    t = np.asarray(t, dtype=float)
    scalar = t.ndim == 0
    tt = np.atleast_1d(t)
    out = np.full(tt.shape, np.nan)
    ks = np.arange(1, N + 1)
    for idx, tv in enumerate(tt):
        if tv <= 0:
            continue
        s = ks * ln2 / tv
        out[idx] = (ln2 / tv) * np.sum(V[1:] * np.real(F(s)))
    return float(out[0]) if scalar else out


def inverse_laplace_talbot(F, t, M: int = 48):
    """Numerically invert F(s) at time(s) t via the fixed Talbot method.

    Deforms the Bromwich contour into the left half-plane (Abate & Valko, 2004),
    which handles oscillatory and decaying f(t) far better than Gaver-Stehfest.
    ``M`` is the number of contour nodes (~32-48 in double precision).
    """
    t = np.asarray(t, dtype=float)
    scalar = t.ndim == 0
    tt = np.atleast_1d(t)
    out = np.full(tt.shape, np.nan)
    k = np.arange(1, M)
    theta = k * np.pi / M
    cot = 1.0 / np.tan(theta)
    delta_k = (2.0 * k * np.pi / 5.0) * (cot + 1j)
    gamma_k = (1.0 + 1j * theta * (1.0 + cot**2) - 1j * cot) * np.exp(delta_k)
    delta_0 = 2.0 * M / 5.0
    for idx, tv in enumerate(tt):
        if tv <= 0:
            continue
        term0 = 0.5 * np.exp(delta_0) * np.real(F(delta_0 / tv))
        terms = np.real(gamma_k * F(delta_k / tv))
        out[idx] = (2.0 / (5.0 * tv)) * (term0 + np.sum(terms))
    return float(out[0]) if scalar else out


def as_function(expr, var=t):
    """Lambdify a SymPy time expression into a NumPy callable on t >= 0."""
    f = sp.lambdify(var, expr, modules=["numpy"])

    def wrapped(x):
        return np.asarray(f(x), dtype=float)

    return wrapped
