use gto_hu::game::{Action, PotType, Street, BB, PLAYER_BB, PLAYER_SB};
use gto_hu::tree::{build_preflop_tree, NodeKind, Tree};

fn t100() -> Tree {
    build_preflop_tree(100 * BB)
}

fn labels(t: &Tree, node: usize) -> Vec<String> {
    t.nodes[node].children.iter().map(|(a, _)| a.label()).collect()
}

fn child_by<F: Fn(&Action) -> bool>(t: &Tree, node: usize, pred: F) -> usize {
    t.nodes[node]
        .children
        .iter()
        .find(|(a, _)| pred(a))
        .map(|&(_, id)| id)
        .expect("child not found")
}

fn next_street(t: &Tree, node: usize) -> PotType {
    match t.nodes[node].kind {
        NodeKind::NextStreet { pot_type } => pot_type,
        k => panic!("expected NextStreet, got {k:?}"),
    }
}

#[test]
fn sb_root_offers_fold_limp_raise() {
    let t = t100();
    // Spec §6: SB initial — fold, limp, raise to 2.5bb.
    assert_eq!(labels(&t, 0), vec!["fold", "call", "raise 2.5bb"]);
    let root = &t.nodes[0];
    assert_eq!(root.state.street, Street::Preflop);
    assert!(matches!(root.kind, NodeKind::Action { actor } if actor == PLAYER_SB));
    // Blinds posted: SB 0.5bb, BB 1bb.
    assert_eq!(root.state.contrib, [BB / 2, BB]);
    assert_eq!(root.state.stacks, [100 * BB - BB / 2, 99 * BB]);
}

#[test]
fn limp_does_not_close_preflop_bb_has_option() {
    let t = t100();
    let limp = child_by(&t, 0, |a| matches!(a, Action::Call));
    // Spec §6: BB vs limp — check, raise to 4bb, raise to 6bb.
    assert_eq!(labels(&t, limp), vec!["check", "raise 4.0bb", "raise 6.0bb"]);
    assert!(matches!(t.nodes[limp].kind, NodeKind::Action { actor } if actor == PLAYER_BB));
}

#[test]
fn limp_check_goes_to_limped_flop() {
    let t = t100();
    let limp = child_by(&t, 0, |a| matches!(a, Action::Call));
    let check = child_by(&t, limp, |a| matches!(a, Action::Check));
    assert_eq!(next_street(&t, check), PotType::Limped);
    assert_eq!(t.nodes[check].state.pot(), 2 * BB);
    assert_eq!(t.nodes[check].state.stacks, [99 * BB; 2]);
    assert!(t.nodes[check].children.is_empty());
}

#[test]
fn open_call_goes_to_srp_flop() {
    let t = t100();
    let open = child_by(&t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    // Spec §6: BB vs open — fold, call, 3bet to 9bb.
    assert_eq!(labels(&t, open), vec!["fold", "call", "raise 9.0bb"]);
    let call = child_by(&t, open, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call), PotType::Srp);
    assert_eq!(t.nodes[call].state.pot(), 5 * BB);
    assert_eq!(t.nodes[call].state.stacks, [975 * BB / 10; 2]);
}

#[test]
fn threebet_line_offers_4bet_and_jam_then_4bp() {
    let t = t100();
    let open = child_by(&t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    let threebet = child_by(&t, open, |a| matches!(a, Action::Raise { to } if *to == 900));
    // Spec §6: SB vs BB 3bet — fold, call, 4bet to 22bb, jam.
    assert_eq!(
        labels(&t, threebet),
        vec!["fold", "call", "raise 22.0bb", "allin 100.0bb"]
    );
    let call3 = child_by(&t, threebet, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call3), PotType::ThreeBet);
    assert_eq!(t.nodes[call3].state.pot(), 18 * BB);

    let fourbet = child_by(&t, threebet, |a| matches!(a, Action::Raise { to } if *to == 2200));
    // Spec §6: BB vs SB 4bet — fold, call, jam.
    assert_eq!(labels(&t, fourbet), vec!["fold", "call", "allin 100.0bb"]);
    let call4 = child_by(&t, fourbet, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call4), PotType::FourBet);
    assert_eq!(t.nodes[call4].state.pot(), 44 * BB);
}

#[test]
fn jam_lines_are_fold_call_only_and_allin_preflop() {
    let t = t100();
    let open = child_by(&t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    let threebet = child_by(&t, open, |a| matches!(a, Action::Raise { to } if *to == 900));
    let fourbet = child_by(&t, threebet, |a| matches!(a, Action::Raise { to } if *to == 2200));
    let jam = child_by(&t, fourbet, |a| matches!(a, Action::AllIn { to } if *to == 100 * BB));
    // Spec §6: facing jam — fold, call.
    assert_eq!(labels(&t, jam), vec!["fold", "call"]);
    let call = child_by(&t, jam, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call), PotType::AllInPreflop);
    assert_eq!(t.nodes[call].state.pot(), 200 * BB);
    assert_eq!(t.nodes[call].state.stacks, [0; 2]);
}

#[test]
fn limp_raise_line_follows_spec_ladder() {
    let t = t100();
    let limp = child_by(&t, 0, |a| matches!(a, Action::Call));
    let braise = child_by(&t, limp, |a| matches!(a, Action::Raise { to } if *to == 400));
    // Spec §6: SB vs BB raise after limp — fold, call, 3bet to 12bb, jam.
    assert_eq!(
        labels(&t, braise),
        vec!["fold", "call", "raise 12.0bb", "allin 100.0bb"]
    );
    // limp-raise call → one raise in: SRP-class pot.
    let call = child_by(&t, braise, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call), PotType::Srp);
    assert_eq!(t.nodes[call].state.pot(), 8 * BB);

    // SB 3bets to 12bb → BB faces the 2nd raise: fold, call, jam.
    let sb3 = child_by(&t, braise, |a| matches!(a, Action::Raise { to } if *to == 1200));
    assert_eq!(labels(&t, sb3), vec!["fold", "call", "allin 100.0bb"]);
    let call3 = child_by(&t, sb3, |a| matches!(a, Action::Call));
    assert_eq!(next_street(&t, call3), PotType::ThreeBet);
    assert_eq!(t.nodes[call3].state.pot(), 24 * BB);
}

#[test]
fn fold_payoffs_are_exact_for_blinds() {
    use gto_hu::game::terminal::fold_payoffs;
    let t = t100();
    // SB open-fold: loses the 0.5bb small blind.
    let fold = child_by(&t, 0, |a| matches!(a, Action::Fold));
    let NodeKind::FoldTerminal { winner } = t.nodes[fold].kind else {
        panic!("expected fold terminal");
    };
    assert_eq!(winner, PLAYER_BB);
    let pay = fold_payoffs(&t.nodes[fold].state, winner);
    assert_eq!(pay, [-BB / 2, BB / 2]);

    // BB folds to the open: loses the 1bb big blind.
    let open = child_by(&t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    let bbfold = child_by(&t, open, |a| matches!(a, Action::Fold));
    let NodeKind::FoldTerminal { winner } = t.nodes[bbfold].kind else {
        panic!("expected fold terminal");
    };
    assert_eq!(winner, PLAYER_SB);
    let pay = fold_payoffs(&t.nodes[bbfold].state, winner);
    assert_eq!(pay, [BB, -BB]);
}

#[test]
fn no_showdown_nodes_and_chips_conserve() {
    let t = t100();
    let initial = 200 * BB;
    for n in &t.nodes {
        assert!(
            !matches!(n.kind, NodeKind::Showdown | NodeKind::Chance { .. }),
            "preflop tree must not contain showdown/chance nodes"
        );
        match n.kind {
            NodeKind::FoldTerminal { .. } | NodeKind::NextStreet { .. } => {
                assert_eq!(
                    n.state.pot() + n.state.stacks[0] + n.state.stacks[1],
                    initial,
                    "chip conservation violated"
                );
                assert!(n.children.is_empty());
            }
            NodeKind::Action { .. } => assert!(!n.children.is_empty()),
            _ => unreachable!(),
        }
    }
}

#[test]
fn short_stack_sizes_cap_to_allin() {
    // At 20bb the 22bb 4bet must become a jam (and never exceed stack).
    let t = build_preflop_tree(20 * BB);
    let open = child_by(&t, 0, |a| matches!(a, Action::Raise { to } if *to == 250));
    let threebet = child_by(&t, open, |a| matches!(a, Action::Raise { to } if *to == 900));
    let labels3 = labels(&t, threebet);
    assert!(
        labels3.contains(&"allin 20.0bb".to_string()),
        "4bet must cap to jam at 20bb: {labels3:?}"
    );
    assert_eq!(
        labels3.iter().filter(|l| l.starts_with("allin")).count(),
        1,
        "capped 4bet and jam must dedupe: {labels3:?}"
    );
}
