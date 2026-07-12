"""Generation diversity / quality metrics (spec §16).

All operate on a list of generated token-id sequences (or a single one):
- repetition_rate: fraction of tokens equal to the immediately preceding token
- distinct_n: unique n-grams / total n-grams (higher = more diverse)
- these are DESCRIPTIVE; low diversity ≠ low quality in every context (a list
  of facts is legitimately low-distinct), which is stated wherever shown.
"""

from __future__ import annotations


def repetition_rate(ids: list[int]) -> float:
    if len(ids) < 2:
        return 0.0
    return sum(1 for a, b in zip(ids, ids[1:], strict=False) if a == b) / (len(ids) - 1)


def distinct_n(ids: list[int], n: int) -> float:
    if len(ids) < n:
        return 0.0
    grams = [tuple(ids[i : i + n]) for i in range(len(ids) - n + 1)]
    return len(set(grams)) / len(grams)


def sequence_metrics(ids: list[int]) -> dict:
    return {
        "length": len(ids),
        "repetition_rate": round(repetition_rate(ids), 4),
        "distinct_1": round(distinct_n(ids, 1), 4),
        "distinct_2": round(distinct_n(ids, 2), 4),
        "distinct_3": round(distinct_n(ids, 3), 4),
    }


def aggregate_metrics(seqs: list[list[int]], eos_id: int | None = None) -> dict:
    if not seqs:
        return {}
    per = [sequence_metrics(s) for s in seqs]
    keys = ["repetition_rate", "distinct_1", "distinct_2", "distinct_3", "length"]
    agg = {k: round(sum(p[k] for p in per) / len(per), 4) for k in keys}
    if eos_id is not None:
        agg["eos_rate"] = round(sum(1 for s in seqs if eos_id in s) / len(seqs), 4)
    return agg
