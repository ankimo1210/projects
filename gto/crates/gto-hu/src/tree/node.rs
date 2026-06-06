use crate::game::{Action, BettingState};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NodeKind {
    Action { actor: u8 },
    FoldTerminal { winner: u8 },
    Showdown,
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
