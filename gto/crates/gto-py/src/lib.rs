use pyo3::prelude::*;
use gto_core::card::Card;
use gto_core::{monte_carlo, parse_cards};
use gto_core::{solve, all_combos, evaluate7, solve_multistreet};
use gto_core::eval::parse_card as parse_card_u8;

#[pyfunction]
fn equity(
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
    let iters = iterations.unwrap_or(10_000);
    let result = monte_carlo(&hero_cards, &villain_cards, &board_cards, iters);
    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("hero_equity", result.hero_equity)?;
        dict.set_item("villain_equity", result.villain_equity)?;
        dict.set_item("tie", result.tie)?;
        dict.set_item("iterations", result.iterations)?;
        Ok(dict.into())
    })
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
    pot_bb: f64,
    effective_stack_bb: f64,
    board: Vec<String>,
    iterations: Option<u32>,
    max_bets: Option<u8>,
) -> PyResult<PyObject> {
    let board_refs: Vec<&str> = board.iter().map(|s| s.as_str()).collect();
    let iters = iterations.unwrap_or(200);
    let bets  = max_bets.unwrap_or(2);
    let result = solve(pot_bb, effective_stack_bb, &board_refs, iters, bets);

    let combos = all_combos();

    Python::with_gil(|py| {
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
    })
}

#[pyfunction]
fn eval7(cards: Vec<u8>) -> PyResult<u16> {
    if cards.len() != 7 {
        return Err(pyo3::exceptions::PyValueError::new_err("need exactly 7 card indices"));
    }
    let arr: [u8; 7] = cards.try_into().unwrap();
    Ok(evaluate7(&arr))
}

/// Single-street flop solve with external terminal EVs at NextStreet nodes.
/// `terminal_evs`: list of 5 lists, each of length 1326.
///   Index order matches tree NextStreet nodes (check-check, check-bet-call,
///   check-bet-raise-call, bet-call, bet-raise-call).
/// Returns {"strategy": [...], "exploitability": float}
#[pyfunction]
fn solve_flop_with_ev(
    pot_bb: f64,
    effective_stack_bb: f64,
    board: Vec<String>,
    terminal_evs: Vec<Vec<f64>>,
    iterations: Option<u32>,
) -> PyResult<PyObject> {
    use gto_core::{multistreet::SubgameSolver, range::Range, tree::Street, eval::parse_card as pc};

    let iters = iterations.unwrap_or(300);
    let pot   = (pot_bb   * 100.0) as i64;
    let stack = (effective_stack_bb * 100.0) as i64;
    let board_u8: Vec<u8> = board.iter().filter_map(|s| pc(s)).collect();
    if board_u8.len() != 3 {
        return Err(pyo3::exceptions::PyValueError::new_err("board must have 3 cards"));
    }

    let ranges = [Range::new_uniform(), Range::new_uniform()];
    let mut solver = SubgameSolver::new(pot, stack, board_u8, ranges, Street::Flop);

    // Inject external terminal EVs at NextStreet nodes
    let ns_ids = solver.next_street_node_ids();
    for (i, &nid) in ns_ids.iter().enumerate() {
        if let Some(ev_vec) = terminal_evs.get(i) {
            solver.next_evs.insert(nid, ev_vec.iter().map(|&v| v).collect());
        }
    }

    let expl = solver.run(iters);
    let strat = solver.root_strategy();

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        let agg  = pyo3::types::PyList::empty(py);
        for (name, freq) in &strat {
            let e = pyo3::types::PyDict::new(py);
            e.set_item("action", name)?;
            e.set_item("freq", freq)?;
            agg.append(e)?;
        }
        dict.set_item("strategy", agg)?;
        dict.set_item("exploitability", expl)?;
        Ok(dict.into())
    })
}

/// Full multi-street (flop→turn→river) GTO solve.
/// Returns {"strategy": [...], "exploitability": float}
#[pyfunction]
fn solve_spot_multistreet(
    pot_bb: f64,
    effective_stack_bb: f64,
    board: Vec<String>,
    iterations: Option<u32>,
) -> PyResult<PyObject> {
    let iters = iterations.unwrap_or(300);
    let board_u8: Vec<u8> = board.iter()
        .filter_map(|s| parse_card_u8(s))
        .collect();
    if board_u8.len() != 3 {
        return Err(pyo3::exceptions::PyValueError::new_err("board must have exactly 3 cards (flop)"));
    }
    let result = solve_multistreet(pot_bb, effective_stack_bb, &board_u8, iters);

    Python::with_gil(|py| {
        let dict = pyo3::types::PyDict::new(py);
        let agg = pyo3::types::PyList::empty(py);
        for (name, freq) in &result.flop_strategy {
            let e = pyo3::types::PyDict::new(py);
            e.set_item("action", name)?;
            e.set_item("freq", freq)?;
            agg.append(e)?;
        }
        dict.set_item("strategy", agg)?;
        dict.set_item("exploitability", result.exploitability)?;
        Ok(dict.into())
    })
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
///   "combos": [{card_a, card_b, freqs:[..]}]// per-combo root strategy (in-range)
/// }
#[pyfunction]
#[pyo3(signature = (board, pot_bb, effective_stack_bb, iterations=None))]
fn solve_hu_river(
    board: Vec<String>,
    pot_bb: f64,
    effective_stack_bb: f64,
    iterations: Option<u32>,
) -> PyResult<PyObject> {
    use gto_hu::game::BB;
    use gto_hu::ranges::all_combos;
    use gto_hu::solver::{CfrVariant, VectorRiverSolver};
    use gto_hu::tree::{build_river_tree, StreetConfig};
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

    let tree = build_river_tree(pot, stack, &StreetConfig::srp_river());
    let ranges = [
        gto_hu::ranges::uniform_excluding(&board5),
        gto_hu::ranges::uniform_excluding(&board5),
    ];
    let mut solver = VectorRiverSolver::new(tree, board5, ranges, CfrVariant::cfr_plus_default());
    let start = Instant::now();
    solver.run(iters);
    let elapsed = start.elapsed().as_secs_f64();
    let expl = solver.exploitability_bb();
    let game_value = solver.game_value_p0();
    let root = solver.aggregate_strategy(0);
    let combos = all_combos();
    let na = root.len();

    Python::with_gil(|py| {
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

        let combo_list = pyo3::types::PyList::empty(py);
        for (c, &(ca, cb)) in combos.iter().enumerate() {
            if solver.ranges[0].weights[c] == 0.0 {
                continue;
            }
            let s = solver.average_strategy(0, c);
            let e = pyo3::types::PyDict::new(py);
            e.set_item("card_a", card_string(ca))?;
            e.set_item("card_b", card_string(cb))?;
            let freqs = pyo3::types::PyList::empty(py);
            for &f in s.iter().take(na) {
                freqs.append(f)?;
            }
            e.set_item("freqs", freqs)?;
            combo_list.append(e)?;
        }
        dict.set_item("combos", combo_list)?;
        Ok(dict.into())
    })
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
    m.add_function(wrap_pyfunction!(solve_spot_multistreet, m)?)?;
    m.add_function(wrap_pyfunction!(solve_flop_with_ev, m)?)?;
    m.add_function(wrap_pyfunction!(solve_hu_river, m)?)?;
    m.add_function(wrap_pyfunction!(eval7, m)?)?;
    Ok(())
}
