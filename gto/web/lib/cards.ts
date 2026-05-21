/** Parse "AKs" → two random card strings like ["Ah","Ks"] */
export function handToCards(hand: string): [string, string] {
  const SUITS = ["h","d","c","s"];
  const SUIT_SYMBOLS: Record<string, string> = { h:"♥", d:"♦", c:"♣", s:"♠" };
  const RED = new Set(["h","d"]);

  if (hand.length === 2) {
    // Pair: e.g. "AA"
    const r = hand[0];
    const s1 = SUITS[Math.floor(Math.random() * 4)];
    let s2 = SUITS[Math.floor(Math.random() * 4)];
    while (s2 === s1) s2 = SUITS[Math.floor(Math.random() * 4)];
    return [`${r}${SUIT_SYMBOLS[s1]}`, `${r}${SUIT_SYMBOLS[s2]}`];
  }

  const r1 = hand[0];
  const r2 = hand[1];
  const suited = hand[2] === "s";

  if (suited) {
    const s = SUITS[Math.floor(Math.random() * 4)];
    return [`${r1}${SUIT_SYMBOLS[s]}`, `${r2}${SUIT_SYMBOLS[s]}`];
  } else {
    const s1 = SUITS[Math.floor(Math.random() * 4)];
    let s2 = SUITS[Math.floor(Math.random() * 4)];
    while (s2 === s1) s2 = SUITS[Math.floor(Math.random() * 4)];
    return [`${r1}${SUIT_SYMBOLS[s1]}`, `${r2}${SUIT_SYMBOLS[s2]}`];
  }
}

export function cardColor(card: string): string {
  const suit = card.slice(-1);
  return (suit === "♥" || suit === "♦") ? "text-rose-400" : "text-white";
}
