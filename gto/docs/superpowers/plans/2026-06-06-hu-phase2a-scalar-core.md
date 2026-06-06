# HU Solver Phase 2a: gto-hu Crate, Game Core & Scalar CFR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `gto-hu` crate with exact chip accounting, the river action tree, and a scalar CFR engine (Vanilla/CFR+/DCFR) validated on Kuhn and Leduc poker with exact best response.

**Architecture:** New workspace crate `crates/gto-hu` depending on `gto-core` (evaluator/combos only). Betting is a pure-state-transition module in centi-bb i64; the tree is a node arena built from a declarative `StreetConfig`; the scalar engine works on any `Game` trait impl (Kuhn, Leduc; tiny river follows in Phase 2b). Payoff convention: `payoff(p) = chips_won(p) − contrib(p)`, reported in bb (f64).

**Tech Stack:** Rust 2021, no new external dependencies. `cargo test -p gto-hu`.

**Prerequisite:** Phase 1 plan completed (needs `gto_core::eval::evaluate_best`).

---

### Task 1: Crate scaffold

**Files:**
- Modify: `gto/Cargo.toml` (workspace members)
- Create: `gto/crates/gto-hu/Cargo.toml`
- Create: `gto/crates/gto-hu/src/lib.rs`

- [ ] **Step 1: Add workspace member**

`gto/Cargo.toml` members list becomes:

```toml
[workspace]
members = [
    "crates/gto-core",
    "crates/gto-py",
    "crates/gto-cuda",
    "crates/gto-hu",
]
resolver = "2"
```

- [ ] **Step 2: Create `gto/crates/gto-hu/Cargo.toml`**

```toml
[package]
name = "gto-hu"
version = "0.1.0"
edition = "2021"
description = "Abstract HU NLHE equilibrium solver (not an unabstracted full GTO solver)"

[dependencies]
gto-core = { path = "../gto-core" }

[[bin]]
name = "solve-hu-river"
path = "src/bin/solve_river.rs"
```

- [ ] **Step 3: Create `gto/crates/gto-hu/src/lib.rs`**

```rust
//! # gto-hu — Abstract HU NLHE equilibrium solver
//!
//! **This is an abstract HU NLHE equilibrium solver, not an unabstracted
//! full GTO solver.** Fixed action abstraction, explicit card abstraction
//! levels, exploitability is always reported alongside strategies.

pub mod game;
pub mod ranges;
pub mod tree;
pub mod solver;
pub mod games;
pub mod validation;
pub mod reports;
```

Submodule files come in later tasks; to keep this compiling now, create
empty placeholder module files:

```bash
cd ~/projects/gto/crates/gto-hu/src
mkdir -p game ranges tree solver games validation reports bin
for m in game ranges tree solver games validation reports; do
  echo "" > $m/mod.rs
done
cat > bin/solve_river.rs <<'EOF'
fn main() {
    eprintln!("solve-hu-river: implemented in Phase 2b");
    std::process::exit(2);
}
EOF
```

- [ ] **Step 4: Verify build**

Run: `cd ~/projects/gto && cargo build -p gto-hu`
Expected: clean build.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/Cargo.toml gto/crates/gto-hu
git commit -m "chore(gto-hu): scaffold abstract HU NLHE solver crate"
```

---

### Task 2: Streets, actions, pot types

**Files:**
- Create: `gto/crates/gto-hu/src/game/street.rs`
- Create: `gto/crates/gto-hu/src/game/action.rs`
- Create: `gto/crates/gto-hu/src/game/pot_type.rs`
- Modify: `gto/crates/gto-hu/src/game/mod.rs`

- [ ] **Step 1: Write the code** (plain data types; tests arrive with betting)

`src/game/street.rs`:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Street {
    Preflop,
    Flop,
    Turn,
    River,
}

impl Street {
    pub fn next(self) -> Option<Street> {
        match self {
            Street::Preflop => Some(Street::Flop),
            Street::Flop => Some(Street::Turn),
            Street::Turn => Some(Street::River),
            Street::River => None,
        }
    }

    /// Number of board cards visible on this street.
    pub fn board_len(self) -> usize {
        match self {
            Street::Preflop => 0,
            Street::Flop => 3,
            Street::Turn => 4,
            Street::River => 5,
        }
    }
}
```

`src/game/action.rs`:

```rust
/// Betting actions. All sizes are **committed totals for the current
/// street** (spec requirement), never increments.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Action {
    Fold,
    Check,
    Call,
    /// Open bet to a total of `to` centi-bb on this street.
    Bet { to: i64 },
    /// Raise to a total of `to` centi-bb on this street.
    Raise { to: i64 },
    /// Commit the entire remaining stack (total = `to`).
    AllIn { to: i64 },
}

impl Action {
    /// Human-readable label with bb amounts (e.g. "bet 15.0bb").
    pub fn label(&self) -> String {
        let bb = |v: i64| format!("{:.1}bb", v as f64 / 100.0);
        match self {
            Action::Fold => "fold".into(),
            Action::Check => "check".into(),
            Action::Call => "call".into(),
            Action::Bet { to } => format!("bet {}", bb(*to)),
            Action::Raise { to } => format!("raise {}", bb(*to)),
            Action::AllIn { to } => format!("allin {}", bb(*to)),
        }
    }
}
```

`src/game/pot_type.rs`:

```rust
/// Postflop pot category, set by the preflop line (Phase 5).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PotType {
    Limped,
    Srp,
    ThreeBet,
    FourBet,
    AllInPreflop,
}
```

`src/game/mod.rs`:

```rust
pub mod action;
pub mod betting;
pub mod pot_type;
pub mod street;
pub mod terminal;

pub use action::Action;
pub use betting::{BettingState, BB, PLAYER_BB, PLAYER_SB};
pub use pot_type::PotType;
pub use street::Street;
```

(`betting.rs` / `terminal.rs` come in Tasks 3-4; create them as empty files
now so the module compiles: `echo "" > src/game/betting.rs` etc. — or do
Tasks 2-4 as one commit; the commit point below assumes Tasks 2-4 together.)

---

### Task 3: BettingState — exact chip accounting

**Files:**
- Create: `gto/crates/gto-hu/src/game/betting.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_betting.rs`:

```rust
use gto_hu::game::{Action, BettingState, BB, PLAYER_BB, PLAYER_SB};

#[test]
fn river_root_state_is_exact() {
    let s = BettingState::river_root(20 * BB, 90 * BB);
    assert_eq!(s.to_act, PLAYER_BB, "OOP (BB) acts first postflop");
    assert_eq!(s.pot(), 20 * BB);
    assert_eq!(s.contrib, [10 * BB, 10 * BB]);
    assert_eq!(s.stacks, [90 * BB, 90 * BB]);
    assert!(!s.facing_bet());
}

#[test]
fn bet_call_conserves_chips() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let total0 = s0.pot() + s0.stacks[0] + s0.stacks[1];
    let s1 = s0.apply(Action::Bet { to: 15 * BB }); // BB bets 15bb (75% pot)
    let s2 = s1.apply(Action::Call);
    let total2 = s2.pot() + s2.stacks[0] + s2.stacks[1];
    assert_eq!(total0, total2, "chips must be conserved");
    assert_eq!(s2.pot(), 50 * BB);
    assert_eq!(s2.street_committed, [15 * BB, 15 * BB]);
    assert_eq!(s2.stacks, [75 * BB, 75 * BB]);
}

#[test]
fn call_is_capped_by_stack() {
    // Short stack: pot 20, stacks 10. BB jams 10bb total, SB calls all-in.
    let s0 = BettingState::river_root(20 * BB, 10 * BB);
    let s1 = s0.apply(Action::AllIn { to: 10 * BB });
    assert_eq!(s1.stacks[PLAYER_BB as usize], 0);
    let s2 = s1.apply(Action::Call);
    assert_eq!(s2.stacks[PLAYER_SB as usize], 0);
    assert_eq!(s2.pot(), 40 * BB);
}

#[test]
fn facing_bet_detection_and_call_amount() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s1 = s0.apply(Action::Bet { to: 30 * BB }); // 150% pot
    assert!(s1.facing_bet());
    assert_eq!(s1.call_amount(), 30 * BB);
    assert_eq!(s1.to_act, PLAYER_SB);
}

#[test]
fn check_check_tracks_street_close() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s1 = s0.apply(Action::Check);
    assert!(!s1.street_closed());
    let s2 = s1.apply(Action::Check);
    assert!(s2.street_closed());
}

#[test]
fn call_closes_street() {
    let s0 = BettingState::river_root(20 * BB, 90 * BB);
    let s2 = s0.apply(Action::Bet { to: 15 * BB }).apply(Action::Call);
    assert!(s2.street_closed());
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_betting`
Expected: COMPILE FAIL (`BettingState` not defined).

- [ ] **Step 3: Implement `BettingState`**

Create `gto/crates/gto-hu/src/game/betting.rs`:

```rust
use super::action::Action;
use super::street::Street;

/// 1 big blind in internal chip units (centi-bb).
pub const BB: i64 = 100;
/// Player 0: SB / Button — acts first preflop, last postflop (IP).
pub const PLAYER_SB: u8 = 0;
/// Player 1: BB — acts last preflop, first postflop (OOP).
pub const PLAYER_BB: u8 = 1;

/// Pure betting state. `apply` returns a new state; legality is enforced
/// with assertions (the tree builder only generates legal actions).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct BettingState {
    pub street: Street,
    pub to_act: u8,
    /// Remaining stacks.
    pub stacks: [i64; 2],
    /// Committed on the current street (totals, not increments).
    pub street_committed: [i64; 2],
    /// Total committed this hand (blinds + all streets). pot() derives from it.
    pub contrib: [i64; 2],
    pub raises_this_street: u8,
    /// Number of actions taken this street (for street-close detection).
    pub actions_this_street: u8,
    /// Set when the street's betting is finished (call, or both checked).
    closed: bool,
}

impl BettingState {
    /// River subgame root: symmetric pot carried in, OOP (BB) to act.
    pub fn river_root(pot: i64, stack: i64) -> Self {
        assert!(pot > 0 && pot % 2 == 0, "carried pot must be positive and even");
        assert!(stack > 0, "stack must be positive");
        BettingState {
            street: Street::River,
            to_act: PLAYER_BB,
            stacks: [stack; 2],
            street_committed: [0; 2],
            contrib: [pot / 2; 2],
            raises_this_street: 0,
            actions_this_street: 0,
            closed: false,
        }
    }

    pub fn pot(&self) -> i64 {
        self.contrib[0] + self.contrib[1]
    }

    pub fn facing_bet(&self) -> bool {
        let me = self.to_act as usize;
        self.street_committed[1 - me] > self.street_committed[me]
    }

    /// Chips needed to call (capped by own stack).
    pub fn call_amount(&self) -> i64 {
        let me = self.to_act as usize;
        (self.street_committed[1 - me] - self.street_committed[me]).min(self.stacks[me])
    }

    pub fn street_closed(&self) -> bool {
        self.closed
    }

    pub fn is_all_in(&self, p: u8) -> bool {
        self.stacks[p as usize] == 0
    }

    /// Apply an action, returning the successor state.
    /// Fold does not change chips — terminal payoff handles the pot.
    pub fn apply(&self, action: Action) -> BettingState {
        let me = self.to_act as usize;
        let opp = 1 - me;
        let mut s = *self;
        s.actions_this_street += 1;
        match action {
            Action::Fold => {
                assert!(self.facing_bet(), "fold only legal when facing a bet");
                s.closed = true;
            }
            Action::Check => {
                assert!(!self.facing_bet(), "check illegal when facing a bet");
                // Both players acted without a bet → street closes.
                if s.actions_this_street >= 2 {
                    s.closed = true;
                }
            }
            Action::Call => {
                assert!(self.facing_bet(), "call only legal when facing a bet");
                let amt = self.call_amount();
                s.stacks[me] -= amt;
                s.street_committed[me] += amt;
                s.contrib[me] += amt;
                s.closed = true;
            }
            Action::Bet { to } | Action::Raise { to } | Action::AllIn { to } => {
                let add = to - self.street_committed[me];
                assert!(add > 0, "size must exceed current commitment");
                assert!(add <= self.stacks[me], "cannot bet more than stack");
                assert!(
                    to > self.street_committed[opp] || add == self.stacks[me],
                    "must exceed facing bet unless all-in"
                );
                if self.facing_bet() {
                    s.raises_this_street += 1;
                }
                s.stacks[me] -= add;
                s.street_committed[me] = to;
                s.contrib[me] += add;
            }
        }
        s.to_act = opp as u8;
        s
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_betting`
Expected: 6 PASS.

---

### Task 4: Terminal payoffs

**Files:**
- Create: `gto/crates/gto-hu/src/game/terminal.rs`
- Create: `gto/crates/gto-hu/tests/test_terminal_payoff.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_terminal_payoff.rs`:

```rust
use gto_hu::game::{terminal, Action, BettingState, BB, PLAYER_BB, PLAYER_SB};

#[test]
fn fold_returns_uncalled_bet() {
    // Pot 20bb, BB bets 15bb, SB folds. BB must win exactly 10bb
    // (SB's half of the carried pot), NOT half of the 35bb pot.
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB });
    let p = terminal::fold_payoffs(&s, PLAYER_BB);
    assert_eq!(p[PLAYER_BB as usize], 10 * BB);
    assert_eq!(p[PLAYER_SB as usize], -10 * BB);
}

#[test]
fn fold_payoffs_are_zero_sum() {
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 30 * BB });
    let p = terminal::fold_payoffs(&s, PLAYER_BB);
    assert_eq!(p[0] + p[1], 0);
}

#[test]
fn showdown_winner_takes_opponent_contribution() {
    // Bet 15bb called: each contributed 25bb total. Winner nets +25bb.
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB })
        .apply(Action::Call);
    let p = terminal::showdown_payoffs(&s, Some(PLAYER_SB));
    assert_eq!(p[PLAYER_SB as usize], 25 * BB);
    assert_eq!(p[PLAYER_BB as usize], -25 * BB);
}

#[test]
fn showdown_tie_splits_to_zero() {
    let s = BettingState::river_root(20 * BB, 90 * BB)
        .apply(Action::Bet { to: 15 * BB })
        .apply(Action::Call);
    let p = terminal::showdown_payoffs(&s, None);
    assert_eq!(p, [0, 0]);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_terminal_payoff`
Expected: COMPILE FAIL (`terminal` module empty).

- [ ] **Step 3: Implement**

Create `gto/crates/gto-hu/src/game/terminal.rs`:

```rust
use super::betting::BettingState;

/// Payoff convention everywhere in gto-hu:
/// `payoff(p) = chips_won(p) − contrib(p)` in centi-bb.
/// Uncalled bets return to the bettor automatically because the winner's
/// own contribution cancels: pot − contrib(w) = contrib(loser).

/// Fold terminal: `winner` takes the pot.
pub fn fold_payoffs(state: &BettingState, winner: u8) -> [i64; 2] {
    let pot = state.pot();
    let w = winner as usize;
    let mut p = [0i64; 2];
    p[w] = pot - state.contrib[w];
    p[1 - w] = -state.contrib[1 - w];
    debug_assert_eq!(p[0] + p[1], 0, "fold payoffs must be zero-sum");
    p
}

/// Showdown: `Some(winner)` or `None` for a chopped pot.
pub fn showdown_payoffs(state: &BettingState, winner: Option<u8>) -> [i64; 2] {
    debug_assert_eq!(
        state.contrib[0], state.contrib[1],
        "contributions must match at showdown"
    );
    match winner {
        Some(w) => fold_payoffs(state, w),
        None => {
            let half = state.pot() / 2;
            [half - state.contrib[0], half - state.contrib[1]]
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_betting --test test_terminal_payoff`
Expected: 10 PASS total.

- [ ] **Step 5: Commit Tasks 2-4**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): exact betting state and terminal payoffs

Committed-total action sizes, centi-bb i64 accounting, payoff =
chips_won - contrib (uncalled bets return correctly, fixing the legacy
±pot/2 fold inflation)."
```

---

### Task 5: River tree from config

**Files:**
- Create: `gto/crates/gto-hu/src/tree/config.rs`
- Create: `gto/crates/gto-hu/src/tree/node.rs`
- Create: `gto/crates/gto-hu/src/tree/builder.rs`
- Modify: `gto/crates/gto-hu/src/tree/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_river_tree.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_river_tree.rs`:

```rust
use gto_hu::game::{Action, BB};
use gto_hu::tree::{build_river_tree, NodeKind, StreetConfig};

#[test]
fn river_tree_root_actions_match_srp_config() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let root = &t.nodes[0];
    let labels: Vec<String> = root.children.iter().map(|(a, _)| a.label()).collect();
    // check, bet 75%, bet 150%, allin
    assert_eq!(labels, vec!["check", "bet 15.0bb", "bet 30.0bb", "allin 90.0bb"]);
}

#[test]
fn facing_bet_offers_fold_call_jam() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    // Child 1 of root = bet 15bb → SB node.
    let bet_node_id = t.nodes[0].children[1].1;
    let acts: Vec<Action> = t.nodes[bet_node_id].children.iter().map(|(a, _)| *a).collect();
    assert!(matches!(acts[0], Action::Fold));
    assert!(matches!(acts[1], Action::Call));
    assert!(matches!(acts[2], Action::AllIn { to } if to == 90 * BB));
    assert_eq!(acts.len(), 3, "facing a bet: fold/call/raise-jam only");
}

#[test]
fn no_reraise_after_jam() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let bet_id = t.nodes[0].children[1].1;
    let jam_id = t.nodes[bet_id].children[2].1;
    let acts: Vec<Action> = t.nodes[jam_id].children.iter().map(|(a, _)| *a).collect();
    assert_eq!(acts.len(), 2, "facing a jam: fold/call only");
    assert!(matches!(acts[0], Action::Fold));
    assert!(matches!(acts[1], Action::Call));
}

#[test]
fn all_terminals_are_fold_or_showdown_and_pots_conserve() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let initial = 20 * BB + 2 * 90 * BB;
    let mut terminals = 0;
    for n in &t.nodes {
        match n.kind {
            NodeKind::FoldTerminal { .. } | NodeKind::Showdown => {
                terminals += 1;
                assert!(n.children.is_empty());
                assert_eq!(
                    n.state.pot() + n.state.stacks[0] + n.state.stacks[1],
                    initial,
                    "chip conservation violated at a terminal"
                );
            }
            NodeKind::Action { .. } => assert!(!n.children.is_empty()),
        }
    }
    assert!(terminals >= 6);
}

#[test]
fn short_stack_dedupes_bet_sizes_to_allin() {
    // Stack 10bb: the 75% pot bet (15bb) and 150% pot bet (30bb) both
    // exceed the stack, so they and the explicit jam dedupe into one all-in.
    let t = build_river_tree(20 * BB, 10 * BB, &StreetConfig::srp_river());
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    assert_eq!(labels, vec!["check", "allin 10.0bb"]);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_river_tree`
Expected: COMPILE FAIL.

- [ ] **Step 3: Implement config, node, builder**

`src/tree/config.rs`:

```rust
/// Response rule when facing a bet.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum RaiseRule {
    /// No raise allowed (fold/call only).
    None,
    /// Raise = jam only (river spec: "raise_jam").
    JamOnly,
    /// Raise to `factor` × the facing total; becomes a jam when the result
    /// reaches the stack. (Flop/turn "raise_3x_or_jam"; used from Phase 4.)
    ToFactorOrJam(f64),
}

/// Action abstraction for one street of one pot type.
#[derive(Debug, Clone)]
pub struct StreetConfig {
    /// Open bet sizes in % of current pot.
    pub bet_pcts: Vec<u32>,
    /// Offer an explicit open jam in addition to bet_pcts.
    pub allow_allin_bet: bool,
    pub raise: RaiseRule,
    pub max_raises: u8,
}

impl StreetConfig {
    /// SRP river per spec: check, bet75, bet150, allin / vs bet: fold,
    /// call, raise-jam / vs raise: fold, call.
    pub fn srp_river() -> Self {
        StreetConfig {
            bet_pcts: vec![75, 150],
            allow_allin_bet: true,
            raise: RaiseRule::JamOnly,
            max_raises: 1,
        }
    }
}
```

`src/tree/node.rs`:

```rust
use crate::game::{Action, BettingState};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Action { actor: u8 },
    FoldTerminal { winner: u8 },
    Showdown,
}

#[derive(Debug, Clone)]
pub struct Node {
    pub kind: NodeKind,
    pub state: BettingState,
    pub children: Vec<(Action, usize)>,
}

#[derive(Debug)]
pub struct Tree {
    pub nodes: Vec<Node>,
}
```

`src/tree/builder.rs`:

```rust
use crate::game::{Action, BettingState};
use super::config::{RaiseRule, StreetConfig};
use super::node::{Node, NodeKind, Tree};

/// Build the river action tree. OOP (BB) acts first.
pub fn build_river_tree(pot: i64, stack: i64, cfg: &StreetConfig) -> Tree {
    let root_state = BettingState::river_root(pot, stack);
    let mut tree = Tree { nodes: Vec::new() };
    tree.nodes.push(Node {
        kind: NodeKind::Action { actor: root_state.to_act },
        state: root_state,
        children: Vec::new(),
    });
    expand(&mut tree, 0, cfg);
    tree
}

/// Legal abstract actions at an action node, per config.
/// Sizes are committed totals, capped at all-in, deduplicated.
fn legal_actions(state: &BettingState, cfg: &StreetConfig) -> Vec<Action> {
    let me = state.to_act as usize;
    let opp = 1 - me;
    let stack = state.stacks[me];
    let all_in_to = state.street_committed[me] + stack;
    let mut out: Vec<Action> = Vec::new();

    if state.facing_bet() {
        out.push(Action::Fold);
        out.push(Action::Call);
        // Raise options (only if opponent isn't already all-in and we can
        // legally exceed the facing total).
        let can_raise = state.raises_this_street < cfg.max_raises
            && state.stacks[opp] > 0
            && all_in_to > state.street_committed[opp];
        if can_raise {
            match cfg.raise {
                RaiseRule::None => {}
                RaiseRule::JamOnly => out.push(Action::AllIn { to: all_in_to }),
                RaiseRule::ToFactorOrJam(f) => {
                    let target = (state.street_committed[opp] as f64 * f) as i64;
                    if target >= all_in_to {
                        out.push(Action::AllIn { to: all_in_to });
                    } else {
                        out.push(Action::Raise { to: target });
                    }
                }
            }
        }
    } else {
        out.push(Action::Check);
        if stack > 0 && state.stacks[opp] > 0 {
            let mut tos: Vec<i64> = Vec::new();
            for &pct in &cfg.bet_pcts {
                let to = (state.pot() * pct as i64 / 100).max(1);
                tos.push(to.min(all_in_to));
            }
            if cfg.allow_allin_bet {
                tos.push(all_in_to);
            }
            tos.sort_unstable();
            tos.dedup();
            for to in tos {
                if to >= all_in_to {
                    out.push(Action::AllIn { to: all_in_to });
                } else {
                    out.push(Action::Bet { to });
                }
            }
        }
    }
    out
}

fn expand(tree: &mut Tree, node_id: usize, cfg: &StreetConfig) {
    let state = tree.nodes[node_id].state;
    let actions = legal_actions(&state, cfg);
    let mut children = Vec::with_capacity(actions.len());

    for action in actions {
        let child_state = state.apply(action);
        let kind = match action {
            Action::Fold => NodeKind::FoldTerminal {
                winner: 1 - state.to_act,
            },
            _ if child_state.street_closed() => NodeKind::Showdown,
            _ => NodeKind::Action { actor: child_state.to_act },
        };
        let child_id = tree.nodes.len();
        tree.nodes.push(Node { kind, state: child_state, children: Vec::new() });
        if matches!(kind, NodeKind::Action { .. }) {
            expand(tree, child_id, cfg);
        }
        children.push((action, child_id));
    }
    tree.nodes[node_id].children = children;
}
```

`src/tree/mod.rs`:

```rust
pub mod builder;
pub mod config;
pub mod node;

pub use builder::build_river_tree;
pub use config::{RaiseRule, StreetConfig};
pub use node::{Node, NodeKind, Tree};
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_river_tree`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): config-driven river action tree with exact states"
```

---

### Task 6: Ranges module (thin re-export + helpers)

**Files:**
- Create: `gto/crates/gto-hu/src/ranges/mod.rs`

- [ ] **Step 1: Implement** (no behavior of its own beyond a helper; covered
by Phase 2b solver tests)

```rust
//! Range handling. The 1326-combo representation comes from gto-core.

pub use gto_core::range::{all_combos, combo_index, Range, NUM_COMBOS};

/// Uniform range with board blockers removed.
pub fn uniform_excluding(board: &[u8]) -> Range {
    let mut r = Range::new_uniform();
    r.remove_blockers(board);
    r
}
```

- [ ] **Step 2: Verify build**

Run: `cargo build -p gto-hu`
Expected: clean.

---

### Task 7: CFR variants and regret matching

**Files:**
- Create: `gto/crates/gto-hu/src/solver/regret.rs`
- Create: `gto/crates/gto-hu/src/solver/variant.rs`
- Modify: `gto/crates/gto-hu/src/solver/mod.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_regret.rs`:

```rust
use gto_hu::solver::{regret_matching, CfrVariant};

#[test]
fn regret_matching_normalizes_positive_regrets() {
    let mut s = vec![0.0; 3];
    regret_matching(&[3.0, 1.0, -2.0], &mut s);
    assert!((s[0] - 0.75).abs() < 1e-12);
    assert!((s[1] - 0.25).abs() < 1e-12);
    assert_eq!(s[2], 0.0);
}

#[test]
fn regret_matching_uniform_when_no_positive_regret() {
    let mut s = vec![0.0; 4];
    regret_matching(&[-1.0, 0.0, -5.0, 0.0], &mut s);
    for &p in &s {
        assert!((p - 0.25).abs() < 1e-12);
    }
}

#[test]
fn cfr_plus_clips_regret_at_zero() {
    let v = CfrVariant::CfrPlus { avg_delay: 0, linear_weighting: true };
    assert_eq!(v.update_regret(1.0, -5.0, 10), 0.0);
    assert_eq!(v.update_regret(1.0, 2.0, 10), 3.0);
}

#[test]
fn dcfr_discounts_positive_and_negative_differently() {
    let v = CfrVariant::Dcfr { alpha: 1.5, beta: 0.0, gamma: 2.0 };
    let t = 4u32;
    // positive: old × t^1.5/(t^1.5+1) + delta = 1.0 × 8/9 + 1.0
    let pos = v.update_regret(1.0, 1.0, t);
    assert!((pos - (8.0 / 9.0 + 1.0)).abs() < 1e-12);
    // negative: old × t^0/(t^0+1) + delta = -1.0 × 0.5 + 1.0
    let neg = v.update_regret(-1.0, 1.0, t);
    assert!((neg - 0.5).abs() < 1e-12);
}

#[test]
fn cfr_plus_linear_weighting_and_delay() {
    let v = CfrVariant::CfrPlus { avg_delay: 5, linear_weighting: true };
    assert_eq!(v.strategy_weight(3), 0.0);
    assert_eq!(v.strategy_weight(6), 1.0);
    assert_eq!(v.strategy_weight(15), 10.0);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_regret`
Expected: COMPILE FAIL.

- [ ] **Step 3: Implement**

`src/solver/regret.rs`:

```rust
/// Regret matching: strategy ∝ positive cumulative regrets, uniform when
/// no positive regret exists.
pub fn regret_matching(regrets: &[f64], out: &mut [f64]) {
    debug_assert_eq!(regrets.len(), out.len());
    let pos_sum: f64 = regrets.iter().map(|r| r.max(0.0)).sum();
    if pos_sum > 0.0 {
        for (o, r) in out.iter_mut().zip(regrets) {
            *o = r.max(0.0) / pos_sum;
        }
    } else {
        out.fill(1.0 / regrets.len() as f64);
    }
}
```

`src/solver/variant.rs`:

```rust
/// CFR family member. References: Zinkevich et al. 2007 (vanilla CFR),
/// Tammelin 2014 (CFR+), Brown & Sandholm 2019 (DCFR).
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum CfrVariant {
    Vanilla,
    /// Regrets clipped at zero after each update. Average-strategy
    /// accumulation starts after `avg_delay` iterations; with
    /// `linear_weighting` iteration t contributes weight (t − avg_delay).
    CfrPlus { avg_delay: u32, linear_weighting: bool },
    /// Discounted CFR: positive regrets × t^α/(t^α+1), negative regrets ×
    /// t^β/(t^β+1), strategy contributions × (t/(t+1))^γ.
    Dcfr { alpha: f64, beta: f64, gamma: f64 },
}

impl CfrVariant {
    pub fn dcfr_default() -> Self {
        CfrVariant::Dcfr { alpha: 1.5, beta: 0.0, gamma: 2.0 }
    }

    pub fn cfr_plus_default() -> Self {
        CfrVariant::CfrPlus { avg_delay: 0, linear_weighting: true }
    }

    /// New cumulative regret from `old` and this iteration's `delta`.
    pub fn update_regret(&self, old: f64, delta: f64, t: u32) -> f64 {
        match *self {
            CfrVariant::Vanilla => old + delta,
            CfrVariant::CfrPlus { .. } => (old + delta).max(0.0),
            CfrVariant::Dcfr { alpha, beta, .. } => {
                let tf = t as f64;
                let exp = if old >= 0.0 { alpha } else { beta };
                let p = tf.powf(exp);
                old * (p / (p + 1.0)) + delta
            }
        }
    }

    /// Multiplier applied to the stored strategy sum at iteration t
    /// (DCFR's γ-discount; 1.0 for other variants).
    pub fn strategy_discount(&self, t: u32) -> f64 {
        match *self {
            CfrVariant::Dcfr { gamma, .. } => {
                let tf = t as f64;
                (tf / (tf + 1.0)).powf(gamma)
            }
            _ => 1.0,
        }
    }

    /// Weight of iteration t's strategy contribution.
    pub fn strategy_weight(&self, t: u32) -> f64 {
        match *self {
            CfrVariant::Vanilla | CfrVariant::Dcfr { .. } => 1.0,
            CfrVariant::CfrPlus { avg_delay, linear_weighting } => {
                if t <= avg_delay {
                    0.0
                } else if linear_weighting {
                    (t - avg_delay) as f64
                } else {
                    1.0
                }
            }
        }
    }
}
```

`src/solver/mod.rs`:

```rust
pub mod regret;
pub mod scalar;
pub mod variant;

pub use regret::regret_matching;
pub use scalar::{Game, InfoNode, ScalarCfr};
pub use variant::CfrVariant;
```

(`scalar.rs` comes in Task 8; create as empty file to keep compiling, or
implement Tasks 7-8 before running. The commit point is after Task 8.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_regret`
Expected: 5 PASS.

---

### Task 8: Scalar CFR engine (generic `Game` trait)

**Files:**
- Create: `gto/crates/gto-hu/src/solver/scalar.rs`

Tests arrive with Kuhn in Task 9 (the engine is only testable against a
game). Keep this task to the implementation + compile check.

- [ ] **Step 1: Implement**

`src/solver/scalar.rs`:

```rust
use std::collections::HashMap;

use super::regret::regret_matching;
use super::variant::CfrVariant;

/// Two-player zero-sum extensive-form game with perfect recall.
/// Payoffs are returned per player at terminal states.
pub trait Game {
    type State: Clone;

    fn root(&self) -> Self::State;
    fn is_terminal(&self, s: &Self::State) -> bool;
    /// Terminal payoff for `player` (must satisfy zero-sum).
    fn payoff(&self, s: &Self::State, player: usize) -> f64;
    fn is_chance(&self, s: &Self::State) -> bool;
    /// Chance successor states with probabilities summing to 1.
    fn chance_outcomes(&self, s: &Self::State) -> Vec<(Self::State, f64)>;
    /// Acting player at a non-terminal, non-chance state (0 or 1).
    fn player(&self, s: &Self::State) -> usize;
    fn num_actions(&self, s: &Self::State) -> usize;
    fn next(&self, s: &Self::State, action: usize) -> Self::State;
    /// Information-set key for the acting player (perfect recall).
    fn infoset_key(&self, s: &Self::State) -> String;
}

#[derive(Debug, Clone)]
pub struct InfoNode {
    pub regrets: Vec<f64>,
    pub strat_sum: Vec<f64>,
}

impl InfoNode {
    fn new(num_actions: usize) -> Self {
        InfoNode { regrets: vec![0.0; num_actions], strat_sum: vec![0.0; num_actions] }
    }
}

/// Reference CFR engine: full traversal, exact chance enumeration.
/// Slow but transparent — used for Kuhn/Leduc and differential testing.
pub struct ScalarCfr<'a, G: Game> {
    pub game: &'a G,
    pub variant: CfrVariant,
    pub nodes: HashMap<String, InfoNode>,
    pub iteration: u32,
}

impl<'a, G: Game> ScalarCfr<'a, G> {
    pub fn new(game: &'a G, variant: CfrVariant) -> Self {
        ScalarCfr { game, variant, nodes: HashMap::new(), iteration: 0 }
    }

    /// Run `iterations` full CFR iterations (both players each iteration).
    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for p in 0..2 {
                let root = self.game.root();
                self.traverse(&root, p, 1.0, 1.0);
            }
        }
    }

    /// Returns EV for `traverser` at `s` under current strategies.
    /// `my_reach` = traverser's own reach; `opp_reach` includes the
    /// opponent's strategy AND chance probabilities (counterfactual reach).
    fn traverse(&mut self, s: &G::State, traverser: usize, my_reach: f64, opp_reach: f64) -> f64 {
        if self.game.is_terminal(s) {
            return self.game.payoff(s, traverser);
        }
        if self.game.is_chance(s) {
            return self
                .game
                .chance_outcomes(s)
                .iter()
                .map(|(c, p)| p * self.traverse(c, traverser, my_reach, opp_reach * p))
                .sum();
        }

        let player = self.game.player(s);
        let na = self.game.num_actions(s);
        let key = self.game.infoset_key(s);
        let mut strat = vec![0.0; na];
        {
            let node = self.nodes.entry(key.clone()).or_insert_with(|| InfoNode::new(na));
            regret_matching(&node.regrets, &mut strat);
        }

        if player == traverser {
            let mut action_vals = vec![0.0; na];
            for a in 0..na {
                let child = self.game.next(s, a);
                action_vals[a] = self.traverse(&child, traverser, my_reach * strat[a], opp_reach);
            }
            let ev: f64 = strat.iter().zip(&action_vals).map(|(p, v)| p * v).sum();
            let t = self.iteration;
            let (sd, sw) = (self.variant.strategy_discount(t), self.variant.strategy_weight(t));
            let variant = self.variant;
            let node = self.nodes.get_mut(&key).unwrap();
            for a in 0..na {
                let delta = opp_reach * (action_vals[a] - ev);
                node.regrets[a] = variant.update_regret(node.regrets[a], delta, t);
                // Average strategy: weighted by the actor's OWN reach.
                node.strat_sum[a] = node.strat_sum[a] * sd + sw * my_reach * strat[a];
            }
            ev
        } else {
            let mut ev = 0.0;
            for a in 0..na {
                let child = self.game.next(s, a);
                ev += strat[a] * self.traverse(&child, traverser, my_reach, opp_reach * strat[a]);
            }
            ev
        }
    }

    /// Normalized average strategy for an infoset key (uniform if unseen).
    pub fn average_strategy(&self, key: &str, num_actions: usize) -> Vec<f64> {
        match self.nodes.get(key) {
            Some(n) => {
                let total: f64 = n.strat_sum.iter().sum();
                if total > 0.0 {
                    n.strat_sum.iter().map(|s| s / total).collect()
                } else {
                    vec![1.0 / num_actions as f64; num_actions]
                }
            }
            None => vec![1.0 / num_actions as f64; num_actions],
        }
    }
}
```

Implementation note: the strategy sum is updated only in the
`player == traverser` branch, so each infoset accumulates exactly once per
iteration (during its owner's traversal), weighted by the owner's reach.
This fixes legacy audit issue #6.

- [ ] **Step 2: Verify build**

Run: `cargo build -p gto-hu`
Expected: clean (warnings about unused code acceptable until Task 9).

---

### Task 9: Kuhn poker on the production engine

**Files:**
- Create: `gto/crates/gto-hu/src/games/kuhn.rs`
- Modify: `gto/crates/gto-hu/src/games/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_cfr_kuhn.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_cfr_kuhn.rs`:

```rust
//! Kuhn poker: cards J=0,Q=1,K=2; both ante 1. Nash: game value = −1/18,
//! P0 Q never bets, P1 K always calls, P1 Q calls 1/3, P1 J bluffs 1/3.

use gto_hu::games::Kuhn;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn kuhn_cfr_plus_reaches_nash() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(20_000);

    let expl = exploitability(&game, &cfr);
    assert!(expl < 0.005, "exploitability {expl:.6} should be < 0.005");

    // Game value to P0 ≈ −1/18 (measured via best responses bracketing it).
    let br1 = best_response_value(&game, &cfr, 1);
    assert!(
        (br1 - 1.0 / 18.0).abs() < 0.01,
        "BR1 value {br1:.6} should be ≈ +1/18"
    );

    // P0 with Q (card 1) never bets at the root.
    let s = cfr.average_strategy("0|1|", 2);
    assert!(s[1] < 0.02, "P0 Q root bet freq {} should be ~0", s[1]);

    // P1 with K (card 2) always calls a bet.
    let s = cfr.average_strategy("1|2|b", 2);
    assert!(s[1] > 0.98, "P1 K call freq {} should be ~1", s[1]);

    // P1 with J (card 0) bluff-bets ~1/3 after a check.
    let s = cfr.average_strategy("1|0|p", 2);
    assert!((s[1] - 1.0 / 3.0).abs() < 0.05, "P1 J bluff {} ≈ 1/3", s[1]);
}

#[test]
fn kuhn_dcfr_also_converges() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::dcfr_default());
    cfr.run(20_000);
    let expl = exploitability(&game, &cfr);
    assert!(expl < 0.01, "DCFR exploitability {expl:.6} should be < 0.01");
}

#[test]
fn kuhn_average_strategies_sum_to_one() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(1_000);
    for (key, node) in &cfr.nodes {
        let s = cfr.average_strategy(key, node.regrets.len());
        let sum: f64 = s.iter().sum();
        assert!((sum - 1.0).abs() < 1e-9, "strategy at {key} sums to {sum}");
    }
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_cfr_kuhn`
Expected: COMPILE FAIL (`Kuhn`, `validation` missing — Task 10 provides
validation; implement Kuhn here, validation next, then both test files run).

- [ ] **Step 3: Implement Kuhn**

`src/games/kuhn.rs`:

```rust
use crate::solver::Game;

/// Kuhn poker. Actions: 0 = pass/check/fold, 1 = bet/call.
/// History chars: 'p' and 'b'. Terminals: pp, pbp, pbb, bp, bb.
pub struct Kuhn;

#[derive(Debug, Clone)]
pub struct KuhnState {
    /// None until the chance node deals (card0, card1).
    pub cards: Option<(u8, u8)>,
    pub history: String,
}

impl Kuhn {
    fn terminal_payoff_p0(cards: (u8, u8), history: &str) -> Option<f64> {
        let win = |a: u8, b: u8| if a > b { 1.0 } else { -1.0 };
        match history {
            "pp" => Some(win(cards.0, cards.1)),           // showdown, pot 2
            "pbp" => Some(-1.0),                            // P0 folds after check-bet
            "pbb" => Some(2.0 * win(cards.0, cards.1)),     // call, pot 4
            "bp" => Some(1.0),                              // P1 folds
            "bb" => Some(2.0 * win(cards.0, cards.1)),      // call, pot 4
            _ => None,
        }
    }
}

impl Game for Kuhn {
    type State = KuhnState;

    fn root(&self) -> KuhnState {
        KuhnState { cards: None, history: String::new() }
    }

    fn is_terminal(&self, s: &KuhnState) -> bool {
        s.cards.is_some() && Self::terminal_payoff_p0(s.cards.unwrap(), &s.history).is_some()
    }

    fn payoff(&self, s: &KuhnState, player: usize) -> f64 {
        let p0 = Self::terminal_payoff_p0(s.cards.unwrap(), &s.history).unwrap();
        if player == 0 { p0 } else { -p0 }
    }

    fn is_chance(&self, s: &KuhnState) -> bool {
        s.cards.is_none()
    }

    fn chance_outcomes(&self, _s: &KuhnState) -> Vec<(KuhnState, f64)> {
        let mut out = Vec::with_capacity(6);
        for c0 in 0..3u8 {
            for c1 in 0..3u8 {
                if c0 != c1 {
                    out.push((
                        KuhnState { cards: Some((c0, c1)), history: String::new() },
                        1.0 / 6.0,
                    ));
                }
            }
        }
        out
    }

    fn player(&self, s: &KuhnState) -> usize {
        s.history.len() % 2
    }

    fn num_actions(&self, _s: &KuhnState) -> usize {
        2
    }

    fn next(&self, s: &KuhnState, action: usize) -> KuhnState {
        let mut h = s.history.clone();
        h.push(if action == 0 { 'p' } else { 'b' });
        KuhnState { cards: s.cards, history: h }
    }

    fn infoset_key(&self, s: &KuhnState) -> String {
        let player = self.player(s);
        let card = match s.cards.unwrap() {
            (c0, _) if player == 0 => c0,
            (_, c1) => c1,
        };
        format!("{player}|{card}|{}", s.history)
    }
}
```

`src/games/mod.rs`:

```rust
pub mod kuhn;
pub mod leduc;

pub use kuhn::Kuhn;
pub use leduc::Leduc;
```

(`leduc.rs` arrives in Task 11; until then keep `pub mod leduc;` commented
out or create the file with just `//! Leduc poker (Task 11).` — choose the
empty-file route so the module list stays final.)

- [ ] **Step 4: Continue to Task 10** (validation is required before the
Kuhn tests compile). Do not commit yet.

---

### Task 10: Exact best response and exploitability (scalar)

**Files:**
- Create: `gto/crates/gto-hu/src/validation/best_response.rs`
- Create: `gto/crates/gto-hu/src/validation/mod.rs`
- Create: `gto/crates/gto-hu/tests/test_best_response.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_best_response.rs`:

```rust
use gto_hu::games::Kuhn;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn best_response_exploits_uniform_strategy() {
    // Against an untrained (uniform) strategy, BR must gain strictly more
    // than the Nash value from each side.
    let game = Kuhn;
    let cfr = ScalarCfr::new(&game, CfrVariant::Vanilla); // no iterations
    let br0 = best_response_value(&game, &cfr, 0);
    let br1 = best_response_value(&game, &cfr, 1);
    assert!(br0 > -1.0 / 18.0 + 0.05, "BR0 {br0:.4} must exploit uniform");
    assert!(br1 > 1.0 / 18.0 + 0.05, "BR1 {br1:.4} must exploit uniform");
}

#[test]
fn exploitability_is_nonnegative_and_decreases() {
    let game = Kuhn;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(100);
    let e100 = exploitability(&game, &cfr);
    cfr.run(4_900);
    let e5000 = exploitability(&game, &cfr);
    assert!(e100 >= -1e-9 && e5000 >= -1e-9);
    assert!(e5000 < e100, "exploitability must decrease: {e100:.5} → {e5000:.5}");
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_best_response`
Expected: COMPILE FAIL.

- [ ] **Step 3: Implement**

`src/validation/best_response.rs`:

```rust
use std::collections::HashMap;

use crate::solver::{Game, ScalarCfr};

/// Exact best response for two-player zero-sum games with perfect recall.
///
/// Infosets of the BR player are processed deepest-first (child infosets
/// always lie strictly deeper than their parents in our games). The action
/// choice at an infoset maximizes Σ over its states of
/// (opponent × chance reach) × value — the BR player's own reach above is
/// constant per infoset under perfect recall and does not affect argmax.
pub fn best_response_value<G: Game>(game: &G, cfr: &ScalarCfr<G>, br_player: usize) -> f64 {
    // Pass 1: enumerate all BR-player decision states, grouped by infoset,
    // with their opponent+chance reach under the opponent's average strategy.
    let mut infosets: HashMap<String, (usize, usize)> = HashMap::new(); // key → (depth, na)
    collect(game, cfr, &game.root(), br_player, 0, &mut infosets);

    let mut ordered: Vec<(String, usize, usize)> =
        infosets.into_iter().map(|(k, (d, na))| (k, d, na)).collect();
    ordered.sort_by(|a, b| b.1.cmp(&a.1)); // deepest first

    // Pass 2: greedily fix the best action per infoset, deepest first.
    let mut choices: HashMap<String, usize> = HashMap::new();
    for (key, _depth, na) in ordered {
        let mut action_vals = vec![0.0; na];
        accumulate_action_values(
            game, cfr, &game.root(), br_player, 1.0, &key, &choices, &mut action_vals,
        );
        let best = action_vals
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0);
        choices.insert(key, best);
    }

    // Pass 3: evaluate the root under the fixed BR policy.
    eval(game, cfr, &game.root(), br_player, &choices)
}

fn collect<G: Game>(
    game: &G,
    cfr: &ScalarCfr<G>,
    s: &G::State,
    br_player: usize,
    depth: usize,
    out: &mut HashMap<String, (usize, usize)>,
) {
    if game.is_terminal(s) {
        return;
    }
    if game.is_chance(s) {
        for (c, _p) in game.chance_outcomes(s) {
            collect(game, cfr, &c, br_player, depth + 1, out);
        }
        return;
    }
    let na = game.num_actions(s);
    if game.player(s) == br_player {
        let key = game.infoset_key(s);
        let e = out.entry(key).or_insert((depth, na));
        e.0 = e.0.max(depth);
    }
    for a in 0..na {
        collect(game, cfr, &game.next(s, a), br_player, depth + 1, out);
    }
}

/// Adds (opp×chance reach) × subtree value to `action_vals` for every state
/// belonging to `target_key`. Deeper BR infosets are already in `choices`;
/// shallower BR nodes on the path contribute reach 1 (their choice cannot
/// remove states of a deeper infoset under perfect recall — every state of
/// `target_key` shares the same own-action history).
fn accumulate_action_values<G: Game>(
    game: &G,
    cfr: &ScalarCfr<G>,
    s: &G::State,
    br_player: usize,
    reach_opp_chance: f64,
    target_key: &str,
    choices: &HashMap<String, usize>,
    action_vals: &mut [f64],
) {
    if game.is_terminal(s) || reach_opp_chance == 0.0 {
        return;
    }
    if game.is_chance(s) {
        for (c, p) in game.chance_outcomes(s) {
            accumulate_action_values(
                game, cfr, &c, br_player, reach_opp_chance * p, target_key, choices, action_vals,
            );
        }
        return;
    }
    let na = game.num_actions(s);
    if game.player(s) == br_player {
        let key = game.infoset_key(s);
        if key == target_key {
            for a in 0..na {
                let v = eval(game, cfr, &game.next(s, a), br_player, choices);
                action_vals[a] += reach_opp_chance * v;
            }
            return;
        }
        // Other own infoset: descend all actions (choice fixed only if deeper
        // sets were already resolved; unresolved shallower sets don't gate
        // reachability of target states — see function doc).
        for a in 0..na {
            accumulate_action_values(
                game, cfr, &game.next(s, a), br_player, reach_opp_chance, target_key, choices,
                action_vals,
            );
        }
    } else {
        let key = game.infoset_key(s);
        let strat = cfr.average_strategy(&key, na);
        for a in 0..na {
            accumulate_action_values(
                game, cfr, &game.next(s, a), br_player, reach_opp_chance * strat[a], target_key,
                choices, action_vals,
            );
        }
    }
}

/// Expected value for `br_player` when they play `choices` and the
/// opponent plays the average strategy.
fn eval<G: Game>(
    game: &G,
    cfr: &ScalarCfr<G>,
    s: &G::State,
    br_player: usize,
    choices: &HashMap<String, usize>,
) -> f64 {
    if game.is_terminal(s) {
        return game.payoff(s, br_player);
    }
    if game.is_chance(s) {
        return game
            .chance_outcomes(s)
            .iter()
            .map(|(c, p)| p * eval(game, cfr, c, br_player, choices))
            .sum();
    }
    let na = game.num_actions(s);
    let key = game.infoset_key(s);
    if game.player(s) == br_player {
        let a = *choices.get(&key).unwrap_or(&0);
        eval(game, cfr, &game.next(s, a), br_player, choices)
    } else {
        let strat = cfr.average_strategy(&key, na);
        (0..na)
            .map(|a| strat[a] * eval(game, cfr, &game.next(s, a), br_player, choices))
            .sum()
    }
}

/// NashConv/2: average best-response gain. 0 at equilibrium.
pub fn exploitability<G: Game>(game: &G, cfr: &ScalarCfr<G>) -> f64 {
    let br0 = best_response_value(game, cfr, 0);
    let br1 = best_response_value(game, cfr, 1);
    (br0 + br1) / 2.0
}
```

`src/validation/mod.rs`:

```rust
pub mod best_response;

pub use best_response::{best_response_value, exploitability};
```

- [ ] **Step 4: Run Kuhn + BR tests**

Run: `cargo test -p gto-hu --test test_cfr_kuhn --test test_best_response`
Expected: 5 PASS. Quote the exploitability numbers from the output in the
task report.

- [ ] **Step 5: Commit Tasks 8-10**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): scalar CFR engine (vanilla/CFR+/DCFR) with exact BR, Kuhn validated"
```

---

### Task 11: Leduc poker validation

**Files:**
- Create: `gto/crates/gto-hu/src/games/leduc.rs`
- Create: `gto/crates/gto-hu/tests/test_cfr_leduc.rs`

- [ ] **Step 1: Write the failing tests**

Create `gto/crates/gto-hu/tests/test_cfr_leduc.rs`:

```rust
//! Leduc hold'em: 6 cards (J,Q,K ×2), ante 1, two betting rounds
//! (bet 2 then 4, max 2 raises/round), one public card. Pair beats rank.
//! Known game value ≈ −0.0856 for player 0 (OpenSpiel reference).

use gto_hu::games::Leduc;
use gto_hu::solver::{CfrVariant, ScalarCfr};
use gto_hu::validation::{best_response_value, exploitability};

#[test]
fn leduc_exploitability_decreases_and_gets_small() {
    let game = Leduc;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(200);
    let e200 = exploitability(&game, &cfr);
    cfr.run(1_800);
    let e2000 = exploitability(&game, &cfr);
    assert!(e2000 < e200, "exploitability must decrease: {e200:.4} → {e2000:.4}");
    assert!(e2000 < 0.1, "exploitability after 2000 iters: {e2000:.4}");
}

#[test]
fn leduc_game_value_in_known_band() {
    let game = Leduc;
    let mut cfr = ScalarCfr::new(&game, CfrVariant::cfr_plus_default());
    cfr.run(5_000);
    // Bracket the value with the two best responses: at low exploitability
    // both are close to the true value (−0.0856 for P0 ⇒ +0.0856 for P1).
    let br1 = best_response_value(&game, &cfr, 1);
    assert!(
        (0.02..0.16).contains(&br1),
        "BR1 {br1:.4} should be near +0.0856"
    );
}

#[test]
fn leduc_chance_probabilities_sum_to_one() {
    use gto_hu::solver::Game;
    let game = Leduc;
    let root = game.root();
    let deals = game.chance_outcomes(&root);
    assert_eq!(deals.len(), 30, "6×5 ordered private deals");
    let total: f64 = deals.iter().map(|(_, p)| p).sum();
    assert!((total - 1.0).abs() < 1e-12);
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cargo test -p gto-hu --test test_cfr_leduc`
Expected: COMPILE FAIL (`Leduc` is an empty module).

- [ ] **Step 3: Implement Leduc**

`src/games/leduc.rs`:

```rust
use crate::solver::Game;

/// Leduc hold'em. Cards 0,1,2 = J,Q,K (two of each). Both ante 1.
/// Round 0: bet size 2; round 1 (after public card): bet size 4.
/// Max 2 raises per round. Actions: 0=fold/check, 1=call/check-as-bet? —
/// We use 3 actions: 0=fold (or check when nothing to call), 1=call (or
/// check), 2=raise. To keep `num_actions` fixed per state we expose only
/// the legal subset via the state's `legal` list.
pub struct Leduc;

const RAISE_SIZES: [i64; 2] = [2, 4];

#[derive(Debug, Clone)]
pub struct LeducState {
    pub holes: Option<(u8, u8)>,
    pub public: Option<u8>,
    pub round: usize,
    /// Per-round action history, 'c'=check/call, 'r'=raise, 'f'=fold.
    pub hist: [String; 2],
    pub contrib: [i64; 2],
    pub to_act: usize,
    pub folded: Option<usize>,
}

impl LeducState {
    fn raises_this_round(&self) -> usize {
        self.hist[self.round].matches('r').count()
    }

    fn facing_raise(&self) -> bool {
        self.contrib[self.to_act] < self.contrib[1 - self.to_act]
    }

    fn round_over(&self) -> bool {
        let h = &self.hist[self.round];
        if h.ends_with("cc") && !h.contains('r') {
            return true; // check-check
        }
        // A call after at least one raise closes the round.
        h.len() >= 2 && h.ends_with('c') && h.contains('r')
    }

    fn legal_actions(&self) -> Vec<usize> {
        let mut v = Vec::new();
        if self.facing_raise() {
            v.push(0); // fold
        }
        v.push(1); // check/call
        if self.raises_this_round() < 2 {
            v.push(2); // raise
        }
        v
    }
}

impl Game for Leduc {
    type State = LeducState;

    fn root(&self) -> LeducState {
        LeducState {
            holes: None,
            public: None,
            round: 0,
            hist: [String::new(), String::new()],
            contrib: [1, 1], // antes
            to_act: 0,
            folded: None,
        }
    }

    fn is_terminal(&self, s: &LeducState) -> bool {
        if s.holes.is_none() {
            return false;
        }
        if s.folded.is_some() {
            return true;
        }
        s.round == 1 && s.public.is_some() && s.round_over()
    }

    fn payoff(&self, s: &LeducState, player: usize) -> f64 {
        let pot = (s.contrib[0] + s.contrib[1]) as f64;
        if let Some(f) = s.folded {
            // Folder loses their contribution.
            return if player == f {
                -(s.contrib[f] as f64)
            } else {
                pot - s.contrib[player] as f64
            };
        }
        let (h0, h1) = s.holes.unwrap();
        let pubc = s.public.unwrap();
        let rank0 = if h0 == pubc { 10 + h0 } else { h0 };
        let rank1 = if h1 == pubc { 10 + h1 } else { h1 };
        let mine = s.contrib[player] as f64;
        if rank0 == rank1 {
            return pot / 2.0 - mine; // chop (equal contribs ⇒ 0)
        }
        let winner = if rank0 > rank1 { 0 } else { 1 };
        if player == winner { pot - mine } else { -mine }
    }

    fn is_chance(&self, s: &LeducState) -> bool {
        s.holes.is_none() || (s.round == 1 && s.public.is_none())
    }

    fn chance_outcomes(&self, s: &LeducState) -> Vec<(LeducState, f64)> {
        let deck = [0u8, 0, 1, 1, 2, 2];
        if s.holes.is_none() {
            // Deal ordered (hole0, hole1) from 6 distinct physical cards.
            let mut out = Vec::with_capacity(30);
            for i in 0..6 {
                for j in 0..6 {
                    if i != j {
                        let mut ns = s.clone();
                        ns.holes = Some((deck[i], deck[j]));
                        // The public draw later removes one copy of each
                        // dealt rank from the deck (see the branch below).
                        out.push((ns, 1.0 / 30.0));
                    }
                }
            }
            return out;
        }
        // Public card: remove one copy of each hole rank from the deck.
        let (h0, h1) = s.holes.unwrap();
        let mut counts = [2u8; 3];
        counts[h0 as usize] -= 1;
        counts[h1 as usize] -= 1;
        let total: u8 = counts.iter().sum(); // always 4
        let mut out = Vec::new();
        for rank in 0..3u8 {
            let c = counts[rank as usize];
            if c > 0 {
                let mut ns = s.clone();
                ns.public = Some(rank);
                out.push((ns, c as f64 / total as f64));
            }
        }
        out
    }

    fn player(&self, s: &LeducState) -> usize {
        s.to_act
    }

    fn num_actions(&self, s: &LeducState) -> usize {
        s.legal_actions().len()
    }

    fn next(&self, s: &LeducState, action: usize) -> LeducState {
        let legal = s.legal_actions();
        let act = legal[action];
        let mut ns = s.clone();
        let me = s.to_act;
        match act {
            0 => {
                ns.folded = Some(me);
                ns.hist[s.round].push('f');
            }
            1 => {
                // Check or call.
                let diff = s.contrib[1 - me] - s.contrib[me];
                ns.contrib[me] += diff;
                ns.hist[s.round].push('c');
            }
            2 => {
                let diff = s.contrib[1 - me] - s.contrib[me];
                ns.contrib[me] += diff + RAISE_SIZES[s.round];
                ns.hist[s.round].push('r');
            }
            _ => unreachable!(),
        }
        ns.to_act = 1 - me;
        if ns.folded.is_none() && ns.round == 0 && ns.round_over() {
            ns.round = 1;
            ns.to_act = 0;
            // public card dealt by the next chance node (public: None)
        }
        ns
    }

    fn infoset_key(&self, s: &LeducState) -> String {
        let me = s.to_act;
        let hole = match s.holes.unwrap() {
            (h, _) if me == 0 => h,
            (_, h) => h,
        };
        let pubs = s.public.map(|p| p.to_string()).unwrap_or_else(|| "-".into());
        format!("{me}|{hole}|{pubs}|{}|{}", s.hist[0], s.hist[1])
    }
}
```

Implementation note (subtle): `round_over` for round transitions — after
the transition, `hist[1]` is empty and `public` is `None`, so `is_chance`
fires before any round-1 action. The `cc` check requires **no** raise in
the round; `r...c` requires a call after a raise. A single leading check
does not close the round.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cargo test -p gto-hu --test test_cfr_leduc`
Expected: 3 PASS (the 2000-iteration test takes a few seconds; Leduc has
~936 infosets). Quote the exploitability numbers in the task report.

- [ ] **Step 5: Run the whole gto-hu suite**

Run: `cargo test -p gto-hu`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add gto/crates/gto-hu
git commit -m "feat(gto-hu): Leduc poker validation on the scalar CFR engine"
```

---

## Completion criteria for Phase 2a

- `cargo test -p gto-hu` fully green.
- Kuhn: exploitability < 0.005 (CFR+), Nash properties asserted.
- Leduc: exploitability decreasing, < 0.1 at 2000 iters.
- `cargo test -p gto-core` still green (no regressions).
- Phase 2b (vector river solver, differential tests, CLI) builds on these
  exact types: `Tree`, `NodeKind`, `BettingState`, `terminal::*`,
  `CfrVariant`, `regret_matching`, `Game`, `ScalarCfr`,
  `best_response_value`, `exploitability`.
