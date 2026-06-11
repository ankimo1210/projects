use pyo3::prelude::*;
use gto_core::card::Card;
use gto_core::{monte_carlo, parse_cards};
use gto_core::{solve, all_combos, evaluate7};
use gto_core::eval::parse_card as parse_card_u8;

/// Plain-Rust result of a GIL-released HU solve, ready for dict-building
/// under the GIL. Keeps the `allow_threads` closure free of Python objects.
struct HuSolveOutput {
    root: Vec<(String, f64)>,
    expl: gto_hu::solver::ExplReport,
    game_value: f64,
    elapsed: f64,
    /// (card_a, card_b, per-action freqs, ev_bb) for each in-range combo
    /// of the ROOT ACTOR (BB/OOP — p1).
    combo_data: Vec<(u8, u8, Vec<f64>, f64)>,
    equity_sb: f64,
}

/// Reject a set of card indices that shares a physical card. gto-core's
/// monte_carlo / solvers dedup only the deck, so an overlap between
/// hero/villain/board silently produces nonsense — guard it at the boundary.
fn reject_duplicate_cards(cards: &[u8]) -> PyResult<()> {
    let mut seen = [false; 52];
    for &c in cards {
        if (c as usize) >= 52 || seen[c as usize] {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "duplicate card across hero/villain/board",
            ));
        }
        seen[c as usize] = true;
    }
    Ok(())
}

/// Build a Range from optional API weights; falls back to uniform.
/// Validation: length == 1326, all finite and >= 0, positive sum.
fn range_from_weights(
    weights: Option<Vec<f64>>,
    board: &[u8],
) -> PyResult<gto_hu::ranges::Range> {
    use gto_hu::ranges::{uniform_excluding, Range, NUM_COMBOS};
    match weights {
        None => Ok(uniform_excluding(board)),
        Some(w) => {
            if w.len() != NUM_COMBOS {
                return Err(pyo3::exceptions::PyValueError::new_err(format!(
                    "range weights must have length {NUM_COMBOS}, got {}",
                    w.len()
                )));
            }
            if w.iter().any(|x| !x.is_finite() || *x < 0.0) {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "range weights must be finite and non-negative",
                ));
            }
            let mut r = Range::new_empty();
            r.weights.copy_from_slice(&w);
            r.remove_blockers(board);
            if r.total_weight() <= 0.0 {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "range has no live combos on this board",
                ));
            }
            Ok(r)
        }
    }
}

/// StreetConfig for the river from pot_type + overrides.
fn river_config(
    pot_type: Option<&str>,
    bet_pcts: Option<Vec<u32>>,
    max_raises: Option<u8>,
) -> PyResult<gto_hu::tree::StreetConfig> {
    use gto_hu::tree::StreetConfig;
    let mut cfg = match pot_type.unwrap_or("srp") {
        "srp" => StreetConfig::srp_river(),
        "3bet" => StreetConfig::threebet_river(),
        "4bet" => StreetConfig::fourbet_street(),
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown pot_type '{other}' (srp | 3bet | 4bet)"
            )))
        }
    };
    if let Some(p) = bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "bet_pcts must be positive",
            ));
        }
        cfg.bet_pcts = p;
    }
    if let Some(m) = max_raises {
        cfg.max_raises = m;
    }
    Ok(cfg)
}

/// RakeModel from optional pct/cap (bb). None/0.0 -> RakeModel::NONE.
fn rake_from_args(rake_pct: Option<f64>, rake_cap_bb: Option<f64>) -> PyResult<gto_hu::game::RakeModel> {
    use gto_hu::game::RakeModel;
    let pct = rake_pct.unwrap_or(0.0);
    if !(0.0..0.5).contains(&pct) {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "rake_pct must be in [0, 0.5)",
        ));
    }
    if pct == 0.0 {
        return Ok(RakeModel::NONE);
    }
    let cap_bb = rake_cap_bb.unwrap_or(f64::MAX / 200.0);
    if cap_bb <= 0.0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "rake_cap_bb must be positive",
        ));
    }
    Ok(RakeModel { pct, cap_cbb: (cap_bb * 100.0) as i64, no_flop_no_drop: true })
}

#[pyfunction]
fn equity(
    py: Python<'_>,
    hero: &str,
    villain: &str,
    board: &str,
    iterations: Option<u32>,
) -> PyResult<PyObject> {
    let hero_cards = parse_cards(hero)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))?;
    let villain_cards = parse_cards(villain)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e))?;
    let board_cards = if board.trim().is_empty() {
        vec![]
    } else {
        parse_cards(board).map_err(|e| pyo3::exceptions::PyValueError::new_err(e))?
    };
    if hero_cards.len() != 2 || villain_cards.len() != 2 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "hero and villain must each have exactly 2 cards",
        ));
    }
    let all_cards: Vec<u8> = hero_cards
        .iter()
        .chain(villain_cards.iter())
        .chain(board_cards.iter())
        .map(|c| c.0)
        .collect();
    reject_duplicate_cards(&all_cards)?;
    let iters = iterations.unwrap_or(10_000);
    let result =
        py.allow_threads(|| monte_carlo(&hero_cards, &villain_cards, &board_cards, iters));
    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("hero_equity", result.hero_equity)?;
    dict.set_item("villain_equity", result.villain_equity)?;
    dict.set_item("tie", result.tie)?;
    dict.set_item("iterations", result.iterations)?;
    Ok(dict.into())
}

#[pyfunction]
fn parse_card_fn(s: &str) -> PyResult<u8> {
    Card::from_str(s)
        .map(|c| c.0)
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(format!("invalid card: {s}")))
}

/// ⚠ Single-street approximation (river-only correctness). Flop/turn
/// results ignore future streets; do not present them as GTO.
#[pyfunction]
fn solve_spot(
    py: Python<'_>,
    pot_bb: f64,
    effective_stack_bb: f64,
    board: Vec<String>,
    iterations: Option<u32>,
    max_bets: Option<u8>,
) -> PyResult<PyObject> {
    let board_u8: Vec<u8> = board.iter().filter_map(|s| parse_card_u8(s)).collect();
    if board_u8.len() == board.len() {
        reject_duplicate_cards(&board_u8)?;
    }
    let board_refs: Vec<&str> = board.iter().map(|s| s.as_str()).collect();
    let iters = iterations.unwrap_or(200);
    let bets  = max_bets.unwrap_or(2);
    let result =
        py.allow_threads(|| solve(pot_bb, effective_stack_bb, &board_refs, iters, bets));

    let combos = all_combos();

    let dict = pyo3::types::PyDict::new(py);

    let agg = pyo3::types::PyList::empty(py);
    for (name, freq) in &result.strategy {
        let e = pyo3::types::PyDict::new(py);
        e.set_item("action", name)?;
        e.set_item("freq", freq)?;
        agg.append(e)?;
    }
    dict.set_item("strategy", agg)?;

    let combo_list = pyo3::types::PyList::empty(py);
    for (ci, action, freq) in &result.combo_strats {
        let (ca, cb) = combos[*ci];
        let e = pyo3::types::PyDict::new(py);
        e.set_item("card_a", ca)?;
        e.set_item("card_b", cb)?;
        e.set_item("action", action)?;
        e.set_item("freq", freq)?;
        combo_list.append(e)?;
    }
    dict.set_item("combo_strategies", combo_list)?;
    dict.set_item("exploitability", result.exploitability)?;
    dict.set_item("iterations", result.iterations)?;
    Ok(dict.into())
}

#[pyfunction]
fn eval7(cards: Vec<u8>) -> PyResult<u16> {
    if cards.len() != 7 {
        return Err(pyo3::exceptions::PyValueError::new_err("need exactly 7 card indices"));
    }
    let arr: [u8; 7] = cards.try_into().unwrap();
    Ok(evaluate7(&arr))
}

/// Exact HU river equilibrium (gto-hu). Unlike `solve_spot` (gto-cuda,
/// single-street approximation), this is a genuinely correct river solve
/// with an EXACT exploitability number attached — fast enough to run live.
///
/// Returns {
///   "strategy": [{action, freq}],          // OOP (BB) root, range-aggregate
///   "exploitability": f64, "br_sb": f64, "br_bb": f64, "game_value_sb": f64,
///   "iterations": u32, "elapsed_secs": f64,
///   "actions": [str],                       // action labels at the root
///   "br_gain_sb": f64, "br_gain_bb": f64,   // per-player incentive to deviate
///   "nashconv": f64, "game_value_bb": f64,
///   "equity_sb": f64, "equity_bb": f64,     // range-vs-range equity at the river
///   "combos": [{card_a, card_b, freqs:[..], ev}] // per-combo root strategy + EV (in-range BB/OOP)
/// }
///
/// Optional inputs: `ip_weights`/`oop_weights` (1326 floats each, p0=SB/IP,
/// p1=BB/OOP), `bet_pcts`/`max_raises`/`pot_type` (StreetConfig overrides),
/// `rake_pct`/`rake_cap_bb` (RakeModel).
#[pyfunction]
#[pyo3(signature = (board, pot_bb, effective_stack_bb, iterations=None, ip_weights=None, oop_weights=None, bet_pcts=None, max_raises=None, pot_type=None, rake_pct=None, rake_cap_bb=None))]
fn solve_hu_river(
    py: Python<'_>,
    board: Vec<String>,
    pot_bb: f64,
    effective_stack_bb: f64,
    iterations: Option<u32>,
    ip_weights: Option<Vec<f64>>,
    oop_weights: Option<Vec<f64>>,
    bet_pcts: Option<Vec<u32>>,
    max_raises: Option<u8>,
    pot_type: Option<&str>,
    rake_pct: Option<f64>,
    rake_cap_bb: Option<f64>,
) -> PyResult<PyObject> {
    use gto_hu::game::BB;
    use gto_hu::ranges::all_combos;
    use gto_hu::solver::{CfrVariant, VectorRiverSolver};
    use gto_hu::tree::build_river_tree;
    use std::time::Instant;

    let iters = iterations.unwrap_or(5_000);
    let board_u8: Vec<u8> = board.iter().filter_map(|s| parse_card_u8(s)).collect();
    if board_u8.len() != 5 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "river board must have exactly 5 cards",
        ));
    }
    let mut seen = [false; 52];
    for &c in &board_u8 {
        if seen[c as usize] {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "duplicate card in board",
            ));
        }
        seen[c as usize] = true;
    }
    let board5: [u8; 5] = board_u8.try_into().unwrap();
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (effective_stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "pot must be positive and even (centi-bb); stack must be positive",
        ));
    }
    // Resolve all fallible inputs (config / rake / ranges) before releasing
    // the GIL — validation errors must surface as Python exceptions.
    let cfg = river_config(pot_type, bet_pcts, max_raises)?;
    let rake = rake_from_args(rake_pct, rake_cap_bb)?;
    let ranges = [
        range_from_weights(ip_weights, &board5)?,   // p0 = SB/IP
        range_from_weights(oop_weights, &board5)?,  // p1 = BB/OOP
    ];

    // Heavy compute: solve + exact best-response/exploitability + per-combo
    // strategy extraction — all plain Rust, so release the GIL throughout.
    let combos = all_combos();
    let out = py.allow_threads(|| {
        let tree = build_river_tree(pot, stack, &cfg);
        let mut solver =
            VectorRiverSolver::with_rake(tree, board5, ranges, CfrVariant::cfr_plus_default(), rake);
        let start = Instant::now();
        solver.run(iters);
        let elapsed = start.elapsed().as_secs_f64();
        let expl = solver.exploitability_bb();
        let game_value = expl.game_value[0];
        let root = solver.aggregate_strategy(0);
        let na = root.len();
        let combo_evs = solver.root_combo_evs(1);
        let equity_sb = solver.range_equity_p0();
        let mut combo_data = Vec::new();
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            // Root node actor is BB (p1) — filter by ITS range, not SB's.
            if solver.ranges[1].weights[c] == 0.0 {
                continue;
            }
            let s = solver.average_strategy(0, c);
            combo_data.push((ca, cb, s.iter().take(na).copied().collect::<Vec<f64>>(), combo_evs[c]));
        }
        HuSolveOutput { root, expl, game_value, elapsed, combo_data, equity_sb }
    });
    let HuSolveOutput { root, expl, game_value, elapsed, combo_data, equity_sb } = out;

    let dict = pyo3::types::PyDict::new(py);
    let agg = pyo3::types::PyList::empty(py);
    let actions = pyo3::types::PyList::empty(py);
    for (name, freq) in &root {
        let e = pyo3::types::PyDict::new(py);
        e.set_item("action", name)?;
        e.set_item("freq", freq)?;
        agg.append(e)?;
        actions.append(name)?;
    }
    dict.set_item("strategy", agg)?;
    dict.set_item("actions", actions)?;
    dict.set_item("exploitability", expl.exploitability)?;
    dict.set_item("br_sb", expl.br_value[0])?;
    dict.set_item("br_bb", expl.br_value[1])?;
    dict.set_item("game_value_sb", game_value)?;
    dict.set_item("iterations", iters)?;
    dict.set_item("elapsed_secs", elapsed)?;
    dict.set_item("br_gain_sb", expl.br_gain[0])?;
    dict.set_item("br_gain_bb", expl.br_gain[1])?;
    dict.set_item("nashconv", expl.nashconv)?;
    dict.set_item("game_value_bb", expl.game_value[1])?;
    dict.set_item("equity_sb", equity_sb)?;
    dict.set_item("equity_bb", 1.0 - equity_sb)?;

    let combo_list = pyo3::types::PyList::empty(py);
    for (ca, cb, freqs_vec, ev) in &combo_data {
        let e = pyo3::types::PyDict::new(py);
        e.set_item("card_a", card_string(*ca))?;
        e.set_item("card_b", card_string(*cb))?;
        let freqs = pyo3::types::PyList::empty(py);
        for &f in freqs_vec {
            freqs.append(f)?;
        }
        e.set_item("freqs", freqs)?;
        e.set_item("ev", *ev)?;
        combo_list.append(e)?;
    }
    dict.set_item("combos", combo_list)?;
    Ok(dict.into())
}

/// Exact HU turn+river equilibrium (gto-hu). The river is a public chance
/// node; the turn is sampled during training but exploitability and game
/// value are always computed by exact enumeration. ~30-40 s for 10k iters.
///
/// Same response shape as `solve_hu_river` (turn-root OOP strategy +
/// exact exploitability + per-combo turn strategies for a heatmap).
#[pyfunction]
#[pyo3(signature = (board, pot_bb, effective_stack_bb, iterations=None, seed=None, ip_weights=None, oop_weights=None, turn_bet_pcts=None, river_bet_pcts=None, max_raises=None, pot_type=None, rake_pct=None, rake_cap_bb=None))]
#[allow(clippy::too_many_arguments)]
fn solve_hu_turn_river(
    py: Python<'_>,
    board: Vec<String>,
    pot_bb: f64,
    effective_stack_bb: f64,
    iterations: Option<u32>,
    seed: Option<u64>,
    ip_weights: Option<Vec<f64>>,
    oop_weights: Option<Vec<f64>>,
    turn_bet_pcts: Option<Vec<u32>>,
    river_bet_pcts: Option<Vec<u32>>,
    max_raises: Option<u8>,
    pot_type: Option<&str>,
    rake_pct: Option<f64>,
    rake_cap_bb: Option<f64>,
) -> PyResult<PyObject> {
    use gto_hu::game::BB;
    use gto_hu::ranges::all_combos;
    use gto_hu::solver::{CfrVariant, ChanceMode, TurnRiverSolver};
    use gto_hu::tree::{build_turn_river_tree, TurnTreeConfig};
    use std::time::Instant;

    let iters = iterations.unwrap_or(10_000);
    let board_u8: Vec<u8> = board.iter().filter_map(|s| parse_card_u8(s)).collect();
    if board_u8.len() != 4 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "turn board must have exactly 4 cards",
        ));
    }
    let mut seen = [false; 52];
    for &c in &board_u8 {
        if seen[c as usize] {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "duplicate card in board",
            ));
        }
        seen[c as usize] = true;
    }
    let board4: [u8; 4] = board_u8.try_into().unwrap();
    let pot = (pot_bb * BB as f64).round() as i64;
    let stack = (effective_stack_bb * BB as f64).round() as i64;
    if pot <= 0 || pot % 2 != 0 || stack <= 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "pot must be positive and even (centi-bb); stack must be positive",
        ));
    }
    let mode = ChanceMode::Sample {
        seed: seed.unwrap_or(42),
    };

    // Resolve all fallible inputs (config / rake / ranges) before releasing
    // the GIL — validation errors must surface as Python exceptions.
    let mut cfg = match pot_type.unwrap_or("srp") {
        "srp" => TurnTreeConfig::srp(),
        "3bet" => TurnTreeConfig {
            turn: gto_hu::tree::StreetConfig::threebet_turn(),
            river: gto_hu::tree::StreetConfig::threebet_river(),
        },
        "4bet" => TurnTreeConfig {
            turn: gto_hu::tree::StreetConfig::fourbet_street(),
            river: gto_hu::tree::StreetConfig::fourbet_street(),
        },
        other => {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "unknown pot_type '{other}' (srp | 3bet | 4bet)"
            )))
        }
    };
    if let Some(p) = turn_bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err("turn_bet_pcts must be positive"));
        }
        cfg.turn.bet_pcts = p;
    }
    if let Some(p) = river_bet_pcts {
        if p.iter().any(|&x| x == 0) {
            return Err(pyo3::exceptions::PyValueError::new_err("river_bet_pcts must be positive"));
        }
        cfg.river.bet_pcts = p;
    }
    if let Some(m) = max_raises {
        cfg.turn.max_raises = m;
        cfg.river.max_raises = m;
    }
    let rake = rake_from_args(rake_pct, rake_cap_bb)?;
    let ranges = [
        range_from_weights(ip_weights, &board4)?,
        range_from_weights(oop_weights, &board4)?,
    ];

    // Heavy compute: solve (sampled chance) + exact enumerated exploitability +
    // per-combo turn strategies — all plain Rust, so release the GIL throughout.
    let combos = all_combos();
    let out = py.allow_threads(|| {
        let tree = build_turn_river_tree(pot, stack, &cfg);
        let mut solver =
            TurnRiverSolver::with_rake(tree, board4, ranges, CfrVariant::cfr_plus_default(), mode, rake);
        let start = Instant::now();
        solver.run(iters);
        let elapsed = start.elapsed().as_secs_f64();
        let expl = solver.exploitability_bb();
        let game_value = expl.game_value[0];
        let root = solver.aggregate_strategy(0, None);
        let na = root.len();
        let combo_evs = solver.root_combo_evs(1);
        let equity_sb = solver.range_equity_p0();
        let mut combo_data = Vec::new();
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.export_weight(1, None, c) == 0.0 {
                continue;
            }
            let s = solver.average_strategy(0, None, c);
            combo_data.push((ca, cb, s.iter().take(na).copied().collect::<Vec<f64>>(), combo_evs[c]));
        }
        HuSolveOutput { root, expl, game_value, elapsed, combo_data, equity_sb }
    });
    let HuSolveOutput { root, expl, game_value, elapsed, combo_data, equity_sb } = out;

    let dict = pyo3::types::PyDict::new(py);
    let agg = pyo3::types::PyList::empty(py);
    let actions = pyo3::types::PyList::empty(py);
    for (name, freq) in &root {
        let e = pyo3::types::PyDict::new(py);
        e.set_item("action", name)?;
        e.set_item("freq", freq)?;
        agg.append(e)?;
        actions.append(name)?;
    }
    dict.set_item("strategy", agg)?;
    dict.set_item("actions", actions)?;
    dict.set_item("exploitability", expl.exploitability)?;
    dict.set_item("br_sb", expl.br_value[0])?;
    dict.set_item("br_bb", expl.br_value[1])?;
    dict.set_item("game_value_sb", game_value)?;
    dict.set_item("iterations", iters)?;
    dict.set_item("elapsed_secs", elapsed)?;
    dict.set_item("br_gain_sb", expl.br_gain[0])?;
    dict.set_item("br_gain_bb", expl.br_gain[1])?;
    dict.set_item("nashconv", expl.nashconv)?;
    dict.set_item("game_value_bb", expl.game_value[1])?;
    dict.set_item("equity_sb", equity_sb)?;
    dict.set_item("equity_bb", 1.0 - equity_sb)?;

    let combo_list = pyo3::types::PyList::empty(py);
    for (ca, cb, freqs_vec, ev) in &combo_data {
        let e = pyo3::types::PyDict::new(py);
        e.set_item("card_a", card_string(*ca))?;
        e.set_item("card_b", card_string(*cb))?;
        let freqs = pyo3::types::PyList::empty(py);
        for &f in freqs_vec {
            freqs.append(f)?;
        }
        e.set_item("freqs", freqs)?;
        e.set_item("ev", *ev)?;
        combo_list.append(e)?;
    }
    dict.set_item("combos", combo_list)?;
    Ok(dict.into())
}

/// "Ah" style label for a `rank*4+suit` card index.
fn card_string(c: u8) -> String {
    const RANKS: [char; 13] = [
        '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A',
    ];
    const SUITS: [char; 4] = ['c', 'd', 'h', 's'];
    format!("{}{}", RANKS[(c / 4) as usize], SUITS[(c % 4) as usize])
}

#[pymodule]
fn gto_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(equity, m)?)?;
    m.add_function(wrap_pyfunction!(parse_card_fn, m)?)?;
    m.add_function(wrap_pyfunction!(solve_spot, m)?)?;
    m.add_function(wrap_pyfunction!(solve_hu_river, m)?)?;
    m.add_function(wrap_pyfunction!(solve_hu_turn_river, m)?)?;
    m.add_function(wrap_pyfunction!(eval7, m)?)?;
    Ok(())
}
