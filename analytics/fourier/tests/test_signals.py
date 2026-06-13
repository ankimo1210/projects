"""Tests for fourier_book.signals."""

import numpy as np
from fourier_book import signals


def test_time_grid_length_and_dt():
    t, dt = signals.time_grid(2.0, 100.0)
    assert len(t) == 200
    assert dt == 1.0 / 100.0
    assert t[0] == 0.0
    np.testing.assert_allclose(t[-1], 2.0 - dt)


def test_sine_amplitude_and_period():
    t, _ = signals.time_grid(1.0, 1000.0)
    x = signals.sine(t, freq=5.0, amp=2.0)
    assert np.isclose(np.max(x), 2.0, atol=1e-2)
    # One period is 1/5 s; samples 1/5 s apart should match.
    shift = round(0.2 * 1000.0)
    np.testing.assert_allclose(x[:100], x[shift : shift + 100], atol=1e-9)


def test_complex_exponential_unit_magnitude():
    t = np.linspace(0, 1, 50)
    z = signals.complex_exponential(t, freq=3.0)
    np.testing.assert_allclose(np.abs(z), 1.0, atol=1e-12)
    assert np.isclose(z[0], 1.0 + 0.0j)


def test_harmonic_sum_matches_manual_sum():
    t, _ = signals.time_grid(1.0, 200.0)
    freqs = [2.0, 5.0]
    amps = [1.0, 0.5]
    manual = amps[0] * np.sin(2 * np.pi * freqs[0] * t) + amps[1] * np.sin(2 * np.pi * freqs[1] * t)
    np.testing.assert_allclose(signals.harmonic_sum(t, freqs, amps), manual, atol=1e-12)


def test_square_wave_takes_two_values():
    t, _ = signals.time_grid(1.0, 1000.0)
    x = signals.square_wave(t, freq=3.0)
    assert set(np.unique(np.round(x, 6))).issubset({-1.0, 0.0, 1.0})
    assert np.isclose(np.abs(x).max(), 1.0)


def test_sawtooth_and_triangle_ranges():
    t, _ = signals.time_grid(1.0, 1000.0)
    saw = signals.sawtooth_wave(t, freq=2.0)
    tri = signals.triangle_wave(t, freq=2.0)
    assert saw.min() >= -1.0 - 1e-9 and saw.max() <= 1.0 + 1e-9
    assert tri.min() >= -1.0 - 1e-9 and tri.max() <= 1.0 + 1e-9


def test_square_partial_sum_converges_in_energy():
    t, _ = signals.time_grid(1.0, 4000.0)
    target = signals.square_wave(t, freq=3.0)
    err_small = np.mean((signals.square_wave_partial_sum(t, 3.0, 2) - target) ** 2)
    err_large = np.mean((signals.square_wave_partial_sum(t, 3.0, 30) - target) ** 2)
    assert err_large < err_small  # more harmonics -> closer in mean-square


def test_gaussian_pulse_peaks_at_center():
    t = np.linspace(-5, 5, 501)
    g = signals.gaussian_pulse(t, t0=1.0, width=0.5, amp=3.0)
    assert np.isclose(t[np.argmax(g)], 1.0, atol=0.05)
    assert np.isclose(g.max(), 3.0, atol=1e-6)


def test_add_noise_reproducible_and_hits_target_snr():
    t, _ = signals.time_grid(2.0, 2000.0)
    clean = signals.sine(t, 10.0)
    a = signals.add_noise(clean, snr_db=10.0, seed=1)
    b = signals.add_noise(clean, snr_db=10.0, seed=1)
    np.testing.assert_array_equal(a, b)  # same seed -> identical
    noise = a - clean
    measured = 10 * np.log10(np.mean(clean**2) / np.mean(noise**2))
    assert abs(measured - 10.0) < 1.0  # within 1 dB
