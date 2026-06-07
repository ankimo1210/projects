use gto_core::eval::evaluate_best;

use crate::game::terminal::{fold_payoffs, showdown_payoffs};
use crate::game::Street;
use crate::solver::Game;
use crate::tree::{NodeKind, Tree};

/// The flop+turn+river `Tree` played with small explicit hand lists and
/// explicitly dealt turn and river cards — the scalar reference for
/// differential-testing the vector flop solver. Chance stages: deal hands,
/// deal turn (45 cards off flop + 4 hole), deal river (44 cards).
pub struct TinyFlopTurnRiver {
    pub tree: Tree,
    pub flop_board: [u8; 3],
    /// hands[p] = player p's combos, all distinct from the board.
    /// Player indices match the tree (0 = SB/IP, 1 = BB/OOP).
    pub hands: [Vec<(u8, u8)>; 2],
}

#[derive(Debug, Clone)]
pub struct TinyFlopTurnRiverState {
    /// (index into hands[0], index into hands[1]); usize::MAX = undealt.
    pub deal: (usize, usize),
    /// Dealt turn card; None while still on the flop.
    pub turn: Option<u8>,
    /// Dealt river card; None until the river chance node resolves.
    pub river: Option<u8>,
    pub node: usize,
}

impl TinyFlopTurnRiver {
    pub fn new(tree: Tree, flop_board: [u8; 3], hands: [Vec<(u8, u8)>; 2]) -> Self {
        for hs in &hands {
            for &(a, b) in hs {
                assert!(
                    a != b && !flop_board.contains(&a) && !flop_board.contains(&b),
                    "hand cards must be distinct and off-board"
                );
            }
        }
        TinyFlopTurnRiver {
            tree,
            flop_board,
            hands,
        }
    }

    fn strength(&self, hand: (u8, u8), turn: u8, river: u8) -> u16 {
        let mut cards = [0u8; 7];
        cards[0] = hand.0;
        cards[1] = hand.1;
        cards[2..5].copy_from_slice(&self.flop_board);
        cards[5] = turn;
        cards[6] = river;
        evaluate_best(&cards)
    }

    fn dead_cards(&self, s: &TinyFlopTurnRiverState) -> Vec<u8> {
        let (a0, b0) = self.hands[0][s.deal.0];
        let (a1, b1) = self.hands[1][s.deal.1];
        let mut dead = vec![a0, b0, a1, b1];
        dead.extend_from_slice(&self.flop_board);
        if let Some(t) = s.turn {
            dead.push(t);
        }
        dead
    }
}

impl Game for TinyFlopTurnRiver {
    type State = TinyFlopTurnRiverState;

    fn root(&self) -> TinyFlopTurnRiverState {
        TinyFlopTurnRiverState {
            deal: (usize::MAX, usize::MAX),
            turn: None,
            river: None,
            node: 0,
        }
    }

    fn is_chance(&self, s: &TinyFlopTurnRiverState) -> bool {
        s.deal.0 == usize::MAX || matches!(self.tree.nodes[s.node].kind, NodeKind::Chance { .. })
    }

    fn chance_outcomes(&self, s: &TinyFlopTurnRiverState) -> Vec<(TinyFlopTurnRiverState, f64)> {
        if s.deal.0 == usize::MAX {
            // Deal both hands: uniform over non-clashing pairs.
            let mut out = Vec::new();
            for (i, &(a0, b0)) in self.hands[0].iter().enumerate() {
                for (j, &(a1, b1)) in self.hands[1].iter().enumerate() {
                    let clash = a0 == a1 || a0 == b1 || b0 == a1 || b0 == b1;
                    if !clash {
                        out.push((
                            TinyFlopTurnRiverState {
                                deal: (i, j),
                                turn: None,
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
            return out;
        }
        let NodeKind::Chance { child } = self.tree.nodes[s.node].kind else {
            unreachable!("chance_outcomes at a non-chance node");
        };
        // The chance node's own state street says which card it deals:
        // a closed flop deals the turn, a closed turn deals the river.
        let deal_street = self.tree.nodes[s.node].state.street;
        let dead = self.dead_cards(s);
        let cards: Vec<u8> = (0..52u8).filter(|c| !dead.contains(c)).collect();
        let p = 1.0 / cards.len() as f64;
        cards
            .into_iter()
            .map(|card| {
                let (turn, river) = match deal_street {
                    Street::Flop => (Some(card), None),
                    Street::Turn => (s.turn, Some(card)),
                    st => unreachable!("chance node on {st:?}"),
                };
                (
                    TinyFlopTurnRiverState {
                        deal: s.deal,
                        turn,
                        river,
                        node: child,
                    },
                    p,
                )
            })
            .collect()
    }

    fn is_terminal(&self, s: &TinyFlopTurnRiverState) -> bool {
        s.deal.0 != usize::MAX
            && matches!(
                self.tree.nodes[s.node].kind,
                NodeKind::FoldTerminal { .. } | NodeKind::Showdown
            )
    }

    fn payoff(&self, s: &TinyFlopTurnRiverState, player: usize) -> f64 {
        let node = &self.tree.nodes[s.node];
        let cbb = match node.kind {
            NodeKind::FoldTerminal { winner } => fold_payoffs(&node.state, winner)[player],
            NodeKind::Showdown => {
                let turn = s.turn.expect("showdown requires a dealt turn");
                let river = s.river.expect("showdown requires a dealt river");
                let s0 = self.strength(self.hands[0][s.deal.0], turn, river);
                let s1 = self.strength(self.hands[1][s.deal.1], turn, river);
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

    fn player(&self, s: &TinyFlopTurnRiverState) -> usize {
        match self.tree.nodes[s.node].kind {
            NodeKind::Action { actor } => actor as usize,
            _ => unreachable!("player() at non-action node"),
        }
    }

    fn num_actions(&self, s: &TinyFlopTurnRiverState) -> usize {
        self.tree.nodes[s.node].children.len()
    }

    fn next(&self, s: &TinyFlopTurnRiverState, action: usize) -> TinyFlopTurnRiverState {
        TinyFlopTurnRiverState {
            deal: s.deal,
            turn: s.turn,
            river: s.river,
            node: self.tree.nodes[s.node].children[action].1,
        }
    }

    fn infoset_key(&self, s: &TinyFlopTurnRiverState) -> String {
        let p = self.player(s);
        let hand_idx = if p == 0 { s.deal.0 } else { s.deal.1 };
        // node id encodes the betting history; turn/river cards are public.
        let t = s.turn.map_or("-".to_string(), |c| c.to_string());
        let r = s.river.map_or("-".to_string(), |c| c.to_string());
        format!("{p}|{hand_idx}|{}|{t}|{r}", s.node)
    }
}
