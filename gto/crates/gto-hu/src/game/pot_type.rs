/// Postflop pot category, set by the preflop line (Phase 5).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum PotType {
    Limped,
    Srp,
    ThreeBet,
    FourBet,
    AllInPreflop,
}
