use crate::solver::Game;

/// Kuhn poker. Actions: 0 = pass/check/fold, 1 = bet/call.
/// History chars: 'p' and 'b'. Terminals: pp, pbp, pbb, bp, bb.
pub struct Kuhn;

#[derive(Debug, Clone)]
pub struct KuhnState {
    /// None until the chance node deals (card0, card1).
    pub cards: Option<(u8, u8)>,
    pub history: String,
}

impl Kuhn {
    fn terminal_payoff_p0(cards: (u8, u8), history: &str) -> Option<f64> {
        let win = |a: u8, b: u8| if a > b { 1.0 } else { -1.0 };
        match history {
            "pp" => Some(win(cards.0, cards.1)),        // showdown, pot 2
            "pbp" => Some(-1.0),                        // P0 folds after check-bet
            "pbb" => Some(2.0 * win(cards.0, cards.1)), // call, pot 4
            "bp" => Some(1.0),                          // P1 folds
            "bb" => Some(2.0 * win(cards.0, cards.1)),  // call, pot 4
            _ => None,
        }
    }
}

impl Game for Kuhn {
    type State = KuhnState;

    fn root(&self) -> KuhnState {
        KuhnState {
            cards: None,
            history: String::new(),
        }
    }

    fn is_terminal(&self, s: &KuhnState) -> bool {
        s.cards.is_some() && Self::terminal_payoff_p0(s.cards.unwrap(), &s.history).is_some()
    }

    fn payoff(&self, s: &KuhnState, player: usize) -> f64 {
        let p0 = Self::terminal_payoff_p0(s.cards.unwrap(), &s.history).unwrap();
        if player == 0 {
            p0
        } else {
            -p0
        }
    }

    fn is_chance(&self, s: &KuhnState) -> bool {
        s.cards.is_none()
    }

    fn chance_outcomes(&self, _s: &KuhnState) -> Vec<(KuhnState, f64)> {
        let mut out = Vec::with_capacity(6);
        for c0 in 0..3u8 {
            for c1 in 0..3u8 {
                if c0 != c1 {
                    out.push((
                        KuhnState {
                            cards: Some((c0, c1)),
                            history: String::new(),
                        },
                        1.0 / 6.0,
                    ));
                }
            }
        }
        out
    }

    fn player(&self, s: &KuhnState) -> usize {
        s.history.len() % 2
    }

    fn num_actions(&self, _s: &KuhnState) -> usize {
        2
    }

    fn next(&self, s: &KuhnState, action: usize) -> KuhnState {
        let mut h = s.history.clone();
        h.push(if action == 0 { 'p' } else { 'b' });
        KuhnState {
            cards: s.cards,
            history: h,
        }
    }

    fn infoset_key(&self, s: &KuhnState) -> String {
        let player = self.player(s);
        let card = match s.cards.unwrap() {
            (c0, _) if player == 0 => c0,
            (_, c1) => c1,
        };
        format!("{player}|{card}|{}", s.history)
    }
}
