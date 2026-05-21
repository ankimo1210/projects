"""Glue between Simulation and NBodyCanvas."""

from __future__ import annotations

from nbody import Simulation
from .renderer import NBodyCanvas


def run_simulation(
    sim: Simulation,
    steps_per_frame: int = 4,
    point_size: float = 3.0,
    show_energy: bool = True,
    title: str = "nbody-gpu",
) -> None:
    canvas = NBodyCanvas(
        step_fn=sim.step,
        pos_view=lambda: sim.pos,
        vel_view=lambda: sim.vel,
        energy_fn=sim.total_energy if show_energy else None,
        n_particles=sim.n,
        steps_per_frame=steps_per_frame,
        point_size=point_size,
        title=title,
    )
    canvas.run()
