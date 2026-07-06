from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from shortest_path_lab.visualization import write_demo_html  # noqa: E402


def main() -> None:
    site_dir = PROJECT_ROOT / "site"
    site_dir.mkdir(exist_ok=True)
    html_path = write_demo_html(site_dir / "index.html")
    print(f"wrote {html_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
