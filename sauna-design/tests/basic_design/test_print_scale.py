import pytest


@pytest.mark.parametrize("scale,length_m,expected_mm", [(100, 1.0, 10.0), (20, 0.5, 25.0)])
def test_drawing_has_the_claimed_physical_scale(scale, length_m, expected_mm):
    from basic_design.plans import plan_axes, plt

    fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4), dpi=100)
    fig._paper_mm = (420, 297)
    ax = plan_axes(fig, 18, 50, (0, 0, 4, 3), scale)
    fig.canvas.draw()
    a = ax.transData.transform((0, 0))
    b = ax.transData.transform((length_m, 0))
    assert (b[0] - a[0]) / fig.dpi * 25.4 == pytest.approx(expected_mm)
    plt.close(fig)
