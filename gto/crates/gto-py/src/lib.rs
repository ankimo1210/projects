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

#[pymodule]
fn gto_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(equity, m)?)?;
    m.add_function(wrap_pyfunction!(parse_card_fn, m)?)?;
    m.add_function(wrap_pyfunction!(solve_spot, m)?)?;
    m.add_function(wrap_pyfunction!(solve_spot_multistreet, m)?)?;
    m.add_function(wrap_pyfunction!(solve_flop_with_ev, m)?)?;
    m.add_function(wrap_pyfunction!(eval7, m)?)?;
    Ok(())
}
