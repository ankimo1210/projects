"""Render the dashboard's chart section to a PNG for the email.

Mail clients strip scripts and inline SVG, so the figures have to travel as a
raster image. Headless Chromium loads the same HTML file the dashboard writes,
the page publishes the chart section's geometry on ``<body data-chart-box>``
once the drawing pass finishes, and this module crops the screenshot to it.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

BOX_RE = re.compile(r'data-chart-box="(\d+),(\d+)"')
THEME_RE = re.compile(r'<html[^>]*\bdata-theme="[^"]*"[^>]*>')
CHROME_CANDIDATES = (
    "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
)


def find_chrome(candidates: tuple[str, ...] = CHROME_CANDIDATES) -> str | None:
    """First existing browser binary among the candidates (globs allowed)."""
    for pattern in candidates:
        expanded = Path(pattern).expanduser()
        if "*" in pattern:
            matches = sorted(Path(expanded.anchor).glob(str(expanded.relative_to(expanded.anchor))))
            if matches:
                return str(matches[-1])
        elif expanded.exists():
            return str(expanded)
    return None


def parse_box(dom: str) -> tuple[int, int]:
    """Top and bottom of the chart section, as the page published them."""
    match = BOX_RE.search(dom)
    if match is None:
        raise RuntimeError("the page published no chart box (the drawing pass did not finish)")
    return int(match.group(1)), int(match.group(2))


def crop_box(
    top: int, bottom: int, width: int, height: int, pad: int = 12
) -> tuple[int, int, int, int]:
    """PIL-style crop box around the section, padded and clamped to the image."""
    return (0, max(0, top - pad), width, min(height, bottom + pad))


def _run(chrome: str, url: str, width: int, height: int, extra: list[str]) -> bytes:
    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        "--virtual-time-budget=9000",
        *extra,
        url,
    ]
    done = subprocess.run(cmd, capture_output=True, timeout=180, check=False)
    return done.stdout


def retheme(html: str, theme: str) -> str:
    """Force the page's theme, so the email image is not at the mercy of the saved toggle."""
    return THEME_RE.sub(f'<html lang="ja" data-theme="{theme}">', html, count=1)


def render(
    html_path: Path,
    out_path: Path,
    chrome: str | None = None,
    width: int = 1100,
    height: int = 5200,
    max_colors: int = 0,
    theme: str | None = "light",
) -> Path | None:
    """Screenshot the chart section of ``html_path`` into ``out_path``.

    Returns the path, or None when no browser is available (the caller then
    sends the email without the image rather than failing the whole run).
    """
    from PIL import Image

    chrome = chrome or find_chrome()
    if chrome is None:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        source = html_path
        if theme:
            source = Path(tmp) / "themed.html"
            source.write_text(
                retheme(html_path.read_text(encoding="utf-8"), theme), encoding="utf-8"
            )
        url = source.resolve().as_uri()
        dom = _run(chrome, url, width, height, ["--dump-dom"]).decode("utf-8", "ignore")
        top, bottom = parse_box(dom)
        shot = Path(tmp) / "page.png"
        _run(chrome, url, width, height, [f"--screenshot={shot}"])
        if not shot.exists():
            raise RuntimeError("headless browser produced no screenshot")
        with Image.open(shot) as image:
            cropped = image.convert("RGB").crop(crop_box(top, bottom, *image.size))
            if max_colors:
                cropped = cropped.quantize(colors=max_colors, method=Image.MEDIANCUT)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(out_path, optimize=True)
    return out_path
