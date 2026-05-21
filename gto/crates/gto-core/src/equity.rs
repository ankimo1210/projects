use crate::card::{Card, evaluate, full_deck};
use rand::seq::SliceRandom;
use rand::thread_rng;

pub struct EquityResult {
    pub hero_equity: f64,
    pub villain_equity: f64,
    pub tie: f64,
    pub iterations: u32,
}

/// Monte Carlo equity calculation.
/// hero_cards: 2 hole cards, villain_cards: 2 hole cards, board: 0-5 known cards.
/// Returns equity for hero (0.0 - 1.0).
pub fn monte_carlo(
    hero: &[Card],
    villain: &[Card],
    board: &[Card],
    iterations: u32,
) -> EquityResult {
    let dead: Vec<u8> = hero.iter()
        .chain(villain.iter())
        .chain(board.iter())
        .map(|c| c.0)
        .collect();

    let deck: Vec<Card> = full_deck()
        .into_iter()
        .filter(|c| !dead.contains(&c.0))
        .collect();

    let needed = 5usize.saturating_sub(board.len());
    let mut hero_wins = 0u32;
    let mut villain_wins = 0u32;
    let mut ties = 0u32;
    let mut rng = thread_rng();

    for _ in 0..iterations {
        let runout: Vec<Card> = deck.choose_multiple(&mut rng, needed).copied().collect();
        let mut hero_all = hero.to_vec();
        hero_all.extend_from_slice(board);
        hero_all.extend_from_slice(&runout);
        let mut villain_all = villain.to_vec();
        villain_all.extend_from_slice(board);
        villain_all.extend_from_slice(&runout);

        let h = evaluate(&hero_all);
        let v = evaluate(&villain_all);
        if h > v { hero_wins += 1; }
        else if v > h { villain_wins += 1; }
        else { ties += 1; }
    }

    let total = iterations as f64;
    EquityResult {
        hero_equity: (hero_wins as f64 + ties as f64 * 0.5) / total,
        villain_equity: (villain_wins as f64 + ties as f64 * 0.5) / total,
        tie: ties as f64 / total,
        iterations,
    }
}

/// Parse a space-separated list of card strings like "Ah Kh"
pub fn parse_cards(s: &str) -> Result<Vec<Card>, String> {
    s.split_whitespace()
        .map(|tok| Card::from_str(tok).ok_or_else(|| format!("invalid card: {tok}")))
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn aces_vs_72o_preflop() {
        let hero = parse_cards("Ah As").unwrap();
        let villain = parse_cards("7c 2d").unwrap();
        let result = monte_carlo(&hero, &villain, &[], 10_000);
        assert!(result.hero_equity > 0.80, "AA should be >80% favorite vs 72o");
    }
}
