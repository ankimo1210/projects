"""
Flop canonicalization: map all C(52,3)=22,100 flops to 1,755 suit-isomorphic
canonical forms.

Two flops are strategically equivalent if one can be obtained from the other
by a permutation of suits (because suit labels have no strategic meaning in
NLHE — only suit relationships matter).

Algorithm:
  1. Sort cards by rank descending (rank tiebreak by suit ascending).
  2. Re-label suits in order of first appearance: first suit seen → 0,
     second → 1, third → 2.
  3. Produce canonical card strings using suit symbols c/d/h/s for labels 0/1/2/3.
"""

from __future__ import annotations
from itertools import combinations

RANKS = "AKQJT98765432"
SUITS = "cdhs"
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}  # A=0 (highest) … 2=12


def _parse(card: str) -> tuple[int, int]:
    """Return (rank_index, suit_index) for a card string like 'Ah'."""
    return RANK_ORDER[card[0]], SUITS.index(card[1])


from itertools import permutations as _perms

def canonicalize(cards: list[str]) -> tuple[str, ...]:
    """
    Return canonical flop under full suit isomorphism.
    Tries all 4! suit permutations and picks the lexicographically smallest
    sorted result.
    """
    parsed = [_parse(c) for c in cards]

    best: tuple[str, ...] | None = None
    for perm in _perms(range(4)):
        remapped = [(r, perm[s]) for r, s in parsed]
        remapped.sort(key=lambda x: (x[0], x[1]))
        candidate = tuple(f"{RANKS[r]}{SUITS[s]}" for r, s in remapped)
        if best is None or candidate < best:
            best = candidate

    assert best is not None
    return best


def board_texture(canon: tuple[str, ...]) -> str:
    """Classify a canonical flop into a texture label."""
    ranks = [c[0] for c in canon]
    suits = [c[1] for c in canon]

    paired = len(set(ranks)) < 3
    monotone = len(set(suits)) == 1
    two_tone = len(set(suits)) == 2

    rank_indices = sorted([RANK_ORDER[r] for r in ranks])
    gaps = [rank_indices[i+1] - rank_indices[i] for i in range(2)]
    connected = all(g <= 2 for g in gaps)
    semi_connected = any(g <= 2 for g in gaps)

    if paired:
        base = "paired"
    elif connected:
        base = "connected"
    elif semi_connected:
        base = "semi_connected"
    else:
        base = "disconnected"

    if monotone:
        suit_label = "monotone"
    elif two_tone:
        suit_label = "two_tone"
    else:
        suit_label = "rainbow"

    return f"{base}_{suit_label}"


def all_canonical_flops() -> list[tuple[str, ...]]:
    """Generate all 1,755 canonical flop representations."""
    seen: set[tuple[str, ...]] = set()
    result = []
    all_cards = [f"{r}{s}" for r in RANKS for s in SUITS]
    for combo in combinations(all_cards, 3):
        canon = canonicalize(list(combo))
        if canon not in seen:
            seen.add(canon)
            result.append(canon)
    return result


def canonical_to_actual(canon: tuple[str, ...], suit_perm: tuple[int, int, int, int] | None = None) -> list[str]:
    """Convert canonical flop back to actual cards (default: use canonical suits)."""
    return list(canon)


if __name__ == "__main__":
    flops = all_canonical_flops()
    print(f"Total canonical flops: {len(flops)}")
    # Show texture distribution
    from collections import Counter
    textures = Counter(board_texture(f) for f in flops)
    for tex, cnt in sorted(textures.items(), key=lambda x: -x[1]):
        print(f"  {tex:35s} {cnt:4d}")
