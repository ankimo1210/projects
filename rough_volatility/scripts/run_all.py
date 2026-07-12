"""Run experiments A--G and export static figures through the package CLI."""

from __future__ import annotations

import sys

from rough_volatility.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["all", *sys.argv[1:]]))
