"""fourier_book — shared helpers for the Fourier-analysis notebook textbook.

Modules:
    signals      pure tones, complex exponentials, classic periodic waves
    transforms   DFT/FFT, Fourier-series coefficients, STFT
    filters      frequency masks, convolution, smoothing kernels
    spectral     Fourier (spectral) methods for periodic PDEs
    datasets     synthetic, download-free sample data
    plotting     matplotlib helpers (English labels)
    widgets      ipywidgets interactive demos (guarded import)
"""

from . import datasets, filters, plotting, signals, spectral, transforms, widgets

__all__ = [
    "datasets",
    "filters",
    "plotting",
    "signals",
    "spectral",
    "transforms",
    "widgets",
]

__version__ = "0.1.0"
