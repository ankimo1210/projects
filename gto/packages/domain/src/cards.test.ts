// Encoding invariants for the shared card-int / combo-index conventions.
// Known values are taken from gto/CLAUDE.md and ARCHITECTURE.md; the Rust
// differential fixtures (gto/fixtures/) extend this in the H1 contract task.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  NUM_CARDS,
  NUM_COMBOS,
  makeCard,
  rankOf,
  suitOf,
  parseCard,
  cardToString,
  comboIndex,
  comboCards,
} from "./cards.ts";

test("known card-int values (card = rank*4 + suit, rank 0=2 … 12=A)", () => {
  assert.equal(parseCard("2c"), 0);
  assert.equal(parseCard("2s"), 3);
  assert.equal(parseCard("3c"), 4);
  assert.equal(parseCard("Ac"), 48);
  assert.equal(parseCard("As"), 51);
  assert.equal(cardToString(0), "2c");
  assert.equal(cardToString(51), "As");
});

test("parse/format round-trips all 52 cards", () => {
  for (let card = 0; card < NUM_CARDS; card++) {
    const s = cardToString(card);
    assert.equal(parseCard(s), card);
    assert.equal(makeCard(rankOf(card), suitOf(card)), card);
  }
});

test("parseCard rejects malformed input", () => {
  for (const bad of ["", "A", "Asx", "1c", "Ax", "cA"]) {
    assert.throws(() => parseCard(bad), RangeError);
  }
});

test("comboIndex enumerates all 1326 pairs bijectively, lo-major", () => {
  let expected = 0;
  for (let lo = 0; lo < NUM_CARDS; lo++) {
    for (let hi = lo + 1; hi < NUM_CARDS; hi++) {
      assert.equal(comboIndex(lo, hi), expected);
      assert.equal(comboIndex(hi, lo), expected); // order-insensitive
      assert.deepEqual(comboCards(expected), [lo, hi]);
      expected++;
    }
  }
  assert.equal(expected, NUM_COMBOS);
});

test("combo edge values", () => {
  assert.equal(comboIndex(0, 1), 0);
  assert.equal(comboIndex(50, 51), NUM_COMBOS - 1);
  assert.throws(() => comboIndex(5, 5), RangeError);
  assert.throws(() => comboCards(NUM_COMBOS), RangeError);
});
