pub mod cuda_ffi;
pub mod kernels;
pub mod cfr;
pub mod fast_cfr;

pub use cfr::{BatchCfrSolver, GameTree, NUM_COMBOS, BET_SIZES};

use gto_core::card::Card as ECard;
use gto_core::evaluate7;
use pyo3::prelude::*;
use rayon::prelude::*;

// ---------------------------------------------------------------------------
// Hand strength precomputation
// ---------------------------------------------------------------------------

fn precompute_strengths(board_ints: &[u8]) -> Vec<u16> {
    let (ca, cb) = cfr::combo_tables();
    (0..NUM_COMBOS).map(|i| {
        let a = ca[i]; let b = cb[i];
        if board_ints.contains(&a) || board_ints.contains(&b) { return 0; }
        let mut c7 = [0u8; 7];
        c7[0] = a; c7[1] = b;
        for (j, &bc) in board_ints.iter().enumerate().take(5) { c7[2+j] = bc; }
        evaluate7(&c7)
    }).collect()
}

// ---------------------------------------------------------------------------
// Python binding
// ---------------------------------------------------------------------------

#[pyfunction]
fn batch_solve_rust(
    py: Python<'_>,
    spots: Vec<pyo3::Bound<'_, pyo3::types::PyDict>>,
    iterations: Option<u32>,
    max_bets: Option<u8>,
    ip_weights: Option<Vec<f32>>,   // per-combo reach for IP player [1326]
    oop_weights: Option<Vec<f32>>,  // per-combo reach for OOP player [1326]
) -> PyResult<PyObject> {
    let iters = iterations.unwrap_or(300);
    let bets  = max_bets.unwrap_or(2);
    let n     = spots.len();

    let mut boards:     Vec<Vec<u8>> = Vec::with_capacity(n);
    let mut half_pots:  Vec<f32>     = Vec::with_capacity(n);
    let mut eff_stacks: Vec<f64>     = Vec::with_capacity(n);

    for spot in &spots {
        let board_py: Vec<String> = spot.get_item("board")?.unwrap().extract()?;
        let board_ints: Vec<u8> = board_py.iter()
            .filter_map(|s| ECard::from_str(s).map(|c| c.0))
            .collect();
        let pot_bb: f64 = spot.get_item("pot_bb")?.unwrap().extract()?;
        let eff_bb: f64 = spot.get_item("effective_stack_bb")?.unwrap().extract()?;
        half_pots.push((pot_bb / 2.0) as f32);
        eff_stacks.push(eff_bb);
        boards.push(board_ints);
    }

    let nc = NUM_COMBOS;
    let strength_vecs: Vec<Vec<u16>> = boards.par_iter()
        .map(|b| precompute_strengths(b))
        .collect();

    let mut hero_str = vec![0u16; n * nc];
    let mut ranges   = vec![1.0f32; n * nc];
    for (i, sv) in strength_vecs.iter().enumerate() {
        for ci in 0..nc {
            hero_str[i * nc + ci] = sv[ci];
            if sv[ci] == 0 { ranges[i * nc + ci] = 0.0; }
        }
    }
    let opp_str = hero_str.clone();

    // Apply custom range weights if provided (zero out blocked combos)
    let ip_reach: Vec<f32> = if let Some(ref iw) = ip_weights {
        (0..n * nc).map(|k| {
            if ranges[k] == 0.0 { 0.0 } else { iw[k % nc] }
        }).collect()
    } else {
        ranges.clone()
    };
    let oop_reach: Vec<f32> = if let Some(ref ow) = oop_weights {
        (0..n * nc).map(|k| {
            if ranges[k] == 0.0 { 0.0 } else { ow[k % nc] }
        }).collect()
    } else {
        ranges.clone()
    };

    // Use IP reach as the output filter (only report combos in hero's range)
    let output_ranges = ip_reach.clone();

    let pot0   = half_pots[0] as f64 * 2.0;
    let stack0 = eff_stacks[0];
    let tree   = GameTree::build(pot0, stack0, bets);

    let mut solver = BatchCfrSolver::new(tree, hero_str, opp_str, output_ranges, half_pots);
    if ip_weights.is_some() || oop_weights.is_some() {
        solver.run_with_reach(iters, ip_reach, oop_reach);
    } else {
        solver.run(iters);
    }

    // Extract root EV per combo for backward induction (one CPU pass)
    let root_evs = solver.root_ev_per_spot(); // [N × NC] f32

    let results = pyo3::types::PyList::empty(py);
    let nc = cfr::NUM_COMBOS;
    for i in 0..n {
        let d = pyo3::types::PyDict::new(py);

        let agg = pyo3::types::PyList::empty(py);
        for (action, freq) in solver.root_strategy() {
            let e = pyo3::types::PyDict::new(py);
            e.set_item("action", &action)?;
            e.set_item("freq", freq)?;
            agg.append(e)?;
        }
        d.set_item("strategy", agg)?;

        let combos = pyo3::types::PyList::empty(py);
        for (ca, cb, action, freq) in solver.combo_strategies(i) {
            let e = pyo3::types::PyDict::new(py);
            e.set_item("card_a", ca)?;
            e.set_item("card_b", cb)?;
            e.set_item("action", &action)?;
            e.set_item("freq", freq)?;
            combos.append(e)?;
        }
        d.set_item("combo_strategies", combos)?;
        d.set_item("exploitability", 0.0f64)?;
        d.set_item("iterations", iters)?;

        // Per-combo root EV slice for this spot [NC] → Python list<float>
        let ev_slice = &root_evs[i * nc .. (i + 1) * nc];
        let ev_list = pyo3::types::PyList::new(py, ev_slice.iter().map(|&v| v as f64))?;
        d.set_item("root_ev", ev_list)?;

        results.append(d)?;
    }
    Ok(results.into())
}

/// Fast solver using fully GPU-accelerated iterative traversal.
///
/// `bet_pct`: single bet size as % of pot (e.g. 50 for flop, 75 for turn/river).
///            If None, uses legacy multi-bet tree (33/75/100).
#[pyfunction]
fn batch_solve_fast(
    py: Python<'_>,
    spots: Vec<pyo3::Bound<'_, pyo3::types::PyDict>>,
    iterations: Option<u32>,
    max_bets: Option<u8>,
    bet_pct: Option<u8>,
) -> PyResult<PyObject> {
    use fast_cfr::FastCfrSolver;

    let iters = iterations.unwrap_or(300);
    let bets  = max_bets.unwrap_or(2);
    let n     = spots.len();

    let mut boards:     Vec<Vec<u8>> = Vec::with_capacity(n);
    let mut half_pots:  Vec<f32>     = Vec::with_capacity(n);
    let mut eff_stacks: Vec<f64>     = Vec::with_capacity(n);

    for spot in &spots {
        let board_py: Vec<String> = spot.get_item("board")?.unwrap().extract()?;
        let board_ints: Vec<u8> = board_py.iter()
            .filter_map(|s| ECard::from_str(s).map(|c| c.0))
            .collect();
        let pot_bb: f64 = spot.get_item("pot_bb")?.unwrap().extract()?;
        let eff_bb: f64 = spot.get_item("effective_stack_bb")?.unwrap().extract()?;
        half_pots.push((pot_bb / 2.0) as f32);
        eff_stacks.push(eff_bb);
        boards.push(board_ints);
    }

    let nc = NUM_COMBOS;
    let strength_vecs: Vec<Vec<u16>> = boards.par_iter()
        .map(|b| precompute_strengths(b))
        .collect();

    let mut hero_str = vec![0u16; n * nc];
    let mut ranges   = vec![1.0f32; n * nc];
    for (i, sv) in strength_vecs.iter().enumerate() {
        for ci in 0..nc {
            hero_str[i * nc + ci] = sv[ci];
            if sv[ci] == 0 { ranges[i * nc + ci] = 0.0; }
        }
    }
    let opp_str = hero_str.clone();

    let pot0   = half_pots[0] as f64 * 2.0;
    let stack0 = eff_stacks[0];
    let tree   = match bet_pct {
        Some(pct) => cfr::GameTree::build_single(pot0, stack0, pct, 2.5, bets),
        None      => cfr::GameTree::build(pot0, stack0, bets),
    };

    let mut solver = FastCfrSolver::new(&tree, hero_str, opp_str, ranges.clone(), half_pots);
    solver.run(iters);

    let root_evs = solver.root_ev_per_spot();
    let strat    = solver.root_strategy();

    let results = pyo3::types::PyList::empty(py);
    for i in 0..n {
        let d   = pyo3::types::PyDict::new(py);
        let agg = pyo3::types::PyList::empty(py);
        for (action, freq) in &strat {
            let e = pyo3::types::PyDict::new(py);
            e.set_item("action", action)?;
            e.set_item("freq", freq)?;
            agg.append(e)?;
        }
        d.set_item("strategy", agg)?;
        d.set_item("exploitability", 0.0f64)?;
        d.set_item("iterations", iters)?;
        let ev_slice = &root_evs[i * nc .. (i + 1) * nc];
        let ev_list  = pyo3::types::PyList::new(py, ev_slice.iter().map(|&v| v as f64))?;
        d.set_item("root_ev", ev_list)?;
        results.append(d)?;
    }
    Ok(results.into())
}

#[pymodule]
fn gto_cuda(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(batch_solve_rust, m)?)?;
    m.add_function(wrap_pyfunction!(batch_solve_fast, m)?)?;
    Ok(())
}
