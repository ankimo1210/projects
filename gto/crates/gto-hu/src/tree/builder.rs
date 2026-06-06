use crate::game::{Action, BettingState};
use super::config::{RaiseRule, StreetConfig};
use super::node::{Node, NodeKind, Tree};

/// Build the river action tree. OOP (BB) acts first.
pub fn build_river_tree(pot: i64, stack: i64, cfg: &StreetConfig) -> Tree {
    cfg.validate();
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
                    debug_assert!(
                        target > state.street_committed[opp],
                        "raise target must exceed facing total"
                    );
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
                let to = state.pot() * pct as i64 / 100;
                if to == 0 {
                    continue; // sub-chip size on a degenerate pot: skip, don't warp
                }
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
