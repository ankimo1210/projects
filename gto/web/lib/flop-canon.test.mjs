// Flop canonicalization (#15): the TS port must stay byte-for-byte identical to
// Python's flop_canon.canonicalize, since the result is the cache key the
// precomputed library is stored under. Run: pnpm test (node --test lib/*.test.mjs).
//
// (The card-encoding fix in library-api.ts (#1) is not unit-tested here: that
// module uses the bundler-style "@/lib/..." alias, which the bare `node --test`
// harness cannot resolve, and a ".ts" extension would break the Next type-check.
// It was cross-verified manually + against the live /api/library/flop/combos ints.)

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
