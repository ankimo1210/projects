"""Run experiments D--E through the package CLI."""

from __future__ import annotations

import sys

from rough_volatility.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["options", *sys.argv[1:]]))
