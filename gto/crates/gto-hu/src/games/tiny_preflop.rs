use crate::game::terminal::fold_payoffs;
use crate::ranges::combo_index;
use crate::solver::{EquityTable, Game};
use crate::tree::{NodeKind, Tree};

/// The preflop `Tree` played with small explicit hand lists and the same
/// injected `EquityTable` as the vector solver — the scalar reference for
/// differential-testing `PreflopSolver`. No chance nodes beyond the deal:
/// `NextStreet` leaves pay equity directly.
pub struct TinyPreflop {
    pub tree: Tree,
    /// hands[p] = player p's combos (0 = SB, 1 = BB).
    pub hands: [Vec<(u8, u8)>; 2],
    eq: EquityTable,
}

#[derive(Debug, Clone)]
pub struct TinyPreflopState {
    /// (index into hands[0], index into hands[1]); usize::MAX = undealt.
    pub deal: (usize, usize),
    pub node: usize,
}

impl TinyPreflop {
    pub fn new(tree: Tree, hands: [Vec<(u8, u8)>; 2], eq: EquityTable) -> Self {
        for hs in &hands {
            for &(a, b) in hs {
                assert!(a != b, "hand cards must be distinct");
            }
        }
        TinyPreflop { tree, hands, eq }
    }
}

impl Game for TinyPreflop {
    type State = TinyPreflopState;

    fn root(&self) -> TinyPreflopState {
        TinyPreflopState {
            deal: (usize::MAX, usize::MAX),
            node: 0,
        }
    }

    fn is_chance(&self, s: &TinyPreflopState) -> bool {
        s.deal.0 == usize::MAX
    }

    fn chance_outcomes(&self, s: &TinyPreflopState) -> Vec<(TinyPreflopState, f64)> {
        debug_assert_eq!(s.deal.0, usize::MAX);
        let mut out = Vec::new();
        for (i, &(a0, b0)) in self.hands[0].iter().enumerate() {
            for (j, &(a1, b1)) in self.hands[1].iter().enumerate() {
                let clash = a0 == a1 || a0 == b1 || b0 == a1 || b0 == b1;
                if !clash {
                    out.push((
                        TinyPreflopState {
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

    fn is_terminal(&self, s: &TinyPreflopState) -> bool {
        s.deal.0 != usize::MAX
            && matches!(
                self.tree.nodes[s.node].kind,
                NodeKind::FoldTerminal { .. } | NodeKind::NextStreet { .. }
            )
    }

    fn payoff(&self, s: &TinyPreflopState, player: usize) -> f64 {
        let node = &self.tree.nodes[s.node];
        match node.kind {
            NodeKind::FoldTerminal { winner } => {
                fold_payoffs(&node.state, winner)[player] as f64 / 100.0
            }
            NodeKind::NextStreet { .. } => {
                let (h0, h1) = (self.hands[0][s.deal.0], self.hands[1][s.deal.1]);
                let (me, opp) = if player == 0 { (h0, h1) } else { (h1, h0) };
                let eq = self.eq.eq(combo_index(me.0, me.1), combo_index(opp.0, opp.1)) as f64;
                let pot = node.state.pot() as f64;
                let contrib = node.state.contrib[player] as f64;
                (eq * pot - contrib) / 100.0
            }
            _ => unreachable!("payoff at non-terminal"),
        }
    }

    fn player(&self, s: &TinyPreflopState) -> usize {
        match self.tree.nodes[s.node].kind {
            NodeKind::Action { actor } => actor as usize,
            _ => unreachable!("player() at non-action node"),
        }
    }

    fn num_actions(&self, s: &TinyPreflopState) -> usize {
        self.tree.nodes[s.node].children.len()
    }

    fn next(&self, s: &TinyPreflopState, action: usize) -> TinyPreflopState {
        TinyPreflopState {
            deal: s.deal,
            node: self.tree.nodes[s.node].children[action].1,
        }
    }

    fn infoset_key(&self, s: &TinyPreflopState) -> String {
        let p = self.player(s);
        let hand_idx = if p == 0 { s.deal.0 } else { s.deal.1 };
        format!("{p}|{hand_idx}|{}", s.node)
    }
}
