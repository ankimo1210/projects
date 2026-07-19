// Card-int encoding shared with the Rust solver (gto-core) and the Python
// backend: card = rank * 4 + suit, rank 0=2 … 12=A, suit 0=c 1=d 2=h 3=s.
// Combo index for an unordered hole-card pair {lo, hi} (lo < hi) is
// lo*51 - lo*(lo-1)/2 + hi - lo - 1, giving 1326 combos total.
// See gto/ARCHITECTURE.md for the derivation. This module must not drift
// from that encoding — pack files store card ints and combo indices.

export const RANK_CHARS = "23456789TJQKA";
export const SUIT_CHARS = "cdhs";
export const NUM_CARDS = 52;
export const NUM_COMBOS = 1326;

/** 0..51 backend card int (rank*4 + suit). */
export type CardInt = number;

export function makeCard(rank: number, suit: number): CardInt {
  if (!Number.isInteger(rank) || rank < 0 || rank > 12) {
    throw new RangeError(`rank out of range: ${rank}`);
  }
  if (!Number.isInteger(suit) || suit < 0 || suit > 3) {
    throw new RangeError(`suit out of range: ${suit}`);
  }
  return rank * 4 + suit;
}

export function rankOf(card: CardInt): number {
  return Math.floor(card / 4);
}

export function suitOf(card: CardInt): number {
  return card % 4;
}

/** Parse "As" / "2c" (rank char + suit char) into a card int. */
export function parseCard(s: string): CardInt {
  if (s.length !== 2) throw new RangeError(`bad card string: ${JSON.stringify(s)}`);
  const rank = RANK_CHARS.indexOf(s[0]!.toUpperCase());
  const suit = SUIT_CHARS.indexOf(s[1]!.toLowerCase());
  if (rank < 0 || suit < 0) throw new RangeError(`bad card string: ${JSON.stringify(s)}`);
  return rank * 4 + suit;
}

export function cardToString(card: CardInt): string {
  if (!Number.isInteger(card) || card < 0 || card >= NUM_CARDS) {
    throw new RangeError(`card int out of range: ${card}`);
  }
  return RANK_CHARS[rankOf(card)]! + SUIT_CHARS[suitOf(card)]!;
}

/**
 * Index of the unordered hole-card pair {a, b} in the canonical 1326-combo
 * enumeration (lo-major). Order of arguments does not matter.
 */
export function comboIndex(a: CardInt, b: CardInt): number {
  if (a === b) throw new RangeError(`combo needs two distinct cards, got ${a} twice`);
  const lo = Math.min(a, b);
  const hi = Math.max(a, b);
  if (lo < 0 || hi >= NUM_CARDS) throw new RangeError(`card int out of range: ${lo}, ${hi}`);
  return lo * 51 - (lo * (lo - 1)) / 2 + hi - lo - 1;
}

/** Inverse of comboIndex: index 0..1325 → [lo, hi] card ints (lo < hi). */
export function comboCards(index: number): [CardInt, CardInt] {
  if (!Number.isInteger(index) || index < 0 || index >= NUM_COMBOS) {
    throw new RangeError(`combo index out of range: ${index}`);
  }
  let lo = 0;
  let remaining = index;
  while (remaining >= NUM_CARDS - 1 - lo) {
    remaining -= NUM_CARDS - 1 - lo;
    lo += 1;
  }
  return [lo, lo + 1 + remaining];
}
