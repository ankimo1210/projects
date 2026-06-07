//! HU preflop tree per spec §6 — fixed action ladder with limp lines.
//!
//! | Situation                  | Options                                |
//! |----------------------------|----------------------------------------|
//! | SB initial                 | fold, limp, raise to 2.5bb             |
//! | BB vs limp                 | check, raise to 4bb, raise to 6bb      |
//! | SB vs BB raise after limp  | fold, call, 3bet to 12bb, jam          |
//! | BB vs SB open 2.5bb        | fold, call, 3bet to 9bb                |
//! | SB vs BB 3bet              | fold, call, 4bet to 22bb, jam          |
//! | BB vs SB 4bet / limp-3bet  | fold, call, jam                        |
//! | Facing jam                 | fold, call                             |
//!
//! Sizes are committed totals in centi-bb, capped to all-in on short
//! stacks (a capped raise IS the jam and dedupes with an explicit jam).
//! Non-fold closes become `NextStreet` leaves tagged with the pot type;
//! any close with an empty stack is `AllInPreflop`.

use super::node::{Node, NodeKind, Tree};
use crate::game::{Action, BettingState, PotType};

/// SB open size (2.5bb).
const OPEN_TO: i64 = 250;
/// BB raise sizes over a limp (4bb / 6bb).
const LIMP_RAISES: [i64; 2] = [400, 600];
/// SB 3bet over a BB limp-raise (12bb).
const LIMP_THREEBET_TO: i64 = 1_200;
/// BB 3bet over the SB open (9bb).
const THREEBET_TO: i64 = 900;
/// SB 4bet over the BB 3bet (22bb).
const FOURBET_TO: i64 = 2_200;

/// Decision context: which spec row applies at this node.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Ctx {
    SbOpen,
    BbVsLimp,
    SbVsLimpRaise,
    BbVsLimp3bet,
    BbVsOpen,
    SbVs3bet,
    BbVs4bet,
    VsJam,
}

/// What an action leads to.
#[derive(Debug, Clone, Copy)]
enum Next {
    Fold,
    Leaf(PotType),
    Decision(Ctx),
}

pub fn build_preflop_tree(stack: i64) -> Tree {
    let root_state = BettingState::preflop_root(stack);
    let mut tree = Tree { nodes: Vec::new() };
    tree.nodes.push(Node {
        kind: NodeKind::Action {
            actor: root_state.to_act,
        },
        state: root_state,
        children: Vec::new(),
    });
    expand(&mut tree, 0, Ctx::SbOpen);
    tree
}

/// Raise to `target`, becoming a jam when the target reaches the stack.
fn raise_to(state: &BettingState, target: i64) -> Action {
    let me = state.to_act as usize;
    let all_in = state.street_committed[me] + state.stacks[me];
    if target >= all_in {
        Action::AllIn { to: all_in }
    } else {
        Action::Raise { to: target }
    }
}

/// (raise action, context the opponent lands in).
fn raise_with_ctx(state: &BettingState, target: i64, ctx: Ctx) -> (Action, Next) {
    let action = raise_to(state, target);
    let next = if matches!(action, Action::AllIn { .. }) {
        Next::Decision(Ctx::VsJam)
    } else {
        Next::Decision(ctx)
    };
    (action, next)
}

fn jam(state: &BettingState) -> (Action, Next) {
    let me = state.to_act as usize;
    let all_in = state.street_committed[me] + state.stacks[me];
    (
        Action::AllIn { to: all_in },
        Next::Decision(Ctx::VsJam),
    )
}

/// Options at a node per the spec table.
fn options(state: &BettingState, ctx: Ctx) -> Vec<(Action, Next)> {
    let mut out: Vec<(Action, Next)> = Vec::new();
    match ctx {
        Ctx::SbOpen => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Decision(Ctx::BbVsLimp))); // limp
            out.push(raise_with_ctx(state, OPEN_TO, Ctx::BbVsOpen));
        }
        Ctx::BbVsLimp => {
            out.push((Action::Check, Next::Leaf(PotType::Limped)));
            for target in LIMP_RAISES {
                out.push(raise_with_ctx(state, target, Ctx::SbVsLimpRaise));
            }
        }
        Ctx::SbVsLimpRaise => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::Srp)));
            out.push(raise_with_ctx(state, LIMP_THREEBET_TO, Ctx::BbVsLimp3bet));
            out.push(jam(state));
        }
        Ctx::BbVsLimp3bet => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::ThreeBet)));
            out.push(jam(state));
        }
        Ctx::BbVsOpen => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::Srp)));
            out.push(raise_with_ctx(state, THREEBET_TO, Ctx::SbVs3bet));
        }
        Ctx::SbVs3bet => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::ThreeBet)));
            out.push(raise_with_ctx(state, FOURBET_TO, Ctx::BbVs4bet));
            out.push(jam(state));
        }
        Ctx::BbVs4bet => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::FourBet)));
            out.push(jam(state));
        }
        Ctx::VsJam => {
            out.push((Action::Fold, Next::Fold));
            out.push((Action::Call, Next::Leaf(PotType::AllInPreflop)));
        }
    }
    // Capped raises become jams: keep only the first of identical all-ins.
    let mut seen_allin: Option<i64> = None;
    out.retain(|(a, _)| match a {
        Action::AllIn { to } => {
            if seen_allin == Some(*to) {
                false
            } else {
                seen_allin = Some(*to);
                true
            }
        }
        _ => true,
    });
    out
}

fn expand(tree: &mut Tree, node_id: usize, ctx: Ctx) {
    let state = tree.nodes[node_id].state;
    let opts = options(&state, ctx);
    let mut children = Vec::with_capacity(opts.len());

    for (action, next) in opts {
        let child_state = state.apply(action);
        let child_id = tree.nodes.len();
        match next {
            Next::Fold => {
                tree.nodes.push(Node {
                    kind: NodeKind::FoldTerminal {
                        winner: 1 - state.to_act,
                    },
                    state: child_state,
                    children: Vec::new(),
                });
            }
            Next::Leaf(tag) => {
                debug_assert!(child_state.street_closed(), "leaf requires a closed street");
                let pot_type = if child_state.stacks.contains(&0) {
                    PotType::AllInPreflop
                } else {
                    tag
                };
                tree.nodes.push(Node {
                    kind: NodeKind::NextStreet { pot_type },
                    state: child_state,
                    children: Vec::new(),
                });
            }
            Next::Decision(next_ctx) => {
                tree.nodes.push(Node {
                    kind: NodeKind::Action {
                        actor: child_state.to_act,
                    },
                    state: child_state,
                    children: Vec::new(),
                });
                expand(tree, child_id, next_ctx);
            }
        }
        children.push((action, child_id));
    }
    tree.nodes[node_id].children = children;
}
