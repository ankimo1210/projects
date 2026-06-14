"""ode_book — shared helpers for the ODE notebook textbook.

Layout:
- calculus   : numerical/symbolic calculus foundations (00 章)
- solvers    : Euler / Heun / RK4 steppers + solve_ivp wrapper
- systems    : right-hand-side factories + fixed-point analysis
- plotting   : direction fields, phase portraits, calculus visuals
- widgets    : ipywidgets demos (JupyterLab only)
- interactive: Plotly slider figures (also render in exported HTML)
- advanced    : BVP/shooting, Sturm-Liouville, SDE, LQR/pole-placement, ODE fitting (09 章)
- datasets   : seeded synthetic scenarios, bring-your-own-data hook
"""

from . import advanced, calculus, datasets, interactive, plotting, solvers, systems, widgets
from .solvers import euler, heun, integrate_ode, rk4, solve
from .systems import classify_fixed_point, jacobian, linear_system

__all__ = [
    "advanced",
    "calculus",
    "classify_fixed_point",
    "datasets",
    "euler",
    "heun",
    "integrate_ode",
    "interactive",
    "jacobian",
    "linear_system",
    "plotting",
    "rk4",
    "solve",
    "solvers",
    "systems",
    "widgets",
]

__version__ = "0.1.0"
