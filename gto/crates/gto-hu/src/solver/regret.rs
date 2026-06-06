/// Regret matching: strategy ∝ positive cumulative regrets, uniform when
/// no positive regret exists.
pub fn regret_matching(regrets: &[f64], out: &mut [f64]) {
    debug_assert_eq!(regrets.len(), out.len());
    let pos_sum: f64 = regrets.iter().map(|r| r.max(0.0)).sum();
    if pos_sum > 0.0 {
        for (o, r) in out.iter_mut().zip(regrets) {
            *o = r.max(0.0) / pos_sum;
        }
    } else {
        out.fill(1.0 / regrets.len() as f64);
    }
}
