// Pot progression for the hand review timeline (pure logic, no React).

import type { HandAction, ParsedHand } from "./review-api";

export interface StreetView {
  street: "preflop" | "flop" | "turn" | "river";
  potBefore: number;
  boardSoFar: string[];
  rows: { action: HandAction; potAfter: number }[];
}

export function applyAction(a: HandAction, contrib: Map<string, number>): number {
  if (a.action === "call" || a.action === "bet") {
    const amt = a.amount ?? 0;
    contrib.set(a.actor, (contrib.get(a.actor) ?? 0) + amt);
    return amt;
  }
  if (a.action === "raise") {
    if (a.raise_to != null) {
      const prev = contrib.get(a.actor) ?? 0;
      const delta = Math.max(a.raise_to - prev, 0);
      contrib.set(a.actor, a.raise_to);
      return delta;
    }
    const amt = a.amount ?? 0;
    contrib.set(a.actor, (contrib.get(a.actor) ?? 0) + amt);
    return amt;
  }
  return 0;
}

/** Street index (0=preflop..3=river) where an uncalled bet is returned:
 *  the street of the player's last bet/raise. An uncalled blind post
 *  (everyone folds preflop) returns on the preflop street. */
function uncalledReturnStreetIndex(hand: ParsedHand, player: string): number {
  const perStreet = [hand.actions.preflop, hand.actions.flop, hand.actions.turn, hand.actions.river];
  for (let i = perStreet.length - 1; i >= 0; i--) {
    if (perStreet[i].some(a => a.actor === player && (a.action === "bet" || a.action === "raise"))) {
      return i;
    }
  }
  return 0;
}

/** Build per-street views with pot progression from posts + actions.
 *  Uncalled bets are subtracted from the pot at the end of the street where
 *  they were returned, so later street headers show the true pot. */
export function buildStreetViews(hand: ParsedHand): StreetView[] {
  let pot = 0;
  const contrib = new Map<string, number>(); // per-street live contributions
  for (const p of hand.posts) {
    pot += p.amount;
    if (p.blind_type !== "ante") {
      contrib.set(p.player, (contrib.get(p.player) ?? 0) + p.amount);
    }
  }

  const views: StreetView[] = [];
  const streets = [
    { street: "preflop" as const, boardLen: 0, actions: hand.actions.preflop },
    { street: "flop"    as const, boardLen: 3, actions: hand.actions.flop },
    { street: "turn"    as const, boardLen: 4, actions: hand.actions.turn },
    { street: "river"   as const, boardLen: 5, actions: hand.actions.river },
  ];

  for (let i = 0; i < streets.length; i++) {
    const { street, boardLen, actions } = streets[i];
    const reached = street === "preflop"
      || hand.board.length >= boardLen
      || actions.length > 0;
    if (!reached) break;
    if (street !== "preflop") contrib.clear();

    const rows: StreetView["rows"] = [];
    const potBefore = pot;
    for (const a of actions) {
      pot += applyAction(a, contrib);
      rows.push({ action: a, potAfter: pot });
    }
    views.push({
      street,
      potBefore,
      boardSoFar: hand.board.slice(0, boardLen),
      rows,
    });

    for (const u of hand.uncalled_bets) {
      if (uncalledReturnStreetIndex(hand, u.player) === i) pot -= u.amount;
    }
  }
  return views;
}
