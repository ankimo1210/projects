"""Smoke tests for laplace_book.plotting (figures build without error)."""

import matplotlib

matplotlib.use("Agg")  # headless: no display needed

import matplotlib.pyplot as plt
import numpy as np
from laplace_book import circuits as C
from laplace_book import plotting as P
from laplace_book import systems as S

T = np.linspace(0, 10, 200)


def teardown_function(_):
    plt.close("all")


def test_plot_exponentials():
    ax = P.plot_exponentials(T, [-0.5, 0.0, 0.5])
    assert isinstance(ax, plt.Axes)


def test_plot_damped_oscillation():
    ax = P.plot_damped_oscillation(T, -0.4, 4.0)
    assert isinstance(ax, plt.Axes)


def test_plot_s_plane_empty_and_with_marks():
    assert isinstance(P.plot_s_plane(), plt.Axes)  # empty is allowed
    ax = P.plot_s_plane(poles=[-1 + 2j, -1 - 2j], zeros=[-3])
    assert isinstance(ax, plt.Axes)


def test_plot_pole_and_response_complex_and_real():
    axes = P.plot_pole_and_response(-0.3, 3.0, T)  # conjugate pair
    assert len(axes) == 2
    axes2 = P.plot_pole_and_response(-0.5, 0.0, T)  # single real pole (omega=0)
    assert len(axes2) == 2


def test_plot_time_responses():
    ax = P.plot_time_responses(T, [np.exp(-T), 1 - np.exp(-T)], labels=["a", "b"])
    assert isinstance(ax, plt.Axes)


def test_plot_convolution():
    dt = T[1] - T[0]
    f = np.exp(-T)
    g = np.exp(-2 * T)
    conv = S.convolve(f, g, dt)
    axes = P.plot_convolution(T, f, g, conv)
    assert len(axes) == 3


def test_plot_bode():
    axes = P.plot_bode(C.rc_lowpass(1000.0, 1e-6), w=np.logspace(1, 6, 100))
    assert len(axes) == 2


def test_plot_root_locus():
    G = S.tf([1.0], [1.0, 1.0, 0.0])  # 1/(s(s+1))
    ax = P.plot_root_locus(G, np.linspace(0, 5, 60))
    assert isinstance(ax, plt.Axes)


def test_surface_abs_F_returns_plotly_figure():
    fig = P.surface_abs_F(lambda Z: 1.0 / ((Z + 1.0) ** 2 + 9.0), n=20)
    assert type(fig).__name__ == "Figure"
    assert len(fig.data) == 1
