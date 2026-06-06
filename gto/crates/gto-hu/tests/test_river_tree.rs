use gto_hu::game::{Action, BB};
use gto_hu::tree::{build_river_tree, NodeKind, StreetConfig};

#[test]
fn river_tree_root_actions_match_srp_config() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let root = &t.nodes[0];
    let labels: Vec<String> = root.children.iter().map(|(a, _)| a.label()).collect();
    // check, bet 75%, bet 150%, allin
    assert_eq!(labels, vec!["check", "bet 15.0bb", "bet 30.0bb", "allin 90.0bb"]);
}

#[test]
fn facing_bet_offers_fold_call_jam() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    // Child 1 of root = bet 15bb → SB node.
    let bet_node_id = t.nodes[0].children[1].1;
    let acts: Vec<Action> = t.nodes[bet_node_id].children.iter().map(|(a, _)| *a).collect();
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
