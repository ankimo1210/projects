"""A VisPy Visual that draws particles as Gaussian point sprites.

Uses additive blending (so overlapping particles brighten the pixel) and
colours each point via an in-shader polynomial fit of matplotlib's magma
colormap (Matt Zucker fit). Sizes shrink with depth for a perspective feel.
"""
from __future__ import annotations

import numpy as np
from vispy.visuals import Visual
from vispy.scene.visuals import create_visual_node


_VERT = """
attribute vec3 a_position;
attribute float a_speed;

uniform float u_base_size;     // pixel size at unit depth
uniform float u_speed_min;
uniform float u_speed_max;
uniform float u_size_min;      // floor in pixels
uniform float u_size_max;      // ceiling in pixels

varying float v_t;

void main(void) {
    gl_Position = $transform(vec4(a_position, 1.0));
    // Perspective sizing: closer particles draw larger.
    float depth = max(abs(gl_Position.w), 1e-3);
    float size = u_base_size / depth;
    gl_PointSize = clamp(size, u_size_min, u_size_max);
    v_t = clamp((a_speed - u_speed_min) / (u_speed_max - u_speed_min + 1e-6),
                0.0, 1.0);
}
"""

_FRAG = """
varying float v_t;

// magma colormap polynomial fit (Matt Zucker, public domain).
vec3 magma(float t) {
    const vec3 c0 = vec3(-0.002136485053939, -0.000749655052795, -0.005386127855323);
    const vec3 c1 = vec3( 0.251660540737164,  0.677523243683767,  2.494026599312351);
    const vec3 c2 = vec3( 8.353717279216625, -3.577719514958484,  0.314467903013257);
    const vec3 c3 = vec3(-27.66873308576866, 14.26473078096533, -13.64921318813922);
    const vec3 c4 = vec3( 52.17613981234068,-27.94360607168351,  12.94416944238394);
    const vec3 c5 = vec3(-50.76863182127939, 29.04658282127291,   4.23415299384310);
    const vec3 c6 = vec3( 18.65570506591883,-11.48977351997711,  -5.60196150873410);
    return c0+t*(c1+t*(c2+t*(c3+t*(c4+t*(c5+t*c6)))));
}

void main(void) {
    vec2 d = 2.0 * gl_PointCoord - 1.0;
    float r2 = dot(d, d);
    if (r2 > 1.0) discard;
    // Gaussian intensity, peaks at the centre and falls smoothly to zero.
    float intensity = exp(-4.5 * r2);
    vec3 col = magma(v_t);
    // Pre-multiplied alpha + additive blending => stacked particles brighten.
    gl_FragColor = vec4(col * intensity, intensity);
}
"""


class StarsVisual(Visual):
    """Per-particle Gaussian point sprite visual.

    Use `set_data(pos, speed)` once per frame. The colour mapping range
    `set_speed_range(lo, hi)` is usually called once at startup; updating it
    every frame causes the palette to wobble as the dynamic range changes.
    """

    def __init__(self):
        Visual.__init__(self, vcode=_VERT, fcode=_FRAG)
        self._draw_mode = "points"
        self.set_gl_state(
            preset=None,
            blend=True,
            blend_func=("src_alpha", "one"),  # additive
            depth_test=False,
            cull_face=False,
        )
        self.shared_program["u_base_size"] = np.float32(80.0)
        self.shared_program["u_speed_min"] = np.float32(0.0)
        self.shared_program["u_speed_max"] = np.float32(1.0)
        self.shared_program["u_size_min"] = np.float32(2.0)
        self.shared_program["u_size_max"] = np.float32(60.0)
        self._n = 0

    def set_data(self, pos: np.ndarray, speed: np.ndarray) -> None:
        from vispy.gloo import VertexBuffer
        pos = np.ascontiguousarray(pos, dtype=np.float32)
        speed = np.ascontiguousarray(speed, dtype=np.float32)
        self.shared_program["a_position"] = VertexBuffer(pos)
        self.shared_program["a_speed"] = VertexBuffer(speed)
        self._n = pos.shape[0]

    def set_speed_range(self, lo: float, hi: float) -> None:
        self.shared_program["u_speed_min"] = np.float32(lo)
        self.shared_program["u_speed_max"] = np.float32(hi)

    def set_base_size(self, s: float) -> None:
        self.shared_program["u_base_size"] = np.float32(s)

    def set_size_clamp(self, lo: float, hi: float) -> None:
        self.shared_program["u_size_min"] = np.float32(lo)
        self.shared_program["u_size_max"] = np.float32(hi)

    def _prepare_transforms(self, view) -> None:
        view.view_program.vert["transform"] = view.get_transform()

    def _prepare_draw(self, view) -> bool:
        # nothing per-draw beyond the standard pipeline
        return self._n > 0


Stars = create_visual_node(StarsVisual)
