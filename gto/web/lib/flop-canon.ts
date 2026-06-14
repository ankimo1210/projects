// Port of Python's flop_canon.canonicalize() (src/gto/library/flop_canon.py).
// Finds the lexicographically smallest suit-permutation of a 3-card flop.
//
// MUST stay byte-for-byte in sync with the Python implementation: the resulting
// string is the cache key the precomputed library is stored under, so any drift
// makes the frontend look up the wrong (or no) solution. Cross-verified against
// the Python output in flop-canon.test.mjs.
//
// NOTE: this RANKS order ("AKQJT98765432", A=0) is the canon's own
// lexicographic convention. It is deliberately NOT the backend card-int
// encoding (gto-core: card = rank*4 + suit, rank 0=2 … 12=A); these two
// representations are separate and must not be conflated.
const RANKS = "AKQJT98765432";
const SUITS = "cdhs";

function parseCard(card: string): [number, number] {
  return [RANKS.indexOf(card[0]), SUITS.indexOf(card[1])];
}

function cardStr(rank: number, suit: number): string {
  return RANKS[rank] + SUITS[suit];
}

// All 24 permutations of [0,1,2,3]
const SUIT_PERMS: number[][] = (() => {
  const perms: number[][] = [];
  const a = [0, 1, 2, 3];
  function permute(arr: number[], start: number) {
    if (start === arr.length) { perms.push([...arr]); return; }
    for (let i = start; i < arr.length; i++) {
      [arr[start], arr[i]] = [arr[i], arr[start]];
      permute(arr, start + 1);
      [arr[start], arr[i]] = [arr[i], arr[start]];
    }
  }
  permute(a, 0);
  return perms;
})();

export function canonicalizeBoard(cards: string[]): string {
  const parsed = cards.map(parseCard);
  let best: string[] | null = null;

  for (const perm of SUIT_PERMS) {
    const remapped = parsed.map(([r, s]) => [r, perm[s]] as [number, number]);
    remapped.sort((a, b) => a[0] !== b[0] ? a[0] - b[0] : a[1] - b[1]);
    const candidate = remapped.map(([r, s]) => cardStr(r, s));
    if (best === null || candidate.join("") < best.join("")) {
      best = candidate;
    }
  }

  return best!.join("");
}
