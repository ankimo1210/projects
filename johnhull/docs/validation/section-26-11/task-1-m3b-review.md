# Task 1 fix round 1 scoped re-review

## Verdict

- ✅ **Approved for I1 scope.** The fix closes the reported piecewise-linear running-extrema display bug.
- ✅ I found no new breakage introduced by `2d886ced..0ce4e6d` within the reviewed fix scope.
- ⚠️ Scope was intentionally limited to I1 and the repair diff. I did not re-review unrelated Task 1 behavior, Book/portal delivery, or broad suites.

## Reviewed inputs

- `task-1-brief.md`
- `task-1-review.md`
- `task-1-fix1-report.md`
- `task-1-fix1-review.diff`
- Actual diff and file ranges for `2d886cedde3da9a56984e802074fb770018734db..0ce4e6d4672ce8cf9edaeef4762a68646b9e2b1f`

Changed files are limited to:

- `johnhull/hullkit/src/hullkit/_lookback_lesson.py`
- `johnhull/hullkit/tests/test_lookback_lesson.py`

## Findings

No blocking or non-blocking issues found in the fix diff.

The new `_running_extreme_breakpoints` helper inserts a breakpoint exactly when the piecewise-linear spot segment crosses the prior running extreme. Before the crossing, the running extreme remains horizontal; after the crossing, the line follows the spot path to the new endpoint. This directly addresses the earlier false display movement at `t=.1875` for the minimum and `t=.3125` for the maximum.

The helper also handles the relevant boundary cases for this figure:

- When the spot starts exactly at the current extreme and moves to a new extreme, the direct line from the node to the endpoint follows the spot path, which is correct.
- When seasoned history already dominates the whole toy path (`80` minimum, `130` maximum), no crossing is inserted and the extrema stay flat, which is correct.
- The payoff trace data and spot path nodes are not changed by the repair.

The added regression test now checks both explicit crossing breakpoints and displayed Plotly-line interpolation before, at, and after the crossings. The previous node-only test was adjusted to check node values by interpolating the richer running-extrema traces, which preserves the old node contract while allowing the added crossing points.

## Focused verification

I ran one focused interpolation probe against the actual generated Plotly traces using the specified worktree and `PYTHONPATH`.

Command shape:

```bash
cd /home/kazumasa/.codex/worktrees/johnhull-binary-m2a/johnhull/hullkit
PYTHONPATH=/home/kazumasa/.codex/worktrees/johnhull-binary-m2a/johnhull/hullkit/src:/home/kazumasa/.codex/worktrees/johnhull-binary-m2a/johnhull/report \
  /home/kazumasa/projects/.venv/bin/python - <<'PY'
# imports _figures(), selects semantic traces, evaluates np.interp on trace x/y arrays
PY
```

Probe output:

```text
new_min_before: t=0.187500000000 actual=100.000000000000 expected=100.000000000000
new_min_cross: t=0.208333333333 actual=100.000000000000 expected=100.000000000000
new_min_after: t=0.229166666667 actual=97.000000000000 expected=97.000000000000
new_max_before: t=0.312500000000 actual=112.000000000000 expected=112.000000000000
new_max_cross: t=0.333333333333 actual=112.000000000000 expected=112.000000000000
new_max_after: t=0.354166666667 actual=116.500000000000 expected=116.500000000000
seasoned_min: t=0.312500000000 actual=80.000000000000 expected=80.000000000000
seasoned_max: t=0.312500000000 actual=130.000000000000 expected=130.000000000000
new_min_x [0.0, 0.125, 0.208333333333, 0.25, 0.375, 0.483870967742, 0.5, 0.625, 0.714285714286, 0.75, 0.875, 1.0]
new_max_x [0.0, 0.125, 0.25, 0.333333333333, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
```

Exit code: `0`.

## Assessment

I1 is fixed. The repair is localized, preserves the original path/payoff semantics, and adds focused semantic coverage for the exact rendering failure mode. No additional fix-round issue is required before controller integration.
