use crate::game::{Action, BettingState, PotType};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Action {
        actor: u8,
    },
    FoldTerminal {
        winner: u8,
    },
    Showdown,
    /// Deal the river card, then continue at `child`. Cards are not
    /// materialized in the tree: the solver enumerates or samples them at
    /// traversal time (design spec §7).
    Chance {
        child: usize,
    },
    /// Preflop betting closed without a fold: play continues on the flop
    /// in a pot of the tagged type (spec §6). A leaf in the standalone
    /// preflop tree (Phase 5); the full blueprint (Phase 6) replaces it
    /// with the postflop subtree.
    NextStreet {
        pot_type: PotType,
    },
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
