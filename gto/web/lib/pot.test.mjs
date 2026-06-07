// Regression tests for pot progression (run: pnpm test / node --test lib).
// Node >= 22.18 strips types from the imported .ts module natively.

import { test } from "node:test";
import assert from "node:assert/strict";
import { buildStreetViews } from "./pot.ts";

function makeHand(overrides) {
  return {
    hand_id: "0",
    stakes: { small_blind: 1, big_blind: 2, currency: "USD" },
    played_at: null,
    timezone: null,
    table_name: "t",
    max_players: null,
    button_seat: 1,
    players: [],
    hero_name: null,
    hero_cards: null,
    posts: [],
    actions: { preflop: [], flop: [], turn: [], river: [] },
    board: [],
    showdown: [],
    uncalled_bets: [],
    winners: [],
    total_pot: null,
    rake: null,
    zoom: false,
    positions: {},
    preflop_deviation: null,
    ...overrides,
  };
}

function act(street, actor, action, amount = null, raise_to = null, all_in = false) {
  return { street, actor, action, amount, raise_to, all_in };
}

test("uncalled preflop all-in return is subtracted before postflop streets", () => {
  // Mirrors tests/fixtures/ps_3handed_allin_uncalled.txt:
  // antes 3x0.50, SB 1, BB 2; Hero shoves to 249.50, shark_ali calls 78.50
  // all-in, BB folds; uncalled 170 returned to Hero. True pot = 162.50.
  const hand = makeHand({
    posts: [
      { player: "shark_ali", blind_type: "ante", amount: 0.5 },
      { player: "rocky_5", blind_type: "ante", amount: 0.5 },
      { player: "Hero", blind_type: "ante", amount: 0.5 },
      { player: "shark_ali", blind_type: "small", amount: 1 },
      { player: "rocky_5", blind_type: "big", amount: 2 },
    ],
    actions: {
      preflop: [
        act("preflop", "Hero", "raise", 247.5, 249.5, true),
        act("preflop", "shark_ali", "call", 78.5, null, true),
        act("preflop", "rocky_5", "fold"),
      ],
      flop: [],
      turn: [],
      river: [],
    },
    board: ["9c", "6h", "3d", "Qs", "2h"],
    uncalled_bets: [{ player: "Hero", amount: 170 }],
    total_pot: 162.5,
  });

  const views = buildStreetViews(hand);
  assert.equal(views.length, 4);
  assert.equal(views[0].potBefore, 4.5);
  // Regression: these used to show 332.50 (uncalled 170 never subtracted).
  assert.equal(views[1].potBefore, 162.5);
  assert.equal(views[2].potBefore, 162.5);
  assert.equal(views[3].potBefore, 162.5);
});

test("uncalled river bet return does not affect earlier streets", () => {
  const hand = makeHand({
    posts: [
      { player: "sb", blind_type: "small", amount: 1 },
      { player: "bb", blind_type: "big", amount: 2 },
    ],
    actions: {
      preflop: [
        act("preflop", "sb", "call", 1),
        act("preflop", "bb", "check"),
      ],
      flop: [
        act("flop", "sb", "check"),
        act("flop", "bb", "check"),
      ],
      turn: [
        act("turn", "sb", "check"),
        act("turn", "bb", "check"),
      ],
      river: [
        act("river", "sb", "bet", 3),
        act("river", "bb", "fold"),
      ],
    },
    board: ["9c", "6h", "3d", "Qs", "2h"],
    uncalled_bets: [{ player: "sb", amount: 3 }],
  });

  const views = buildStreetViews(hand);
  assert.deepEqual(views.map(v => v.potBefore), [3, 4, 4, 4]);
  // The bet still shows in the river row before the return.
  assert.equal(views[3].rows[0].potAfter, 7);
});

test("uncalled open raise after all fold preflop", () => {
  // Everyone folds to an open: return happens on the preflop street itself.
  const hand = makeHand({
    posts: [
      { player: "sb", blind_type: "small", amount: 0.5 },
      { player: "bb", blind_type: "big", amount: 1 },
    ],
    actions: {
      preflop: [
        act("preflop", "btn", "raise", 1.5, 2.5),
        act("preflop", "sb", "fold"),
        act("preflop", "bb", "fold"),
      ],
      flop: [],
      turn: [],
      river: [],
    },
    uncalled_bets: [{ player: "btn", amount: 1.5 }],
    total_pot: 2.5,
  });

  const views = buildStreetViews(hand);
  assert.equal(views.length, 1);
  assert.equal(views[0].potBefore, 1.5);
  assert.equal(views[0].rows[0].potAfter, 4);
});
