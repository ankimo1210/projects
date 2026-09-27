"""Execute the notebook headlessly, with widget callbacks forced to run and to raise."""

from pathlib import Path

import nbformat
import pytest
from nbclient import NotebookClient

NOTEBOOK = Path(__file__).resolve().parents[1] / "rates_volatility_models.ipynb"

# ipywidgets swallows exceptions in two places: interact() shows them inside the
# widget, and `with Output():` prints the traceback and suppresses it. A plain
# headless run therefore stays green even when every interactive cell is broken
# (the np.trapz crash in the HJM chapter was invisible this way).
_PREAMBLE = """
import matplotlib
matplotlib.use("Agg")
import ipywidgets as _w

def _interact_now(f, **kwargs):
    f(**{k: (v.value if hasattr(v, "value") else v) for k, v in kwargs.items()})
    return f

class _RaisingOutput(_w.Output):
    def __exit__(self, etype, evalue, tb):
        super().__exit__(None, None, None)
        return False

_w.interact = _interact_now
_w.Output = _RaisingOutput
"""


@pytest.mark.xfail(strict=True, reason="HJM chapter still calls np.trapz until Task 6")
def test_notebook_executes_without_errors():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nb.cells.insert(0, nbformat.v4.new_code_cell(_PREAMBLE))
    # raises CellExecutionError, with the failing cell's traceback, on the first error
    NotebookClient(nb, timeout=600, kernel_name="python3").execute()
