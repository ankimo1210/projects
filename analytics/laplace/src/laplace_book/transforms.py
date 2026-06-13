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
def numeric_laplace(f, s_value, t_max: float = 200.0, limit: int = 200):
    """Evaluate F(s) = integral_0^inf f(t) e^{-st} dt numerically.

    ``f`` is a real-valued Python callable f(t). ``s_value`` may be a complex
    scalar or array. For complex s = sigma + i*omega we split

        e^{-st} = e^{-sigma t} (cos(omega t) - i sin(omega t))

    and integrate the real / imaginary parts with ``scipy.integrate.quad``.
    Convergence needs sigma to exceed the abscissa of convergence of f.
    """
    scalar = np.ndim(s_value) == 0
    s_arr = np.atleast_1d(np.asarray(s_value, dtype=complex)).ravel()
    out = np.empty(s_arr.shape, dtype=complex)
    for i, sv in enumerate(s_arr):
        sigma, omega = float(sv.real), float(sv.imag)
        re, _ = quad(lambda x: f(x) * np.exp(-sigma * x) * np.cos(omega * x), 0.0, t_max, limit=limit)
        im, _ = quad(lambda x: -f(x) * np.exp(-sigma * x) * np.sin(omega * x), 0.0, t_max, limit=limit)
        out[i] = complex(re, im)
    return complex(out[0]) if scalar else out.reshape(np.shape(s_value))


def as_function(expr, var=t):
    """Lambdify a SymPy time expression into a NumPy callable on t >= 0."""
    f = sp.lambdify(var, expr, modules=["numpy"])

    def wrapped(x):
        return np.asarray(f(x), dtype=float)

    return wrapped
