# HU Phase 3: Turn+River Solver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `gto-hu` with a correct HU NLHE Turn+River abstract solver: fixed 4-card turn board, river dealt as a public chance node (exact enumeration or seeded public chance sampling), reusing the validated river action tree, terminal payoffs, and CFR+/DCFR machinery.

**Architecture:** Per design spec §7, chance nodes do **not** materialize cards in the tree — a single `Chance { child }` node marks "deal the river", and the solver enumerates or samples the 48 off-board cards at traversal time. River-street action nodes get card-indexed table slices (`ctx * na * N` layout). Exact chance weight is `1/44` per (hero, villain) deal (52 − 4 board − 2 − 2); sampling draws uniform from the 48 public cards with importance scale `48/44`, which is unbiased. Exploitability is always computed by exact enumeration regardless of training mode.

**Tech Stack:** Rust (no new dependencies — RNG is a local SplitMix64), existing `gto-core` evaluator, existing `gto-hu` scalar/vector CFR framework.

**Verification baseline:** Run all test commands with `--release` (the existing differential test assumes release speed: "30 000 scalar iterations (~18 s in release)").

```bash
cd ~/projects/gto && source ~/.cargo/env
cargo test --release -p gto-hu          # full crate suite
```

---

## Correctness arguments baked into this plan (read first)

1. **Exact chance weight = 1/44.** At a chance node the solver loops the 48 public
   river cards. For traverser combo `h`, contributions are masked to cards
   `r ∉ h`; the opponent's reach entering subtree `r` is zeroed for combos
   containing `r`. So for each fixed (h, o) pair exactly 44 cards survive both
   masks, each weighted 1/44 → probabilities sum to 1 per deal and the chance
   node value is exact.
2. **Sampling is unbiased.** Draw `r ~ U(48 public cards)`. For `h ∌ r`, return
   `v_r[h] × 48/44`; for `h ∋ r`, return 0. Expectation:
   `E[v̂[h]] = Σ_{r∉h} (1/48)(48/44) v_r[h] = (1/44) Σ_{r∉h} v_r[h]` = the exact
   enumerated value. Regret updates inside the sampled subtree follow standard
   chance-sampled MCCFR.
3. **All-in on turn:** turn street closes with both stacks 0 → `Chance` →
   `Showdown` node directly (spec §6 "All-in handling"); the river card still
   decides the winner via the per-card showdown table.
4. **No turn-call→showdown shortcut:** a non-all-in turn close always produces
   `Chance` → river `Action` subtree (pinned by test).
5. **Junk infosets are inert.** Inside river subtree `r`, combos containing `r`
   still receive regret updates (values computed vs an opp reach that excludes
   `r`-blocked combos), but (a) their chance-level contribution is masked, (b)
   their reach is zeroed so their `strat_sum` stays 0, and (c) exports mask them
   via `export_weight`. They cannot influence any real strategy or value.

## File structure

| File | Status | Responsibility |
|---|---|---|
| `crates/gto-hu/src/game/betting.rs` | modify | `street_root` (generalize `river_root`), `advance_street` |
| `crates/gto-hu/src/tree/node.rs` | modify | `NodeKind::Chance { child }` |
| `crates/gto-hu/src/tree/config.rs` | modify | `StreetConfig::srp_turn()` |
| `crates/gto-hu/src/tree/builder.rs` | modify | `legal_actions` / `expand` → `pub(super)` for reuse |
| `crates/gto-hu/src/tree/turn_builder.rs` | create | `TurnTreeConfig`, `build_turn_river_tree` |
| `crates/gto-hu/src/tree/mod.rs` | modify | exports |
| `crates/gto-hu/src/solver/showdown.rs` | create | `ShowdownTable`, `weighted_compat` (extracted from vector.rs) |
| `crates/gto-hu/src/solver/vector.rs` | modify | use shared showdown module (mechanical refactor, pinned by tests) |
| `crates/gto-hu/src/solver/rng.rs` | create | SplitMix64 (seeded, dependency-free) |
| `crates/gto-hu/src/solver/turn_river.rs` | create | `ChanceMode`, `TurnRiverSolver` (traversal, BR, exploitability, game value) |
| `crates/gto-hu/src/solver/mod.rs` | modify | exports |
| `crates/gto-hu/src/games/tiny_turn_river.rs` | create | scalar reference game (explicit deals + explicit river chance) |
| `crates/gto-hu/src/games/mod.rs` | modify | exports |
| `crates/gto-hu/src/reports/mod.rs` | modify | `TreeStats.chance_nodes`, `card_str` → `pub(crate)`, `turn` submodule |
| `crates/gto-hu/src/reports/turn.rs` | create | turn CSV/JSON exports |
| `crates/gto-hu/src/bin/solve_turn_river.rs` | create | `solve-hu-turn-river` CLI |
| `crates/gto-hu/Cargo.toml` | modify | `[[bin]]` entry |
| `crates/gto-hu/tests/test_betting.rs` | modify | street_root / advance_street tests |
| `crates/gto-hu/tests/test_river_tree.rs` | modify | add `Chance` match arm (1 test) |
| `crates/gto-hu/tests/test_turn_tree.rs` | create | tree structure + payoff tests |
| `crates/gto-hu/tests/test_turn_river_solver.rs` | create | chance legality, masking, strategy sums, exploitability, quads, sampling |
| `crates/gto-hu/tests/test_turn_differential.rs` | create | TinyTurnRiver scalar vs vector enumerate |
| `crates/gto-hu/tests/test_turn_reports.rs` | create | export files + finite exploitability in JSON |
| `crates/gto-hu/README.md`, `gto/PROGRESS.md`, `gto/CLAUDE.md` | modify | docs |

**Memory note:** with `TurnTreeConfig::srp()` at 20bb pot / 90bb stacks, table
memory ≈ 9 river betting subtrees × ~34 (node,action) pairs × 48 cards × 1326
combos × 16 B ≈ **~300 MB**. Expected and fine on the dev machine; the CLI
prints the actual figure. Tests use reduced configs (a few MB).

---

### Task 1: `BettingState::street_root` and `advance_street`

**Files:**
- Modify: `crates/gto-hu/src/game/betting.rs`
- Test: `crates/gto-hu/tests/test_betting.rs`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_betting.rs`)

```rust
// --- Phase 3: street_root / advance_street ---------------------------------

#[test]
fn turn_root_matches_river_root_shape() {
    let s = BettingState::street_root(Street::Turn, 20 * BB, 90 * BB);
    assert_eq!(s.street, Street::Turn);
    assert_eq!(s.to_act, PLAYER_BB);
    assert_eq!(s.stacks, [90 * BB; 2]);
    assert_eq!(s.contrib, [10 * BB; 2]);
    assert_eq!(s.pot(), 20 * BB);
    assert!(!s.street_closed());
}

#[test]
fn advance_street_resets_betting_and_keeps_chips() {
    // Turn: OOP bets 10bb, IP calls → street closes.
    let s = BettingState::street_root(Street::Turn, 20 * BB, 90 * BB)
        .apply(Action::Bet { to: 10 * BB })
        .apply(Action::Call);
    assert!(s.street_closed());
    let r = s.advance_street();
    assert_eq!(r.street, Street::River);
    assert_eq!(r.to_act, PLAYER_BB);
    assert_eq!(r.stacks, [80 * BB; 2]);
    assert_eq!(r.street_committed, [0; 2]);
    assert_eq!(r.contrib, [20 * BB; 2]);
    assert_eq!(r.pot(), 40 * BB);
    assert!(!r.street_closed());
}

#[test]
#[should_panic(expected = "matched contributions")]
fn advance_street_rejects_fold_close() {
    // Fold closes the street with unmatched contributions.
    let s = BettingState::street_root(Street::Turn, 20 * BB, 90 * BB)
        .apply(Action::Bet { to: 10 * BB })
        .apply(Action::Fold);
    let _ = s.advance_street();
}
```

Check the existing imports at the top of `test_betting.rs`; ensure they include
`Street` (add `use gto_hu::game::Street;` style import matching the file's
current import block if missing).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test --release -p gto-hu --test test_betting`
Expected: FAIL — `no function or associated item named 'street_root'`

- [ ] **Step 3: Implement** (in `betting.rs`, replace `river_root` with the pair below; keep the doc comments)

```rust
    /// Symmetric street subgame root: pot carried in, OOP (BB) to act.
    /// Generalizes `river_root` to any postflop street.
    pub fn street_root(street: Street, pot: i64, stack: i64) -> Self {
        assert!(
            pot > 0 && pot % 2 == 0,
            "carried pot must be positive and even"
        );
        assert!(stack > 0, "stack must be positive");
        BettingState {
            street,
            to_act: PLAYER_BB,
            stacks: [stack; 2],
            street_committed: [0; 2],
            contrib: [pot / 2; 2],
            raises_this_street: 0,
            actions_this_street: 0,
            closed: false,
        }
    }

    /// River subgame root: symmetric pot carried in, OOP (BB) to act.
    pub fn river_root(pot: i64, stack: i64) -> Self {
        Self::street_root(Street::River, pot, stack)
    }

    /// Move a closed (non-fold) street to the next one: betting counters
    /// reset, OOP to act, chips carried over.
    pub fn advance_street(&self) -> BettingState {
        assert!(self.closed, "cannot advance an open street");
        assert_eq!(
            self.contrib[0], self.contrib[1],
            "advance_street requires matched contributions (no fold)"
        );
        let next = self.street.next().expect("no street after river");
        BettingState {
            street: next,
            to_act: PLAYER_BB,
            stacks: self.stacks,
            street_committed: [0; 2],
            contrib: self.contrib,
            raises_this_street: 0,
            actions_this_street: 0,
            closed: false,
        }
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test --release -p gto-hu --test test_betting`
Expected: PASS (all, including the 13 pre-existing tests)

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/game/betting.rs crates/gto-hu/tests/test_betting.rs
git commit -m "feat(gto-hu): street_root and advance_street for multistreet subgames"
```

---

### Task 2: `NodeKind::Chance` variant (compile-green refactor)

Adds the variant and patches every exhaustive match. **No behavior change** —
the full existing suite must stay green.

**Files:**
- Modify: `crates/gto-hu/src/tree/node.rs`
- Modify: `crates/gto-hu/src/solver/vector.rs` (3 match sites)
- Modify: `crates/gto-hu/src/reports/mod.rs` (`tree_stats`, `TreeStats`)
- Modify: `crates/gto-hu/src/games/tiny_river.rs` (`payoff` match)
- Modify: `crates/gto-hu/tests/test_river_tree.rs` (`all_terminals_…` match)

- [ ] **Step 1: Add the variant** (`tree/node.rs`)

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Action { actor: u8 },
    FoldTerminal { winner: u8 },
    Showdown,
    /// Deal the river card, then continue at `child`. Cards are not
    /// materialized in the tree: the solver enumerates or samples them at
    /// traversal time (design spec §7).
    Chance { child: usize },
}
```

- [ ] **Step 2: Build and fix every non-exhaustive match the compiler reports.**

Run: `cargo build --release -p gto-hu` and patch:

`solver/vector.rs` — in `traverse`, `br_values`, and `avg_values`, add to each
`match kind { … }`:

```rust
            NodeKind::Chance { .. } => unreachable!("river-only tree has no chance nodes"),
```

`reports/mod.rs` — add field + arm:

```rust
pub struct TreeStats {
    pub total_nodes: usize,
    pub action_nodes: usize,
    pub chance_nodes: usize,
    pub fold_terminals: usize,
    pub showdown_terminals: usize,
    /// Structural estimate: regrets + strategy sums, 8 bytes each, per
    /// (node, action, combo). For chance trees this ignores the per-river-
    /// card multiplicity — use `TurnRiverSolver::table_bytes()` instead.
    pub memory_estimate_bytes: usize,
}
```

(initialize `chance_nodes: 0` in the struct literal inside `tree_stats`, and
add the arm)

```rust
            NodeKind::Chance { .. } => s.chance_nodes += 1,
```

`games/tiny_river.rs` — `payoff` match: replace the
`NodeKind::Action { .. } => unreachable!(…)` arm with a wildcard:

```rust
            _ => unreachable!("payoff at non-terminal"),
```

`tests/test_river_tree.rs` — in `all_terminals_are_fold_or_showdown_and_pots_conserve`,
add an arm to the match:

```rust
            NodeKind::Chance { .. } => unreachable!("river tree has no chance nodes"),
```

- [ ] **Step 3: Run the full suite to prove no behavior change**

Run: `cargo test --release -p gto-hu`
Expected: PASS — same 56 tests as before plus Task 1's 3.

- [ ] **Step 4: Commit**

```bash
git add -A crates/gto-hu
git commit -m "feat(gto-hu): NodeKind::Chance variant (cards dealt at traversal time)"
```

---

### Task 3: `srp_turn` config and `build_turn_river_tree`

**Files:**
- Modify: `crates/gto-hu/src/tree/config.rs`
- Modify: `crates/gto-hu/src/tree/builder.rs` (visibility only)
- Create: `crates/gto-hu/src/tree/turn_builder.rs`
- Modify: `crates/gto-hu/src/tree/mod.rs`
- Test: `crates/gto-hu/tests/test_turn_tree.rs`

- [ ] **Step 1: Write the failing tests** (`tests/test_turn_tree.rs`)

```rust
use gto_core::eval::parse_card;
use gto_hu::game::{Action, Street, BB, PLAYER_BB};
use gto_hu::tree::{build_turn_river_tree, NodeKind, Tree, TurnTreeConfig};

#[allow(dead_code)]
fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn srp_tree() -> Tree {
    build_turn_river_tree(20 * BB, 90 * BB, &TurnTreeConfig::srp())
}

fn child_by<F: Fn(&Action) -> bool>(t: &Tree, node: usize, pred: F) -> usize {
    t.nodes[node]
        .children
        .iter()
        .find(|(a, _)| pred(a))
        .map(|&(_, id)| id)
        .expect("child not found")
}

fn chance_child(t: &Tree, node: usize) -> usize {
    match t.nodes[node].kind {
        NodeKind::Chance { child } => child,
        k => panic!("expected chance node, got {k:?}"),
    }
}

#[test]
fn turn_root_offers_check_b50_b100() {
    let t = srp_tree();
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    // SRP turn per design spec §6: check, b50, b100 — no open all-in.
    assert_eq!(labels, vec!["check", "bet 10.0bb", "bet 20.0bb"]);
    assert_eq!(t.nodes[0].state.street, Street::Turn);
}

#[test]
fn turn_bet_call_proceeds_to_river_betting() {
    // Hard constraint: no turn-call → showdown shortcut.
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let call = child_by(&t, bet, |a| matches!(a, Action::Call));
    let river = chance_child(&t, call); // call closes turn → Chance node
    let n = &t.nodes[river];
    assert!(matches!(n.kind, NodeKind::Action { actor } if actor == PLAYER_BB));
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.pot(), 40 * BB);
    assert_eq!(n.state.stacks, [80 * BB; 2]);
    assert_eq!(n.state.street_committed, [0; 2]);
}

#[test]
fn check_check_deals_river_with_unchanged_chips() {
    let t = srp_tree();
    let x1 = child_by(&t, 0, |a| matches!(a, Action::Check));
    let x2 = child_by(&t, x1, |a| matches!(a, Action::Check));
    let river = chance_child(&t, x2);
    let n = &t.nodes[river];
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.pot(), 20 * BB);
    assert_eq!(n.state.stacks, [90 * BB; 2]);
}

#[test]
fn vs_raise_offers_jam_at_this_depth() {
    // b50 = 10bb → raise 3x = 30bb → second raise 3x = 90bb ≥ stack ⇒ AllIn.
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 30 * BB));
    let jam = t.nodes[raise]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::AllIn { to } if *to == 90 * BB));
    assert!(jam.is_some(), "second raise must become a jam at 90bb stacks");
}

#[test]
fn allin_turn_runout_goes_to_showdown_with_no_betting() {
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 30 * BB));
    let jam = child_by(&t, raise, |a| matches!(a, Action::AllIn { .. }));
    let call = child_by(&t, jam, |a| matches!(a, Action::Call));
    let sd = chance_child(&t, call);
    let n = &t.nodes[sd];
    assert!(matches!(n.kind, NodeKind::Showdown), "all-in runout must be showdown");
    assert!(n.children.is_empty(), "no betting after all-in");
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.stacks, [0; 2]);
    assert_eq!(n.state.pot(), 20 * BB + 2 * 90 * BB);
}

#[test]
fn turn_bet_fold_terminal_payoff_exact() {
    use gto_hu::game::terminal::fold_payoffs;
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let fold = child_by(&t, bet, |a| matches!(a, Action::Fold));
    let n = &t.nodes[fold];
    let NodeKind::FoldTerminal { winner } = n.kind else {
        panic!("expected fold terminal");
    };
    assert_eq!(winner, PLAYER_BB); // OOP bet, IP folded
    let pay = fold_payoffs(&n.state, winner);
    // Winner nets the loser's total contribution: 10bb (pot half).
    assert_eq!(pay, [-10 * BB, 10 * BB]);
    assert_eq!(pay[0] + pay[1], 0);
}

#[test]
fn river_close_inside_turn_tree_is_showdown_not_chance() {
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let call = child_by(&t, bet, |a| matches!(a, Action::Call));
    let river_root = chance_child(&t, call);
    // River: OOP bets 75% pot (30bb), IP calls → Showdown.
    let rbet = child_by(&t, river_root, |a| matches!(a, Action::Bet { .. }));
    let rcall = child_by(&t, rbet, |a| matches!(a, Action::Call));
    assert!(matches!(t.nodes[rcall].kind, NodeKind::Showdown));
}

#[test]
fn chips_conserve_at_every_terminal_and_chance() {
    let t = srp_tree();
    let initial = 20 * BB + 2 * 90 * BB;
    for n in &t.nodes {
        match n.kind {
            NodeKind::FoldTerminal { .. } | NodeKind::Showdown | NodeKind::Chance { .. } => {
                assert_eq!(
                    n.state.pot() + n.state.stacks[0] + n.state.stacks[1],
                    initial,
                    "chip conservation violated"
                );
            }
            NodeKind::Action { .. } => assert!(!n.children.is_empty()),
        }
    }
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cargo test --release -p gto-hu --test test_turn_tree`
Expected: FAIL — `unresolved imports … build_turn_river_tree, TurnTreeConfig`

- [ ] **Step 3: Implement.**

`tree/config.rs` — add to `impl StreetConfig`:

```rust
    /// SRP turn per spec §6: check, b50, b100 / vs bet: fold, call,
    /// raise 3x-or-jam / vs raise: fold, call, jam (the second 3x raise
    /// reaches the stack at normal SPRs and becomes a jam).
    pub fn srp_turn() -> Self {
        StreetConfig {
            bet_pcts: vec![50, 100],
            allow_allin_bet: false,
            raise: RaiseRule::ToFactorOrJam(3.0),
            max_raises: 2,
        }
    }
```

`tree/builder.rs` — change visibility (signatures otherwise untouched):

```rust
pub(super) fn legal_actions(state: &BettingState, cfg: &StreetConfig) -> Vec<Action> {
```

```rust
pub(super) fn expand(tree: &mut Tree, node_id: usize, cfg: &StreetConfig) {
```

`tree/turn_builder.rs` — new file:

```rust
use super::builder::{expand as expand_street, legal_actions};
use super::config::StreetConfig;
use super::node::{Node, NodeKind, Tree};
use crate::game::{Action, BettingState, Street};

/// Action abstraction per street for a turn+river tree.
#[derive(Debug, Clone)]
pub struct TurnTreeConfig {
    pub turn: StreetConfig,
    pub river: StreetConfig,
}

impl TurnTreeConfig {
    pub fn srp() -> Self {
        TurnTreeConfig {
            turn: StreetConfig::srp_turn(),
            river: StreetConfig::srp_river(),
        }
    }
}

/// Build the turn+river tree. Turn betting starts from a symmetric pot with
/// OOP (BB) to act; every non-fold turn close deals the river through a
/// `Chance` node (cards are enumerated/sampled by the solver, not
/// materialized here — design spec §7). All-in closes skip river betting:
/// Chance → Showdown (spec §6).
pub fn build_turn_river_tree(pot: i64, stack: i64, cfg: &TurnTreeConfig) -> Tree {
    cfg.turn.validate();
    cfg.river.validate();
    let root_state = BettingState::street_root(Street::Turn, pot, stack);
    let mut tree = Tree { nodes: Vec::new() };
    tree.nodes.push(Node {
        kind: NodeKind::Action {
            actor: root_state.to_act,
        },
        state: root_state,
        children: Vec::new(),
    });
    expand_turn(&mut tree, 0, cfg);
    tree
}

fn expand_turn(tree: &mut Tree, node_id: usize, cfg: &TurnTreeConfig) {
    let state = tree.nodes[node_id].state;
    debug_assert_eq!(state.street, Street::Turn);
    let actions = legal_actions(&state, &cfg.turn);
    let mut children = Vec::with_capacity(actions.len());

    for action in actions {
        let child_state = state.apply(action);
        let child_id = tree.nodes.len();
        if matches!(action, Action::Fold) {
            tree.nodes.push(Node {
                kind: NodeKind::FoldTerminal {
                    winner: 1 - state.to_act,
                },
                state: child_state,
                children: Vec::new(),
            });
        } else if child_state.street_closed() {
            // Turn betting finished → deal the river through a chance node.
            tree.nodes.push(Node {
                kind: NodeKind::Chance { child: 0 }, // patched below
                state: child_state,
                children: Vec::new(),
            });
            let river_state = child_state.advance_street();
            let grandchild_id = tree.nodes.len();
            if river_state.stacks.iter().any(|&s| s == 0) {
                // All-in on the turn: river is dealt as chance, then straight
                // to showdown — no further betting (spec §6).
                tree.nodes.push(Node {
                    kind: NodeKind::Showdown,
                    state: river_state,
                    children: Vec::new(),
                });
            } else {
                tree.nodes.push(Node {
                    kind: NodeKind::Action {
                        actor: river_state.to_act,
                    },
                    state: river_state,
                    children: Vec::new(),
                });
                expand_street(tree, grandchild_id, &cfg.river);
            }
            tree.nodes[child_id].kind = NodeKind::Chance {
                child: grandchild_id,
            };
        } else {
            tree.nodes.push(Node {
                kind: NodeKind::Action {
                    actor: child_state.to_act,
                },
                state: child_state,
                children: Vec::new(),
            });
            expand_turn(tree, child_id, cfg);
        }
        children.push((action, child_id));
    }
    tree.nodes[node_id].children = children;
}
```

`tree/mod.rs`:

```rust
pub mod builder;
pub mod config;
pub mod node;
pub mod turn_builder;

pub use builder::build_river_tree;
pub use config::{RaiseRule, StreetConfig};
pub use node::{Node, NodeKind, Tree};
pub use turn_builder::{build_turn_river_tree, TurnTreeConfig};
```

- [ ] **Step 4: Run tests**

Run: `cargo test --release -p gto-hu --test test_turn_tree --test test_river_tree`
Expected: PASS (9 new + 8 existing)

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/tree crates/gto-hu/tests/test_turn_tree.rs
git commit -m "feat(gto-hu): turn+river tree with chance node and srp_turn abstraction"
```

---

### Task 4: Extract `ShowdownTable` + `weighted_compat` (shared module)

Mechanical refactor pinned by the existing river tests (incl. differential).

**Files:**
- Create: `crates/gto-hu/src/solver/showdown.rs`
- Modify: `crates/gto-hu/src/solver/vector.rs`
- Modify: `crates/gto-hu/src/solver/mod.rs`

- [ ] **Step 1: Create `solver/showdown.rs`** — move the two-sweep diff and
  `weighted_compat` out of `vector.rs` verbatim (bodies unchanged except
  `self.strengths`/`self.sorted_idx` become struct fields):

```rust
//! Blocker-exact showdown machinery shared by the vector solvers.

use gto_core::eval::showdown_strengths;

use crate::ranges::NUM_COMBOS;

const N: usize = NUM_COMBOS;

/// Per-board combo strengths with the O(N) two-sweep win/lose difference.
pub struct ShowdownTable {
    strengths: Vec<u16>,
    /// Combo indices with strength > 0, sorted ascending by strength.
    sorted_idx: Vec<usize>,
}

impl ShowdownTable {
    pub fn new(board: &[u8; 5]) -> Self {
        let strengths = showdown_strengths(board);
        let mut sorted_idx: Vec<usize> = (0..N).filter(|&i| strengths[i] > 0).collect();
        sorted_idx.sort_unstable_by_key(|&i| strengths[i]);
        ShowdownTable {
            strengths,
            sorted_idx,
        }
    }

    /// win_w − lose_w per combo against `opp_reach`, blocker-exact. O(N).
    pub fn diff(&self, combos: &[(u8, u8)], opp_reach: &[f64; N]) -> Vec<f64> {
        let idx = &self.sorted_idx;
        let mut out = vec![0.0; N];

        // Ascending sweep: cum sums over strictly weaker tiers → win_w.
        let mut cum = 0.0f64;
        let mut cum_card = [0.0f64; 52];
        let mut g = 0;
        while g < idx.len() {
            let s = self.strengths[idx[g]];
            let mut h = g;
            while h < idx.len() && self.strengths[idx[h]] == s {
                h += 1;
            }
            for &i in &idx[g..h] {
                let (a, b) = combos[i];
                out[i] += cum - cum_card[a as usize] - cum_card[b as usize];
            }
            for &i in &idx[g..h] {
                let w = opp_reach[i];
                if w != 0.0 {
                    let (a, b) = combos[i];
                    cum += w;
                    cum_card[a as usize] += w;
                    cum_card[b as usize] += w;
                }
            }
            g = h;
        }

        // Descending sweep: cum sums over strictly stronger tiers → −lose_w.
        let mut cum = 0.0f64;
        let mut cum_card = [0.0f64; 52];
        let mut g = idx.len();
        while g > 0 {
            let s = self.strengths[idx[g - 1]];
            let mut start = g;
            while start > 0 && self.strengths[idx[start - 1]] == s {
                start -= 1;
            }
            for &i in &idx[start..g] {
                let (a, b) = combos[i];
                out[i] -= cum - cum_card[a as usize] - cum_card[b as usize];
            }
            for &i in &idx[start..g] {
                let w = opp_reach[i];
                if w != 0.0 {
                    let (a, b) = combos[i];
                    cum += w;
                    cum_card[a as usize] += w;
                    cum_card[b as usize] += w;
                }
            }
            g = start;
        }
        out
    }
}

/// For each combo c: Σ over opponent combos compatible with c of their
/// weight (total − per-card sums + own-combo weight added back).
pub fn weighted_compat(combos: &[(u8, u8)], opp_reach: &[f64; N]) -> Vec<f64> {
    let total: f64 = opp_reach.iter().sum();
    let mut per_card = [0.0f64; 52];
    for (i, &(a, b)) in combos.iter().enumerate() {
        let w = opp_reach[i];
        if w != 0.0 {
            per_card[a as usize] += w;
            per_card[b as usize] += w;
        }
    }
    combos
        .iter()
        .enumerate()
        .map(|(i, &(a, b))| total - per_card[a as usize] - per_card[b as usize] + opp_reach[i])
        .collect()
}
```

- [ ] **Step 2: Refactor `vector.rs` to use it.**
  - Replace fields `strengths: Vec<u16>` and `sorted_idx: Vec<usize>` with
    `showdown: ShowdownTable`.
  - In `new`: replace the strengths/sorted_idx setup with
    `let showdown = ShowdownTable::new(&board);` (after `remove_blockers`).
  - Replace the body of `fn showdown_diff(&self, opp_reach)` with
    `self.showdown.diff(&self.combos, opp_reach)`.
  - Delete the private `fn weighted_compat` at the bottom and import the
    shared one: `use super::showdown::{weighted_compat, ShowdownTable};`
  - Remove the now-unused `use gto_core::eval::showdown_strengths;`.

- [ ] **Step 3: Run the full suite (this refactor is pinned by the differential test)**

Run: `cargo test --release -p gto-hu`
Expected: PASS, no count change.

- [ ] **Step 4: Update `solver/mod.rs`**

```rust
pub mod regret;
pub mod rng;
pub mod scalar;
pub mod showdown;
pub mod variant;
pub mod vector;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use showdown::{weighted_compat, ShowdownTable};
pub use variant::CfrVariant;
pub use vector::{ExplReport, VectorRiverSolver};
```

(`pub mod rng;` forward-declares Task 5 — if you do this step before Task 5,
omit that line and add it in Task 5.)

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/solver
git commit -m "refactor(gto-hu): extract ShowdownTable and weighted_compat for reuse"
```

---

### Task 5: SplitMix64 RNG

**Files:**
- Create: `crates/gto-hu/src/solver/rng.rs`
- Modify: `crates/gto-hu/src/solver/mod.rs` (add `pub mod rng;`)

- [ ] **Step 1: Create the module with an inline determinism test**

```rust
//! SplitMix64 — tiny deterministic RNG for public chance sampling.
//! Dependency-free; the sequence for a given seed is part of the test
//! contract (sampled runs must be reproducible).

pub struct SplitMix64(u64);

impl SplitMix64 {
    pub fn new(seed: u64) -> Self {
        SplitMix64(seed)
    }

    pub fn next_u64(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.0;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }

    /// Uniform index in `0..n`. Modulo bias is < n/2^64 — negligible for
    /// n ≤ 52.
    pub fn next_index(&mut self, n: usize) -> usize {
        (self.next_u64() % n as u64) as usize
    }
}

#[cfg(test)]
mod tests {
    use super::SplitMix64;

    #[test]
    fn same_seed_same_sequence() {
        let mut a = SplitMix64::new(42);
        let mut b = SplitMix64::new(42);
        for _ in 0..100 {
            assert_eq!(a.next_u64(), b.next_u64());
        }
        let mut c = SplitMix64::new(43);
        let same = (0..100).all(|_| SplitMix64::new(42).next_u64() == c.next_u64());
        assert!(!same, "different seeds must diverge");
    }

    #[test]
    fn next_index_in_range() {
        let mut r = SplitMix64::new(7);
        for _ in 0..1000 {
            assert!(r.next_index(48) < 48);
        }
    }
}
```

- [ ] **Step 2: Run** `cargo test --release -p gto-hu --lib`
Expected: PASS (2 tests)

- [ ] **Step 3: Commit**

```bash
git add crates/gto-hu/src/solver/rng.rs crates/gto-hu/src/solver/mod.rs
git commit -m "feat(gto-hu): seeded SplitMix64 for public chance sampling"
```

---

### Task 6: `TurnRiverSolver` — construction + exact enumeration traversal

**Files:**
- Create: `crates/gto-hu/src/solver/turn_river.rs`
- Modify: `crates/gto-hu/src/solver/mod.rs`
- Test: `crates/gto-hu/tests/test_turn_chance.rs`, `crates/gto-hu/tests/test_turn_river_solver.rs`

- [ ] **Step 1: Write the failing tests.**

`tests/test_turn_chance.rs`:

```rust
use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::{all_combos, combo_index, uniform_excluding};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

/// Small abstraction: keeps solver tables at a few MB for tests.
fn reduced_cfg() -> TurnTreeConfig {
    TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    }
}

fn solver(mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &reduced_cfg());
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    TurnRiverSolver::new(tree, b, ranges, CfrVariant::cfr_plus_default(), mode)
}

#[test]
fn rivers_exclude_board_unique_and_complete() {
    let s = solver(ChanceMode::Enumerate);
    let rivers = s.rivers();
    assert_eq!(rivers.len(), 48, "52 − 4 board cards");
    let b = board();
    for &r in rivers {
        assert!(!b.contains(&r), "river card duplicates the board");
    }
    let mut sorted = rivers.to_vec();
    sorted.sort_unstable();
    sorted.dedup();
    assert_eq!(sorted.len(), 48, "river cards must be unique");
}

#[test]
fn chance_weights_sum_to_one_per_deal() {
    // For any fixed (hero, villain) deal, exactly 44 of the 48 public cards
    // avoid all four hole cards; the enumerate weight is 1/44 each.
    let s = solver(ChanceMode::Enumerate);
    let combos = all_combos();
    let hero = combos[combo_index(c("Ah"), c("Kd"))];
    let vill = combos[combo_index(c("Qs"), c("Qc"))];
    let legal = s
        .rivers()
        .iter()
        .filter(|&&r| r != hero.0 && r != hero.1 && r != vill.0 && r != vill.1)
        .count();
    assert_eq!(legal, 44);
    assert!((legal as f64 * (1.0 / 44.0) - 1.0).abs() < 1e-12);
}

#[test]
fn river_card_blocked_combos_are_masked() {
    let mut s = solver(ChanceMode::Enumerate);
    s.run(5);
    let combos = all_combos();
    let card = s.rivers()[0];
    // A combo holding the dealt river card, otherwise legal on the turn.
    let partner = c("As");
    assert_ne!(card, partner);
    let blocked = combo_index(card, partner);
    assert_eq!(combos[blocked].0.min(combos[blocked].1), card.min(partner));

    // Visible on the turn, masked under that river card.
    assert!(s.export_weight(0, None, blocked) > 0.0);
    assert_eq!(s.export_weight(0, Some(0), blocked), 0.0);

    // Its reach under that river was zeroed, so strat_sum stayed 0 →
    // average strategy is uniform there.
    let river_node = s
        .action_node_ids()
        .into_iter()
        .find(|&id| s.tree.nodes[id].state.street == gto_hu::game::Street::River)
        .expect("river action node");
    let avg = s.average_strategy(river_node, Some(0), blocked);
    let na = avg.len();
    for v in &avg {
        assert!((v - 1.0 / na as f64).abs() < 1e-12, "expected untouched uniform");
    }
}
```

`tests/test_turn_river_solver.rs` (first test now; later tasks append):

```rust
use gto_core::eval::parse_card;
use gto_hu::game::{Street, BB};
use gto_hu::ranges::{uniform_excluding, NUM_COMBOS};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn board() -> [u8; 4] {
    [c("2c"), c("7d"), c("9h"), c("Jh")]
}

fn reduced_cfg() -> TurnTreeConfig {
    TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    }
}

fn solver(cfg: &TurnTreeConfig, mode: ChanceMode) -> TurnRiverSolver {
    let tree = build_turn_river_tree(20 * BB, 90 * BB, cfg);
    let b = board();
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    TurnRiverSolver::new(tree, b, ranges, CfrVariant::cfr_plus_default(), mode)
}

#[test]
fn strategies_sum_to_one_for_unblocked_combos() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Enumerate);
    s.run(10);
    for node_id in s.action_node_ids() {
        let actor = s.actor_at(node_id) as usize;
        let ctxs: Vec<Option<usize>> = if s.tree.nodes[node_id].state.street == Street::River {
            (0..s.rivers().len()).map(Some).collect()
        } else {
            vec![None]
        };
        for ctx in ctxs {
            for combo in 0..NUM_COMBOS {
                if s.export_weight(actor, ctx, combo) == 0.0 {
                    continue;
                }
                let strat = s.average_strategy(node_id, ctx, combo);
                let sum: f64 = strat.iter().sum();
                assert!(
                    (sum - 1.0).abs() < 1e-9,
                    "node {node_id} ctx {ctx:?} combo {combo}: sums to {sum}"
                );
            }
        }
    }
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cargo test --release -p gto-hu --test test_turn_chance`
Expected: FAIL — unresolved import `ChanceMode`, `TurnRiverSolver`

- [ ] **Step 3: Implement `solver/turn_river.rs`** (full file; BR/exploitability
  bodies arrive in Task 7 — for now stop after `aggregate_strategy` and the
  helpers, the file must compile):

```rust
//! Exact-combo vector CFR for a fixed turn board. The river is a public
//! chance node: enumerated exactly (tests, exploitability) or sampled
//! (public chance sampling for larger runs). Design spec §6–§7.
//!
//! Chance math: for each (hero, villain) deal exactly 44 of the 48 public
//! river cards are legal (52 − 4 board − 2 − 2). Enumeration weights each
//! surviving card 1/44 (masks below make the per-deal count exactly 44).
//! Sampling draws uniform from the 48 public cards and scales by 48/44,
//! which is unbiased: E[v̂] = Σ_{r∉h} (1/48)(48/44) v_r = (1/44) Σ_{r∉h} v_r.

use super::regret::regret_matching;
use super::rng::SplitMix64;
use super::showdown::{weighted_compat, ShowdownTable};
use super::variant::CfrVariant;
use super::vector::ExplReport;
use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::game::Street;
use crate::ranges::{all_combos, Range, NUM_COMBOS};
use crate::tree::{NodeKind, Tree};

const N: usize = NUM_COMBOS;

/// How the river chance node is expanded during traversal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChanceMode {
    /// Every legal river card, weight 1/44 per deal. Exact; slow.
    Enumerate,
    /// One river card per chance-node visit, importance-scaled (unbiased).
    /// Deterministic for a given seed.
    Sample { seed: u64 },
}

pub struct TurnRiverSolver {
    pub tree: Tree,
    pub turn_board: [u8; 4],
    pub ranges: [Range; 2],
    pub variant: CfrVariant,
    pub mode: ChanceMode,
    /// Legal public river cards (off the turn board), ascending.
    /// The index into this vec is the "card context" (ctx).
    rivers: Vec<u8>,
    /// Showdown table per river card (same index as `rivers`).
    tables: Vec<ShowdownTable>,
    /// [node] → flat tables. Turn action nodes: na*N. River action nodes:
    /// n_rivers*na*N (ctx-major). Other nodes: empty.
    regrets: Vec<Vec<f64>>,
    strat_sum: Vec<Vec<f64>>,
    rng: SplitMix64,
    iteration: u32,
    combos: Vec<(u8, u8)>,
}

#[inline]
fn combo_blocks(combo: (u8, u8), card: u8) -> bool {
    combo.0 == card || combo.1 == card
}

fn zero_card(combos: &[(u8, u8)], card: u8, weights: &mut [f64; N]) {
    for (i, &(a, b)) in combos.iter().enumerate() {
        if a == card || b == card {
            weights[i] = 0.0;
        }
    }
}

impl TurnRiverSolver {
    pub fn new(
        tree: Tree,
        turn_board: [u8; 4],
        mut ranges: [Range; 2],
        variant: CfrVariant,
        mode: ChanceMode,
    ) -> Self {
        assert_eq!(
            tree.nodes[0].state.street,
            Street::Turn,
            "root must be a turn node (build with build_turn_river_tree)"
        );
        let mut seen = [false; 52];
        for &c in &turn_board {
            assert!(!seen[c as usize], "duplicate card on turn board");
            seen[c as usize] = true;
        }
        for r in &mut ranges {
            r.remove_blockers(&turn_board);
        }
        let rivers: Vec<u8> = (0..52u8).filter(|c| !turn_board.contains(c)).collect();
        let tables: Vec<ShowdownTable> = rivers
            .iter()
            .map(|&r| {
                let mut b5 = [0u8; 5];
                b5[..4].copy_from_slice(&turn_board);
                b5[4] = r;
                ShowdownTable::new(&b5)
            })
            .collect();
        let n_rivers = rivers.len();
        let alloc = |tree: &Tree| -> Vec<Vec<f64>> {
            tree.nodes
                .iter()
                .map(|n| match n.kind {
                    NodeKind::Action { .. } => {
                        let ctx = if n.state.street == Street::River {
                            n_rivers
                        } else {
                            1
                        };
                        vec![0.0; ctx * n.children.len() * N]
                    }
                    _ => Vec::new(),
                })
                .collect()
        };
        let regrets = alloc(&tree);
        let strat_sum = alloc(&tree);
        let seed = match mode {
            ChanceMode::Sample { seed } => seed,
            ChanceMode::Enumerate => 0,
        };
        TurnRiverSolver {
            tree,
            turn_board,
            ranges,
            variant,
            mode,
            rivers,
            tables,
            regrets,
            strat_sum,
            rng: SplitMix64::new(seed),
            iteration: 0,
            combos: all_combos(),
        }
    }

    pub fn rivers(&self) -> &[u8] {
        &self.rivers
    }

    /// Total bytes held by regret + average-strategy tables.
    pub fn table_bytes(&self) -> usize {
        self.regrets
            .iter()
            .chain(self.strat_sum.iter())
            .map(|v| v.len() * 8)
            .sum()
    }

    /// Legal river cards per (hero, villain) deal: 52−4−2−2 = 44.
    fn legal_rivers_per_deal(&self) -> f64 {
        (self.rivers.len() - 4) as f64
    }

    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for traverser in 0..2u8 {
                let reach = self.ranges[traverser as usize].weights;
                let opp = self.ranges[1 - traverser as usize].weights;
                self.traverse(0, traverser, &reach, &opp, None);
            }
        }
    }

    /// Table offset for a node: river nodes are ctx-major per card.
    fn table_base(&self, node_id: usize, ctx: Option<usize>, na: usize) -> usize {
        if self.tree.nodes[node_id].state.street == Street::River {
            ctx.expect("river node requires a card context") * na * N
        } else {
            debug_assert!(ctx.is_none(), "turn nodes precede the river deal");
            0
        }
    }

    /// Counterfactual values (bb) for `traverser`'s combos.
    fn traverse(
        &mut self,
        node_id: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
        ctx: Option<usize>,
    ) -> Vec<f64> {
        let kind = self.tree.nodes[node_id].kind;
        match kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[traverser as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(traverser))[traverser as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => match self.mode {
                ChanceMode::Enumerate => {
                    self.chance_enumerate(child, traverser, reach, opp_reach)
                }
                ChanceMode::Sample { .. } => {
                    self.chance_sample(child, traverser, reach, opp_reach)
                }
            },
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let base = self.table_base(node_id, ctx, na);
                let strat = self.node_strategy(node_id, base, na);

                if actor == traverser {
                    let mut action_vals: Vec<Vec<f64>> = Vec::with_capacity(na);
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut nr = *reach;
                        for c in 0..N {
                            nr[c] *= strat[a * N + c];
                        }
                        action_vals.push(self.traverse(child, traverser, &nr, opp_reach, ctx));
                    }
                    let mut ev = vec![0.0; N];
                    for c in 0..N {
                        for (a, av) in action_vals.iter().enumerate() {
                            ev[c] += strat[a * N + c] * av[c];
                        }
                    }
                    // Same per-iteration discount/update discipline as the
                    // river solver. In sampled mode unvisited (node, ctx)
                    // slices keep their stored sums — standard lazy-discount
                    // chance-sampled MCCFR.
                    let t = self.iteration;
                    let (sd, sw) = (
                        self.variant.strategy_discount(t),
                        self.variant.strategy_weight(t),
                    );
                    let variant = self.variant;
                    let reg = &mut self.regrets[node_id];
                    let ssum = &mut self.strat_sum[node_id];
                    #[allow(clippy::needless_range_loop)]
                    for c in 0..N {
                        for a in 0..na {
                            let i = base + a * N + c;
                            let discounted = reg[i] * variant.regret_discount(reg[i], t);
                            reg[i] =
                                variant.accumulate_regret(discounted, action_vals[a][c] - ev[c]);
                            ssum[i] = ssum[i] * sd + sw * reach[c] * strat[a * N + c];
                        }
                    }
                    ev
                } else {
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            no[c] *= strat[a * N + c];
                        }
                        let av = self.traverse(child, traverser, reach, &no, ctx);
                        for c in 0..N {
                            ev[c] += av[c];
                        }
                    }
                    ev
                }
            }
        }
    }

    fn chance_enumerate(
        &mut self,
        child: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let w = 1.0 / self.legal_rivers_per_deal();
        let n_pub = self.rivers.len();
        let mut ev = vec![0.0; N];
        for ctx in 0..n_pub {
            let card = self.rivers[ctx];
            let mut r = *reach;
            let mut o = *opp_reach;
            zero_card(&self.combos, card, &mut r);
            zero_card(&self.combos, card, &mut o);
            let v = self.traverse(child, traverser, &r, &o, Some(ctx));
            for c in 0..N {
                if !combo_blocks(self.combos[c], card) {
                    ev[c] += w * v[c];
                }
            }
        }
        ev
    }

    fn chance_sample(
        &mut self,
        child: usize,
        traverser: u8,
        reach: &[f64; N],
        opp_reach: &[f64; N],
    ) -> Vec<f64> {
        let n_pub = self.rivers.len();
        let ctx = self.rng.next_index(n_pub);
        let card = self.rivers[ctx];
        let scale = n_pub as f64 / self.legal_rivers_per_deal(); // 48/44
        let mut r = *reach;
        let mut o = *opp_reach;
        zero_card(&self.combos, card, &mut r);
        zero_card(&self.combos, card, &mut o);
        let v = self.traverse(child, traverser, &r, &o, Some(ctx));
        let mut ev = vec![0.0; N];
        for c in 0..N {
            if !combo_blocks(self.combos[c], card) {
                ev[c] = scale * v[c];
            }
        }
        ev
    }

    /// Current per-combo strategy at a (node, ctx): [action * N + combo].
    fn node_strategy(&self, node_id: usize, base: usize, na: usize) -> Vec<f64> {
        let reg = &self.regrets[node_id];
        let mut strat = vec![0.0; na * N];
        let mut r = vec![0.0; na];
        let mut s = vec![0.0; na];
        for c in 0..N {
            for a in 0..na {
                r[a] = reg[base + a * N + c];
            }
            regret_matching(&r, &mut s);
            for a in 0..na {
                strat[a * N + c] = s[a];
            }
        }
        strat
    }

    // ----- Introspection / outputs -------------------------------------

    pub fn action_node_ids(&self) -> Vec<usize> {
        (0..self.tree.nodes.len())
            .filter(|&i| matches!(self.tree.nodes[i].kind, NodeKind::Action { .. }))
            .collect()
    }

    pub fn actor_at(&self, node_id: usize) -> u8 {
        match self.tree.nodes[node_id].kind {
            NodeKind::Action { actor } => actor,
            _ => panic!("not an action node"),
        }
    }

    /// Range weight for exports: zero when the combo holds the context's
    /// river card (such infosets are unreachable and their tables junk).
    pub fn export_weight(&self, actor: usize, ctx: Option<usize>, combo: usize) -> f64 {
        if let Some(i) = ctx {
            if combo_blocks(self.combos[combo], self.rivers[i]) {
                return 0.0;
            }
        }
        self.ranges[actor].weights[combo]
    }

    /// Normalized average strategy for one combo at one (node, ctx).
    pub fn average_strategy(
        &self,
        node_id: usize,
        ctx: Option<usize>,
        combo: usize,
    ) -> Vec<f64> {
        let na = self.tree.nodes[node_id].children.len();
        let base = self.table_base(node_id, ctx, na);
        let ssum = &self.strat_sum[node_id];
        let total: f64 = (0..na).map(|a| ssum[base + a * N + combo]).sum();
        if total > 0.0 {
            (0..na)
                .map(|a| ssum[base + a * N + combo] / total)
                .collect()
        } else {
            vec![1.0 / na as f64; na]
        }
    }

    /// Range-weighted aggregate strategy at a (node, ctx) for display.
    pub fn aggregate_strategy(&self, node_id: usize, ctx: Option<usize>) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[node_id];
        let actor = self.actor_at(node_id) as usize;
        let na = node.children.len();
        let mut freq = vec![0.0; na];
        let mut total = 0.0;
        for c in 0..N {
            let w = self.export_weight(actor, ctx, c);
            if w == 0.0 {
                continue;
            }
            let s = self.average_strategy(node_id, ctx, c);
            for a in 0..na {
                freq[a] += w * s[a];
            }
            total += w;
        }
        if total > 0.0 {
            for f in &mut freq {
                *f /= total;
            }
        }
        node.children
            .iter()
            .zip(freq)
            .map(|((act, _), f)| (act.label(), f))
            .collect()
    }
}
```

`solver/mod.rs` — final form:

```rust
pub mod regret;
pub mod rng;
pub mod scalar;
pub mod showdown;
pub mod turn_river;
pub mod variant;
pub mod vector;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use showdown::{weighted_compat, ShowdownTable};
pub use turn_river::{ChanceMode, TurnRiverSolver};
pub use variant::CfrVariant;
pub use vector::{ExplReport, VectorRiverSolver};
```

Note: `ExplReport` import in `turn_river.rs` is unused until Task 7 — either
omit it now and add in Task 7, or add `#[allow(unused_imports)]` temporarily.
Prefer omitting.

- [ ] **Step 4: Run tests**

Run: `cargo test --release -p gto-hu --test test_turn_chance --test test_turn_river_solver`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/solver crates/gto-hu/tests/test_turn_chance.rs crates/gto-hu/tests/test_turn_river_solver.rs
git commit -m "feat(gto-hu): vector turn+river solver with exact river enumeration"
```

---

### Task 7: Exact best response, exploitability, game value

**Files:**
- Modify: `crates/gto-hu/src/solver/turn_river.rs`
- Test: append to `crates/gto-hu/tests/test_turn_river_solver.rs`

- [ ] **Step 1: Write the failing tests** (append):

```rust
#[test]
fn exploitability_is_finite_and_decreases() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Enumerate);
    s.run(10);
    let e1 = s.exploitability_bb();
    s.run(90);
    let e2 = s.exploitability_bb();
    eprintln!(
        "turn+river exploitability: {:.4} bb → {:.4} bb",
        e1.exploitability, e2.exploitability
    );
    assert!(e1.exploitability.is_finite() && e2.exploitability.is_finite());
    assert!(e1.exploitability >= -1e-9 && e2.exploitability >= -1e-9);
    assert!(
        e2.exploitability < e1.exploitability,
        "exploitability must fall: {:.4} → {:.4}",
        e1.exploitability,
        e2.exploitability
    );
}

#[test]
fn quads_never_fold_to_turn_jam() {
    use gto_hu::game::Action;
    use gto_hu::ranges::combo_index;
    // Board 7c7d2h2s: pocket 7h7s is quads and unbeatable on ANY river
    // (no 3-flush possible → no straight flush; 2222 is the only other
    // quads and loses). Folding to the turn jam is strictly dominated.
    let jam_cfg = TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::ToFactorOrJam(3.0),
            max_raises: 2,
        },
        river: StreetConfig {
            bet_pcts: vec![75],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    };
    let b = [c("7c"), c("7d"), c("2h"), c("2s")];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &jam_cfg);
    let ranges = [uniform_excluding(&b), uniform_excluding(&b)];
    let mut s = TurnRiverSolver::new(
        tree,
        b,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Enumerate,
    );
    // Path: OOP b50 → IP raise 3x → OOP jam → IP (hero) faces the jam.
    let bet = s.tree.nodes[0]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::Bet { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    let raise = s.tree.nodes[bet]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::Raise { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    let jam = s.tree.nodes[raise]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::AllIn { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    s.run(150);
    let quads = combo_index(c("7h"), c("7s"));
    let strat = s.average_strategy(jam, None, quads);
    eprintln!("quads fold freq vs turn jam = {}", strat[0]);
    assert!(strat[0] < 0.02, "quads folded to jam: {}", strat[0]);
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cargo test --release -p gto-hu --test test_turn_river_solver`
Expected: FAIL — `no method named 'exploitability_bb'`

- [ ] **Step 3: Implement** (append inside `impl TurnRiverSolver`; add
  `use super::vector::ExplReport;` to the imports):

```rust
    // ----- Exact best response ------------------------------------------
    // The chance node is ALWAYS enumerated here, regardless of training
    // mode: exploitability and game value are exact.

    /// Counterfactual BR values for `br_player` (opponent plays the
    /// average strategy).
    fn br_values(
        &self,
        node_id: usize,
        br_player: u8,
        opp_reach: &[f64; N],
        ctx: Option<usize>,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[br_player as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(br_player))[br_player as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => {
                let w = 1.0 / self.legal_rivers_per_deal();
                let mut ev = vec![0.0; N];
                for i in 0..self.rivers.len() {
                    let card = self.rivers[i];
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let v = self.br_values(child, br_player, &o, Some(i));
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                if actor == br_player {
                    let mut best = vec![f64::NEG_INFINITY; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.br_values(child, br_player, opp_reach, ctx);
                        for c in 0..N {
                            if v[c] > best[c] {
                                best[c] = v[c];
                            }
                        }
                    }
                    best
                } else {
                    let mut ev = vec![0.0; N];
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            let s = self.average_strategy(node_id, ctx, c);
                            no[c] = opp_reach[c] * s[a];
                        }
                        let v = self.br_values(child, br_player, &no, ctx);
                        for c in 0..N {
                            ev[c] += v[c];
                        }
                    }
                    ev
                }
            }
        }
    }

    /// Counterfactual values for `player` when BOTH players follow the
    /// average strategy (chance enumerated exactly).
    fn avg_values(
        &self,
        node_id: usize,
        player: u8,
        opp_reach: &[f64; N],
        ctx: Option<usize>,
    ) -> Vec<f64> {
        match self.tree.nodes[node_id].kind {
            NodeKind::FoldTerminal { winner } => {
                let state = self.tree.nodes[node_id].state;
                let pay = fold_payoffs(&state, winner)[player as usize] as f64 / 100.0;
                weighted_compat(&self.combos, opp_reach)
                    .iter()
                    .map(|w| pay * w)
                    .collect()
            }
            NodeKind::Showdown => {
                let state = self.tree.nodes[node_id].state;
                let win_bb =
                    showdown_payoffs(&state, Some(player))[player as usize] as f64 / 100.0;
                let table = &self.tables[ctx.expect("showdown requires a river card")];
                table
                    .diff(&self.combos, opp_reach)
                    .iter()
                    .map(|d| win_bb * d)
                    .collect()
            }
            NodeKind::Chance { child } => {
                let w = 1.0 / self.legal_rivers_per_deal();
                let mut ev = vec![0.0; N];
                for i in 0..self.rivers.len() {
                    let card = self.rivers[i];
                    let mut o = *opp_reach;
                    zero_card(&self.combos, card, &mut o);
                    let v = self.avg_values(child, player, &o, Some(i));
                    for c in 0..N {
                        if !combo_blocks(self.combos[c], card) {
                            ev[c] += w * v[c];
                        }
                    }
                }
                ev
            }
            NodeKind::Action { actor } => {
                let na = self.tree.nodes[node_id].children.len();
                let mut ev = vec![0.0; N];
                if actor == player {
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let v = self.avg_values(child, player, opp_reach, ctx);
                        for c in 0..N {
                            let s = self.average_strategy(node_id, ctx, c);
                            ev[c] += s[a] * v[c];
                        }
                    }
                } else {
                    for a in 0..na {
                        let child = self.tree.nodes[node_id].children[a].1;
                        let mut no = *opp_reach;
                        for c in 0..N {
                            let s = self.average_strategy(node_id, ctx, c);
                            no[c] = opp_reach[c] * s[a];
                        }
                        let v = self.avg_values(child, player, &no, ctx);
                        for c in 0..N {
                            ev[c] += v[c];
                        }
                    }
                }
                ev
            }
        }
    }

    /// Game value (bb/hand) to player 0 (SB/IP) under avg-vs-avg play.
    pub fn game_value_p0(&self) -> f64 {
        let r0 = self.ranges[0].weights;
        let r1 = self.ranges[1].weights;
        let vals = self.avg_values(0, 0, &r1, None);
        let compat = weighted_compat(&self.combos, &r1);
        let mut num = 0.0;
        let mut z = 0.0;
        for c in 0..N {
            if r0[c] > 0.0 {
                num += r0[c] * vals[c];
                z += r0[c] * compat[c];
            }
        }
        if z > 0.0 {
            num / z
        } else {
            0.0
        }
    }

    /// Exploitability in bb/hand: (BR_sb + BR_bb) / 2. Always exact
    /// (chance enumerated), even when training used sampling.
    pub fn exploitability_bb(&self) -> ExplReport {
        let mut br_value = [0.0f64; 2];
        #[allow(clippy::needless_range_loop)]
        for p in 0..2usize {
            let own = self.ranges[p].weights;
            let opp = self.ranges[1 - p].weights;
            let vals = self.br_values(0, p as u8, &opp, None);
            let compat = weighted_compat(&self.combos, &opp);
            let mut num = 0.0;
            let mut z = 0.0;
            for c in 0..N {
                if own[c] > 0.0 {
                    num += own[c] * vals[c];
                    z += own[c] * compat[c];
                }
            }
            br_value[p] = if z > 0.0 { num / z } else { 0.0 };
        }
        ExplReport {
            br_value,
            exploitability: (br_value[0] + br_value[1]) / 2.0,
        }
    }
```

- [ ] **Step 4: Run tests**

Run: `cargo test --release -p gto-hu --test test_turn_river_solver`
Expected: PASS (3 tests). Note the printed exploitability values; if the
`quads` test is slower than ~30 s, lower its iterations (the assertion holds
from ~50 iterations on — fold regret is negative from iteration 1).

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/solver/turn_river.rs crates/gto-hu/tests/test_turn_river_solver.rs
git commit -m "feat(gto-hu): exact best response and exploitability for turn+river"
```

---

### Task 8: `TinyTurnRiver` scalar game + differential test

**Files:**
- Create: `crates/gto-hu/src/games/tiny_turn_river.rs`
- Modify: `crates/gto-hu/src/games/mod.rs`
- Test: `crates/gto-hu/tests/test_turn_differential.rs`

- [ ] **Step 1: Create the scalar reference game**

```rust
use gto_core::eval::evaluate_best;

use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::solver::Game;
use crate::tree::{NodeKind, Tree};

/// The turn+river `Tree` played with small explicit hand lists and an
/// explicitly dealt river card — the scalar reference for differential-
/// testing the vector turn+river solver.
pub struct TinyTurnRiver {
    pub tree: Tree,
    pub turn_board: [u8; 4],
    /// hands[p] = player p's combos, all distinct from the board.
    /// Player indices match the tree (0 = SB/IP, 1 = BB/OOP).
    pub hands: [Vec<(u8, u8)>; 2],
}

#[derive(Debug, Clone)]
pub struct TinyTurnRiverState {
    /// (index into hands[0], index into hands[1]); usize::MAX = undealt.
    pub deal: (usize, usize),
    /// Dealt river card; None while still on the turn.
    pub river: Option<u8>,
    pub node: usize,
}

impl TinyTurnRiver {
    pub fn new(tree: Tree, turn_board: [u8; 4], hands: [Vec<(u8, u8)>; 2]) -> Self {
        for hs in &hands {
            for &(a, b) in hs {
                assert!(
                    a != b && !turn_board.contains(&a) && !turn_board.contains(&b),
                    "hand cards must be distinct and off-board"
                );
            }
        }
        TinyTurnRiver {
            tree,
            turn_board,
            hands,
        }
    }

    fn strength(&self, hand: (u8, u8), river: u8) -> u16 {
        let mut cards = [0u8; 7];
        cards[0] = hand.0;
        cards[1] = hand.1;
        cards[2..6].copy_from_slice(&self.turn_board);
        cards[6] = river;
        evaluate_best(&cards)
    }
}

impl Game for TinyTurnRiver {
    type State = TinyTurnRiverState;

    fn root(&self) -> TinyTurnRiverState {
        TinyTurnRiverState {
            deal: (usize::MAX, usize::MAX),
            river: None,
            node: 0,
        }
    }

    fn is_chance(&self, s: &TinyTurnRiverState) -> bool {
        s.deal.0 == usize::MAX
            || matches!(self.tree.nodes[s.node].kind, NodeKind::Chance { .. })
    }

    fn chance_outcomes(&self, s: &TinyTurnRiverState) -> Vec<(TinyTurnRiverState, f64)> {
        if s.deal.0 == usize::MAX {
            // Deal both hands: uniform over non-clashing pairs.
            let mut out = Vec::new();
            for (i, &(a0, b0)) in self.hands[0].iter().enumerate() {
                for (j, &(a1, b1)) in self.hands[1].iter().enumerate() {
                    let clash = a0 == a1 || a0 == b1 || b0 == a1 || b0 == b1;
                    if !clash {
                        out.push((
                            TinyTurnRiverState {
                                deal: (i, j),
                                river: None,
                                node: s.node,
                            },
                            0.0,
                        ));
                    }
                }
            }
            let p = 1.0 / out.len() as f64;
            for o in &mut out {
                o.1 = p;
            }
            out
        } else {
            // Deal the river: uniform over the 44 cards off the board and
            // off both players' hands.
            let NodeKind::Chance { child } = self.tree.nodes[s.node].kind else {
                unreachable!("chance_outcomes at a non-chance node");
            };
            let (a0, b0) = self.hands[0][s.deal.0];
            let (a1, b1) = self.hands[1][s.deal.1];
            let cards: Vec<u8> = (0..52u8)
                .filter(|c| {
                    !self.turn_board.contains(c)
                        && *c != a0
                        && *c != b0
                        && *c != a1
                        && *c != b1
                })
                .collect();
            let p = 1.0 / cards.len() as f64;
            cards
                .into_iter()
                .map(|card| {
                    (
                        TinyTurnRiverState {
                            deal: s.deal,
                            river: Some(card),
                            node: child,
                        },
                        p,
                    )
                })
                .collect()
        }
    }

    fn is_terminal(&self, s: &TinyTurnRiverState) -> bool {
        s.deal.0 != usize::MAX
            && matches!(
                self.tree.nodes[s.node].kind,
                NodeKind::FoldTerminal { .. } | NodeKind::Showdown
            )
    }

    fn payoff(&self, s: &TinyTurnRiverState, player: usize) -> f64 {
        let node = &self.tree.nodes[s.node];
        let cbb = match node.kind {
            NodeKind::FoldTerminal { winner } => fold_payoffs(&node.state, winner)[player],
            NodeKind::Showdown => {
                let river = s.river.expect("showdown requires a dealt river");
                let s0 = self.strength(self.hands[0][s.deal.0], river);
                let s1 = self.strength(self.hands[1][s.deal.1], river);
                let winner = match s0.cmp(&s1) {
                    std::cmp::Ordering::Greater => Some(0),
                    std::cmp::Ordering::Less => Some(1),
                    std::cmp::Ordering::Equal => None,
                };
                showdown_payoffs(&node.state, winner)[player]
            }
            _ => unreachable!("payoff at non-terminal"),
        };
        cbb as f64 / 100.0 // bb
    }

    fn player(&self, s: &TinyTurnRiverState) -> usize {
        match self.tree.nodes[s.node].kind {
            NodeKind::Action { actor } => actor as usize,
            _ => unreachable!("player() at non-action node"),
        }
    }

    fn num_actions(&self, s: &TinyTurnRiverState) -> usize {
        self.tree.nodes[s.node].children.len()
    }

    fn next(&self, s: &TinyTurnRiverState, action: usize) -> TinyTurnRiverState {
        TinyTurnRiverState {
            deal: s.deal,
            river: s.river,
            node: self.tree.nodes[s.node].children[action].1,
        }
    }

    fn infoset_key(&self, s: &TinyTurnRiverState) -> String {
        let p = self.player(s);
        let hand_idx = if p == 0 { s.deal.0 } else { s.deal.1 };
        // node id encodes the betting history; the river card is public.
        match s.river {
            Some(r) => format!("{p}|{hand_idx}|{}|{r}", s.node),
            None => format!("{p}|{hand_idx}|{}|-", s.node),
        }
    }
}
```

`games/mod.rs` — add:

```rust
pub mod tiny_turn_river;
pub use tiny_turn_river::{TinyTurnRiver, TinyTurnRiverState};
```

(match the existing file's structure: it declares `kuhn`, `leduc`,
`tiny_river` the same way)

- [ ] **Step 2: Write the differential test** (`tests/test_turn_differential.rs`)

```rust
//! Differential test: the scalar reference engine (explicit deals, explicit
//! 44-card river chance) and the vector turn+river engine (range masks,
//! 48-card public enumeration weighted 1/44) must converge to the same
//! equilibrium on identical tiny spots. This pins the chance weighting,
//! the river-card masking, and the all-streets value computation at once.

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::{TinyTurnRiver, TinyTurnRiverState};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{CfrVariant, ChanceMode, Game, ScalarCfr, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Minimal abstraction keeps the scalar side tractable.
fn tiny_cfg() -> TurnTreeConfig {
    TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    }
}

/// Game value to player 0 when both follow the scalar average strategy.
fn scalar_game_value_p0(
    game: &TinyTurnRiver,
    solver: &ScalarCfr<TinyTurnRiver>,
    state: &TinyTurnRiverState,
) -> f64 {
    if game.is_terminal(state) {
        return game.payoff(state, 0);
    }
    if game.is_chance(state) {
        return game
            .chance_outcomes(state)
            .iter()
            .map(|(child, prob)| prob * scalar_game_value_p0(game, solver, child))
            .sum();
    }
    let na = game.num_actions(state);
    let key = game.infoset_key(state);
    let strat = solver.average_strategy(&key, na);
    (0..na)
        .map(|a| strat[a] * scalar_game_value_p0(game, solver, &game.next(state, a)))
        .sum()
}

#[test]
fn scalar_and_vector_agree_on_tiny_turn_river_spot() {
    let board = [c("2c"), c("7d"), c("9h"), c("Jh")];
    // Player 0 = SB/IP; player 1 = BB/OOP. No card clashes between lists.
    let hands0 = vec![(c("Qc"), c("Tc")), (c("Ah"), c("Ad"))];
    let hands1 = vec![(c("Kh"), c("Qh")), (c("8s"), c("8d"))];
    let scalar_iters = 2_000;
    let vector_iters = 600;
    let variant = CfrVariant::cfr_plus_default();

    // --- Scalar reference ------------------------------------------------
    let tree_s = build_turn_river_tree(20 * BB, 90 * BB, &tiny_cfg());
    let game = TinyTurnRiver::new(tree_s, board, [hands0.clone(), hands1.clone()]);
    let mut scalar = ScalarCfr::new(&game, variant);
    scalar.run(scalar_iters);
    let scalar_expl = exploitability(&game, &scalar);

    // --- Vector engine, exact enumeration ---------------------------------
    let tree_v = build_turn_river_tree(20 * BB, 90 * BB, &tiny_cfg());
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    for &(a, b) in &hands0 {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    for &(a, b) in &hands1 {
        r1.weights[combo_index(a, b)] = 1.0;
    }
    let mut vector =
        TurnRiverSolver::new(tree_v, board, [r0, r1], variant, ChanceMode::Enumerate);
    vector.run(vector_iters);
    let vector_expl = vector.exploitability_bb();

    // --- 1. Both engines converge ----------------------------------------
    assert!(
        vector_expl.exploitability < 0.02,
        "vector exploitability {:.4}",
        vector_expl.exploitability
    );
    assert!(
        scalar_expl < 0.10,
        "scalar exploitability {scalar_expl:.4} — not converging"
    );

    // --- 2. Game-value invariant ------------------------------------------
    // Same equilibrium ⇒ game values agree within the exploitability budget.
    let v_scalar = scalar_game_value_p0(&game, &scalar, &game.root());
    let v_vector = vector.game_value_p0();
    let budget = scalar_expl + vector_expl.exploitability;
    eprintln!(
        "game values: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );
    assert!(
        (v_scalar - v_vector).abs() <= budget,
        "game values diverge: scalar {v_scalar:.4} vs vector {v_vector:.4} (budget {budget:.4})"
    );

    // --- 3. Turn-root strategy agreement (root is always on-path) ----------
    let na = vector.tree.nodes[0].children.len();
    for (hi, &(a, b)) in hands1.iter().enumerate() {
        let key = format!("1|{hi}|0|-");
        let ss = scalar.average_strategy(&key, na);
        let vs = vector.average_strategy(0, None, combo_index(a, b));
        for ai in 0..na {
            assert!(
                (ss[ai] - vs[ai]).abs() < 0.06,
                "root hand {hi} action {ai}: scalar {:.4} vs vector {:.4}",
                ss[ai],
                vs[ai]
            );
        }
    }

    eprintln!(
        "turn+river differential OK: scalar expl {scalar_expl:.5}, vector expl {:.5}",
        vector_expl.exploitability
    );
}
```

- [ ] **Step 3: Run it**

Run: `cargo test --release -p gto-hu --test test_turn_differential -- --nocapture`
Expected: PASS. **Calibration note:** thresholds (0.10 scalar / 0.02 vector /
0.06 strategy) are estimates pending the first real run. If the scalar side
hasn't converged enough at 2 000 iterations (check the printed expl), raise
scalar iterations before loosening any threshold. Runtime budget: tens of
seconds in release; if it exceeds ~90 s, reduce scalar iterations and relax
`scalar_expl < 0.10` accordingly — never weaken assertion 2 (game-value
within budget), it is the core invariant and self-scales.

- [ ] **Step 4: Run the full crate suite** (the new `games` export must not
  break anything): `cargo test --release -p gto-hu`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/games crates/gto-hu/tests/test_turn_differential.rs
git commit -m "test(gto-hu): TinyTurnRiver scalar reference and turn+river differential"
```

---

### Task 9: Public chance sampling tests

(The sampling implementation already landed in Task 6; this task pins its
behavior.)

**Files:**
- Test: append to `crates/gto-hu/tests/test_turn_river_solver.rs`

- [ ] **Step 1: Write the tests**

```rust
#[test]
fn sampled_mode_is_deterministic_per_seed() {
    let run = |seed: u64| {
        let mut s = solver(&reduced_cfg(), ChanceMode::Sample { seed });
        s.run(200);
        let e = s.exploitability_bb().exploitability;
        let root: Vec<f64> = s
            .aggregate_strategy(0, None)
            .into_iter()
            .map(|(_, f)| f)
            .collect();
        (e, root)
    };
    let (e1, r1) = run(7);
    let (e2, r2) = run(7);
    let (e3, r3) = run(8);
    // Same seed ⇒ bit-identical training run.
    assert_eq!(e1, e2, "same seed must reproduce exploitability exactly");
    assert_eq!(r1, r2, "same seed must reproduce the root strategy exactly");
    // Different seed ⇒ different sampled card sequence ⇒ different tables.
    assert!(
        e1 != e3 || r1 != r3,
        "seed appears to be ignored (identical run for different seeds)"
    );
}

#[test]
fn sampled_mode_converges_toward_equilibrium() {
    let mut s = solver(&reduced_cfg(), ChanceMode::Sample { seed: 42 });
    s.run(3_000);
    let e = s.exploitability_bb();
    eprintln!("sampled 3000 iters: expl {:.4} bb", e.exploitability);
    assert!(e.exploitability.is_finite());
    assert!(e.exploitability >= -1e-9);
    assert!(
        e.exploitability < 0.15,
        "sampled training failed to converge: {:.4} bb",
        e.exploitability
    );
}
```

- [ ] **Step 2: Run**

Run: `cargo test --release -p gto-hu --test test_turn_river_solver -- --nocapture`
Expected: PASS. Calibrate the 0.15 bound from the printed value (leave ≥3×
headroom above the observed exploitability so seed changes can't flake it).

- [ ] **Step 3: Commit**

```bash
git add crates/gto-hu/tests/test_turn_river_solver.rs
git commit -m "test(gto-hu): seeded determinism and convergence of public chance sampling"
```

---

### Task 10: Reports — turn CSV/JSON exports

**Files:**
- Modify: `crates/gto-hu/src/reports/mod.rs`
- Create: `crates/gto-hu/src/reports/turn.rs`
- Test: `crates/gto-hu/tests/test_turn_reports.rs`

- [ ] **Step 1: Write the failing test**

```rust
use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    tree_stats, write_river_aggregate_csv, write_turn_strategy_csv, write_turn_summary_json,
    TurnSolverStats,
};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, RaiseRule, StreetConfig, TurnTreeConfig};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

#[test]
fn turn_reports_written_with_finite_exploitability() {
    let cfg = TurnTreeConfig {
        turn: StreetConfig {
            bet_pcts: vec![50],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    };
    let board = [c("2c"), c("7d"), c("9h"), c("Jh")];
    let tree = build_turn_river_tree(20 * BB, 90 * BB, &cfg);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let mut s = TurnRiverSolver::new(
        tree,
        board,
        ranges,
        CfrVariant::cfr_plus_default(),
        ChanceMode::Sample { seed: 1 },
    );
    s.run(50);

    let dir = std::env::temp_dir().join(format!("gto_hu_turn_reports_{}", std::process::id()));
    std::fs::create_dir_all(&dir).unwrap();

    let expl = s.exploitability_bb();
    let stats = TurnSolverStats {
        iterations: 50,
        elapsed_secs: 0.0,
        mode: "sample".into(),
        expl,
        game_value_bb: s.game_value_p0(),
        root_strategy: s.aggregate_strategy(0, None),
    };
    let ts = tree_stats(&s.tree);
    write_turn_summary_json(&dir.join("summary.json"), &board, &stats, &ts, s.table_bytes())
        .unwrap();
    write_turn_strategy_csv(&dir.join("strategy_turn.csv"), &s).unwrap();
    write_river_aggregate_csv(&dir.join("strategy_river_agg.csv"), &s).unwrap();

    // Deliverable: summary JSON with a finite exploitability in bb/hand.
    let json = std::fs::read_to_string(dir.join("summary.json")).unwrap();
    let expl_field = json
        .split("\"exploitability_bb\":")
        .nth(1)
        .expect("exploitability_bb field present")
        .split(',')
        .next()
        .unwrap()
        .trim()
        .parse::<f64>()
        .unwrap();
    assert!(expl_field.is_finite() && expl_field >= -1e-9);
    assert!(json.contains("\"chance_nodes\":"));
    assert!(json.contains("\"game_value_sb_bb\":"));
    assert!(json.contains("\"mode\":\"sample\""));

    let csv = std::fs::read_to_string(dir.join("strategy_turn.csv")).unwrap();
    assert!(csv.starts_with("node_id,actor,combo,action,freq"));
    assert!(csv.lines().count() > 1, "turn strategy CSV has rows");

    let rcsv = std::fs::read_to_string(dir.join("strategy_river_agg.csv")).unwrap();
    assert!(rcsv.starts_with("node_id,river,actor,action,freq"));
    assert!(rcsv.lines().count() > 1, "river aggregate CSV has rows");

    std::fs::remove_dir_all(&dir).ok();
}
```

- [ ] **Step 2: Run to verify failure**

Run: `cargo test --release -p gto-hu --test test_turn_reports`
Expected: FAIL — unresolved imports

- [ ] **Step 3: Implement.**

`reports/mod.rs` — top of file: declare the submodule and widen `card_str`:

```rust
pub mod turn;

pub use turn::{
    write_river_aggregate_csv, write_turn_strategy_csv, write_turn_summary_json, TurnSolverStats,
};
```

```rust
pub(crate) fn card_str(c: u8) -> String {
```

`reports/turn.rs`:

```rust
//! Turn+river solver exports (CSV + minimal JSON, no external deps).
//!
//! `strategy_turn.csv` is per-combo (turn-street nodes only). The river
//! side would be ~6M rows per-combo, so `strategy_river_agg.csv` exports
//! range-aggregate frequencies per (node, river card) instead; per-combo
//! river strategies remain available via `TurnRiverSolver::average_strategy`.

use std::fmt::Write as _;
use std::fs;
use std::path::Path;

use super::{card_str, TreeStats};
use crate::game::Street;
use crate::ranges::all_combos;
use crate::solver::{ExplReport, TurnRiverSolver};

#[derive(Debug, Clone)]
pub struct TurnSolverStats {
    pub iterations: u32,
    pub elapsed_secs: f64,
    /// "enumerate" or "sample(seed=N)".
    pub mode: String,
    pub expl: ExplReport,
    /// Avg-vs-avg game value to player 0 (SB/IP), bb/hand.
    pub game_value_bb: f64,
    pub root_strategy: Vec<(String, f64)>,
}

/// Per-combo average strategy for turn-street action nodes.
pub fn write_turn_strategy_csv(path: &Path, solver: &TurnRiverSolver) -> std::io::Result<()> {
    let combos = all_combos();
    let mut out = String::from("node_id,actor,combo,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::Turn {
            continue;
        }
        let actor = solver.actor_at(node_id);
        let node = &solver.tree.nodes[node_id];
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.export_weight(actor as usize, None, c) == 0.0 {
                continue;
            }
            let strat = solver.average_strategy(node_id, None, c);
            for (a, (act, _)) in node.children.iter().enumerate() {
                if strat[a] > 0.001 {
                    let _ = writeln!(
                        out,
                        "{node_id},{actor},{}{},{},{:.4}",
                        card_str(ca),
                        card_str(cb),
                        act.label(),
                        strat[a]
                    );
                }
            }
        }
    }
    fs::write(path, out)
}

/// Range-aggregate river strategy per (node, river card).
pub fn write_river_aggregate_csv(path: &Path, solver: &TurnRiverSolver) -> std::io::Result<()> {
    let mut out = String::from("node_id,river,actor,action,freq\n");
    for node_id in solver.action_node_ids() {
        if solver.tree.nodes[node_id].state.street != Street::River {
            continue;
        }
        let actor = solver.actor_at(node_id);
        for (i, &card) in solver.rivers().iter().enumerate() {
            for (act, f) in solver.aggregate_strategy(node_id, Some(i)) {
                let _ = writeln!(out, "{node_id},{},{actor},{act},{f:.4}", card_str(card));
            }
        }
    }
    fs::write(path, out)
}

/// Minimal flat JSON summary (no external deps).
pub fn write_turn_summary_json(
    path: &Path,
    board: &[u8; 4],
    stats: &TurnSolverStats,
    ts: &TreeStats,
    table_bytes: usize,
) -> std::io::Result<()> {
    let board_s: String = board.iter().map(|&c| card_str(c)).collect();
    let root: String = stats
        .root_strategy
        .iter()
        .map(|(a, f)| format!("{{\"action\":\"{a}\",\"freq\":{f:.5}}}"))
        .collect::<Vec<_>>()
        .join(",");
    let json = format!(
        concat!(
            "{{\"solver\":\"gto-hu vector turn+river (abstract HU NLHE equilibrium solver)\",",
            "\"board\":\"{}\",\"mode\":\"{}\",\"iterations\":{},\"elapsed_secs\":{:.2},",
            "\"exploitability_bb\":{:.6},\"br_sb_bb\":{:.6},\"br_bb_bb\":{:.6},",
            "\"game_value_sb_bb\":{:.6},",
            "\"tree\":{{\"nodes\":{},\"action_nodes\":{},\"chance_nodes\":{},",
            "\"fold_terminals\":{},\"showdowns\":{},\"table_bytes\":{}}},",
            "\"turn_root_strategy\":[{}]}}\n"
        ),
        board_s,
        stats.mode,
        stats.iterations,
        stats.elapsed_secs,
        stats.expl.exploitability,
        stats.expl.br_value[0],
        stats.expl.br_value[1],
        stats.game_value_bb,
        ts.total_nodes,
        ts.action_nodes,
        ts.chance_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        table_bytes,
        root,
    );
    fs::write(path, json)
}
```

- [ ] **Step 4: Run tests**

Run: `cargo test --release -p gto-hu --test test_turn_reports --test test_reports`
Expected: PASS (new + existing river report test)

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/reports crates/gto-hu/tests/test_turn_reports.rs
git commit -m "feat(gto-hu): turn+river strategy/summary exports with chance stats"
```

---

### Task 11: CLI `solve-hu-turn-river`

**Files:**
- Create: `crates/gto-hu/src/bin/solve_turn_river.rs`
- Modify: `crates/gto-hu/Cargo.toml`

- [ ] **Step 1: Add the bin entry** (`Cargo.toml`):

```toml
[[bin]]
name = "solve-hu-turn-river"
path = "src/bin/solve_turn_river.rs"
```

- [ ] **Step 2: Implement the CLI**

```rust
//! solve-hu-turn-river — exact-combo HU turn+river solver (abstract action
//! set, river dealt as a public chance node).
//!
//! Example:
//!   solve-hu-turn-river --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
//!
//! Default training mode is public chance sampling (seeded, reproducible);
//! pass `--mode enumerate` for exact-but-slow training. The reported
//! exploitability is always exact (enumerated best response).

use std::path::PathBuf;
use std::process::exit;
use std::time::Instant;

use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::ranges::uniform_excluding;
use gto_hu::reports::{
    tree_stats, write_river_aggregate_csv, write_turn_strategy_csv, write_turn_summary_json,
    TurnSolverStats,
};
use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
use gto_hu::tree::{build_turn_river_tree, TurnTreeConfig};

fn usage() -> ! {
    eprintln!(
        "usage: solve-hu-turn-river --board AhKd7s2c --pot <bb> --stack <bb> \
         [--iterations N=10000] [--variant cfr+|dcfr] \
         [--mode sample|enumerate] [--seed N=42] [--out DIR]"
    );
    exit(2);
}

fn parse_board(s: &str) -> Result<[u8; 4], String> {
    if s.len() != 8 {
        return Err(format!("board must be 8 chars (4 cards), got '{s}'"));
    }
    let mut board = [0u8; 4];
    for i in 0..4 {
        let cs = &s[i * 2..i * 2 + 2];
        board[i] = parse_card(cs).ok_or_else(|| format!("bad card '{cs}'"))?;
    }
    let mut seen = [false; 52];
    for &card in &board {
        if seen[card as usize] {
            return Err(format!("duplicate card in board '{s}'"));
        }
        seen[card as usize] = true;
    }
    Ok(board)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut board: Option<[u8; 4]> = None;
    let mut pot_bb: Option<f64> = None;
    let mut stack_bb: Option<f64> = None;
    let mut iterations: u32 = 10_000;
    let mut variant = CfrVariant::cfr_plus_default();
    let mut sample = true;
    let mut seed: u64 = 42;
    let mut out_dir: Option<PathBuf> = None;
    let mut board_raw = String::new();

    let mut i = 0;
    while i < args.len() {
        let need = |i: usize| args.get(i + 1).cloned().unwrap_or_else(|| usage());
        match args[i].as_str() {
            "--board" => {
                board_raw = need(i);
                board = Some(parse_board(&board_raw).unwrap_or_else(|e| {
                    eprintln!("error: {e}");
                    exit(2);
                }));
                i += 2;
            }
            "--pot" => {
                pot_bb = need(i).parse().ok();
                i += 2;
            }
            "--stack" => {
                stack_bb = need(i).parse().ok();
                i += 2;
            }
            "--iterations" => {
                iterations = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--variant" => {
                variant = match need(i).as_str() {
                    "cfr+" => CfrVariant::cfr_plus_default(),
                    "dcfr" => CfrVariant::dcfr_default(),
                    v => {
                        eprintln!("unknown variant '{v}'");
                        exit(2);
                    }
                };
                i += 2;
            }
            "--mode" => {
                sample = match need(i).as_str() {
                    "sample" => true,
                    "enumerate" => false,
                    m => {
                        eprintln!("unknown mode '{m}' (sample|enumerate)");
                        exit(2);
                    }
                };
                i += 2;
            }
            "--seed" => {
                seed = need(i).parse().unwrap_or_else(|_| usage());
                i += 2;
            }
            "--out" => {
                out_dir = Some(PathBuf::from(need(i)));
                i += 2;
            }
            _ => usage(),
        }
    }
    let (Some(board), Some(pot_bb), Some(stack_bb)) = (board, pot_bb, stack_bb) else {
        usage()
    };
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        eprintln!("error: pot must be positive and split evenly; stack must be positive");
        exit(2);
    }

    let mode = if sample {
        ChanceMode::Sample { seed }
    } else {
        ChanceMode::Enumerate
    };
    let mode_label = if sample {
        format!("sample(seed={seed})")
    } else {
        "enumerate".to_string()
    };

    let tree = build_turn_river_tree(pot, stack, &TurnTreeConfig::srp());
    let ts = tree_stats(&tree);
    let ranges = [uniform_excluding(&board), uniform_excluding(&board)];
    let solver_start = Instant::now();
    let mut solver = TurnRiverSolver::new(tree, board, ranges, variant, mode);
    eprintln!(
        "tree: {} nodes ({} action, {} chance, {} fold, {} showdown), {:.1} MB tables ({:.1}s setup)",
        ts.total_nodes,
        ts.action_nodes,
        ts.chance_nodes,
        ts.fold_terminals,
        ts.showdown_terminals,
        solver.table_bytes() as f64 / 1e6,
        solver_start.elapsed().as_secs_f64()
    );

    let start = Instant::now();
    let chunk = (iterations / 10).max(1);
    let mut done = 0;
    while done < iterations {
        let n = chunk.min(iterations - done);
        solver.run(n);
        done += n;
        eprintln!(
            "iter {done}/{iterations}  elapsed {:.1}s",
            start.elapsed().as_secs_f64()
        );
    }
    let elapsed = start.elapsed().as_secs_f64();
    eprintln!("computing exact best response…");
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();

    let root = solver.aggregate_strategy(0, None);
    println!("\n== solve-hu-turn-river (abstract HU NLHE equilibrium solver) ==");
    println!(
        "board {board_raw}  pot {pot_bb}bb  stack {stack_bb}bb  iters {iterations}  mode {mode_label}"
    );
    println!(
        "exploitability: {:.4} bb/hand (BR sb {:.4}, BR bb {:.4})",
        expl.exploitability, expl.br_value[0], expl.br_value[1]
    );
    println!("game value (SB/IP, avg vs avg): {game_value:.4} bb/hand");
    println!("OOP (BB) turn root strategy:");
    for (action, freq) in &root {
        println!("  {action:<14} {:>6.2}%", freq * 100.0);
    }

    let out = out_dir.unwrap_or_else(|| {
        PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into()))
            .join("projects/_data/gto/hu")
            .join(format!("turnriver_{board_raw}"))
    });
    std::fs::create_dir_all(&out).expect("create out dir");
    let stats = TurnSolverStats {
        iterations,
        elapsed_secs: elapsed,
        mode: mode_label,
        expl,
        game_value_bb: game_value,
        root_strategy: root,
    };
    write_turn_strategy_csv(&out.join("strategy_turn.csv"), &solver).expect("write turn csv");
    write_river_aggregate_csv(&out.join("strategy_river_agg.csv"), &solver)
        .expect("write river csv");
    write_turn_summary_json(&out.join("summary.json"), &board, &stats, &ts, solver.table_bytes())
        .expect("write json");
    eprintln!("wrote {}", out.display());
}
```

- [ ] **Step 3: Build** — `cargo build --release -p gto-hu`
Expected: compiles, two binaries.

- [ ] **Step 4: Run the real entry point (Definition of Done: observe real output)**

```bash
cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
  --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
```

Expected output shape (numbers will differ):

```
tree: ~900 nodes (… action, 13 chance, … fold, … showdown), ~300 MB tables (…s setup)
iter 1000/10000  elapsed …s
…
exploitability: 0.0XXX bb/hand (BR sb …, BR bb …)
game value (SB/IP, avg vs avg): 0.XXXX bb/hand
OOP (BB) turn root strategy:
  check          XX.XX%
  bet 10.0bb     XX.XX%
  bet 20.0bb     XX.XX%
wrote /home/kazumasa/projects/_data/gto/hu/turnriver_AhKd7s2c
```

Verify and record in the final report:
1. exploitability is finite, ≥ 0, and small (sampled 10k iterations — expect
   well under 1 bb; if it is not, STOP and debug before proceeding);
2. `summary.json`, `strategy_turn.csv`, `strategy_river_agg.csv` exist in
   `~/projects/_data/gto/hu/turnriver_AhKd7s2c/` and the JSON parses
   (`python3 -c "import json;print(json.load(open('…/summary.json'))['exploitability_bb'])"`);
3. total wall time (sampled 10k expected within a few minutes; if far slower,
   note it — do **not** GPU/parallel-optimize, out of scope).
4. spot-check sanity: on AhKd7s2c, river-aggregate rows for an A river vs a
   2 river should differ (board-texture sensitivity).

- [ ] **Step 5: Commit**

```bash
git add crates/gto-hu/src/bin/solve_turn_river.rs crates/gto-hu/Cargo.toml
git commit -m "feat(gto-hu): solve-hu-turn-river CLI with sampling and exact exploitability"
```

---

### Task 12: Docs + final verification

**Files:**
- Modify: `crates/gto-hu/README.md`
- Modify: `gto/PROGRESS.md`
- Modify: `gto/CLAUDE.md` (HU solver row)

- [ ] **Step 1: Update `crates/gto-hu/README.md`** — change scope line and add
  the new CLI; replace the "Current scope" paragraph and Usage with:

```markdown
Current scope (Phase 3): exact-combo river solver + turn+river solver with
the river dealt as a public chance node (exact enumeration or seeded public
chance sampling).

- Game: HU NLHE cash, configurable pot/stack. SRP turn action set
  (check / bet 50% / bet 100%; vs bet: fold / call / raise 3x-or-jam) and
  SRP river action set (check / bet 75% / bet 150% / all-in; vs bet:
  fold / call / raise-jam). All-in on the turn runs out the river as
  chance straight to showdown.
- Solver: CFR+ (default) or DCFR, per-combo vector traversal,
  blocker-exact showdowns; chance weight 1/44 per deal (sampling is
  importance-corrected and unbiased). Exploitability is always computed
  by exact enumeration.
- Validation: Kuhn & Leduc on the same engine family, exact best
  response, scalar-vs-vector differential tests on both the river and
  turn+river games.

## Usage

```bash
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000

cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
  --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
```

Outputs land under `~/projects/_data/gto/hu/`: aggregate strategy tables,
exploitability in bb/hand, `strategy*.csv` / `summary.json`.

## Roadmap

Flop trees (two chance streets) → preflop with limp → full blueprint.
See `gto/docs/superpowers/specs/2026-06-06-hu-abstract-solver-design.md`.
```

- [ ] **Step 2: Update `gto/PROGRESS.md`** — in the Phase HU section, check off
  the roadmap item and append a line:

```markdown
- [x] Turn+River（public chance sampling）— `solve-hu-turn-river` CLI、
      チャンス重み 1/44 厳密・サンプリングは 48/44 補正で不偏、
      オールイン後はチャンス→即ショーダウン、TinyTurnRiver 差分テストで検証
```

(and in the `### Phase HU 続き` TODO list, remove the now-done
`- [ ] Turn+River（public chance sampling）` line)

- [ ] **Step 3: Update `gto/CLAUDE.md`** — HU solver row in the architecture
  table: append `, solve-hu-turn-river` to the CLI mention.

- [ ] **Step 4: Full verification (Definition of Done)**

```bash
cd ~/projects/gto && source ~/.cargo/env
cargo fmt --all --manifest-path Cargo.toml
cargo test --release -p gto-hu            # full crate: old 56 + new ≈ 20
cargo test --release -p gto-core          # untouched but confirm
cargo clippy --release -p gto-hu 2>&1 | tail -20   # warnings: fix trivial ones
```

Expected: all tests pass. Quote 1–3 lines of the test summary output in the
final report. Re-run the CLI example once after `cargo fmt` to confirm the
binary still works.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "docs(gto-hu): document turn+river solver; update progress"
```

---

## Spec coverage self-review

| Requirement | Where |
|---|---|
| Fixed 4-card turn board | Task 6 (`TurnRiverSolver::new` asserts), Task 11 CLI `parse_board` |
| River as public chance node | Task 3 (`NodeKind::Chance`), Task 6 traversal |
| Enumerate or sample all legal river cards | Task 6 `chance_enumerate` / `chance_sample` |
| No duplicate cards vs combos/board | Task 6 masks + `zero_card`; Task 3 builder; tests in Tasks 3, 6 |
| Exact enumeration for tests | `ChanceMode::Enumerate`, used in all correctness tests |
| Public chance sampling for larger runs | `ChanceMode::Sample`, CLI default, Task 9 tests |
| Reuse river action tree + terminal payoffs | Task 3 (`expand_street` reuse), payoffs unchanged |
| Exact pot/stack accounting | Task 1 `advance_street`, Task 3 chip-conservation test |
| All-in on turn → chance → showdown, no betting | Task 3 builder + test |
| CFR+/DCFR via existing framework | Task 6 (same `CfrVariant` discipline as river solver) |
| Export avg strategy, EV, tree/solver stats, exploitability | Task 10 reports, Task 11 CLI |
| CLI `solve-hu-turn-river --board AhKd7s2c --pot 20 --stack 90 --iterations 10000` | Task 11 (exact invocation verified) |
| Test: legal river generation | Task 6 `rivers_exclude_board_unique_and_complete` |
| Test: chance probability sums to 1 | Task 6 `chance_weights_sum_to_one_per_deal` |
| Test: no duplicate board/private cards | Tasks 3, 6 (`river_card_blocked_combos_are_masked`) |
| Test: all-in turn runout to showdown | Task 3 `allin_turn_runout_goes_to_showdown_with_no_betting` |
| Test: turn bet/call proceeds to river | Task 3 `turn_bet_call_proceeds_to_river_betting` |
| Test: turn bet/fold terminal payoff | Task 3 `turn_bet_fold_terminal_payoff_exact` |
| Test: exact enumeration vs tiny manual game | Task 8 differential |
| Test: sampled deterministic with seed | Task 9 |
| Test: exploitability exists and finite | Tasks 7, 9, 10 |
| Hard: no turn-call→showdown shortcut | Task 3 builder + test |
| Hard: no legacy gto-core/gto-cuda flop solver | nothing imports them beyond `eval`/`range` |
| Hard: no flop/preflop work | out of scope everywhere |
| Hard: no GPU optimization | pure CPU; CLI prints cost only |
| Summary JSON with exploitability bb/hand | Task 10 `write_turn_summary_json` + Task 10 test |
