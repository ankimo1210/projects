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
            if river_state.stacks.contains(&0) {
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
