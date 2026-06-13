"""Tests for fourier_book.transforms."""

import numpy as np
from fourier_book import signals, transforms


def test_dft_matches_numpy_fft():
    rng = np.random.default_rng(0)
    x = rng.standard_normal(16)
    np.testing.assert_allclose(transforms.dft(x), np.fft.fft(x), atol=1e-10)


def test_idft_inverts_dft():
    rng = np.random.default_rng(1)
    x = rng.standard_normal(32) + 1j * rng.standard_normal(32)
    np.testing.assert_allclose(transforms.idft(transforms.dft(x)), x, atol=1e-10)


def test_dft_matrix_is_orthogonal_up_to_scale():
    n = 12
    w = transforms.dft_matrix(n)
    # (1/N) W^H W = I.
    np.testing.assert_allclose(w.conj().T @ w / n, np.eye(n), atol=1e-10)


def test_amplitude_spectrum_recovers_tone_amplitude():
    fs = 128.0
    t, _ = signals.time_grid(1.0, fs)  # N = 128, 1 Hz bins
    x = signals.sine(t, freq=8.0, amp=2.0) + signals.sine(t, freq=20.0, amp=0.5)
    freqs, amp = transforms.amplitude_spectrum(x, fs)
    assert np.isclose(amp[np.argmin(np.abs(freqs - 8.0))], 2.0, atol=1e-6)
    assert np.isclose(amp[np.argmin(np.abs(freqs - 20.0))], 0.5, atol=1e-6)


def test_parseval_for_dft():
    rng = np.random.default_rng(2)
    x = rng.standard_normal(64)
    spectrum = np.fft.fft(x)
    np.testing.assert_allclose(np.sum(x**2), np.sum(np.abs(spectrum) ** 2) / len(x), atol=1e-9)


def test_fourier_series_coeffs_of_cosine():
    # cos(t) over [0, 2π): c_{+1} = c_{-1} = 1/2, the rest ~ 0.
    ns, c = transforms.fourier_series_coeffs(np.cos, n_max=4, period=2 * np.pi)
    idx = {n: i for i, n in enumerate(ns)}
    assert np.isclose(c[idx[1]], 0.5, atol=1e-10)
    assert np.isclose(c[idx[-1]], 0.5, atol=1e-10)
    assert np.isclose(c[idx[2]], 0.0, atol=1e-10)


def test_trig_coeffs_of_cosine_harmonic():
    a, b = transforms.trig_coeffs(lambda t: np.cos(2 * t), n_max=5, period=2 * np.pi)
    assert np.isclose(a[2], 1.0, atol=1e-10)
    assert np.allclose(np.delete(a, 2), 0.0, atol=1e-10)
    assert np.allclose(b, 0.0, atol=1e-10)


def test_reconstruct_trig_round_trip():
    period = 2 * np.pi

    def f(t):
        return 0.7 + 1.3 * np.cos(t) - 0.4 * np.sin(2 * t) + 0.2 * np.cos(3 * t)

    a, b = transforms.trig_coeffs(f, n_max=4, period=period)
    t = np.linspace(0, period, 200, endpoint=False)
    np.testing.assert_allclose(transforms.reconstruct_trig(a, b, t, period), f(t), atol=1e-9)


def test_reconstruct_complex_round_trip():
    period = 2 * np.pi

    def f(t):
        return np.cos(t) + 0.5 * np.sin(3 * t)

    ns, c = transforms.fourier_series_coeffs(f, n_max=5, period=period)
    t = np.linspace(0, period, 200, endpoint=False)
    np.testing.assert_allclose(transforms.reconstruct_complex(ns, c, t, period), f(t), atol=1e-9)


def test_stft_istft_round_trip_interior():
    fs = 1000.0
    t, _ = signals.time_grid(1.0, fs)
    x = signals.chirp(t, 10.0, 200.0, duration=1.0)
    f, tt, z = transforms.stft(x, fs, nperseg=128)
    xr = transforms.istft(z, fs, nperseg=128)
    n = min(len(x), len(xr))
    # COLA Hann + 50% overlap reconstructs the interior to high precision.
    np.testing.assert_allclose(xr[128 : n - 128], x[128 : n - 128], atol=1e-6)
    assert z.shape[0] == len(f)
    assert z.shape[1] == len(tt)


def test_amplitude_spectrum_recovers_cosine():
    fs = 128.0
    t, _ = signals.time_grid(1.0, fs)
    x = signals.cosine(t, freq=8.0, amp=2.0)
    freqs, amp = transforms.amplitude_spectrum(x, fs)
    assert np.isclose(amp[np.argmin(np.abs(freqs - 8.0))], 2.0, atol=1e-6)


def test_amplitude_spectrum_calibration_matches_power():
    # Peak amplitude = A, and the sine's mean-square power = A^2 / 2, must agree.
    fs = 256.0
    t, _ = signals.time_grid(1.0, fs)
    a = 1.7
    x = signals.sine(t, 20.0, amp=a)
    _, amp = transforms.amplitude_spectrum(x, fs)
    assert np.isclose(amp.max(), a, atol=1e-6)
    assert np.isclose(amp.max() ** 2 / 2, np.mean(x**2), atol=1e-6)
