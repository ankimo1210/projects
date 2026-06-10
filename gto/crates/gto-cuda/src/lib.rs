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

/// Group spot indices by (half_pot, effective_stack). All spots in a group can
/// share one game tree because the tree's node pots are a deterministic function
/// of the root pot and effective stack. First-appearance order is preserved so
/// the output ordering is stable and (for single-pot batches) identical to a
/// non-grouped solve.
fn group_spots(half_pots: &[f32], eff_stacks: &[f64]) -> Vec<Vec<usize>> {
    let mut keys: Vec<(u32, u64)> = Vec::new();
    let mut groups: Vec<Vec<usize>> = Vec::new();
    for i in 0..half_pots.len() {
        let key = (half_pots[i].to_bits(), eff_stacks[i].to_bits());
        match keys.iter().position(|&k| k == key) {
            Some(gi) => groups[gi].push(i),
            None => {
                keys.push(key);
                groups.push(vec![i]);
            }
        }
    }
    groups
}

// ---------------------------------------------------------------------------
// Python binding
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (spots, iterations=None, max_bets=None, ip_weights=None, oop_weights=None))]
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
    let nc    = NUM_COMBOS;

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

    let strength_vecs: Vec<Vec<u16>> = boards.par_iter()
        .map(|b| precompute_strengths(b))
        .collect();

    // Group spots by (half_pot, effective_stack). The game tree's node pots are
    // derived from the spot's pot/stack, so a single tree is only correct for
    // spots that share both. Mixed-pot batches (the production multistreet path)
    // would otherwise solve every spot except the first with the wrong pot (B1).
    let groups = group_spots(&half_pots, &eff_stacks);

    // Per-original-index result dicts, scattered back after each group solves.
    let mut results_by_index: Vec<Option<pyo3::Bound<'_, pyo3::types::PyDict>>> =
        (0..n).map(|_| None).collect();

    for idxs in groups {
        let g = idxs.len();
        // Build group-local flat arrays in group order.
        let mut hero_str = vec![0u16; g * nc];
        let mut ranges   = vec![1.0f32; g * nc];
        let mut g_half_pots = Vec::with_capacity(g);
        for (gi, &oi) in idxs.iter().enumerate() {
            let sv = &strength_vecs[oi];
            for ci in 0..nc {
                hero_str[gi * nc + ci] = sv[ci];
                if sv[ci] == 0 { ranges[gi * nc + ci] = 0.0; }
            }
            g_half_pots.push(half_pots[oi]);
        }
        let opp_str = hero_str.clone();

        // Apply custom range weights if provided (zero out blocked combos).
        let ip_reach: Vec<f32> = if let Some(ref iw) = ip_weights {
            (0..g * nc).map(|k| {
                if ranges[k] == 0.0 { 0.0 } else { iw[k % nc] }
            }).collect()
        } else {
            ranges.clone()
        };
        let oop_reach: Vec<f32> = if let Some(ref ow) = oop_weights {
            (0..g * nc).map(|k| {
                if ranges[k] == 0.0 { 0.0 } else { ow[k % nc] }
            }).collect()
        } else {
            ranges.clone()
        };

        // Use IP reach as the output filter (only report combos in hero's range).
        let output_ranges = ip_reach.clone();

        // Build the tree from THIS group's pot/stack (identical across the group).
        let pot0   = g_half_pots[0] as f64 * 2.0;
        let stack0 = eff_stacks[idxs[0]];
        let tree   = GameTree::build(pot0, stack0, bets);

        let mut solver = BatchCfrSolver::new(tree, hero_str, opp_str, output_ranges, g_half_pots);
        if ip_weights.is_some() || oop_weights.is_some() {
            solver.run_with_reach(iters, ip_reach, oop_reach);
        } else {
            solver.run(iters);
        }

        // Extract root EV per combo for backward induction (one CPU pass).
        let root_evs = solver.root_ev_per_spot(); // [g × NC] f32
        let root_strat = solver.root_strategy();

        for (gi, &oi) in idxs.iter().enumerate() {
            let d = pyo3::types::PyDict::new(py);

            let agg = pyo3::types::PyList::empty(py);
            for (action, freq) in &root_strat {
                let e = pyo3::types::PyDict::new(py);
                e.set_item("action", action)?;
                e.set_item("freq", *freq)?;
                agg.append(e)?;
            }
            d.set_item("strategy", agg)?;

            let combos = pyo3::types::PyList::empty(py);
            for (ca, cb, action, freq) in solver.combo_strategies(gi) {
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

            // Per-combo root EV slice for this spot [NC] → Python list<float>.
            let ev_slice = &root_evs[gi * nc .. (gi + 1) * nc];
            let ev_list = pyo3::types::PyList::new(py, ev_slice.iter().map(|&v| v as f64))?;
            d.set_item("root_ev", ev_list)?;

            results_by_index[oi] = Some(d);
        }
    }

    let results = pyo3::types::PyList::empty(py);
    for d in results_by_index {
        results.append(d.expect("every spot assigned to a group"))?;
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
    let nc    = NUM_COMBOS;

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

    let strength_vecs: Vec<Vec<u16>> = boards.par_iter()
        .map(|b| precompute_strengths(b))
        .collect();

    // Group spots by (half_pot, effective_stack): one tree is only correct for
    // spots sharing both, otherwise non-first spots solve with the wrong pot (B1).
    let groups = group_spots(&half_pots, &eff_stacks);

    let mut results_by_index: Vec<Option<pyo3::Bound<'_, pyo3::types::PyDict>>> =
        (0..n).map(|_| None).collect();

    for idxs in groups {
        let g = idxs.len();
        let mut hero_str = vec![0u16; g * nc];
        let mut ranges   = vec![1.0f32; g * nc];
        let mut g_half_pots = Vec::with_capacity(g);
        for (gi, &oi) in idxs.iter().enumerate() {
            let sv = &strength_vecs[oi];
            for ci in 0..nc {
                hero_str[gi * nc + ci] = sv[ci];
                if sv[ci] == 0 { ranges[gi * nc + ci] = 0.0; }
            }
            g_half_pots.push(half_pots[oi]);
        }
        let opp_str = hero_str.clone();

        let pot0   = g_half_pots[0] as f64 * 2.0;
        let stack0 = eff_stacks[idxs[0]];
        let tree   = match bet_pct {
            Some(pct) => cfr::GameTree::build_single(pot0, stack0, pct, 2.5, bets),
            None      => cfr::GameTree::build(pot0, stack0, bets),
        };

        let mut solver = FastCfrSolver::new(&tree, hero_str, opp_str, ranges.clone(), g_half_pots);
        solver.run(iters);

        let root_evs = solver.root_ev_per_spot();
        let strat    = solver.root_strategy();

        for (gi, &oi) in idxs.iter().enumerate() {
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
            let ev_slice = &root_evs[gi * nc .. (gi + 1) * nc];
            let ev_list  = pyo3::types::PyList::new(py, ev_slice.iter().map(|&v| v as f64))?;
            d.set_item("root_ev", ev_list)?;
            results_by_index[oi] = Some(d);
        }
    }

    let results = pyo3::types::PyList::empty(py);
    for d in results_by_index {
        results.append(d.expect("every spot assigned to a group"))?;
    }
    Ok(results.into())
}

#[pymodule]
fn gto_cuda(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(batch_solve_rust, m)?)?;
    m.add_function(wrap_pyfunction!(batch_solve_fast, m)?)?;
    Ok(())
}
