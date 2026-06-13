"""Tests for fourier_book.filters."""

import numpy as np
from fourier_book import filters, signals, transforms


def _amp_at(x, fs, freq):
    freqs, amp = transforms.amplitude_spectrum(x, fs)
    return amp[np.argmin(np.abs(freqs - freq))]


def test_lowpass_keeps_low_removes_high():
    fs = 500.0
    t, _ = signals.time_grid(1.0, fs)
    x = signals.sine(t, 5.0, amp=1.0) + signals.sine(t, 80.0, amp=1.0)
    y = filters.lowpass(x, fs, cutoff=20.0)
    assert _amp_at(y, fs, 5.0) > 0.9  # low tone survives
    assert _amp_at(y, fs, 80.0) < 1e-6  # high tone gone


def test_highpass_is_complement():
    fs = 500.0
    t, _ = signals.time_grid(1.0, fs)
    x = signals.sine(t, 5.0) + signals.sine(t, 80.0)
    y = filters.highpass(x, fs, cutoff=20.0)
    assert _amp_at(y, fs, 80.0) > 0.9
    assert _amp_at(y, fs, 5.0) < 1e-6


def test_bandpass_selects_middle_tone():
    fs = 1000.0
    t, _ = signals.time_grid(1.0, fs)
    x = signals.sine(t, 5.0) + signals.sine(t, 50.0) + signals.sine(t, 200.0)
    y = filters.bandpass(x, fs, low=30.0, high=70.0)
    assert _amp_at(y, fs, 50.0) > 0.9
    assert _amp_at(y, fs, 5.0) < 1e-6
    assert _amp_at(y, fs, 200.0) < 1e-6


def test_convolution_theorem_circular():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(64)
    h = rng.standard_normal(64)
    lhs = np.fft.fft(filters.circular_convolve(x, h))
    rhs = np.fft.fft(x) * np.fft.fft(h)
    np.testing.assert_allclose(lhs, rhs, atol=1e-10)


def test_gaussian_kernel_normalised_and_symmetric():
    k = filters.gaussian_kernel(11, sigma=2.0)
    assert np.isclose(k.sum(), 1.0, atol=1e-12)
    np.testing.assert_allclose(k, k[::-1], atol=1e-12)
    assert np.argmax(k) == 5  # peak at center


def test_moving_average_reduces_variance():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(500)
    y = filters.moving_average(x, 11)
    assert len(y) == len(x)
    assert np.var(y) < np.var(x)


def test_smooth_gaussian_preserves_length_and_constant():
    x = np.full(50, 3.0)
    y = filters.smooth_gaussian(x, sigma=2.0)
    assert len(y) == len(x)
    np.testing.assert_allclose(y, 3.0, atol=1e-9)  # smoothing a constant changes nothing


def test_lowpass_mask_values():
    freqs = np.array([-30.0, -10.0, 0.0, 10.0, 30.0])
    m = filters.lowpass_mask(freqs, cutoff=15.0)
    np.testing.assert_array_equal(m, [0.0, 1.0, 1.0, 1.0, 0.0])
