"""pde_book — shared helpers for the PDE notebook textbook.

Layout:
- calculus   : numerical/symbolic calculus foundations (00 章, shared with ODE book)
- grids      : 1-D/2-D grids, stencils, CFL / diffusion numbers
- solvers    : FDM solvers (heat, transport, wave, Poisson) + Fourier helpers
- plotting   : calculus visuals + field snapshots, heatmaps, animations
- widgets    : ipywidgets demos (JupyterLab only)
- datasets   : initial/boundary conditions, sample fields
"""

from . import calculus, datasets, grids, plotting, solvers, widgets
from .grids import Grid1D, Grid2D, courant_number, heat_number
from .solvers import (
    solve_heat_explicit,
    solve_heat_implicit,
    solve_poisson_2d,
    solve_transport,
    solve_wave,
)

__all__ = [
    "Grid1D",
    "Grid2D",
    "calculus",
    "courant_number",
    "datasets",
    "grids",
    "heat_number",
    "plotting",
    "solve_heat_explicit",
    "solve_heat_implicit",
    "solve_poisson_2d",
    "solve_transport",
    "solve_wave",
    "solvers",
    "widgets",
]

__version__ = "0.1.0"
