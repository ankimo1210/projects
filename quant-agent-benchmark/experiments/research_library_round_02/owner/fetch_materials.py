"""Owner-only download of fixed research/doc resources, with content hashes."""

import argparse
import shutil
import urllib.request
from pathlib import Path

from datasets import digest, outside_git, save_json

KIT = Path(__file__).resolve().parents[1]
SOURCES = {
    "papers/waggoner.pdf": "https://fraser.stlouisfed.org/files/docs/historical/frbatl/wp/frbatl_wp_1997-10.pdf",
    "papers/hagan_west.pdf": "https://dlu-umich.github.io/docs/HaganWest.pdf",
    "quantlib/piecewiseyieldcurve.hpp": "https://raw.githubusercontent.com/lballabio/QuantLib/v1.43/ql/termstructures/yield/piecewiseyieldcurve.hpp",
    "quantlib/fittedbonddiscountcurve.hpp": "https://raw.githubusercontent.com/lballabio/QuantLib/v1.43/ql/termstructures/yield/fittedbonddiscountcurve.hpp",
    "quantlib/discountcurve.hpp": "https://raw.githubusercontent.com/lballabio/QuantLib/v1.43/ql/termstructures/yield/discountcurve.hpp",
    "quantlib/schedule.hpp": "https://raw.githubusercontent.com/lballabio/QuantLib/v1.43/ql/time/schedule.hpp",
}


def fetch(destination):
    destination = outside_git(destination)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    entries = []
    for relative, url in SOURCES.items():
        request = urllib.request.Request(
            url, headers={"User-Agent": "quant-benchmark-research/2.0"}
        )
        with urllib.request.urlopen(request, timeout=40) as response:
            data = response.read(20_000_001)
        if len(data) > 20_000_000 or len(data) < 500:
            raise ValueError(f"unexpected resource size: {relative}")
        if relative.endswith(".pdf") and not data.startswith(b"%PDF"):
            raise ValueError(f"expected PDF, got other content: {relative}")
        if relative.endswith(".hpp") and b"namespace QuantLib" not in data:
            raise ValueError(f"expected official C++ header: {relative}")
        path = destination / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        entries.append(dict(path=relative, source=url, sha256=digest(path), bytes=len(data)))
    for group, name in (("papers", "paper_notes.md"), ("quantlib", "quantlib_quickstart.md")):
        path = destination / group / name
        shutil.copy2(KIT / "materials" / name, path)
        entries.append(
            dict(
                path=f"{group}/{name}",
                source="locally authored notes",
                sha256=digest(path),
                bytes=path.stat().st_size,
            )
        )
    save_json(destination / "manifest.json", {"resources": entries, "quantlib_version": "1.43"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    fetch(parser.parse_args().destination)
    print("Downloaded and hashed research resources; no publication performed.")
