use gto_hu::game::BB;
use gto_hu::reports::{tree_stats, TreeStats};
use gto_hu::tree::{build_river_tree, StreetConfig};

#[test]
fn tree_stats_counts_node_kinds() {
    let t = build_river_tree(20 * BB, 90 * BB, &StreetConfig::srp_river());
    let s: TreeStats = tree_stats(&t);
    assert_eq!(
        s.action_nodes + s.fold_terminals + s.showdown_terminals,
        s.total_nodes
    );
    assert!(s.action_nodes > 0 && s.fold_terminals > 0 && s.showdown_terminals > 0);
    assert!(s.memory_estimate_bytes > 0);
}
