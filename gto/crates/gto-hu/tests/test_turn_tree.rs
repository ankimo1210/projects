use gto_core::eval::parse_card;
use gto_hu::game::{Action, Street, BB, PLAYER_BB};
use gto_hu::tree::{build_turn_river_tree, NodeKind, Tree, TurnTreeConfig};

#[allow(dead_code)]
fn c(s: &str) -> u8 {
    parse_card(s).unwrap()
}

fn srp_tree() -> Tree {
    build_turn_river_tree(20 * BB, 90 * BB, &TurnTreeConfig::srp())
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
fn turn_root_offers_check_b50_b100() {
    let t = srp_tree();
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    // SRP turn per design spec §6: check, b50, b100 — no open all-in.
    assert_eq!(labels, vec!["check", "bet 10.0bb", "bet 20.0bb"]);
    assert_eq!(t.nodes[0].state.street, Street::Turn);
}

#[test]
fn turn_bet_call_proceeds_to_river_betting() {
    // Hard constraint: no turn-call → showdown shortcut.
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let call = child_by(&t, bet, |a| matches!(a, Action::Call));
    let river = chance_child(&t, call); // call closes turn → Chance node
    let n = &t.nodes[river];
    assert!(matches!(n.kind, NodeKind::Action { actor } if actor == PLAYER_BB));
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.pot(), 40 * BB);
    assert_eq!(n.state.stacks, [80 * BB; 2]);
    assert_eq!(n.state.street_committed, [0; 2]);
}

#[test]
fn check_check_deals_river_with_unchanged_chips() {
    let t = srp_tree();
    let x1 = child_by(&t, 0, |a| matches!(a, Action::Check));
    let x2 = child_by(&t, x1, |a| matches!(a, Action::Check));
    let river = chance_child(&t, x2);
    let n = &t.nodes[river];
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.pot(), 20 * BB);
    assert_eq!(n.state.stacks, [90 * BB; 2]);
}

#[test]
fn vs_raise_offers_jam_at_this_depth() {
    // b50 = 10bb → raise 3x = 30bb → second raise 3x = 90bb ≥ stack ⇒ AllIn.
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 30 * BB));
    let jam = t.nodes[raise]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::AllIn { to } if *to == 90 * BB));
    assert!(jam.is_some(), "second raise must become a jam at 90bb stacks");
}

#[test]
fn allin_turn_runout_goes_to_showdown_with_no_betting() {
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let raise = child_by(&t, bet, |a| matches!(a, Action::Raise { to } if *to == 30 * BB));
    let jam = child_by(&t, raise, |a| matches!(a, Action::AllIn { .. }));
    let call = child_by(&t, jam, |a| matches!(a, Action::Call));
    let sd = chance_child(&t, call);
    let n = &t.nodes[sd];
    assert!(matches!(n.kind, NodeKind::Showdown), "all-in runout must be showdown");
    assert!(n.children.is_empty(), "no betting after all-in");
    assert_eq!(n.state.street, Street::River);
    assert_eq!(n.state.stacks, [0; 2]);
    assert_eq!(n.state.pot(), 20 * BB + 2 * 90 * BB);
}

#[test]
fn turn_bet_fold_terminal_payoff_exact() {
    use gto_hu::game::terminal::fold_payoffs;
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let fold = child_by(&t, bet, |a| matches!(a, Action::Fold));
    let n = &t.nodes[fold];
    let NodeKind::FoldTerminal { winner } = n.kind else {
        panic!("expected fold terminal");
    };
    assert_eq!(winner, PLAYER_BB); // OOP bet, IP folded
    let pay = fold_payoffs(&n.state, winner);
    // Winner nets the loser's total contribution: 10bb (pot half).
    assert_eq!(pay, [-10 * BB, 10 * BB]);
    assert_eq!(pay[0] + pay[1], 0);
}

#[test]
fn river_close_inside_turn_tree_is_showdown_not_chance() {
    let t = srp_tree();
    let bet = child_by(&t, 0, |a| matches!(a, Action::Bet { to } if *to == 10 * BB));
    let call = child_by(&t, bet, |a| matches!(a, Action::Call));
    let river_root = chance_child(&t, call);
    // River: OOP bets 75% pot (30bb), IP calls → Showdown.
    let rbet = child_by(&t, river_root, |a| matches!(a, Action::Bet { .. }));
    let rcall = child_by(&t, rbet, |a| matches!(a, Action::Call));
    assert!(matches!(t.nodes[rcall].kind, NodeKind::Showdown));
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
