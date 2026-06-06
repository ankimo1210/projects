# HU Solver Phase 1: Foundation Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the card-evaluation bugs in `gto-core` (straight-flush miss, phantom-2c padding) and mark the single-street solver as a river-only approximation, without breaking the existing app.

**Architecture:** Surgical fixes inside `crates/gto-core` only. A new public `evaluate_best` (5-7 cards, duplicate-checked) replaces the buggy `evaluate7` flush path; a new shared `showdown_strengths` removes the zero-padding in both CFR solvers. Doc warnings demote `CfrSolver`/`solve()` to "river-only correct".

**Tech Stack:** Rust (existing `gto-core`), cargo test.

**Working directory:** `~/projects/gto` (workspace member of `~/projects` git repo).

**Build/test commands:**
```bash
cd ~/projects/gto && source ~/.cargo/env
cargo test -p gto-core                # all gto-core tests
```

---

### Task 1: Fix straight-flush miss in `evaluate7` via new `evaluate_best`

The bug: `evaluate7` (`crates/gto-core/src/eval.rs:187-225`) keeps only the
top-5 ranks of a 6-7 card flush suit (`best5_from_flush_mask`), so straight
flushes made of lower cards (incl. wheel SF) are scored as plain flushes.

**Files:**
- Modify: `crates/gto-core/src/eval.rs`

- [ ] **Step 1: Write the failing tests**

Append inside `mod tests` in `crates/gto-core/src/eval.rs`:

```rust
    #[test]
    fn low_straight_flush_in_six_card_flush_beats_ace_high_flush() {
        // Spade ranks {2,3,4,5,6,K}: best hand is the 6-high straight flush,
        // not a K-high flush. Must beat a plain A-high flush.
        let sf: [Card; 7] = [
            parse_card("2s").unwrap(), parse_card("3s").unwrap(),
            parse_card("4s").unwrap(), parse_card("5s").unwrap(),
            parse_card("6s").unwrap(), parse_card("Ks").unwrap(),
            parse_card("2d").unwrap(),
        ];
        let flush: [Card; 7] = [
            parse_card("As").unwrap(), parse_card("Ks").unwrap(),
            parse_card("Qs").unwrap(), parse_card("Js").unwrap(),
            parse_card("9s").unwrap(), parse_card("2d").unwrap(),
            parse_card("3h").unwrap(),
        ];
        assert!(
            evaluate7(&sf) > evaluate7(&flush),
            "6-high straight flush must beat A-high flush: {} vs {}",
            evaluate7(&sf), evaluate7(&flush)
        );
    }

    #[test]
    fn wheel_straight_flush_detected_in_six_card_flush() {
        // Spade ranks {A,2,3,4,5,K}: wheel straight flush (5-high SF).
        let wheel_sf: [Card; 7] = [
            parse_card("As").unwrap(), parse_card("2s").unwrap(),
            parse_card("3s").unwrap(), parse_card("4s").unwrap(),
            parse_card("5s").unwrap(), parse_card("Ks").unwrap(),
            parse_card("Qh").unwrap(),
        ];
        let flush: [Card; 7] = [
            parse_card("As").unwrap(), parse_card("Ks").unwrap(),
            parse_card("Qs").unwrap(), parse_card("Js").unwrap(),
            parse_card("9s").unwrap(), parse_card("2d").unwrap(),
            parse_card("3h").unwrap(),
        ];
        assert!(evaluate7(&wheel_sf) > evaluate7(&flush));
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-core low_straight_flush wheel_straight_flush`
Expected: both FAIL (current code scores the SF hands as plain flushes,
below the A-high flush).

- [ ] **Step 3: Implement `evaluate_best` and delegate `evaluate7` to it**

In `crates/gto-core/src/eval.rs`, replace the whole block from
`pub fn evaluate7` through `fn best5_from_flush_mask` (lines 186-235)
with:

```rust
/// Evaluate one exact 5-card hand via the lookup tables.
fn eval5_table(cards: &[Card; 5], t: &Tables) -> u16 {
    let s0 = suit(cards[0]);
    if cards.iter().all(|&c| suit(c) == s0) {
        let mask: u16 = cards.iter().fold(0u16, |acc, &c| acc | (1 << rank(c)));
        return t.flush[mask as usize];
    }
    let mut ranks = [0u8; 5];
    for (i, &c) in cards.iter().enumerate() {
        ranks[i] = rank(c);
    }
    ranks.sort_unstable();
    eval5_nonflush(&ranks, t)
}

/// Evaluate the best 5-card hand from 5..=7 **distinct** cards.
/// Returns strength u16 (higher = better, 0 is reserved for "invalid").
/// Debug builds panic on duplicate or out-of-range cards.
pub fn evaluate_best(cards: &[Card]) -> u16 {
    let n = cards.len();
    assert!((5..=7).contains(&n), "evaluate_best needs 5..=7 cards, got {n}");
    #[cfg(debug_assertions)]
    {
        let mut seen = [false; 52];
        for &c in cards {
            assert!((c as usize) < 52, "card index out of range: {c}");
            assert!(!seen[c as usize], "duplicate card: {c}");
            seen[c as usize] = true;
        }
    }
    let t = get_tables();
    if n == 5 {
        let five: [Card; 5] = cards.try_into().unwrap();
        return eval5_table(&five, t);
    }
    // Enumerate all 5-card subsets (6 for n=6, 21 for n=7) and take the max.
    // This also fixes the historic flush-path bug: straight flushes formed by
    // low cards of a 6-7 card flush suit are found by subset enumeration.
    let mut best = 0u16;
    for i in 0..n {
        for j in (i + 1)..n.max(i + 2) {
            if n == 6 && j != i + 1 {
                break; // n=6: drop exactly one card (j loop runs once per i)
            }
            let mut five = [0u8; 5];
            let mut k = 0;
            for (idx, &c) in cards.iter().enumerate() {
                let dropped = if n == 6 { idx == i } else { idx == i || idx == j };
                if !dropped {
                    five[k] = c;
                    k += 1;
                }
            }
            if k != 5 {
                continue;
            }
            best = best.max(eval5_table(&five, t));
            if n == 6 {
                break;
            }
        }
    }
    best
}

/// Evaluate the best 5-card hand from exactly 7 cards.
/// Returns strength u16 (higher = better).
pub fn evaluate7(cards: &[Card; 7]) -> u16 {
    evaluate_best(cards)
}
```

Note: `best5_from_flush_mask` is deleted (dead code). If the n=6/n=7 loop
above feels too clever during implementation, replace it with two separate
simple loops (one `for skip in 0..6`, one nested `for i, for j`) — clarity
beats compactness; behavior must be identical.

- [ ] **Step 4: Export `evaluate_best` from the crate root**

In `crates/gto-core/src/lib.rs` change line 12:

```rust
pub use eval::{evaluate7, evaluate_best, parse_card};
```

- [ ] **Step 5: Run the full gto-core test suite**

Run: `cargo test -p gto-core`
Expected: all tests PASS, including the two new ones and the pre-existing
`royal_beats_straight_flush` / `quads_beat_full_house`.

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add gto/crates/gto-core/src/eval.rs gto/crates/gto-core/src/lib.rs
git commit -m "fix(gto-core): straight flushes missed in 6-7 card flush suits

evaluate7 kept only the top-5 ranks of the flush suit, scoring low
straight flushes (incl. wheel SF) as plain flushes. evaluate_best now
enumerates 5-card subsets with table lookups; evaluate7 delegates to it.
Adds duplicate-card assertions in debug builds."
```

---

### Task 2: Fix phantom-2c padding via shared `showdown_strengths`

The bug: both `showdown_values` copies build `let mut c7 = [0u8; 7]` and
fill only `2 + board.len()` slots (`cfr.rs:188-194`, `multistreet.rs:179-185`).
For 3-4 card boards the remaining slots stay 0 = 2c, so hands are evaluated
with duplicated phantom 2c cards (e.g. on board 9h8d7c, 2s2d scores quads
and "beats" the real straight 6s5s).

**Files:**
- Modify: `crates/gto-core/src/eval.rs` (add `showdown_strengths`)
- Modify: `crates/gto-core/src/cfr.rs:183-194`
- Modify: `crates/gto-core/src/multistreet.rs:174-185`
- Modify: `crates/gto-core/src/lib.rs:12`

- [ ] **Step 1: Write the failing tests**

Append inside `mod tests` in `crates/gto-core/src/eval.rs`:

```rust
    #[test]
    fn showdown_strengths_no_phantom_cards_on_flop_board() {
        use crate::range::combo_index;
        let board: Vec<Card> = ["9h", "8d", "7c"]
            .iter().map(|s| parse_card(s).unwrap()).collect();
        let s = showdown_strengths(&board);
        let straight = combo_index(parse_card("6s").unwrap(), parse_card("5s").unwrap());
        let deuces   = combo_index(parse_card("2s").unwrap(), parse_card("2d").unwrap());
        // 65s makes the nut straight; 22 is a mere underpair. With the
        // phantom-2c bug, 22 scored quads and won.
        assert!(
            s[straight] > s[deuces],
            "straight {} must beat pocket deuces {}", s[straight], s[deuces]
        );
    }

    #[test]
    fn showdown_strengths_blocked_combos_are_zero() {
        use crate::range::combo_index;
        let board: Vec<Card> = ["9h", "8d", "7c"]
            .iter().map(|s| parse_card(s).unwrap()).collect();
        let s = showdown_strengths(&board);
        let blocked = combo_index(parse_card("9h").unwrap(), parse_card("Ah").unwrap());
        assert_eq!(s[blocked], 0, "combos containing a board card must be 0");
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-core showdown_strengths`
Expected: COMPILE FAIL — `showdown_strengths` not defined yet.

- [ ] **Step 3: Implement `showdown_strengths` in eval.rs**

Add after `evaluate7` in `crates/gto-core/src/eval.rs`:

```rust
/// Per-combo showdown strength on a 3-5 card board.
/// Index = `range::combo_index`; 0 marks combos blocked by the board.
/// Evaluates exactly 2 hole + board cards — no padding, no phantom cards.
pub fn showdown_strengths(board: &[Card]) -> Vec<u16> {
    assert!(
        (3..=5).contains(&board.len()),
        "board must have 3-5 cards, got {}", board.len()
    );
    crate::range::all_combos()
        .iter()
        .map(|&(a, b)| {
            if board.contains(&a) || board.contains(&b) {
                return 0;
            }
            let mut cards = Vec::with_capacity(2 + board.len());
            cards.push(a);
            cards.push(b);
            cards.extend_from_slice(board);
            evaluate_best(&cards)
        })
        .collect()
}
```

And export it in `crates/gto-core/src/lib.rs` line 12:

```rust
pub use eval::{evaluate7, evaluate_best, parse_card, showdown_strengths};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-core showdown_strengths`
Expected: 2 PASS.

- [ ] **Step 5: Replace both zero-padded strength computations**

In `crates/gto-core/src/cfr.rs`, inside `showdown_values` (lines 183-194),
replace:

```rust
        let strengths: Vec<u16> = combos.iter().map(|&(ca, cb)| {
            if board.contains(&ca) || board.contains(&cb) { return 0; }
            let mut c7 = [0u8; 7];
            c7[0] = ca; c7[1] = cb;
            for (j, &bc) in board.iter().enumerate().take(5) { c7[2+j] = bc; }
            evaluate7(&c7)
        }).collect();
```

with:

```rust
        let strengths: Vec<u16> = crate::eval::showdown_strengths(board);
```

Apply the identical replacement in `crates/gto-core/src/multistreet.rs`
inside its `showdown_values` (lines 179-185). Remove the now-unused
`evaluate7` imports from both files if the compiler warns
(`use crate::eval::{evaluate7, Card};` → `use crate::eval::Card;`).

- [ ] **Step 6: Run the full gto-core test suite**

Run: `cargo test -p gto-core`
Expected: all PASS. Note: `river_subgame_smoke` / `flop_with_dummy_turn_ev`
outputs may shift slightly (they assert structure, not values).

- [ ] **Step 7: Build gto-py to confirm the API surface still compiles**

Run: `cargo build -p gto-py --release`
Expected: clean build (no signature changes were made).

- [ ] **Step 8: Commit**

```bash
cd ~/projects
git add gto/crates/gto-core/src/eval.rs gto/crates/gto-core/src/cfr.rs \
        gto/crates/gto-core/src/multistreet.rs gto/crates/gto-core/src/lib.rs
git commit -m "fix(gto-core): phantom 2c in flop/turn showdown evaluation

showdown_values zero-padded a [0u8;7] board buffer, so 3-4 card boards
were evaluated with duplicated phantom 2c cards. Both solvers now use a
shared eval::showdown_strengths that evaluates exactly 2+board cards."
```

---

### Task 3: Doc-mark the single-street solver as river-only approximation

No behavior change; documentation only (audit issue #1 stays by design —
the correct multistreet engine lands in the new `gto-hu` crate).

**Files:**
- Modify: `crates/gto-core/src/cfr.rs:1` (module doc)
- Modify: `crates/gto-core/src/lib.rs:22` (`solve` doc)
- Modify: `crates/gto-py/src/lib.rs:48` (`solve_spot` doc)

- [ ] **Step 1: Add warnings**

At the top of `crates/gto-core/src/cfr.rs` (before line 1), prepend:

```rust
//! # ⚠ Single-street approximation — river-only correctness
//!
//! `CfrSolver` evaluates `NextStreet` nodes as immediate showdowns
//! (see the `NodeKind::Showdown | NodeKind::NextStreet` arm below).
//! Results are only game-theoretically meaningful on **river** (5-card)
//! boards. For flop/turn boards this is a rough approximation that
//! ignores future streets — never present its output as GTO.
//! The preflop-to-river solver lives in the `gto-hu` crate.
```

In `crates/gto-core/src/lib.rs`, above `pub fn solve(` add:

```rust
/// ⚠ Single-street approximation: flop/turn boards are solved as if the
/// hand ends after this street (NextStreet ≈ Showdown). Only river boards
/// produce correct equilibrium strategies. See `gto-hu` for the real
/// multistreet solver.
```

In `crates/gto-py/src/lib.rs`, above `fn solve_spot(` (line ~48) add:

```rust
/// ⚠ Single-street approximation (river-only correctness). Flop/turn
/// results ignore future streets; do not present them as GTO.
```

- [ ] **Step 2: Verify build and tests**

Run: `cargo test -p gto-core && cargo build -p gto-py --release`
Expected: PASS / clean build.

- [ ] **Step 3: Commit**

```bash
cd ~/projects
git add gto/crates/gto-core/src/cfr.rs gto/crates/gto-core/src/lib.rs \
        gto/crates/gto-py/src/lib.rs
git commit -m "docs(gto-core): mark single-street solver as river-only approximation"
```

---

### Task 4: Strict card-duplication tests

**Files:**
- Create: `crates/gto-core/tests/card_integrity.rs`

- [ ] **Step 1: Write the tests**

Create `crates/gto-core/tests/card_integrity.rs`:

```rust
//! Strict card-integrity tests: duplicates must be impossible or fatal.

use gto_core::eval::{evaluate_best, parse_card};
use gto_core::{all_combos, combo_index, full_deck, NUM_COMBOS};

#[test]
#[should_panic(expected = "duplicate card")]
fn evaluate_best_panics_on_duplicate_cards_in_debug() {
    let c = |s: &str| parse_card(s).unwrap();
    // 2c appears twice — exactly the historic phantom-card shape.
    let cards = [c("Ah"), c("Kd"), c("2c"), c("2c"), c("9h"), c("3s"), c("4d")];
    let _ = evaluate_best(&cards);
}

#[test]
#[should_panic(expected = "5..=7 cards")]
fn evaluate_best_rejects_short_input() {
    let c = |s: &str| parse_card(s).unwrap();
    let _ = evaluate_best(&[c("Ah"), c("Kd"), c("2c"), c("9h")]);
}

#[test]
fn full_deck_has_52_unique_cards() {
    let deck = full_deck();
    assert_eq!(deck.len(), 52);
    let mut seen = [false; 52];
    for card in deck {
        assert!(!seen[card.0 as usize], "duplicate card {}", card.0);
        seen[card.0 as usize] = true;
    }
}

#[test]
fn combo_index_is_a_bijection() {
    let combos = all_combos();
    assert_eq!(combos.len(), NUM_COMBOS);
    for (i, &(a, b)) in combos.iter().enumerate() {
        assert!(a < b, "combo {i} not ordered: ({a},{b})");
        assert_eq!(combo_index(a, b), i, "combo_index mismatch at {i}");
        assert_eq!(combo_index(b, a), i, "combo_index must be order-insensitive");
    }
}
```

- [ ] **Step 2: Run the tests**

Run: `cargo test -p gto-core --test card_integrity`
Expected: 4 PASS (the `should_panic` ones rely on debug assertions, which
are active under `cargo test`).

- [ ] **Step 3: Run the full suite once more**

Run: `cargo test -p gto-core`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
cd ~/projects
git add gto/crates/gto-core/tests/card_integrity.rs
git commit -m "test(gto-core): strict card-duplication and combo-index integrity tests"
```

---

## Out of scope (by design, see spec §16)

- The fold-payoff inflation in `tree.rs` FoldTerminals (winner gets half of
  a pot that includes the uncalled bet) is **not** fixed here: it is part of
  the legacy approximation; the correct accounting ships in `gto-hu`
  (`payoff = chips_won − contrib`). Spec audit table issue #8.
- No regeneration of the 5265-spot Parquet library (numbers improve after
  Task 2; regeneration is a separate ~40 min GPU decision for the user).
- No changes to `gto-cuda`.
