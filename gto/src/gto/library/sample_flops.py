"""Sample M canonical flops + frequency weights for solve-hu-blueprint.

The blueprint's M-flop abstract game (gto-hu, blueprint design v2) takes
explicit flops and weights. This utility picks them from the 1,755
canonical classes with their real-game frequencies (class size / 22,100),
so the CLI arguments stop being hand-picked.

Strategies:
  diverse   (default) round-robin across board textures, taking each
            texture's most frequent class first — texture-diverse and
            high-mass.
  frequency the M most frequent classes overall.
  random    seeded frequency-weighted draw without replacement.

Weights are the selected classes' frequencies renormalized over the
selection; the unselected mass is truncated (that is what makes it an
M-flop ABSTRACT game — exploitability numbers are relative to it).

Usage:
  uv run --no-sync python -m gto.library.sample_flops --m 3
  → prints a ready --flops/--weights argument pair.
"""

from __future__ import annotations

import argparse
import random
from collections import Counter, defaultdict
from itertools import combinations

from gto.library.flop_canon import RANKS, SUITS, board_texture, canonicalize


def canonical_class_counts() -> dict[tuple[str, ...], int]:
    """canonical flop → number of raw flops (Σ = C(52,3) = 22,100)."""
    counts: Counter[tuple[str, ...]] = Counter()
    all_cards = [f"{r}{s}" for r in RANKS for s in SUITS]
    for combo in combinations(all_cards, 3):
        counts[canonicalize(list(combo))] += 1
    return dict(counts)


def sample_flops(
    m: int, strategy: str = "diverse", seed: int = 42
) -> list[tuple[str, float]]:
    """Return [(flop_str, weight)] with weights normalized over the M."""
    counts = canonical_class_counts()
    total = sum(counts.values())
    assert total == 22_100, f"canonical counts must cover C(52,3), got {total}"

    if strategy == "frequency":
        picked = sorted(counts, key=counts.get, reverse=True)[:m]
    elif strategy == "random":
        rng = random.Random(seed)
        pool = list(counts)
        weights = [counts[f] for f in pool]
        picked = []
        for _ in range(m):
            choice = rng.choices(range(len(pool)), weights=weights, k=1)[0]
            picked.append(pool.pop(choice))
            weights.pop(choice)
    elif strategy == "diverse":
        by_texture: dict[str, list[tuple[str, ...]]] = defaultdict(list)
        for f in counts:
            by_texture[board_texture(f)].append(f)
        for fs in by_texture.values():
            fs.sort(key=counts.get, reverse=True)
        textures = sorted(
            by_texture, key=lambda t: sum(counts[f] for f in by_texture[t]), reverse=True
        )
        picked = []
        rank = 0
        while len(picked) < m:
            for t in textures:
                if rank < len(by_texture[t]):
                    picked.append(by_texture[t][rank])
                    if len(picked) == m:
                        break
            rank += 1
    else:
        raise ValueError(f"unknown strategy '{strategy}'")

    mass = sum(counts[f] for f in picked)
    return [("".join(f), counts[f] / mass) for f in picked]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--m", type=int, default=3)
    p.add_argument("--strategy", choices=["diverse", "frequency", "random"], default="diverse")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    picks = sample_flops(args.m, args.strategy, args.seed)
    flops = ",".join(f for f, _ in picks)
    weights = ",".join(f"{w:.6f}" for _, w in picks)
    for f, w in picks:
        print(f"  {f}  weight {w:.4f}")
    print(f"\n--flops {flops} --weights {weights}")


if __name__ == "__main__":
    main()
