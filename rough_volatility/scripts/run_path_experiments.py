"""Run experiments A--C through the package CLI."""

from __future__ import annotations

import sys

from rough_volatility.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["paths", *sys.argv[1:]]))
