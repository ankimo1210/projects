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
        s.deal.0 == usize::MAX || matches!(self.tree.nodes[s.node].kind, NodeKind::Chance { .. })
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
                    !self.turn_board.contains(c) && *c != a0 && *c != b0 && *c != a1 && *c != b1
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
