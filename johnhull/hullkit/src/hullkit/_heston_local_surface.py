"""Private Heston marginal and local variance construction for synthetic RB-F04.

The Fourier inversion supplies the log-return density ``f`` and the variance
weighted density ``f_v``. Their ratio is E[v_T | S_T=K], which equals Dupire's
local variance. Positive numerical density alone is not a convergence proof;
the research protocol must refine the frequency cutoff and order separately.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from scipy.special import ndtr, roots_legendre


@dataclass(frozen=True)
class HestonParameters:
    """Finite risk-neutral Heston parameters, allowing the deterministic xi=0 limit."""

    spot: float
    rate: float
    dividend_yield: float
    v0: float
    kappa: float
    theta: float
    xi: float
    rho: float

    def __post_init__(self):
        if not all(math.isfinite(value) for value in vars(self).values()):
            raise ValueError("Heston parameters must be finite")
        if self.spot <= 0 or self.v0 < 0 or self.kappa <= 0 or self.theta <= 0 or self.xi < 0:
            raise ValueError("require spot,kappa,theta>0 and v0,xi>=0")
        if not -1 < self.rho < 1:
            raise ValueError("rho must lie in (-1,1)")

    def integrated_variance(self, t):
        """Return E[integral_0^t v_s ds] in variance times years, including t=0."""
        if not math.isfinite(t) or t < 0:
            raise ValueError("time must be finite and nonnegative")
        return self.theta * t + (self.v0 - self.theta) * -math.expm1(-self.kappa * t) / self.kappa


def _characteristic_terms(u, maturity, parameters):
    u = np.asarray(u, dtype=complex)
    iu = 1j * u
    drift = parameters.rate - parameters.dividend_yield
    if parameters.xi == 0:
        integrated = parameters.integrated_variance(maturity)
        variance = parameters.theta + (parameters.v0 - parameters.theta) * np.exp(
            -parameters.kappa * maturity
        )
        phi = np.exp(iu * drift * maturity - 0.5 * (u * u + iu) * integrated)
        exponent_t = iu * drift - 0.5 * (u * u + iu) * variance
        return phi, phi * exponent_t, np.full(u.shape, variance) * phi
    xi2 = parameters.xi**2
    quadratic = u * u + iu
    b = parameters.kappa - parameters.rho * parameters.xi * iu
    d = np.sqrt(b * b + xi2 * quadratic)
    # Rationalization avoids b-d cancellation at low u and small vol of variance.
    denominator = np.where(quadratic == 0, 1.0, b + d)
    b_minus_d_over_xi2 = -quadratic / denominator
    g = xi2 * b_minus_d_over_xi2 / denominator
    decay = np.exp(-d * maturity)
    log_term = np.log1p(-g * decay) - np.log1p(-g)
    c = iu * drift * maturity + parameters.kappa * parameters.theta * (
        b_minus_d_over_xi2 * maturity - 2 * log_term / xi2
    )
    riccati_d = b_minus_d_over_xi2 * -np.expm1(-d * maturity) / (1 - g * decay)
    phi = np.exp(c + riccati_d * parameters.v0)
    d_t = 0.5 * xi2 * riccati_d**2 - b * riccati_d - 0.5 * quadratic
    variance_exponent = parameters.kappa * parameters.theta * riccati_d + parameters.v0 * d_t
    phi_t = phi * (iu * drift + variance_exponent)
    weighted_phi = np.empty_like(phi)
    np.divide(-2 * phi * variance_exponent, quadratic, out=weighted_phi, where=quadratic != 0)
    # The inversion uses real strictly positive u; zero is useful for CF diagnostics.
    weighted_phi[u == 0] = parameters.theta + (parameters.v0 - parameters.theta) * np.exp(
        -parameters.kappa * maturity
    )
    if np.any(u == -1j):
        tilted_reversion = parameters.kappa - parameters.rho * parameters.xi
        integral = (
            -math.expm1(-tilted_reversion * maturity) / tilted_reversion
            if tilted_reversion != 0
            else maturity
        )
        weighted_phi[u == -1j] = math.exp(drift * maturity) * (
            parameters.v0 * math.exp(-tilted_reversion * maturity)
            + parameters.kappa * parameters.theta * integral
        )
    return phi, phi_t, weighted_phi


def _characteristic_and_time_derivative(u, maturity, parameters):
    """Return the trap-stable log-return CF and its Riccati time derivative."""
    phi, phi_t, _ = _characteristic_terms(u, maturity, parameters)
    return phi, phi_t


@lru_cache(maxsize=12)
def _quadrature(order, maximum):
    # One very high-order panel magnifies its weight roundoff at the far-right
    # tail (density around 1e-9). Composite panels keep that cancellation small.
    panels = min(16, max(1, order // 8))
    width = maximum / panels
    frequencies, scaled_weights = [], []
    for panel in range(panels):
        count = order // panels + int(panel < order % panels)
        nodes, weights = roots_legendre(count)
        frequencies.append((nodes + 1) * width / 2 + panel * width)
        scaled_weights.append(weights * width / (2 * np.pi))
    return np.concatenate(frequencies), np.concatenate(scaled_weights)


def fourier_surface(strikes, T, parameters, order=1024, max_frequency=None, density_floor=1e-10):
    """Return call prices, derivatives and conditional local variance at fixed strikes.

    ``density`` is the density of log(S_T/S0), so ``ckk=exp(-rT)*density/K``.
    ``ct`` is the derivative at fixed strike, obtained from the Riccati equations.
    ``weighted_density`` inverts E[v_T exp(iu log(S_T/S0))]. Raw diagnostics
    are retained at every cell; unsupported cells have NaN local variance.
    Support requires density above ``density_floor``, positive weighted density,
    finite prices/derivatives, <=0.1% density changes against half order, and
    CF/weighted-CF cutoff amplitudes <=1e-10 relative to their zero-frequency
    scales. These diagnostics do not replace independent cutoff refinements.
    The default cutoff is ``512/sqrt(T)`` and Gauss-Legendre excludes u=0.
    """
    strikes = np.asarray(strikes, dtype=float)
    if strikes.size == 0 or not np.all(np.isfinite(strikes)) or np.any(strikes <= 0):
        raise ValueError("strikes must be nonempty, finite and positive")
    if not math.isfinite(T) or T <= 0:
        raise ValueError("maturity must be finite and positive")
    if isinstance(order, bool) or not isinstance(order, (int, np.integer)) or order < 2:
        raise ValueError("order must be an integer >=2")
    if not math.isfinite(density_floor) or density_floor < 0:
        raise ValueError("density_floor must be finite and nonnegative")
    maximum = 512 / math.sqrt(T) if max_frequency is None else max_frequency
    if not math.isfinite(maximum) or maximum <= 0:
        raise ValueError("max_frequency must be finite and positive")
    shape = strikes.shape
    k = strikes.reshape(-1)
    log_strike = np.log(k / parameters.spot)
    drift = parameters.rate - parameters.dividend_yield
    discount = math.exp(-parameters.rate * T)
    spot_discount = parameters.spot * math.exp(-parameters.dividend_yield * T)
    numerically_resolved = np.ones(k.shape, dtype=bool)
    if parameters.xi == 0:
        integrated = parameters.integrated_variance(T)
        standard_deviation = math.sqrt(integrated)
        d1 = (-log_strike + drift * T + 0.5 * integrated) / standard_deviation
        d2 = d1 - standard_deviation
        p1, p2 = ndtr(d1), ndtr(d2)
        density = np.exp(-0.5 * d2**2) / (math.sqrt(2 * np.pi) * standard_deviation)
        terminal_variance = parameters.theta + (parameters.v0 - parameters.theta) * math.exp(
            -parameters.kappa * T
        )
        weighted_density = terminal_variance * density
        price = spot_discount * p1 - k * discount * p2
        ck = -discount * p2
        ct = (
            0.5 * k * discount * weighted_density
            - parameters.dividend_yield * price
            - drift * k * ck
        )
    else:
        u, weights = _quadrature(int(order), float(maximum))
        phi, phi_t, weighted_phi = _characteristic_terms(u, T, parameters)
        phi_shift, phi_shift_t, _ = _characteristic_terms(u - 1j, T, parameters)
        forward = math.exp(drift * T)
        phase = np.exp(-1j * log_strike[:, None] * u)

        def invert(values):
            return np.real(phase * values) @ weights

        p2 = 0.5 + invert(phi / (1j * u))
        p1 = 0.5 + invert(phi_shift / (1j * u * forward))
        p2_t = invert(phi_t / (1j * u))
        p1_t = invert((phi_shift_t - drift * phi_shift) / (1j * u * forward))
        density = invert(phi)
        weighted_density = invert(weighted_phi)
        check_order = max(2, int(order) // 2) if order > 2 else 4
        check_u, check_weights = _quadrature(check_order, float(maximum))
        check_phi, _, check_weighted_phi = _characteristic_terms(check_u, T, parameters)
        check_phase = np.exp(-1j * log_strike[:, None] * check_u)
        check_density = np.real(check_phase * check_phi) @ check_weights
        check_weighted_density = np.real(check_phase * check_weighted_phi) @ check_weights
        numerically_resolved &= np.abs(density - check_density) <= 1e-3 * np.abs(density)
        numerically_resolved &= np.abs(weighted_density - check_weighted_density) <= (
            1e-3 * np.abs(weighted_density)
        )
        end_phi, _, end_weighted_phi = _characteristic_terms(np.array([maximum]), T, parameters)
        numerically_resolved &= (np.abs(end_phi[0]) <= 1e-10) & (
            np.abs(end_weighted_phi[0]) <= 1e-10 * max(parameters.v0, parameters.theta)
        )
        price = spot_discount * p1 - k * discount * p2
        ck = -discount * p2
        ct = spot_discount * (p1_t - parameters.dividend_yield * p1) - k * discount * (
            p2_t - parameters.rate * p2
        )
    ckk = discount * density / k
    supported = (density > density_floor) & (weighted_density > 0) & numerically_resolved
    for value in (price, ck, ckk, ct, density, weighted_density):
        supported &= np.isfinite(value)
    local_variance = np.full(k.shape, np.nan)
    np.divide(weighted_density, density, out=local_variance, where=supported)
    supported &= np.isfinite(local_variance) & (local_variance > 0)
    local_variance[~supported] = np.nan
    return {
        key: value.reshape(shape)
        for key, value in {
            "price": price,
            "ck": ck,
            "ckk": ckk,
            "ct": ct,
            "density": density,
            "weighted_density": weighted_density,
            "local_variance": local_variance,
            "supported": supported,
        }.items()
    }


@dataclass(frozen=True)
class LocalVarianceGrid:
    """Positive variance grid with explicit standardized wings and early-time proxy.

    The z coordinate is (log(S/S0)-(r-q)t)/sqrt(E[integral_0^t v_s ds]).
    Linear interpolation acts on t and z. Outside z, the variance equals the
    nearest supported edge value, with a wing status. Optional ``wing_boundaries``
    are inclusive integer (left_index,right_index) pairs, one per time row. Inside
    each pair all values must be finite and positive; outside values (including
    NaN) remain unchanged. Each row is extended before time interpolation; a
    wing in either active row is labelled, including ``wing_both`` if necessary.
    The retained ``support_mask`` describes the original row interiors.
    For 0<t<min(times), both time and
    the z mapping use min(times); this is a labelled proxy. At t=0 only S=S0
    is defined (variance v0). Times beyond the maximum are unsupported.
    """

    times: np.ndarray
    z_nodes: np.ndarray
    values: np.ndarray
    parameters: HestonParameters
    wing_boundaries: np.ndarray | None = None
    support_mask: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        times = np.array(self.times, dtype=float, copy=True)
        z_nodes = np.array(self.z_nodes, dtype=float, copy=True)
        values = np.array(self.values, dtype=float, copy=True)
        if (
            times.ndim != 1
            or times.size == 0
            or not np.all(np.isfinite(times))
            or np.any(times <= 0)
            or np.any(np.diff(times) <= 0)
        ):
            raise ValueError("times must be a finite, positive, strictly increasing axis")
        if (
            z_nodes.ndim != 1
            or z_nodes.size < 2
            or not np.all(np.isfinite(z_nodes))
            or np.any(np.diff(z_nodes) <= 0)
        ):
            raise ValueError("z_nodes must be a finite, strictly increasing axis of length >=2")
        if values.shape != (times.size, z_nodes.size):
            raise ValueError("values must be a (times,z_nodes) grid")
        boundaries = (
            np.tile([0, z_nodes.size - 1], (times.size, 1))
            if self.wing_boundaries is None
            else np.array(self.wing_boundaries, copy=True)
        )
        if boundaries.shape != (times.size, 2) or boundaries.dtype.kind not in "iu":
            raise ValueError(
                "wing_boundaries must contain an integer (left_index,right_index) pair per row"
            )
        if (
            np.any(boundaries < 0)
            or np.any(boundaries >= z_nodes.size)
            or np.any(boundaries[:, 0] >= boundaries[:, 1])
        ):
            raise ValueError("wing boundaries must be distinct, ordered indices inside the z axis")
        node_indices = np.arange(z_nodes.size)[None, :]
        support_mask = (node_indices >= boundaries[:, :1]) & (node_indices <= boundaries[:, 1:])
        if np.any(support_mask.sum(axis=1) < 2):
            raise ValueError("each supported row must contain at least two nodes")
        if not np.all(np.isfinite(values[support_mask])) or np.any(values[support_mask] <= 0):
            raise ValueError("supported row interiors must be contiguous, finite and positive")
        for name, array in (
            ("times", times),
            ("z_nodes", z_nodes),
            ("values", values),
            ("wing_boundaries", boundaries),
            ("support_mask", support_mask),
        ):
            array.setflags(write=False)
            object.__setattr__(self, name, array)

    def _evaluate_row(self, row, z):
        supported = self.support_mask[row]
        value = np.interp(z, self.z_nodes[supported], self.values[row, supported])
        return (
            value,
            z < self.z_nodes[self.wing_boundaries[row, 0]],
            z > self.z_nodes[self.wing_boundaries[row, 1]],
        )

    def evaluate(self, t, spots):
        """Return shape-preserving variance/status arrays, retaining unsupported states as NaN."""
        if not math.isfinite(t) or t < 0:
            raise ValueError("time must be finite and nonnegative")
        spots = np.asarray(spots, dtype=float)
        shape = spots.shape
        flat_spots = spots.reshape(-1)
        variance = np.full(flat_spots.shape, np.nan)
        status = np.full(flat_spots.shape, "unsupported_spot", dtype="<U32")
        valid = np.isfinite(flat_spots) & (flat_spots > 0)
        if t == 0:
            status[valid] = "unsupported_initial_state"
            initial = valid & (flat_spots == self.parameters.spot)
            variance[initial] = self.parameters.v0
            status[initial] = "initial_state"
        elif t > self.times[-1]:
            status[valid] = "unsupported_time"
        else:
            proxy_time = max(float(t), float(self.times[0]))
            standard_deviation = math.sqrt(self.parameters.integrated_variance(proxy_time))
            z = (
                np.log(flat_spots[valid] / self.parameters.spot)
                - (self.parameters.rate - self.parameters.dividend_yield) * proxy_time
            ) / standard_deviation
            upper = min(
                int(np.searchsorted(self.times, proxy_time, side="right")), self.times.size - 1
            )
            lower = max(0, upper - 1)
            weight = (
                (proxy_time - self.times[lower]) / (self.times[upper] - self.times[lower])
                if upper != lower
                else 0.0
            )
            if weight == 0:
                row_values, left, right = self._evaluate_row(lower, z)
            elif weight == 1:
                row_values, left, right = self._evaluate_row(upper, z)
            else:
                low_values, low_left, low_right = self._evaluate_row(lower, z)
                high_values, high_left, high_right = self._evaluate_row(upper, z)
                row_values = (1 - weight) * low_values + weight * high_values
                left, right = low_left | high_left, low_right | high_right
            variance[valid] = row_values
            labels = np.full(z.shape, "interior", dtype="<U32")
            labels[left] = "wing_left"
            labels[right] = "wing_right"
            labels[left & right] = "wing_both"
            if t < self.times[0]:
                labels = np.where(
                    labels == "interior", "early_time", np.char.add("early_time_", labels)
                )
            status[valid] = labels
        return {"variance": variance.reshape(shape), "status": status.reshape(shape)}
