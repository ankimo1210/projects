"""CLI: build the analytics portal.

Run from the workspace with the report dir on the path, e.g.::

    PYTHONPATH=analytics/report uv run python -m report_builder.build

or simply ``make report`` from the repo root.
"""

from __future__ import annotations

import sys
from pathlib import Path

from .render import SITE_DIR, render_site, render_standalone


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--standalone" in argv:
        rest = [a for a in argv if a != "--standalone"]
        out = rest[0] if rest else str(SITE_DIR / "analytics_gallery_standalone.html")
        render_standalone(Path(out))
    else:
        out = argv[0] if argv else None
        render_site(output_dir=out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
