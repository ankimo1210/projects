use super::builder::{expand as expand_street, legal_actions};
use super::config::StreetConfig;
use super::node::{Node, NodeKind, Tree};
use crate::game::{Action, BettingState, Street};

/// Action abstraction per street for a flop+turn+river tree.
#[derive(Debug, Clone)]
pub struct FlopTreeConfig {
    pub flop: StreetConfig,
    pub turn: StreetConfig,
    pub river: StreetConfig,
}

impl FlopTreeConfig {
    /// Single-raised pot per spec §6.
    pub fn srp() -> Self {
        FlopTreeConfig {
            flop: StreetConfig::srp_flop(),
            turn: StreetConfig::srp_turn(),
            river: StreetConfig::srp_river(),
        }
    }

    /// 3-bet pot per spec §6.
    pub fn threebet() -> Self {
        FlopTreeConfig {
            flop: StreetConfig::threebet_flop(),
            turn: StreetConfig::threebet_turn(),
            river: StreetConfig::threebet_river(),
        }
    }
}

/// Build the flop+turn+river tree. Flop betting starts from a symmetric
/// pot with OOP (BB) to act. Every non-fold street close deals the next
/// card through a `Chance` node (cards are enumerated/sampled by the
/// solver, never materialized here — design spec §7). All-in closes deal
/// the remaining streets as a chance chain straight to showdown with no
/// further betting (spec §6); a flop all-in therefore produces
/// Chance(turn) → Chance(river) → Showdown.
pub fn build_flop_tree(pot: i64, stack: i64, cfg: &FlopTreeConfig) -> Tree {
    cfg.flop.validate();
    cfg.turn.validate();
    cfg.river.validate();
    let root_state = BettingState::street_root(Street::Flop, pot, stack);
    let mut tree = Tree { nodes: Vec::new() };
    tree.nodes.push(Node {
        kind: NodeKind::Action {
            actor: root_state.to_act,
        },
        state: root_state,
        children: Vec::new(),
    });
    expand_betting(&mut tree, 0, cfg);
    tree
}

/// Expand a flop or turn action node; street closes chain a Chance node
/// to the next street (river closes inside `expand_street` are showdowns).
fn expand_betting(tree: &mut Tree, node_id: usize, cfg: &FlopTreeConfig) {
    let state = tree.nodes[node_id].state;
    let street_cfg = match state.street {
        Street::Flop => &cfg.flop,
        Street::Turn => &cfg.turn,
        s => unreachable!("expand_betting on {s:?}"),
    };
    let actions = legal_actions(&state, street_cfg);
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
            // Street finished → deal the next card through a chance node.
            push_chance_chain(tree, child_state, cfg);
        } else {
            tree.nodes.push(Node {
                kind: NodeKind::Action {
                    actor: child_state.to_act,
                },
                state: child_state,
                children: Vec::new(),
            });
            expand_betting(tree, child_id, cfg);
        }
        children.push((action, child_id));
    }
    tree.nodes[node_id].children = children;
}

/// Push the Chance node for a closed street and everything below it.
/// All-in: chain chance nodes (turn, then river) directly to Showdown.
fn push_chance_chain(tree: &mut Tree, closed_state: BettingState, cfg: &FlopTreeConfig) {
    let chance_id = tree.nodes.len();
    tree.nodes.push(Node {
        kind: NodeKind::Chance { child: 0 }, // patched below
        state: closed_state,
        children: Vec::new(),
    });
    let next_state = closed_state.advance_street();
    let child_id = tree.nodes.len();

    if next_state.stacks.contains(&0) {
        // All-in: deal out the remaining streets with no betting.
        if next_state.street == Street::River {
            tree.nodes.push(Node {
                kind: NodeKind::Showdown,
                state: next_state,
                children: Vec::new(),
            });
        } else {
            // Turn dealt all-in on the flop: a second chance node deals
            // the river, then showdown.
            tree.nodes.push(Node {
                kind: NodeKind::Chance { child: 0 }, // patched below
                state: next_state,
                children: Vec::new(),
            });
            let river_state = next_state.advance_runout();
            let sd_id = tree.nodes.len();
            tree.nodes.push(Node {
                kind: NodeKind::Showdown,
                state: river_state,
                children: Vec::new(),
            });
            tree.nodes[child_id].kind = NodeKind::Chance { child: sd_id };
        }
    } else if next_state.street == Street::River {
        tree.nodes.push(Node {
            kind: NodeKind::Action {
                actor: next_state.to_act,
            },
            state: next_state,
            children: Vec::new(),
        });
        expand_street(tree, child_id, &cfg.river);
    } else {
        tree.nodes.push(Node {
            kind: NodeKind::Action {
                actor: next_state.to_act,
            },
            state: next_state,
            children: Vec::new(),
        });
        expand_betting(tree, child_id, cfg);
    }
    tree.nodes[chance_id].kind = NodeKind::Chance { child: child_id };
}
