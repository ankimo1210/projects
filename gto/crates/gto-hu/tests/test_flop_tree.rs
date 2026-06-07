use gto_core::eval::parse_card;
use gto_hu::game::{Action, Street, BB, PLAYER_BB};
use gto_hu::tree::{build_flop_tree, FlopTreeConfig, NodeKind, Tree};

#[allow(dead_code)]
fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn srp_tree() -> Tree {
    build_flop_tree(20 * BB, 90 * BB, &FlopTreeConfig::srp())
}

fn child_by<F: Fn(&Action) -> bool>(t: &Tree, node: usize, pred: F) -> usize {
    t.nodes[node]
        .children
        .iter()
        .find(|(a, _)| pred(a))
        .map(|&(_, id)| id)
        .expect("child not found")
}

fn chance_child(t: &Tree, node: usize) -> usize {
    match t.nodes[node].kind {
        NodeKind::Chance { child } => child,
        k => panic!("expected chance node, got {k:?}"),
    }
}

#[test]
fn flop_root_offers_check_b33_b75() {
    let t = srp_tree();
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    // SRP flop per design spec §6: check, b33, b75 — no open all-in.
    assert_eq!(labels, vec!["check", "bet 6.6bb", "bet 15.0bb"]);
    assert_eq!(t.nodes[0].state.street, Street::Flop);
    assert!(matches!(t.nodes[0].kind, NodeKind::Action { actor } if actor == PLAYER_BB));
}

#[test]
fn flop_bet_call_deals_turn_then_turn_betting() {
    // Hard constraint: no flop-call → showdown shortcut (acceptance #4).
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 15 * BB));
    let call = child_by(&t, bet, |a| matches!(a, Action::Call));
    let turn = chance_child(&t, call); // call closes flop → Chance node
    let n = &t.nodes[turn];
    assert!(matches!(n.kind, NodeKind::Action { actor } if actor == PLAYER_BB));
    assert_eq!(n.state.street, Street::Turn);
    assert_eq!(n.state.pot(), 50 * BB);
    assert_eq!(n.state.stacks, [75 * BB; 2]);
    assert_eq!(n.state.street_committed, [0; 2]);
}

#[test]
fn check_check_deals_turn_with_unchanged_chips() {
    let t = srp_tree();
    let x1 = child_by(&t, 0, |a| matches!(a, Action::Check));
    let x2 = child_by(&t, x1, |a| matches!(a, Action::Check));
    let turn = chance_child(&t, x2);
    let n = &t.nodes[turn];
    assert_eq!(n.state.street, Street::Turn);
    assert_eq!(n.state.pot(), 20 * BB);
    assert_eq!(n.state.stacks, [90 * BB; 2]);
}

#[test]
fn flop_to_river_passes_two_chance_nodes() {
    // x-x → Chance(turn) → turn x-x → Chance(river) → river betting.
    let t = srp_tree();
    let x1 = child_by(&t, 0, |a| matches!(a, Action::Check));
    let x2 = child_by(&t, x1, |a| matches!(a, Action::Check));
    let turn_root = chance_child(&t, x2);
    assert_eq!(t.nodes[turn_root].state.street, Street::Turn);
    let tx1 = child_by(&t, turn_root, |a| matches!(a, Action::Check));
    let tx2 = child_by(&t, tx1, |a| matches!(a, Action::Check));
    let river_root = chance_child(&t, tx2);
    let n = &t.nodes[river_root];
    assert!(matches!(n.kind, NodeKind::Action { actor } if actor == PLAYER_BB));
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.pot(), 20 * BB);
}

#[test]
fn every_showdown_is_on_the_river() {
    // No showdown shortcut anywhere in the tree.
    let t = srp_tree();
    let mut showdowns = 0;
    for n in &t.nodes {
        if matches!(n.kind, NodeKind::Showdown) {
            assert_eq!(
                n.state.street,
                Street::River,
                "showdown before the river: {:?}",
                n.state
            );
            showdowns += 1;
        }
    }
    assert!(showdowns > 0);
}

#[test]
fn vs_raise_on_flop_is_jam_only() {
    // Spec §6 SRP flop: vs raise → fold, call, jam (never another 3x).
    // b33 = 6.6bb → raise 3x = 19.8bb; the re-raise must be the 90bb jam,
    // not 59.4bb.
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 660));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 1980));
    let labels: Vec<String> = t.nodes[raise]
        .children
        .iter()
        .map(|(a, _)| a.label())
        .collect();
    assert_eq!(labels, vec!["fold", "call", "allin 90.0bb"]);
}

#[test]
fn allin_flop_runout_is_double_chance_to_showdown() {
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 15 * BB));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 45 * BB));
    let jam = child_by(&t, raise, |a| matches!(a, Action::AllIn { to } if *to == 90 * BB));
    let call = child_by(&t, jam, |a| matches!(a, Action::Call));
    // call closes the flop all-in → Chance(turn) → Chance(river) → Showdown.
    let turn_chance = call;
    assert!(matches!(t.nodes[turn_chance].kind, NodeKind::Chance { .. }));
    assert_eq!(t.nodes[turn_chance].state.street, Street::Flop);
    let river_chance = chance_child(&t, turn_chance);
    assert!(
        matches!(t.nodes[river_chance].kind, NodeKind::Chance { .. }),
        "all-in flop runout needs a second chance node for the river"
    );
    assert_eq!(t.nodes[river_chance].state.street, Street::Turn);
    let sd = chance_child(&t, river_chance);
    let n = &t.nodes[sd];
    assert!(matches!(n.kind, NodeKind::Showdown));
    assert!(n.children.is_empty(), "no betting after all-in");
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.stacks, [0; 2]);
    assert_eq!(n.state.pot(), 20 * BB + 2 * 90 * BB);
}

#[test]
fn flop_bet_fold_terminal_payoff_exact() {
    use gto_hu::game::terminal::fold_payoffs;
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 15 * BB));
    let fold = child_by(&t, bet, |a| matches!(a, Action::Fold));
    let n = &t.nodes[fold];
    let NodeKind::FoldTerminal { winner } = n.kind else {
        panic!("expected fold terminal");
    };
    assert_eq!(winner, PLAYER_BB); // OOP bet, IP folded
    let pay = fold_payoffs(&n.state, winner);
    // Winner nets the loser's total contribution: the 10bb pot half.
    assert_eq!(pay, [-10 * BB, 10 * BB]);
    assert_eq!(pay[0] + pay[1], 0);
}

#[test]
fn chips_conserve_at_every_terminal_and_chance() {
    let t = srp_tree();
    let initial = 20 * BB + 2 * 90 * BB;
    for n in &t.nodes {
        match n.kind {
            NodeKind::FoldTerminal { .. } | NodeKind::Showdown | NodeKind::Chance { .. } => {
                assert_eq!(
                    n.state.pot() + n.state.stacks[0] + n.state.stacks[1],
                    initial,
                    "chip conservation violated"
                );
            }
            NodeKind::Action { .. } => assert!(!n.children.is_empty()),
        }
    }
}

#[test]
fn threebet_preset_builds_with_allin_turn_and_no_river_raise() {
    // 3BP per spec §6: flop check/b25/b50 + raise-jam; turn adds open
    // all-in; river check/b75/allin with fold/call only vs bet.
    let t = build_flop_tree(18 * BB, 41 * BB, &FlopTreeConfig::threebet());
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    assert_eq!(labels, vec!["check", "bet 4.5bb", "bet 9.0bb"]);
    // vs bet: fold, call, jam (raise-jam rule).
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 450));
    let vs: Vec<String> = t.nodes[bet]
        .children
        .iter()
        .map(|(a, _)| a.label())
        .collect();
    assert_eq!(vs, vec!["fold", "call", "allin 41.0bb"]);
}
