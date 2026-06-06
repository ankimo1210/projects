use gto_core::eval::evaluate_best;

use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::solver::Game;
use crate::tree::{NodeKind, Tree};

/// The river `Tree` played with small explicit hand lists — a scalar
/// reference game for differential-testing the vector solver.
pub struct TinyRiver {
    pub tree: Tree,
    pub board: [u8; 5],
    /// hands[p] = player p's combos (card_a, card_b), all distinct from the
    /// board. Player indices match the tree (0 = SB/IP, 1 = BB/OOP).
    pub hands: [Vec<(u8, u8)>; 2],
}

#[derive(Debug, Clone)]
pub struct TinyRiverState {
    /// (index into hands[0], index into hands[1]); usize::MAX = undealt.
    pub deal: (usize, usize),
    pub node: usize,
}

impl TinyRiver {
    pub fn new(tree: Tree, board: [u8; 5], hands: [Vec<(u8, u8)>; 2]) -> Self {
        for hs in &hands {
            for &(a, b) in hs {
                assert!(
                    a != b && !board.contains(&a) && !board.contains(&b),
                    "hand cards must be distinct and off-board"
                );
            }
        }
        TinyRiver { tree, board, hands }
    }

    fn strength(&self, hand: (u8, u8)) -> u16 {
        let mut cards = [0u8; 7];
        cards[0] = hand.0;
        cards[1] = hand.1;
        cards[2..7].copy_from_slice(&self.board);
        evaluate_best(&cards)
    }
}

impl Game for TinyRiver {
    type State = TinyRiverState;

    fn root(&self) -> TinyRiverState {
        TinyRiverState {
            deal: (usize::MAX, usize::MAX),
            node: 0,
        }
    }

    fn is_chance(&self, s: &TinyRiverState) -> bool {
        s.deal.0 == usize::MAX
    }

    fn chance_outcomes(&self, s: &TinyRiverState) -> Vec<(TinyRiverState, f64)> {
        let mut out = Vec::new();
        for (i, &(a0, b0)) in self.hands[0].iter().enumerate() {
            for (j, &(a1, b1)) in self.hands[1].iter().enumerate() {
                let clash = a0 == a1 || a0 == b1 || b0 == a1 || b0 == b1;
                if !clash {
                    out.push((
                        TinyRiverState {
                            deal: (i, j),
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
    }

    fn is_terminal(&self, s: &TinyRiverState) -> bool {
        !self.is_chance(s)
            && matches!(
                self.tree.nodes[s.node].kind,
                NodeKind::FoldTerminal { .. } | NodeKind::Showdown
            )
    }

    fn payoff(&self, s: &TinyRiverState, player: usize) -> f64 {
        let node = &self.tree.nodes[s.node];
        let cbb = match node.kind {
            NodeKind::FoldTerminal { winner } => fold_payoffs(&node.state, winner)[player],
            NodeKind::Showdown => {
                let s0 = self.strength(self.hands[0][s.deal.0]);
                let s1 = self.strength(self.hands[1][s.deal.1]);
                let winner = match s0.cmp(&s1) {
                    std::cmp::Ordering::Greater => Some(0),
                    std::cmp::Ordering::Less => Some(1),
                    std::cmp::Ordering::Equal => None,
                };
                showdown_payoffs(&node.state, winner)[player]
            }
            NodeKind::Action { .. } => unreachable!("payoff at non-terminal"),
        };
        cbb as f64 / 100.0 // bb
    }

    fn player(&self, s: &TinyRiverState) -> usize {
        match self.tree.nodes[s.node].kind {
            NodeKind::Action { actor } => actor as usize,
            _ => unreachable!("player() at non-action node"),
        }
    }

    fn num_actions(&self, s: &TinyRiverState) -> usize {
        self.tree.nodes[s.node].children.len()
    }

    fn next(&self, s: &TinyRiverState, action: usize) -> TinyRiverState {
        TinyRiverState {
            deal: s.deal,
            node: self.tree.nodes[s.node].children[action].1,
        }
    }

    fn infoset_key(&self, s: &TinyRiverState) -> String {
        let p = self.player(s);
        let hand_idx = if p == 0 { s.deal.0 } else { s.deal.1 };
        // node id encodes the full betting history (tree is fixed).
        format!("{p}|{hand_idx}|{}", s.node)
    }
}
