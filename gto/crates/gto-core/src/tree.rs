/// Multi-street postflop game tree.
///
/// Design:
///   - 2 players, OOP acts first each street
///   - Single bet size per street (50% flop, 75% turn, 75% river)
///   - max 1 raise per street (bet → raise → call/fold)
///   - After call or both-check: NextStreet on flop/turn, Showdown on river
///
/// The tree is a template for one street's action structure.
/// MultiStreetSolver uses three copies (one per street), iterating over
/// all 49 turn cards and 48 river cards in the CFR traversal.

// ---------------------------------------------------------------------------
// Street
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Street {
    Flop,
    Turn,
    River,
}

impl Street {
    /// Single bet size (% of pot) for this street.
    pub fn bet_pct(self) -> u8 {
        match self {
            Street::Flop  => 50,
            Street::Turn  => 75,
            Street::River => 75,
        }
    }

    pub fn next(self) -> Option<Street> {
        match self {
            Street::Flop  => Some(Street::Turn),
            Street::Turn  => Some(Street::River),
            Street::River => None,
        }
    }
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Action {
    Fold,
    Check,
    Call,
    Bet,    // single size: street.bet_pct()
    Raise,  // single size: 2.5x previous bet
}

// ---------------------------------------------------------------------------
// Nodes
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum NodeKind {
    /// A player decides an action.
    Action { actor: u8 },
    /// Fold: pot to winner.
    FoldTerminal { winner: u8 },
    /// End of street action: deal next card (flop/turn).
    NextStreet,
    /// River showdown: evaluate hands.
    Showdown,
}

#[derive(Debug, Clone)]
pub struct Node {
    pub kind:        NodeKind,
    pub pot:         i64,   // chips × 100 for precision
    pub stacks:      [i64; 2],
    pub street_bets: [i64; 2],
    pub bet_count:   u8,
    pub children:    Vec<(Action, usize)>,
}

// ---------------------------------------------------------------------------
// GameTree — single-street action template
// ---------------------------------------------------------------------------

pub struct GameTree {
    pub nodes: Vec<Node>,
}

impl GameTree {
    /// Build the action tree for one street.
    /// `street` determines the bet size and whether call/both-check → NextStreet or Showdown.
    pub fn build(pot: i64, effective_stack: i64, street: Street) -> Self {
        let mut tree = GameTree { nodes: Vec::new() };
        let root = Node {
            kind:        NodeKind::Action { actor: 0 },
            pot,
            stacks:      [effective_stack; 2],
            street_bets: [0; 2],
            bet_count:   0,
            children:    Vec::new(),
        };
        tree.nodes.push(root);
        tree.expand(0, street);
        tree
    }

    fn end_of_street_node(&mut self, street: Street, from: &Node) -> usize {
        let kind = if street.next().is_some() {
            NodeKind::NextStreet
        } else {
            NodeKind::Showdown
        };
        self.add_terminal(kind, from)
    }

    fn expand(&mut self, node_id: usize, street: Street) {
        let node = self.nodes[node_id].clone();
        let NodeKind::Action { actor } = node.kind else { return };
        let opponent = 1 - actor;
        let bet_pct  = street.bet_pct() as i64;

        let facing_bet = node.street_bets[opponent as usize] > node.street_bets[actor as usize];
        let mut children: Vec<(Action, usize)> = Vec::new();

        if facing_bet {
            // Fold
            let fold_id = self.add_terminal(NodeKind::FoldTerminal { winner: opponent }, &node);
            children.push((Action::Fold, fold_id));

            // Call
            let call_amt = (node.street_bets[opponent as usize] - node.street_bets[actor as usize])
                .min(node.stacks[actor as usize]);
            let mut call_node = node.clone();
            call_node.stacks[actor as usize]      -= call_amt;
            call_node.pot                         += call_amt;
            call_node.street_bets[actor as usize] += call_amt;
            let call_id = self.end_of_street_node(street, &call_node);
            children.push((Action::Call, call_id));

            // Raise (at most 1 raise per street: bet_count < 2)
            if node.bet_count < 2 {
                let raise_base   = node.street_bets[opponent as usize];
                // 2.5x the current bet, relative to pot
                let raise_total  = (raise_base as f64 * 2.5) as i64;
                let raise_amt    = (raise_total - node.street_bets[actor as usize])
                    .min(node.stacks[actor as usize]);
                if raise_amt > 0 {
                    let mut raise_node                     = node.clone();
                    raise_node.stacks[actor as usize]     -= raise_amt;
                    raise_node.pot                        += raise_amt;
                    raise_node.street_bets[actor as usize] += raise_amt;
                    raise_node.bet_count                  += 1;
                    raise_node.kind = NodeKind::Action { actor: opponent };
                    raise_node.children = Vec::new();
                    let raise_id = self.nodes.len();
                    self.nodes.push(raise_node);
                    self.expand(raise_id, street);
                    children.push((Action::Raise, raise_id));
                }
            }
        } else {
            // Check
            if actor == 0 {
                // OOP checked; IP to act
                let mut check_node  = node.clone();
                check_node.kind     = NodeKind::Action { actor: 1 };
                check_node.children = Vec::new();
                let check_id = self.nodes.len();
                self.nodes.push(check_node);
                self.expand(check_id, street);
                children.push((Action::Check, check_id));
            } else {
                // Both checked → end of street
                let check_id = self.end_of_street_node(street, &node);
                children.push((Action::Check, check_id));
            }

            // Bet (at most 1 bet without prior bet: bet_count == 0)
            if node.bet_count < 2 {
                let bet_amt = (node.pot * bet_pct / 100).min(node.stacks[actor as usize]);
                if bet_amt > 0 {
                    let mut bet_node                     = node.clone();
                    bet_node.stacks[actor as usize]     -= bet_amt;
                    bet_node.pot                        += bet_amt;
                    bet_node.street_bets[actor as usize] += bet_amt;
                    bet_node.bet_count                  += 1;
                    bet_node.kind = NodeKind::Action { actor: opponent };
                    bet_node.children = Vec::new();
                    let bet_id = self.nodes.len();
                    self.nodes.push(bet_node);
                    self.expand(bet_id, street);
                    children.push((Action::Bet, bet_id));
                }
            }
        }

        self.nodes[node_id].children = children;
    }

    fn add_terminal(&mut self, kind: NodeKind, from: &Node) -> usize {
        let id = self.nodes.len();
        self.nodes.push(Node {
            kind,
            pot:         from.pot,
            stacks:      from.stacks,
            street_bets: from.street_bets,
            bet_count:   from.bet_count,
            children:    Vec::new(),
        });
        id
    }

    /// Return (action_node_count, nextstreet_count, showdown_count, fold_count)
    pub fn stats(&self) -> (usize, usize, usize, usize) {
        let mut action = 0; let mut next = 0; let mut sd = 0; let mut fold = 0;
        for n in &self.nodes {
            match n.kind {
                NodeKind::Action     { .. } => action += 1,
                NodeKind::NextStreet        => next   += 1,
                NodeKind::Showdown          => sd     += 1,
                NodeKind::FoldTerminal { .. }=> fold  += 1,
            }
        }
        (action, next, sd, fold)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flop_tree_structure() {
        let t = GameTree::build(650, 9700, Street::Flop);
        let (action, next, sd, fold) = t.stats();
        println!("flop: total={} action={} next={} sd={} fold={}", t.nodes.len(), action, next, sd, fold);
        assert!(action > 0);
        assert!(next  > 0, "flop must have NextStreet nodes");
        assert_eq!(sd, 0,  "flop must have no Showdown nodes");
    }

    #[test]
    fn river_tree_structure() {
        let t = GameTree::build(650, 9700, Street::River);
        let (action, next, sd, fold) = t.stats();
        println!("river: total={} action={} next={} sd={} fold={}", t.nodes.len(), action, next, sd, fold);
        assert_eq!(next, 0, "river must have no NextStreet nodes");
        assert!(sd > 0,     "river must have Showdown nodes");
    }

    #[test]
    fn all_streets_have_same_shape() {
        for street in [Street::Flop, Street::Turn, Street::River] {
            let t = GameTree::build(650, 9700, street);
            let (act, _, _, _) = t.stats();
            println!("{:?}: {} total, {} action nodes", street, t.nodes.len(), act);
            assert!(act >= 5);
        }
    }
}
