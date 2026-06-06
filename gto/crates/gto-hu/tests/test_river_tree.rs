use gto_hu::game::{Action, BB};
use gto_hu::tree::{build_river_tree, NodeKind, RaiseRule, StreetConfig};

#[test]
fn river_tree_root_actions_match_srp_config() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let root = &t.nodes[0];
    let labels: Vec<String> = root.children.iter().map(|(a, _)| a.label()).collect();
    // check, bet 75%, bet 150%, allin
    assert_eq!(
        labels,
        vec!["check", "bet 15.0bb", "bet 30.0bb", "allin 90.0bb"]
    );
}

#[test]
fn facing_bet_offers_fold_call_jam() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    // Child 1 of root = bet 15bb → SB node.
    let bet_node_id = t.nodes[0].children[1].1;
    let acts: Vec<Action> = t.nodes[bet_node_id]
        .children
        .iter()
        .map(|(a, _)| *a)
        .collect();
    assert!(matches!(acts[0], Action::Fold));
    assert!(matches!(acts[1], Action::Call));
    assert!(matches!(acts[2], Action::AllIn { to } if to == 90 * BB));
    assert_eq!(acts.len(), 3, "facing a bet: fold/call/raise-jam only");
}

#[test]
fn no_reraise_after_jam() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let bet_id = t.nodes[0].children[1].1;
    let jam_id = t.nodes[bet_id].children[2].1;
    let acts: Vec<Action> = t.nodes[jam_id].children.iter().map(|(a, _)| *a).collect();
    assert_eq!(acts.len(), 2, "facing a jam: fold/call only");
    assert!(matches!(acts[0], Action::Fold));
    assert!(matches!(acts[1], Action::Call));
}

#[test]
fn all_terminals_are_fold_or_showdown_and_pots_conserve() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let initial = 20 * BB + 2 * 90 * BB;
    let mut terminals = 0;
    for n in &t.nodes {
        match n.kind {
            NodeKind::FoldTerminal { .. } | NodeKind::Showdown => {
                terminals += 1;
                assert!(n.children.is_empty());
                assert_eq!(
                    n.state.pot() + n.state.stacks[0] + n.state.stacks[1],
                    initial,
                    "chip conservation violated at a terminal"
                );
            }
            NodeKind::Action { .. } => assert!(!n.children.is_empty()),
        }
    }
    assert!(terminals >= 6);
}

#[test]
fn short_stack_dedupes_bet_sizes_to_allin() {
    // Stack 10bb: the 75% pot bet (15bb) and 150% pot bet (30bb) both
    // exceed the stack, so they and the explicit jam dedupe into one all-in.
    let t = build_river_tree(20 * BB, 10 * BB, &StreetConfig::srp_river());
    let labels: Vec<String> = t.nodes[0].children.iter().map(|(a, _)| a.label()).collect();
    assert_eq!(labels, vec!["check", "allin 10.0bb"]);
}

#[test]
#[should_panic(expected = "below 2.0")]
fn factor_below_two_rejected() {
    let cfg = StreetConfig {
        bet_pcts: vec![75],
        allow_allin_bet: false,
        raise: RaiseRule::ToFactorOrJam(1.5),
        max_raises: 1,
    };
    let _ = build_river_tree(20 * BB, 90 * BB, &cfg);
}

#[test]
#[should_panic(expected = "must be positive")]
fn zero_bet_pct_rejected() {
    let cfg = StreetConfig {
        bet_pcts: vec![0],
        allow_allin_bet: false,
        raise: RaiseRule::JamOnly,
        max_raises: 1,
    };
    let _ = build_river_tree(20 * BB, 90 * BB, &cfg);
}

#[test]
fn factor_raise_builds_legal_three_x() {
    // Facing the 15bb root bet, factor 3.0 must offer raise to 45bb.
    let cfg = StreetConfig {
        bet_pcts: vec![75],
        allow_allin_bet: false,
        raise: RaiseRule::ToFactorOrJam(3.0),
        max_raises: 1,
    };
    let t = build_river_tree(20 * BB, 90 * BB, &cfg);
    let bet_node = t.nodes[0]
        .children
        .iter()
        .find(|(a, _)| matches!(a, Action::Bet { .. }))
        .map(|&(_, id)| id)
        .unwrap();
    let raise = t.nodes[bet_node]
        .children
        .iter()
        .find_map(|(a, id)| match a {
            Action::Raise { to } => Some((*to, *id)),
            _ => None,
        });
    let (to, raise_id) = raise.expect("factor rule must offer a raise");
    assert_eq!(to, 45 * BB);
    // The raise child must expand legally (fold/call available, no panic).
    assert!(t.nodes[raise_id].children.len() >= 2);
}

#[test]
fn raise_rule_none_offers_fold_call_only() {
    let cfg = StreetConfig {
        bet_pcts: vec![75],
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 1,
    };
    let t = build_river_tree(20 * BB, 90 * BB, &cfg);
    let bet_node = t.nodes[0].children[1].1;
    assert_eq!(t.nodes[bet_node].children.len(), 2, "fold/call only");
}
