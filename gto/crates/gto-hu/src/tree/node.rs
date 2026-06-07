use crate::game::{Action, BettingState};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Action { actor: u8 },
    FoldTerminal { winner: u8 },
    Showdown,
    /// Deal the river card, then continue at `child`. Cards are not
    /// materialized in the tree: the solver enumerates or samples them at
    /// traversal time (design spec §7).
    Chance { child: usize },
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
