"""Point-in-time research platform for Japanese and US macroeconomic indicators.

Design note: US series carry real vintages (ALFRED exposes every revision with
its release date). Japanese series do not -- e-Stat has no vintage parameter at
all -- so their history is reconstructed from snapshots this package takes from
today onward, and is unrecoverable for the past. Every observation therefore
records whether its release_date is `actual` or merely a `snapshot` timestamp.
"""

__version__ = "0.1.0"
