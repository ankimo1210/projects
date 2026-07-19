// The TS port must stay byte-for-byte identical to Python's
// flop_canon.canonicalize, since the result is the cache key precomputed
// solutions are stored under. The cross-verified values below are carried
// over from web/lib/flop-canon.test.mjs.
import { test } from "node:test";
import assert from "node:assert/strict";
import { canonicalizeBoard } from "./flop-canon.ts";

test("canonicalizeBoard matches the Python canon (cross-verified values)", () => {
  assert.equal(canonicalizeBoard(["As", "Kd", "7c"]), "AcKd7h");
  assert.equal(canonicalizeBoard(["2c", "2d", "2h"]), "2c2d2h");
  assert.equal(canonicalizeBoard(["Ts", "Th", "2c"]), "TcTd2h");
  assert.equal(canonicalizeBoard(["9c", "8c", "2c"]), "9c8c2c");
  assert.equal(canonicalizeBoard(["7h", "7d", "7s"]), "7c7d7h");
  assert.equal(canonicalizeBoard(["Ac", "Kc", "Qc"]), "AcKcQc");
});

test("suit-isomorphic boards collapse to the same canonical form", () => {
  assert.equal(
    canonicalizeBoard(["As", "Kd", "7c"]),
    canonicalizeBoard(["Ah", "Ks", "7d"]),
  );
});

test("every suit relabeling of a board collapses to the same canon", () => {
  const SUITS = "cdhs";
  const boards = [
    ["As", "Kd", "7c"],
    ["Ts", "Th", "2c"],
    ["9c", "8c", "2c"],
    ["7h", "7d", "7s"],
    ["Qd", "Jd", "Td"],
  ];
  // All 24 permutations of the 4 suits.
  const perms: number[][] = [];
  const permute = (arr: number[], start: number) => {
    if (start === arr.length) { perms.push([...arr]); return; }
    for (let i = start; i < arr.length; i++) {
      [arr[start], arr[i]] = [arr[i]!, arr[start]!];
      permute(arr, start + 1);
      [arr[start], arr[i]] = [arr[i]!, arr[start]!];
    }
  };
  permute([0, 1, 2, 3], 0);

  for (const board of boards) {
    const canon = canonicalizeBoard(board);
    for (const perm of perms) {
      const relabeled = board.map(
        (c) => c[0]! + SUITS[perm[SUITS.indexOf(c[1]!)]!]!,
      );
      assert.equal(canonicalizeBoard(relabeled), canon);
    }
  }
});
