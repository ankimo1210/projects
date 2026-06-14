"""Smoke tests for fourier_book.plotting.

These assert the shared figure helpers build without error (no display needed —
the helpers never call plt.show(); figures are closed after each test).
"""

import matplotlib.pyplot as plt
import numpy as np
from fourier_book import plotting, signals, spectral, transforms


def teardown_function(_):
    plt.close("all")


def test_plot_time_and_freq():
    t, _ = signals.time_grid(1.0, 200.0)
    x = signals.sine(t, 5.0)
    freqs, amp = transforms.amplitude_spectrum(x, 200.0)
    _, axes = plotting.plot_time_and_freq(t, x, freqs, amp)
    assert len(axes) == 2


def test_plot_projection():
    x = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    f = 1 + 2 * np.cos(2 * x)
    ax = plotting.plot_projection(x, f, np.cos(2 * x), 2.0, basis_label="cos 2x")
    assert ax is not None


def test_plot_spacetime_shape():
    x = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    ts = np.linspace(0, 1, 20)
    field = np.array([spectral.solve_heat_spectral(np.sin(x), 2 * np.pi, 0.1, t) for t in ts])
    plotting.plot_spacetime(field, x, ts)
    assert field.shape == (20, 64)


def test_plot_window_comparison():
    _, ax = plotting.plot_window_comparison(n=64)
    assert len(ax) == 2


def test_plot_tf_tiling():
    _, ax = plotting.plot_tf_tiling()
    assert len(ax) == 2


def test_plot_convolution_slide():
    t, _ = signals.time_grid(2.0, 100.0)
    f = ((t > 0.3) & (t < 0.8)).astype(float)
    g = np.exp(-((t - 1.0) ** 2) / (2 * 0.02))
    _, ax = plotting.plot_convolution_slide(t, f, g)
    assert len(ax) == 3


def test_plot_partial_sums_and_spectrum():
    t, _ = signals.time_grid(1.0, 500.0)
    partials = [signals.square_wave_partial_sum(t, 3.0, k) for k in (1, 5)]
    _, ax = plotting.plot_partial_sums(t, partials, [1, 5], target=signals.square_wave(t, 3.0))
    freqs, amp = transforms.amplitude_spectrum(signals.sine(t, 5.0), 500.0)
    ax2 = plotting.plot_spectrum(freqs, amp, stem=False)
    assert ax is not None and ax2 is not None
