# Task 5 replay cash follow-up fix

## Changed behavior

- Exact zero exposure/entitlement contributes exact zero even when its raw price/CF is unknown. Dataset arrays remain unchanged. Nonzero trades, liquidation and entitled CF still require finite inputs; failed original paths remain unknown.
- Saved unused-call masks are derived from raw invalid price/CF and holdings, then compared. A saved flag cannot repair an active unknown quote.
- Finite legal actions must equal clipped finite raw targets. Invalid target/earlier policy failure retains whole-action NaN and its supplied failure reason; finite repair and missing reason are rejected.
- Independent cash-event reasons are checked against `raw_account` reasons. Top-level model/risk/precision reasons remain separate.

## Verification

RED: **9 failed / 1 passed** against the previous implementation. GREEN: **82 passed** before and after formatting. Both owned files pass `ruff check` and `ruff format --check`.

Exact before sources, final hashes, RED/GREEN, format/check outputs and `task-5-replay-inactive-fix.diff` are preserved. Final fingerprint is also in `task-5-replay-fix-formatted-source.json`. The old independent reviews and old R1/R2 fix records remain unchanged.

**Independent re-review is pending.** Accounting is the saved market/holdings-to-cash boundary; financial market/policy/pilot qualification remains external. No full suite, index/docs or Git changes were performed.
