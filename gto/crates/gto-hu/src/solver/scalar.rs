use std::collections::HashMap;

use super::regret::regret_matching;
use super::variant::CfrVariant;

/// Two-player zero-sum extensive-form game with perfect recall.
/// Payoffs are returned per player at terminal states.
pub trait Game {
    type State: Clone;

    fn root(&self) -> Self::State;
    fn is_terminal(&self, s: &Self::State) -> bool;
    /// Terminal payoff for `player` (must satisfy zero-sum).
    fn payoff(&self, s: &Self::State, player: usize) -> f64;
    fn is_chance(&self, s: &Self::State) -> bool;
    /// Chance successor states with probabilities summing to 1.
    fn chance_outcomes(&self, s: &Self::State) -> Vec<(Self::State, f64)>;
    /// Acting player at a non-terminal, non-chance state (0 or 1).
    fn player(&self, s: &Self::State) -> usize;
    fn num_actions(&self, s: &Self::State) -> usize;
    fn next(&self, s: &Self::State, action: usize) -> Self::State;
    /// Information-set key for the acting player (perfect recall).
    fn infoset_key(&self, s: &Self::State) -> String;
}

#[derive(Debug, Clone)]
pub struct InfoNode {
    pub regrets: Vec<f64>,
    pub strat_sum: Vec<f64>,
    /// Last iteration in which the per-iteration discounts were applied.
    last_discount_iter: u32,
}

impl InfoNode {
    fn new(num_actions: usize) -> Self {
        InfoNode {
            regrets: vec![0.0; num_actions],
            strat_sum: vec![0.0; num_actions],
            last_discount_iter: 0,
        }
    }
}

/// Reference CFR engine: full traversal, exact chance enumeration.
/// Slow but transparent — used for Kuhn/Leduc and differential testing.
pub struct ScalarCfr<'a, G: Game> {
    pub game: &'a G,
    pub variant: CfrVariant,
    pub nodes: HashMap<String, InfoNode>,
    pub iteration: u32,
}

impl<'a, G: Game> ScalarCfr<'a, G> {
    pub fn new(game: &'a G, variant: CfrVariant) -> Self {
        ScalarCfr { game, variant, nodes: HashMap::new(), iteration: 0 }
    }

    /// Run `iterations` full CFR iterations (both players each iteration).
    pub fn run(&mut self, iterations: u32) {
        for _ in 0..iterations {
            self.iteration += 1;
            for p in 0..2 {
                let root = self.game.root();
                self.traverse(&root, p, 1.0, 1.0);
            }
        }
    }

    /// Returns EV for `traverser` at `s` under current strategies.
    /// `my_reach` = traverser's own reach; `opp_reach` includes the
    /// opponent's strategy AND chance probabilities (counterfactual reach).
    fn traverse(&mut self, s: &G::State, traverser: usize, my_reach: f64, opp_reach: f64) -> f64 {
        if self.game.is_terminal(s) {
            return self.game.payoff(s, traverser);
        }
        if self.game.is_chance(s) {
            return self
                .game
                .chance_outcomes(s)
                .iter()
                .map(|(c, p)| p * self.traverse(c, traverser, my_reach, opp_reach * p))
                .sum();
        }

        let player = self.game.player(s);
        let na = self.game.num_actions(s);
        let key = self.game.infoset_key(s);
        let mut strat = vec![0.0; na];
        {
            let node = self.nodes.entry(key.clone()).or_insert_with(|| InfoNode::new(na));
            assert_eq!(
                node.regrets.len(),
                na,
                "num_actions mismatch for infoset {key:?}: stored {}, state reports {na}",
                node.regrets.len()
            );
            regret_matching(&node.regrets, &mut strat);
        }

        if player == traverser {
            let mut action_vals = vec![0.0; na];
            for a in 0..na {
                let child = self.game.next(s, a);
                action_vals[a] = self.traverse(&child, traverser, my_reach * strat[a], opp_reach);
            }
            let ev: f64 = strat.iter().zip(&action_vals).map(|(p, v)| p * v).sum();
            let t = self.iteration;
            let variant = self.variant;
            let node = self.nodes.get_mut(&key).unwrap();
            // Apply per-iteration discounts exactly once (lazily on first visit).
            if node.last_discount_iter < t {
                node.last_discount_iter = t;
                let sd = variant.strategy_discount(t);
                for r in node.regrets.iter_mut() {
                    *r *= variant.regret_discount(*r, t);
                }
                for s in node.strat_sum.iter_mut() {
                    *s *= sd;
                }
            }
            let sw = variant.strategy_weight(t);
            for a in 0..na {
                let delta = opp_reach * (action_vals[a] - ev);
                node.regrets[a] = variant.accumulate_regret(node.regrets[a], delta);
                // Average strategy: weighted by the actor's OWN reach.
                node.strat_sum[a] += sw * my_reach * strat[a];
            }
            ev
        } else {
            let mut ev = 0.0;
            for (a, &p) in strat.iter().enumerate() {
                let child = self.game.next(s, a);
                ev += p * self.traverse(&child, traverser, my_reach, opp_reach * p);
            }
            ev
        }
    }

    /// Normalized average strategy for an infoset key (uniform if unseen).
    pub fn average_strategy(&self, key: &str, num_actions: usize) -> Vec<f64> {
        match self.nodes.get(key) {
            Some(n) => {
                debug_assert_eq!(
                    n.strat_sum.len(),
                    num_actions,
                    "average_strategy length mismatch for {key:?}"
                );
                let total: f64 = n.strat_sum.iter().sum();
                if total > 0.0 {
                    n.strat_sum.iter().map(|s| s / total).collect()
                } else {
                    vec![1.0 / num_actions as f64; num_actions]
                }
            }
            None => vec![1.0 / num_actions as f64; num_actions],
        }
    }
}
