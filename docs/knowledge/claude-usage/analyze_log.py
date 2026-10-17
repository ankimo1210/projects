"""Estimate USD per percentage point of each Claude usage window from the statusline log.

~/.claude/usage-log/rate-limits.jsonl gets a line whenever a window's percentage
or reset time changes. Within one reset period, take the first and last observed
step of a window and price the local transcript tokens between them:

    USD/pp = cost(t_first_step, t_last_step) / (pct_last - pct_first)

Only usage logged on this machine is priced, so usage on other devices or
claude.ai in the same period raises the percentage without adding cost
(the result is then an underestimate).
"""

import datetime as dt
import json
import os
from decimal import Decimal

from api_cost import cost, rows, ts

LOG = os.path.expanduser("~/.claude/usage-log/rate-limits.jsonl")


def main():
    with open(LOG) as f:
        log = [json.loads(line) for line in f]
    for name in ("five_hour", "seven_day"):
        periods = {}
        for e in log:
            w = e.get(name)
            if w:
                periods.setdefault(w["resets_at"], []).append((ts(e["ts"]), w["used_percentage"]))
        for reset, pts in periods.items():
            steps = [pts[i] for i in range(1, len(pts)) if pts[i][1] != pts[i - 1][1]]
            reset_s = dt.datetime.fromtimestamp(reset).strftime("%m-%d %H:%M")
            if len(steps) < 2:
                print(f"{name} (resets {reset_s}): {len(steps)} step(s), not enough yet")
                continue
            (t0, p0), (t1, p1) = steps[0], steps[-1]
            usd = sum((cost(m, u) or Decimal(0)) for _, m, u, _ in rows(t0, t1))
            per_pp = usd / Decimal(p1 - p0)
            print(
                f"{name} (resets {reset_s}): {p0}%→{p1}% between {t0:%m-%d %H:%M}Z and "
                f"{t1:%m-%d %H:%M}Z, ${usd:.2f} → ${per_pp:.3f}/pp → 100% ≈ ${per_pp * 100:.0f}"
            )


if __name__ == "__main__":
    main()
