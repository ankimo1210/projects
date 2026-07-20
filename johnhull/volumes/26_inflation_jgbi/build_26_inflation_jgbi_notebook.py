"""Build and execute the artifact-only volume 26 inflation/JGBi notebook."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_frontier_notebooks import build_volume

build_volume(26)
