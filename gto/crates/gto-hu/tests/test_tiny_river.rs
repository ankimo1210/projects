use gto_core::eval::parse_card;
use gto_hu::game::BB;
use gto_hu::games::TinyRiver;
use gto_hu::solver::{CfrVariant, Game, ScalarCfr};
use gto_hu::tree::{build_river_tree, StreetConfig};
use gto_hu::validation::exploitability;

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn nuts_vs_bluffcatcher() -> TinyRiver {
    // Board 2c 7d 9h Jh Kd: QT = nut straight, no flush possible.
    let board = [c("2c"), c("7d"), c("9h"), c("Jh"), c("Kd")];
    let tree = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    // hands[0] = player 0 (SB/IP); hands[1] = player 1 (BB/OOP).
    // Deviation from plan: plan listed OOP first, but TinyRiver indexes
    // hands by player number (0=IP, 1=OOP), so we swap the order here.
    TinyRiver::new(
        tree,
        board,
        [
            vec![(c("Kh"), c("Qh"))], // IP: bluff catcher (player 0, SB)
            vec![(c("Qc"), c("Tc")), (c("4s"), c("3s"))], // OOP: nuts or air  (player 1, BB)
        ],
    )
}

#[test]
fn chance_outcomes_are_uniform_and_card_safe() {
    let g = nuts_vs_bluffcatcher();
    let deals = g.chance_outcomes(&g.root());
    assert_eq!(
        deals.len(),
        2,
        "2 OOP hands × 1 IP hand, no blocker overlap"
    );
    let total: f64 = deals.iter().map(|(_, p)| p).sum();
    assert!((total - 1.0).abs() < 1e-12);
}

#[test]
fn polarized_oop_bets_nuts_and_solver_converges() {
    let g = nuts_vs_bluffcatcher();
    // Deviation from plan: plan specified 5_000 iters, but this deeper-stack
    // spot (pot=20bb, stack=90bb, four bet sizes) converges at O(1/T) and
    // needs ~10_000 iters for CFR+ average strategy to reach 0.05 bb.
    // The plan's convergence estimate was optimistic for this game geometry.
    let mut cfr = ScalarCfr::new(&g, CfrVariant::cfr_plus_default());
    cfr.run(10_000);
    let expl = exploitability(&g, &cfr);
    eprintln!("exploitability: {expl:.5} bb");
    assert!(expl < 0.05, "exploitability {expl:.4} bb should be < 0.05");
    // OOP root infoset for the nuts (hand index 0), root node id 0.
    // Actions: [check, bet15, bet30, allin90] — nuts must rarely check.
    let s = cfr.average_strategy("1|0|0", 4);
    assert!(s[0] < 0.05, "nuts check freq {} should be ~0", s[0]);
}

#[test]
fn zero_sum_at_every_terminal() {
    let g = nuts_vs_bluffcatcher();
    // Walk the whole game; at terminals payoffs must sum to 0.
    fn walk(g: &TinyRiver, s: &<TinyRiver as Game>::State) {
        if g.is_terminal(s) {
            let p0 = g.payoff(s, 0);
            let p1 = g.payoff(s, 1);
            assert!((p0 + p1).abs() < 1e-9, "not zero-sum: {p0} + {p1}");
            return;
        }
        if g.is_chance(s) {
            for (cs, _) in g.chance_outcomes(s) {
                walk(g, &cs);
            }
            return;
        }
        for a in 0..g.num_actions(s) {
            walk(g, &g.next(s, a));
        }
    }
    walk(&g, &g.root());
}
