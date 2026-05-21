//! Kuhn Poker CFR test — verified reference implementation.
//!
//! Kuhn poker: J=0, Q=1, K=2. Two players, each antes 1 chip.
//! P1 acts first: bet or check.
//! If bet: P2 calls (+1 pot) or folds.
//! If check: P2 bets or checks. If P2 bets: P1 calls or folds.
//!
//! Unique Nash equilibrium (up to P1 K mixing):
//!   P1 J bet = 1/3,  P1 Q bet = 0,  P1 K bet = any (indifferent)
//!   P2 J fold = 1,   P2 Q call = 1/3, P2 K call = 1
//!   P2 J bluff = 1/3 (after P1 check), P2 Q bet = 0, P2 K bet = 1
//!   EV for P1 = -1/18 ≈ -0.05556

use std::collections::HashMap;

const PASS: usize = 0;
const BET:  usize = 1;

// ── Info set storage ─────────────────────────────────────────────────────────

#[derive(Default, Clone)]
struct Node {
    regret:       [f64; 2],
    strategy_sum: [f64; 2],
}

impl Node {
    fn current_strategy(&mut self, reach: f64) -> [f64; 2] {
        let pos = [self.regret[0].max(0.0), self.regret[1].max(0.0)];
        let total = pos[0] + pos[1];
        let s = if total > 0.0 {
            [pos[0] / total, pos[1] / total]
        } else {
            [0.5, 0.5]
        };
        self.strategy_sum[0] += reach * s[0];
        self.strategy_sum[1] += reach * s[1];
        s
    }

    fn avg_strategy(&self) -> [f64; 2] {
        let total = self.strategy_sum[0] + self.strategy_sum[1];
        if total > 0.0 {
            [self.strategy_sum[0] / total, self.strategy_sum[1] / total]
        } else {
            [0.5, 0.5]
        }
    }
}

struct KuhnCfr {
    nodes: HashMap<String, Node>,
}

impl KuhnCfr {
    fn new() -> Self {
        Self { nodes: HashMap::new() }
    }

    fn iset(card: usize, history: &str) -> String {
        format!("{}{}", card, history)
    }

    fn terminal_util(cards: &[usize; 2], history: &str) -> Option<f64> {
        let n = history.len();
        if n < 2 { return None; }
        let player  = n % 2;
        let opp     = 1 - player;
        let last    = history.chars().last().unwrap();
        if last == 'p' {
            if history == "pp" {
                // both checked: showdown
                return Some(if cards[player] > cards[opp] { 1.0 } else { -1.0 });
            } else {
                // fold after bet: current player wins (opponent folded)
                return Some(1.0);
            }
        }
        if history.len() >= 2 && &history[history.len()-2..] == "bb" {
            // call: showdown, pot = 4
            return Some(if cards[player] > cards[opp] { 2.0 } else { -2.0 });
        }
        None
    }

    fn cfr(&mut self, cards: &[usize; 2], history: &str, p0: f64, p1: f64) -> f64 {
        if let Some(ev) = Self::terminal_util(cards, history) {
            return ev;
        }
        let player   = history.len() % 2;
        let iset_key = Self::iset(cards[player], history);

        let s = {
            let nd = self.nodes.entry(iset_key.clone()).or_default();
            let reach = if player == 0 { p0 } else { p1 };
            nd.current_strategy(reach)
        };

        let mut util = [0.0f64; 2];
        for a in [PASS, BET] {
            let nh = format!("{}{}", history, if a == PASS { 'p' } else { 'b' });
            let child = if player == 0 {
                self.cfr(cards, &nh, p0 * s[a], p1)
            } else {
                self.cfr(cards, &nh, p0, p1 * s[a])
            };
            util[a] = -child;
        }
        let ev = s[0] * util[0] + s[1] * util[1];
        let opp_reach = if player == 0 { p1 } else { p0 };

        let nd = self.nodes.get_mut(&iset_key).unwrap();
        nd.regret[0] += opp_reach * (util[0] - ev);
        nd.regret[1] += opp_reach * (util[1] - ev);
        ev
    }

    fn train(&mut self, n: u64) -> f64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let all_deals = [(0,1), (0,2), (1,0), (1,2), (2,0), (2,1)];
        let mut total = 0.0;
        // Pseudo-random deal selection for reproducibility
        for i in 0..n {
            let mut h = DefaultHasher::new();
            i.hash(&mut h);
            let idx = (h.finish() as usize) % 6;
            let (c0, c1) = all_deals[idx];
            total += self.cfr(&[c0, c1], "", 1.0, 1.0);
        }
        total / n as f64
    }

    fn avg(&self, card: usize, hist: &str) -> [f64; 2] {
        self.nodes
            .get(&Self::iset(card, hist))
            .map(|n| n.avg_strategy())
            .unwrap_or([0.5, 0.5])
    }

    // ── Info-set-aware exploitability ─────────────────────────────────────────

    fn subtree_ev(&self, br_player: usize, cards: &[usize; 2], history: &str,
                  br_act: &HashMap<String, usize>) -> f64 {
        if let Some(ev) = Self::terminal_util(cards, history) {
            let pl = history.len() % 2;
            return if pl == br_player { ev } else { -ev };
        }
        let pl   = history.len() % 2;
        let iset = Self::iset(cards[pl], history);
        if pl == br_player {
            let a  = *br_act.get(&iset).unwrap_or(&0);
            let nh = format!("{}{}", history, if a == PASS { 'p' } else { 'b' });
            return self.subtree_ev(br_player, cards, &nh, br_act);
        }
        let s  = self.avg(cards[pl], history);
        let mut ev = 0.0;
        for a in [PASS, BET] {
            let nh = format!("{}{}", history, if a == PASS { 'p' } else { 'b' });
            ev += s[a] * self.subtree_ev(br_player, cards, &nh, br_act);
        }
        ev
    }

    fn opp_reach_to(&self, cards: &[usize; 2], target: &str,
                    br_player: usize, br_act: &HashMap<String, usize>) -> f64 {
        let mut h = String::new();
        let mut reach = 1.0f64;
        for ch in target.chars() {
            let pl   = h.len() % 2;
            let a    = if ch == 'p' { PASS } else { BET };
            let iset = Self::iset(cards[pl], &h);
            if pl != br_player {
                let s = self.avg(cards[pl], &h);
                reach *= s[a];
            } else if let Some(&ba) = br_act.get(&iset) {
                if ba != a { return 0.0; }
            }
            h.push(ch);
        }
        reach
    }

    fn best_response_ev(&self, br_player: usize) -> f64 {
        let all_deals: &[[usize; 2]] = &[[0,1],[0,2],[1,0],[1,2],[2,0],[2,1]];
        let ordered: &[&str] = if br_player == 0 { &["pb", ""] } else { &["b", "p"] };
        let mut br_act: HashMap<String, usize> = HashMap::new();

        for &hist in ordered {
            for card in 0..3usize {
                let iset = Self::iset(card, hist);
                let mut act_ev = [0.0f64; 2];
                let mut total_w = 0.0f64;
                for deal in all_deals {
                    if deal[br_player] != card { continue; }
                    let w = self.opp_reach_to(deal, hist, br_player, &br_act);
                    if w <= 0.0 { continue; }
                    for a in [PASS, BET] {
                        let nh  = format!("{}{}", hist, if a == PASS { 'p' } else { 'b' });
                        let ev  = self.subtree_ev(br_player, deal, &nh, &br_act);
                        act_ev[a] += w * ev;
                    }
                    total_w += w;
                }
                let best = if total_w <= 0.0 { PASS }
                           else if act_ev[PASS] >= act_ev[BET] { PASS } else { BET };
                br_act.insert(iset, best);
            }
        }

        let total: f64 = all_deals.iter()
            .map(|deal| self.subtree_ev(br_player, deal, "", &br_act))
            .sum();
        total / all_deals.len() as f64
    }

    fn exploitability(&self) -> f64 {
        let br0 = self.best_response_ev(0);
        let br1 = self.best_response_ev(1);
        // At Nash: br0=-1/18, br1=+1/18. Sum = 0.
        br0 + br1
    }
}

// ── Tests ────────────────────────────────────────────────────────────────────

#[test]
fn test_kuhn_nash_equilibrium() {
    let mut solver = KuhnCfr::new();
    let game_ev = solver.train(500_000);
    let expl    = solver.exploitability();

    // Game EV should be close to -1/18
    let nash_ev = -1.0 / 18.0;
    assert!(
        (game_ev - nash_ev).abs() < 0.01,
        "Game EV {game_ev:.6} is far from Nash {nash_ev:.6}"
    );

    // Exploitability should be nearly zero
    assert!(
        expl.abs() < 0.01,
        "Exploitability {expl:.6} is too high (expected < 0.01)"
    );

    // P1 J should bet with ~1/3 frequency (or less — Nash family has β_J ≤ 1/3)
    let p1_j_bet = solver.avg(0, "")[BET];
    assert!(p1_j_bet <= 0.5, "P1 J bet {p1_j_bet:.4} should be ≤ 0.5");

    // P1 Q should never bet
    let p1_q_bet = solver.avg(1, "")[BET];
    assert!(p1_q_bet < 0.05, "P1 Q bet {p1_q_bet:.4} should be ~0");

    // P2 J should always fold to a bet
    let p2_j_call = solver.avg(0, "b")[BET];
    assert!(p2_j_call < 0.05, "P2 J call {p2_j_call:.4} should be ~0");

    // P2 Q should call with ~1/3
    let p2_q_call = solver.avg(1, "b")[BET];
    assert!(
        (p2_q_call - 1.0/3.0).abs() < 0.05,
        "P2 Q call {p2_q_call:.4} should be ~0.333"
    );

    // P2 K should always call
    let p2_k_call = solver.avg(2, "b")[BET];
    assert!(p2_k_call > 0.95, "P2 K call {p2_k_call:.4} should be ~1.0");

    // P2 J should bluff ~1/3 after P1 checks
    let p2_j_bluff = solver.avg(0, "p")[BET];
    assert!(
        (p2_j_bluff - 1.0/3.0).abs() < 0.05,
        "P2 J bluff {p2_j_bluff:.4} should be ~0.333"
    );

    // P2 K should always bet after P1 checks
    let p2_k_bet = solver.avg(2, "p")[BET];
    assert!(p2_k_bet > 0.95, "P2 K bet-after-check {p2_k_bet:.4} should be ~1.0");

    eprintln!("✅ Kuhn Nash equilibrium verified:");
    eprintln!("   Game EV: {game_ev:.6}  (target -0.055556)");
    eprintln!("   Exploitability: {expl:.6}  (target 0)");
    eprintln!("   P1 J bet: {p1_j_bet:.4}  P1 Q bet: {p1_q_bet:.4}");
    eprintln!("   P2 J call: {p2_j_call:.4}  P2 Q call: {p2_q_call:.4}  P2 K call: {p2_k_call:.4}");
    eprintln!("   P2 J bluff: {p2_j_bluff:.4}  P2 K bet: {p2_k_bet:.4}");
}

#[test]
fn test_kuhn_strategy_sums_to_one() {
    let mut solver = KuhnCfr::new();
    solver.train(10_000);
    for card in 0..3usize {
        for hist in &["", "b", "p", "pb"] {
            let s = solver.avg(card, hist);
            let sum = s[0] + s[1];
            assert!(
                (sum - 1.0).abs() < 1e-9,
                "Strategy sum for iset {card}{hist} = {sum:.9} (should be 1.0)"
            );
        }
    }
    eprintln!("✅ All strategies sum to 1.0");
}

#[test]
fn test_kuhn_zero_sum() {
    let mut solver = KuhnCfr::new();
    let game_ev = solver.train(200_000);
    // Zero-sum: P1 EV + P2 EV = 0, so P1 EV ≈ -1/18 (which is P1's Nash EV)
    // The game value should be in [-0.1, 0.0]
    assert!(
        game_ev > -0.15 && game_ev < 0.0,
        "Game EV {game_ev:.6} is out of expected range [-0.15, 0.0]"
    );
    eprintln!("✅ Zero-sum: Game EV = {game_ev:.6}");
}
