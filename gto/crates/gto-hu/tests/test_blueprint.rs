//! Blueprint composition tests (blueprint design §6). Assertions are
//! exact-equality or adversarial-fixture based — budget-form |Δv| ≤
//! ε₁+ε₂ checks are tautologies and banned as primary assertions.

use gto_core::eval::{evaluate_best, parse_card};
use gto_hu::game::{Action, BettingState, PotType, BB};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{
    Abstraction, BlueprintSolver, CfrVariant, ChanceMode, FlopSolver,
};
use gto_hu::tree::{
    build_flop_tree, build_preflop_tree, FlopTreeConfig, Node, NodeKind, RaiseRule, StreetConfig,
    Tree,
};

fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

/// Tiny subgame config: river is the only decision street, so even
/// enumerated composed runs stay affordable.
fn tiny_cfg(_pot: PotType) -> FlopTreeConfig {
    let simple = |pcts: Vec<u32>| StreetConfig {
        bet_pcts: pcts,
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    FlopTreeConfig {
        flop: simple(vec![]),
        turn: simple(vec![]),
        river: simple(vec![100]),
    }
}

fn tiny_ranges() -> [Range; 2] {
    let mut r0 = Range::new_empty();
    let mut r1 = Range::new_empty();
    r0.weights[combo_index(c("Qc"), c("Tc"))] = 1.0;
    r0.weights[combo_index(c("Ah"), c("Ad"))] = 1.0;
    r1.weights[combo_index(c("Kh"), c("Qh"))] = 1.0;
    r1.weights[combo_index(c("8s"), c("8d"))] = 1.0;
    [r0, r1]
}

/// Degenerate preflop tree: SB raise-to-10bb (forced) → BB call
/// (forced) → NextStreet(Srp) at pot 20bb / stack 90bb.
fn forced_line_tree() -> Tree {
    let root_state = BettingState::preflop_root(100 * BB);
    let raise = Action::Raise { to: 10 * BB };
    let s1 = root_state.apply(raise);
    let s2 = s1.apply(Action::Call);
    assert!(s2.street_closed());
    assert_eq!(s2.pot(), 20 * BB);
    assert_eq!(s2.stacks, [90 * BB; 2]);
    Tree {
        nodes: vec![
            Node {
                kind: NodeKind::Action { actor: 0 },
                state: root_state,
                children: vec![(raise, 1)],
            },
            Node {
                kind: NodeKind::Action { actor: 1 },
                state: s1,
                children: vec![(Action::Call, 2)],
            },
            Node {
                kind: NodeKind::NextStreet {
                    pot_type: PotType::Srp,
                },
                state: s2,
                children: Vec::new(),
            },
        ],
    }
}

#[test]
fn degenerate_composition_equals_standalone_flop_solver() {
    // Design §6.1: M=1, flop-disjoint ranges, Enumerate, forced preflop
    // line → game value, exploitability and per-combo subgame strategies
    // must match the standalone FlopSolver essentially exactly.
    let board = [c("2c"), c("7d"), c("9h")];
    let iters = 40;
    let variant = CfrVariant::cfr_plus_default();

    let mut standalone = FlopSolver::new(
        build_flop_tree(20 * BB, 90 * BB, &tiny_cfg(PotType::Srp)),
        board,
        tiny_ranges(),
        variant,
        ChanceMode::Enumerate,
    );
    standalone.run(iters);
    let s_expl = standalone.exploitability_bb();
    let s_val = standalone.game_value_p0();

    let mut bp = BlueprintSolver::new_with_configs(
        forced_line_tree(),
        tiny_ranges(),
        variant,
        vec![board],
        vec![1.0],
        Abstraction::default(),
        false,
        0,
        tiny_cfg,
    );
    bp.run(iters);
    let b_expl = bp.exploitability_bb();
    let b_val = bp.game_value_p0();

    assert!(
        (s_val - b_val).abs() < 1e-9,
        "game values must match exactly: standalone {s_val:.9} vs blueprint {b_val:.9}"
    );
    assert!(
        (s_expl.exploitability - b_expl.exploitability).abs() < 1e-9,
        "exploitability must match exactly: {:.9} vs {:.9}",
        s_expl.exploitability,
        b_expl.exploitability
    );
    // Per-combo average strategies at the subgame root.
    let leaf = bp.betting_leaf_node_ids()[0];
    let sub = bp.subgame(leaf, 0);
    for combo in [
        combo_index(c("Kh"), c("Qh")),
        combo_index(c("8s"), c("8d")),
    ] {
        let a = standalone.average_strategy(0, None, None, combo);
        let b = sub.average_strategy(0, None, None, combo);
        for (x, y) in a.iter().zip(&b) {
            assert!((x - y).abs() < 1e-9, "strategy mismatch: {a:?} vs {b:?}");
        }
    }
    eprintln!(
        "degenerate composition OK: val {b_val:.6}, expl {:.6}",
        b_expl.exploitability
    );
}

/// All-in leaf tree: SB jam (forced) → BB call (forced) → AllInPreflop.
fn forced_jam_tree() -> Tree {
    let root_state = BettingState::preflop_root(100 * BB);
    let jam = Action::AllIn { to: 100 * BB };
    let s1 = root_state.apply(jam);
    let s2 = s1.apply(Action::Call);
    assert_eq!(s2.stacks, [0; 2]);
    assert_eq!(s2.pot(), 200 * BB);
    Tree {
        nodes: vec![
            Node {
                kind: NodeKind::Action { actor: 0 },
                state: root_state,
                children: vec![(jam, 1)],
            },
            Node {
                kind: NodeKind::Action { actor: 1 },
                state: s1,
                children: vec![(Action::Call, 2)],
            },
            Node {
                kind: NodeKind::NextStreet {
                    pot_type: PotType::AllInPreflop,
                },
                state: s2,
                children: Vec::new(),
            },
        ],
    }
}

/// Independent exact runout equity on one flop for one pair.
fn reference_equity(flop: [u8; 3], hero: (u8, u8), vill: (u8, u8)) -> f64 {
    let mut cards = [0u8; 7];
    cards[2..5].copy_from_slice(&flop);
    let dead = [hero.0, hero.1, vill.0, vill.1];
    let mut score = 0.0;
    let mut n = 0u32;
    for t in 0..52u8 {
        if flop.contains(&t) || dead.contains(&t) {
            continue;
        }
        for r in (t + 1)..52u8 {
            if flop.contains(&r) || dead.contains(&r) {
                continue;
            }
            cards[5] = t;
            cards[6] = r;
            cards[0] = hero.0;
            cards[1] = hero.1;
            let sh = evaluate_best(&cards);
            cards[0] = vill.0;
            cards[1] = vill.1;
            let sv = evaluate_best(&cards);
            score += match sh.cmp(&sv) {
                std::cmp::Ordering::Greater => 1.0,
                std::cmp::Ordering::Equal => 0.5,
                std::cmp::Ordering::Less => 0.0,
            };
            n += 1;
        }
    }
    score / n as f64
}

#[test]
fn allin_leaves_follow_the_m_flop_measure() {
    // Design §6.2 adversarial fixture: M=2, NON-uniform weights, one
    // hero combo blocking flop B. A naive (1/M)Σ-equity implementation
    // must fail this test.
    let flop_a = [c("2c"), c("7d"), c("9h")];
    let flop_b = [c("Kh"), c("Qh"), c("2h")];
    let (w_a, w_b) = (0.7, 0.3);
    let aa = (c("Ah"), c("Ad")); // legal on both flops
    let kk = (c("Kd"), c("Ks")); // legal on both
    let kh = (c("Kc"), c("Qd")); // legal on both
    let blocker = (c("Qs"), c("Qh")); // Qh blocks flop B
    let vill = (c("8s"), c("8d"));

    let mut r0 = Range::new_empty();
    for &(a, b) in &[aa, kk, kh, blocker] {
        r0.weights[combo_index(a, b)] = 1.0;
    }
    let mut r1 = Range::new_empty();
    r1.weights[combo_index(vill.0, vill.1)] = 1.0;

    let bp = BlueprintSolver::new_with_configs(
        forced_jam_tree(),
        [r0, r1.clone()],
        CfrVariant::cfr_plus_default(),
        vec![flop_a, flop_b],
        vec![w_a, w_b],
        Abstraction::default(),
        false,
        0,
        tiny_cfg,
    );
    let state = bp.preflop_tree.nodes[2].state;
    let vals = bp.allin_values(&state, 0, &r1.weights);

    let pot = 200.0; // bb
    let contrib = 100.0;
    for &(hero, blocks_b) in &[(aa, false), (kk, false), (kh, false), (blocker, true)] {
        let eq_a = reference_equity(flop_a, hero, vill);
        let mut expect = w_a * (eq_a * pot - contrib);
        if !blocks_b {
            let eq_b = reference_equity(flop_b, hero, vill);
            expect += w_b * (eq_b * pot - contrib);
        }
        let got = vals[combo_index(hero.0, hero.1)];
        // The blueprint stores per-flop equity as f32; the reference is
        // f64 — tolerance covers the cast (≪ the 1e-3 naive margin).
        assert!(
            (got - expect).abs() < 1e-4,
            "allin value mismatch for {hero:?}: got {got:.6}, expected {expect:.6}"
        );
        // The naive unmasked uniform average must NOT match the blocker combo.
        if blocks_b {
            let eq_b_naive = reference_equity(flop_a, hero, vill); // any placeholder
            let naive = 0.5 * (eq_a * pot - contrib) + 0.5 * (eq_b_naive * pot - contrib);
            assert!(
                (got - naive).abs() > 1e-3,
                "fixture failed to discriminate the naive implementation"
            );
        }
    }
    eprintln!("allin measure OK");
}

#[test]
fn bucketed_handoff_matches_exact_composition() {
    // Design §6.4: real preflop tree (mixed lines), M=2, tier-injective
    // K=N postflop buckets vs exact composition — the regret-aggregation
    // weight under preflop reach is the bug class this guards.
    let flops = vec![[c("2c"), c("7d"), c("9h")], [c("Jh"), c("8c"), c("3d")]];
    let weights = vec![0.6, 0.4];
    let iters = 30;
    let build = |abs: Abstraction| {
        BlueprintSolver::new_with_configs(
            build_preflop_tree(100 * BB),
            tiny_ranges(),
            CfrVariant::cfr_plus_default(),
            flops.clone(),
            weights.clone(),
            abs,
            false,
            0,
            tiny_cfg,
        )
    };
    let mut exact = build(Abstraction::default());
    exact.run(iters);
    let e = exact.exploitability_bb().exploitability;
    let ev = exact.game_value_p0();

    let mut bucketed = build(Abstraction {
        buckets_river: 1326,
        buckets_turn: 0,
    });
    bucketed.run(iters);
    let b = bucketed.exploitability_bb().exploitability;
    let bv = bucketed.game_value_p0();

    eprintln!("handoff: exact expl {e:.5} val {ev:.5} | K=N expl {b:.5} val {bv:.5}");
    assert!(e < 0.10, "exact composition not converging: {e:.4}");
    assert!(
        (e - b).abs() < 0.02,
        "tier-injective bucketing diverged from exact composition: {e:.5} vs {b:.5}"
    );
    assert!((ev - bv).abs() < 0.05, "values diverged: {ev:.5} vs {bv:.5}");
}

#[test]
fn smoke_full_preflop_tree_m3_converges() {
    // Design §6.5 (scaled to test budget): full preflop ladder, M=3,
    // uniform ranges, tiny subgame configs.
    let flops = vec![
        [c("2c"), c("7d"), c("9h")],
        [c("Kh"), c("Qh"), c("2h")],
        [c("As"), c("8c"), c("8d")],
    ];
    let weights = vec![0.5, 0.3, 0.2];
    let mut bp = BlueprintSolver::new_with_configs(
        build_preflop_tree(100 * BB),
        [Range::new_uniform(), Range::new_uniform()],
        CfrVariant::cfr_plus_default(),
        flops,
        weights,
        Abstraction::default(),
        false,
        0,
        tiny_cfg,
    );
    bp.run(10);
    let early = bp.exploitability_bb().exploitability;
    bp.run(30);
    let late = bp.exploitability_bb().exploitability;
    eprintln!("blueprint smoke expl: 10 iters {early:.4} → 40 iters {late:.4}");
    assert!(late < early, "exploitability must decrease");

    // Anchor: AA never open-folds (children: [fold, call, raise]).
    for aa in [combo_index(c("Ah"), c("Ad")), combo_index(c("Ks"), c("Kc"))] {
        let s = bp.average_strategy(0, aa);
        assert!(s[0] < 0.05, "premium pair open-folds: {s:?}");
    }
    // Chips conserve at every betting-subgame root.
    for leaf in bp.betting_leaf_node_ids() {
        let st = bp.preflop_tree.nodes[leaf].state;
        assert_eq!(st.pot() + st.stacks[0] + st.stacks[1], 200 * BB);
    }
    // Distribution sanity at the root.
    let agg = bp.aggregate_strategy(0);
    let total: f64 = agg.iter().map(|(_, f)| f).sum();
    assert!((total - 1.0).abs() < 1e-9);
}

#[test]
fn parallel_run_is_bit_identical_to_sequential() {
    // The 3-phase parallel run reorders independent work only; results
    // must equal the sequential DFS EXACTLY (==, not approximately).
    let flops = vec![[c("2c"), c("7d"), c("9h")], [c("Jh"), c("8c"), c("3d")]];
    let weights = vec![0.6, 0.4];
    let build = || {
        BlueprintSolver::new_with_configs(
            build_preflop_tree(100 * BB),
            tiny_ranges(),
            CfrVariant::cfr_plus_default(),
            flops.clone(),
            weights.clone(),
            Abstraction::default(),
            false,
            0,
            tiny_cfg,
        )
    };
    let mut seq = build();
    seq.run_sequential(12);
    let mut par = build();
    par.run(12);

    let (es, ep) = (seq.exploitability_bb(), par.exploitability_bb());
    assert_eq!(es.exploitability, ep.exploitability, "expl must be bit-identical");
    assert_eq!(es.br_value, ep.br_value);
    assert_eq!(seq.game_value_p0(), par.game_value_p0());
    for node_id in 0..seq.preflop_tree.nodes.len() {
        if !matches!(seq.preflop_tree.nodes[node_id].kind, NodeKind::Action { .. }) {
            continue;
        }
        for combo in [0usize, 700, 1325] {
            assert_eq!(
                seq.average_strategy(node_id, combo),
                par.average_strategy(node_id, combo),
                "preflop strategy diverged at node {node_id}"
            );
        }
    }
    eprintln!(
        "parallel == sequential OK (expl {:.6})",
        ep.exploitability
    );
}
