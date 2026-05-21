"""VisPy 3D renderer for an N-body simulation."""

from __future__ import annotations

from typing import Callable

import cupy as cp
import numpy as np
from vispy import app, scene
from vispy.scene.visuals import Text

from .stars_visual import Stars


class NBodyCanvas:
    """A self-contained interactive 3D canvas.

    Particles are drawn with a custom GLSL visual (`StarsVisual`) that renders
    each point as an additive Gaussian sprite coloured via an in-shader magma
    LUT. Overlapping particles brighten naturally, giving a nebula look.

    The GUI event loop drives the simulation: each timer tick we advance
    `step_fn` and re-upload the positions/speeds to the vertex buffer. The
    cp→np copy each frame is the only CPU bottleneck and can later be replaced
    with CUDA-GL interop.
    """

    def __init__(
        self,
        step_fn: Callable[[int], None],
        pos_view: Callable[[], cp.ndarray],
        vel_view: Callable[[], cp.ndarray],
        energy_fn: Callable[[], float] | None = None,
        n_particles: int = 0,
        steps_per_frame: int = 4,
        point_size: float = 80.0,
        bg: str = "#02030a",
        title: str = "nbody-gpu",
    ) -> None:
        self.step_fn = step_fn
        self.pos_view = pos_view
        self.vel_view = vel_view
        self.energy_fn = energy_fn
        self.steps_per_frame = steps_per_frame
        self.n = n_particles

        self.canvas = scene.SceneCanvas(
            keys="interactive", bgcolor=bg, show=True, size=(1200, 800), title=title
        )
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = scene.cameras.ArcballCamera(fov=45, distance=6.0)

        self.stars = Stars(parent=self.view.scene)
        self.stars.set_base_size(point_size)
        # Empirically, sprites smaller than ~1.5px alias badly with additive
        # blending; capping at ~120px stops one bright particle from filling
        # the screen when the camera zooms in.
        self.stars.set_size_clamp(1.5, 120.0)

        self.hud = Text(
            "",
            parent=self.canvas.scene,
            color=(0.85, 0.9, 1.0, 0.9),
            anchor_x="left",
            anchor_y="top",
            pos=(10, 10),
            font_size=10,
            bold=False,
        )

        # FPS estimation (EMA over frame times).
        self._last_t = None
        self._ema_fps = 0.0
        self._frame = 0
        self._E0: float | None = None
        self._speed_range_locked = False

        self._timer = app.Timer(interval=0.0, connect=self._on_timer, start=True)
        self._update_particles()  # initial draw

    def _update_particles(self) -> None:
        pos_d = self.pos_view()
        vel_d = self.vel_view()
        pos_h = cp.asnumpy(pos_d)
        speed = cp.asnumpy(cp.linalg.norm(vel_d, axis=1))

        if not self._speed_range_locked:
            # Lock the colour-mapping range once from the initial distribution
            # so the palette doesn't shift around as the cluster relaxes.
            lo = float(np.percentile(speed, 5))
            hi = float(np.percentile(speed, 99))
            if hi <= lo:
                hi = lo + 1e-6
            self.stars.set_speed_range(lo, hi)
            self._speed_range_locked = True

        self.stars.set_data(pos_h, speed)

    def _on_timer(self, event) -> None:
        import time

        self.step_fn(self.steps_per_frame)
        self._update_particles()

        now = time.perf_counter()
        if self._last_t is not None:
            dt = now - self._last_t
            fps = 1.0 / dt if dt > 0 else 0.0
            self._ema_fps = 0.9 * self._ema_fps + 0.1 * fps if self._ema_fps else fps
        self._last_t = now
        self._frame += 1

        if self._frame % 5 == 0:
            energy_str = ""
            if self.energy_fn is not None and self._frame % 60 == 0:
                E = self.energy_fn()
                if self._E0 is None:
                    self._E0 = E
                drift = abs(E - self._E0) / max(abs(self._E0), 1e-30)
                energy_str = f" | E={E:.4e}  ΔE/E={drift:.2e}"
            self.hud.text = (
                f"N={self.n}  steps/frame={self.steps_per_frame}  "
                f"FPS={self._ema_fps:5.1f}{energy_str}\n"
                f"controls: drag=rotate  scroll=zoom  shift+drag=pan  q=quit"
            )

    def run(self) -> None:
        app.run()
