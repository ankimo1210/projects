use std::collections::HashMap;

use crate::solver::{Game, ScalarCfr};

/// Exact best response for two-player zero-sum games with perfect recall.
///
/// Infosets of the BR player are processed deepest-first (child infosets
/// always lie strictly deeper than their parents in our games). The action
/// choice at an infoset maximizes Σ over its states of
/// (opponent × chance reach) × value — the BR player's own reach above is
/// constant per infoset under perfect recall and does not affect argmax.
///
/// Complexity: O(infosets × tree size) — pass 2 re-walks the tree per infoset. Fine for reference games; do not call in a solver's inner loop.
pub fn best_response_value<G: Game>(game: &G, cfr: &ScalarCfr<G>, br_player: usize) -> f64 {
    // Pass 1: enumerate all BR-player decision states, grouped by infoset,
    // with their opponent+chance reach under the opponent's average strategy.
    let mut infosets: HashMap<String, (usize, usize)> = HashMap::new(); // key → (depth, na)
    collect(game, &game.root(), br_player, 0, &mut infosets);

    let mut ordered: Vec<(String, usize, usize)> = infosets
        .into_iter()
        .map(|(k, (d, na))| (k, d, na))
        .collect();
    ordered.sort_by_key(|b| std::cmp::Reverse(b.1)); // deepest first

    // Pass 2: greedily fix the best action per infoset, deepest first.
    let mut choices: HashMap<String, usize> = HashMap::new();
    for (key, _depth, na) in ordered {
        let mut action_vals = vec![0.0; na];
        accumulate_action_values(
            game,
            cfr,
            &game.root(),
            br_player,
            1.0,
            &key,
            &choices,
            &mut action_vals,
        );
        let best = action_vals
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0);
        choices.insert(key, best);
    }

    // Pass 3: evaluate the root under the fixed BR policy.
    eval(game, cfr, &game.root(), br_player, &choices)
}

fn collect<G: Game>(
    game: &G,
    s: &G::State,
    br_player: usize,
    depth: usize,
    out: &mut HashMap<String, (usize, usize)>,
) {
    if game.is_terminal(s) {
        return;
    }
    if game.is_chance(s) {
        for (c, _p) in game.chance_outcomes(s) {
            collect(game, &c, br_player, depth + 1, out);
        }
        return;
    }
    let na = game.num_actions(s);
    if game.player(s) == br_player {
        let key = game.infoset_key(s);
        let e = out.entry(key).or_insert((depth, na));
        e.0 = e.0.max(depth);
    }
    for a in 0..na {
        collect(game, &game.next(s, a), br_player, depth + 1, out);
    }
}

/// Adds (opp×chance reach) × subtree value to `action_vals` for every state
/// belonging to `target_key`. Deeper BR infosets are already in `choices`;
/// shallower BR nodes on the path contribute reach 1 (their choice cannot
/// remove states of a deeper infoset under perfect recall — every state of
/// `target_key` shares the same own-action history).
#[allow(clippy::too_many_arguments)]
fn accumulate_action_values<G: Game>(
    game: &G,
    cfr: &ScalarCfr<G>,
    s: &G::State,
    br_player: usize,
    reach_opp_chance: f64,
    target_key: &str,
    choices: &HashMap<String, usize>,
    action_vals: &mut [f64],
) {
    if game.is_terminal(s) || reach_opp_chance == 0.0 {
        return;
    }
    if game.is_chance(s) {
        for (c, p) in game.chance_outcomes(s) {
            accumulate_action_values(
                game,
                cfr,
                &c,
                br_player,
                reach_opp_chance * p,
                target_key,
                choices,
                action_vals,
            );
        }
        return;
    }
    let na = game.num_actions(s);
    if game.player(s) == br_player {
        let key = game.infoset_key(s);
        if key == target_key {
            for (a, val) in action_vals.iter_mut().enumerate().take(na) {
                let v = eval(game, cfr, &game.next(s, a), br_player, choices);
                *val += reach_opp_chance * v;
            }
            return;
        }
        // Other own infoset: descend all actions (choice fixed only if deeper
        // sets were already resolved; unresolved shallower sets don't gate
        // reachability of target states — see function doc).
        for a in 0..na {
            accumulate_action_values(
                game,
                cfr,
                &game.next(s, a),
                br_player,
                reach_opp_chance,
                target_key,
                choices,
                action_vals,
            );
        }
    } else {
        let key = game.infoset_key(s);
        let strat = cfr.average_strategy(&key, na);
        for (a, &p) in strat.iter().enumerate() {
            accumulate_action_values(
                game,
                cfr,
                &game.next(s, a),
                br_player,
                reach_opp_chance * p,
                target_key,
                choices,
                action_vals,
            );
        }
    }
}

/// Expected value for `br_player` when they play `choices` and the
/// opponent plays the average strategy.
fn eval<G: Game>(
    game: &G,
    cfr: &ScalarCfr<G>,
    s: &G::State,
    br_player: usize,
    choices: &HashMap<String, usize>,
) -> f64 {
    if game.is_terminal(s) {
        return game.payoff(s, br_player);
    }
    if game.is_chance(s) {
        return game
            .chance_outcomes(s)
            .iter()
            .map(|(c, p)| p * eval(game, cfr, c, br_player, choices))
            .sum();
    }
    let na = game.num_actions(s);
    let key = game.infoset_key(s);
    if game.player(s) == br_player {
        let a = *choices
            .get(&key)
            .unwrap_or_else(|| panic!("BR ordering violated: unresolved infoset {key}"));
        eval(game, cfr, &game.next(s, a), br_player, choices)
    } else {
        let strat = cfr.average_strategy(&key, na);
        (0..na)
            .map(|a| strat[a] * eval(game, cfr, &game.next(s, a), br_player, choices))
            .sum()
    }
}

/// NashConv/2: average best-response gain. 0 at equilibrium.
pub fn exploitability<G: Game>(game: &G, cfr: &ScalarCfr<G>) -> f64 {
    let br0 = best_response_value(game, cfr, 0);
    let br1 = best_response_value(game, cfr, 1);
    (br0 + br1) / 2.0
}
