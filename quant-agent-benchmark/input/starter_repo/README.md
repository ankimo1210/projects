# QuantCurve starter repository

This is intentionally incomplete. Copy its contents into your assigned result directory, implement the research workflow described in `../TASK.md`, and replace this README with complete installation and usage documentation.

## Supplied components

- `quantcurve.io`: strict input schema loading and basic coercion.
- `quantcurve.instruments`: immutable observation schema.
- `quantcurve.conventions`: documented elementary rate/discount conversions.
- `quantcurve.cli`: required CLI shape, with the implementation deliberately absent.
- `tests/`: interface and convention checks only. Passing these tests does not imply a valid submission.

The benchmark requires Python 3.12. The input rate quotes are percentage points, bond coupons are decimal rates, and bond prices are points per 100. Read `market_data/CONVENTIONS.md` before implementing any valuation logic.
