"""In-process Python sandbox for Claude-generated analysis code.

Captures stdout and Plotly figures via monkey-patching fig.show().
Runs with a 60-second timeout enforced by threading.Timer.
"""

from __future__ import annotations

import io
import sys
import threading
import traceback
from typing import Any


def run(code: str) -> dict[str, Any]:
    """Execute code and return {"output": str, "figures": [json_str], "error": str|None}."""
    figures: list[str] = []
    stdout_buf = io.StringIO()
    error: str | None = None

    def _show_capture(fig, *args, **kwargs):
        figures.append(fig.to_json())

    sandbox_globals: dict[str, Any] = {
        "__builtins__": __builtins__,
    }

    # Inject allowed modules
    try:
        import numpy as np
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        import plotly.io as pio
        from stockkit.data import get_jp_cpi as _get_jp_cpi
        from stockkit.data import get_macro as _get_macro
        from stockkit.data import get_prices as _get_prices

        # Wrap with use_cache=False to avoid DuckDB concurrent-access issues in sandbox threads
        def get_prices(symbol, period="1y", **kw):
            return _get_prices(symbol, period=period, use_cache=False, source="yfinance", **kw)

        def get_macro(series_id, start=None, **kw):
            return _get_macro(series_id, start=start, use_cache=False, **kw)

        def get_jp_cpi(start=None, **kw):
            return _get_jp_cpi(start=start, use_cache=False, **kw)

        sandbox_globals.update(
            {
                "pd": pd,
                "pandas": pd,
                "np": np,
                "numpy": np,
                "go": go,
                "px": px,
                "plotly": __import__("plotly"),
                "get_prices": get_prices,
                "get_macro": get_macro,
                "get_jp_cpi": get_jp_cpi,
            }
        )
    except ImportError as e:
        return {"output": "", "figures": [], "error": f"Import error: {e}"}

    timed_out = threading.Event()

    def _run():
        nonlocal error
        old_stdout = sys.stdout
        old_show = None
        try:
            import plotly.io as pio

            old_show = pio.show
            pio.show = _show_capture

            sys.stdout = stdout_buf
            exec(code, sandbox_globals)
        except Exception:
            error = traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            if old_show is not None:
                try:
                    import plotly.io as pio

                    pio.show = old_show
                except Exception:
                    pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=60)

    if t.is_alive():
        timed_out.set()
        return {
            "output": stdout_buf.getvalue(),
            "figures": figures,
            "error": "Timeout: execution exceeded 60 seconds",
        }

    return {
        "output": stdout_buf.getvalue(),
        "figures": figures,
        "error": error,
    }
