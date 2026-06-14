/// GPU-accelerated Discounted CFR.
///
/// Design: iterative (not recursive) tree traversal using a pre-computed
/// topological ordering. Eliminates Python overhead and enables GPU overlap.
///
/// Arrays layout: (N_spots × NUM_COMBOS) flat, row-major.

use std::collections::HashMap;
use std::ffi::c_void;

use crate::cuda_ffi::{
    CUdeviceptr, CUfunction, CUmodule,
    mem_alloc, mem_free, memcpy_htod, memcpy_dtoh, ctx_sync, launch_kernel,
    compile_and_load, get_function, set_current,
};
use crate::kernels::{BATCH_SHOWDOWN, REGRET_MATCH, REGRET_UPDATE, STRATEGY_SUM_UPDATE};

pub const NUM_COMBOS: usize = 1326;
const ALPHA: f64 = 1.5;
const BETA:  f64 = 0.0;
pub const BET_SIZES: &[u8] = &[33, 75, 100];

fn discount(t: u32, exp: f64) -> f64 {
    if exp == 0.0 { return 1.0; }
    let tf = t as f64;
    tf.powf(exp) / (tf.powf(exp) + 1.0)
}

// ---------------------------------------------------------------------------
// Combo tables
// ---------------------------------------------------------------------------

pub fn combo_tables() -> (Vec<u8>, Vec<u8>) {
    let mut ca = Vec::with_capacity(NUM_COMBOS);
    let mut cb = Vec::with_capacity(NUM_COMBOS);
    for a in 0u8..51 {
        for b in (a+1)..52 {
            ca.push(a);
            cb.push(b);
        }
    }
    (ca, cb)
}

// ---------------------------------------------------------------------------
// Game tree
// ---------------------------------------------------------------------------

#[derive(Clone, Debug)]
pub enum NodeKind {
    Action { actor: u8 },
    FoldTerminal { winner: u8 },
    Showdown,
}

#[derive(Clone, Debug)]
pub struct Node {
    pub kind:     NodeKind,
    pub pot:      f64,
    pub bet_count: u8,
    pub children: Vec<(String, usize)>,
}

pub struct GameTree {
    pub nodes: Vec<Node>,
}

impl GameTree {
    /// Legacy multi-bet-size tree (33/75/100% pot, max_bets bets per street).
    pub fn build(pot: f64, stack: f64, max_bets: u8) -> Self {
        Self::build_multi(pot, stack, max_bets, BET_SIZES)
    }

    /// Configurable tree: pass any set of bet-size percentages.
    pub fn build_multi(pot: f64, stack: f64, max_bets: u8, bet_sizes: &[u8]) -> Self {
        let mut t = GameTree { nodes: vec![] };
        t.nodes.push(Node { kind: NodeKind::Action { actor: 0 }, pot, bet_count: 0, children: vec![] });
        t.expand_multi(0, [stack; 2], [0.0; 2], max_bets, bet_sizes, /* raise_mult */ 2.5);
        t
    }

    /// Single-bet-size tree matching gto-core's Street/CFR structure.
    /// `bet_pct`: e.g. 50 for flop, 75 for turn/river.  `max_raises` = 1 means bet→raise→call/fold only.
    pub fn build_single(pot: f64, stack: f64, bet_pct: u8, raise_mult: f64, max_bets_total: u8) -> Self {
        let mut t = GameTree { nodes: vec![] };
        t.nodes.push(Node { kind: NodeKind::Action { actor: 0 }, pot, bet_count: 0, children: vec![] });
        t.expand_multi(0, [stack; 2], [0.0; 2], max_bets_total, &[bet_pct], raise_mult);
        t
    }

    fn expand(&mut self, id: usize, stacks: [f64; 2], bets: [f64; 2], max_bets: u8) {
        self.expand_multi(id, stacks, bets, max_bets, BET_SIZES, 2.5);
    }

    fn expand_multi(&mut self, id: usize, stacks: [f64; 2], bets: [f64; 2],
                    max_bets: u8, bet_sizes: &[u8], raise_mult: f64) {
        let pot = self.nodes[id].pot;
        let bc  = self.nodes[id].bet_count;
        let actor = match self.nodes[id].kind { NodeKind::Action { actor } => actor, _ => return };
        let opp   = 1 - actor as usize;
        let a     = actor as usize;
        let facing = bets[opp] > bets[a];
        let mut ch = vec![];

        if facing {
            // Fold
            let fi = self.nodes.len();
            self.nodes.push(Node { kind: NodeKind::FoldTerminal { winner: opp as u8 }, pot, bet_count: bc, children: vec![] });
            ch.push(("Fold".into(), fi));

            // Call
            let call = (bets[opp] - bets[a]).min(stacks[a]);
            let ci = self.nodes.len();
            self.nodes.push(Node { kind: NodeKind::Showdown, pot: pot + call, bet_count: bc, children: vec![] });
            ch.push(("Call".into(), ci));

            // Raise
            if bc < max_bets {
                // Raise size = raise_mult × opponent's current bet (relative to pot)
                let raise_total = bets[opp] * raise_mult;
                let ramt        = (raise_total - bets[a]).min(stacks[a]);
                if ramt > 0.0 {
                    let mut ns = stacks; ns[a] -= ramt;
                    let mut nb = bets;   nb[a] += ramt;
                    let ri = self.nodes.len();
                    self.nodes.push(Node { kind: NodeKind::Action { actor: opp as u8 }, pot: pot + ramt, bet_count: bc + 1, children: vec![] });
                    self.expand_multi(ri, ns, nb, max_bets, bet_sizes, raise_mult);
                    ch.push(("Raise".into(), ri));
                }
            }
        } else {
            // Check
            if actor == 0 {
                let ci = self.nodes.len();
                self.nodes.push(Node { kind: NodeKind::Action { actor: 1 }, pot, bet_count: bc, children: vec![] });
                self.expand_multi(ci, stacks, bets, max_bets, bet_sizes, raise_mult);
                ch.push(("Check".into(), ci));
            } else {
                let ci = self.nodes.len();
                self.nodes.push(Node { kind: NodeKind::Showdown, pot, bet_count: bc, children: vec![] });
                ch.push(("Check".into(), ci));
            }
            // Bet
            if bc < max_bets {
                for &pct in bet_sizes {
                    let bamt = (pot * pct as f64 / 100.0).min(stacks[a]);
                    if bamt <= 0.0 { continue; }
                    let mut ns = stacks; ns[a] -= bamt;
                    let mut nb = bets;   nb[a] += bamt;
                    let bi = self.nodes.len();
                    self.nodes.push(Node { kind: NodeKind::Action { actor: opp as u8 }, pot: pot + bamt, bet_count: bc + 1, children: vec![] });
                    self.expand_multi(bi, ns, nb, max_bets, bet_sizes, raise_mult);
                    let action_name = if bet_sizes.len() == 1 { "Bet".to_string() } else { format!("Bet{pct}") };
                    ch.push((action_name, bi));
                }
            }
        }
        self.nodes[id].children = ch;
    }

    /// Topological order (leaves first, root last) for bottom-up traversal.
    pub fn topo_order(&self) -> Vec<usize> {
        let n = self.nodes.len();
        let mut visited = vec![false; n];
        let mut order   = Vec::with_capacity(n);
        let mut stack   = vec![0usize];
        while let Some(id) = stack.pop() {
            if visited[id] { continue; }
            visited[id] = true;
            for (_, child) in &self.nodes[id].children {
                if !visited[*child] { stack.push(*child); }
            }
            order.push(id);
        }
        order.reverse(); // leaves first
        order
    }
}

// ---------------------------------------------------------------------------
// Compiled kernels (lazy-init, cached per thread)
// ---------------------------------------------------------------------------

#[derive(Clone, Copy)]
struct Kernels {
    _m: [CUmodule; 4],
    showdown:    CUfunction,
    regret_match:   CUfunction,
    regret_update:  CUfunction,
    strategy_sum:   CUfunction,
}

thread_local! {
    // Compiled once per thread and reused across solver instances. The CUDA
    // context is thread-bound, so kernels JIT-compiled on a worker thread are
    // valid for that thread's lifetime. Previously every BatchCfrSolver::new
    // recompiled all 4 NVRTC kernels and loaded 4 CUmodules (never unloaded),
    // wasting hundreds of ms per solve and leaking module handles.
    static KERNELS: Kernels = Kernels::init();
}

impl Kernels {
    fn init() -> Self {
        let (m1, _) = compile_and_load(BATCH_SHOWDOWN,      "showdown",  "sm_120");
        let (m2, _) = compile_and_load(REGRET_MATCH,        "regret",    "sm_120");
        let (m3, _) = compile_and_load(REGRET_UPDATE,       "rupdate",   "sm_120");
        let (m4, _) = compile_and_load(STRATEGY_SUM_UPDATE, "ssupdate",  "sm_120");
        Kernels {
            showdown:       get_function(m1, "batch_showdown"),
            regret_match:   get_function(m2, "regret_match"),
            regret_update:  get_function(m3, "regret_update"),
            strategy_sum:   get_function(m4, "strategy_sum_update"),
            _m: [m1, m2, m3, m4],
        }
    }

    /// Per-thread cached kernels. The caller must have bound the CUDA context to
    /// this thread first (`set_current()`), which BatchCfrSolver::new does.
    fn cached() -> Self {
        KERNELS.with(|k| *k)
    }
}

// ---------------------------------------------------------------------------
// Solver
// ---------------------------------------------------------------------------

pub struct BatchCfrSolver {
    pub tree:   GameTree,
    pub n:      usize,  // N_spots
    k:          Kernels,

    // Static GPU buffers
    g_hero:  CUdeviceptr, // [N × NC] u16
    g_opp:   CUdeviceptr, // [N × NC] u16
    g_ca:    CUdeviceptr, // [NC] u8
    g_cb:    CUdeviceptr, // [NC] u8

    // Per-Showdown-node half-pot vectors [N] f32, precomputed once at setup.
    // The pot is a node constant; after a bet/call the showdown is valued at
    // the node pot, not the root pot. Keyed by node id.
    g_hpot_nodes: HashMap<usize, CUdeviceptr>, // node_id -> [N] f32

    // Persistent scratch GPU buffers — allocated once, reused every showdown call
    g_scratch_ow:     CUdeviceptr, // [N × NC] f32  opp_reach upload
    g_scratch_result: CUdeviceptr, // [N × NC] f32  showdown result

    // Per-node: regret [na×N×NC f64], strat_sum [na×N×NC f64], strat [na×N×NC f32]
    regrets:   HashMap<usize, Vec<f64>>,
    strat_sums:HashMap<usize, Vec<f64>>,

    // Scratch host buffers (reused)
    scratch_ev:   Vec<f32>,   // [N×NC]
    scratch_strat:Vec<f32>,   // [na×N×NC] max
    opp_weight_host: Vec<f32>,// [N×NC]

    // ranges for result extraction
    pub ranges: Vec<f32>,   // [N×NC]
}

impl BatchCfrSolver {
    pub fn new(
        tree:      GameTree,
        hero_str:  Vec<u16>,  // [N×NC]
        opp_str:   Vec<u16>,
        ranges:    Vec<f32>,  // [N×NC]
        half_pots: Vec<f32>,  // [N]
    ) -> Self {
        // Bind the CUDA context to the calling thread before any module load /
        // allocation — `new` may run on a worker thread that did not create the
        // context (B9). Idempotent and cheap.
        set_current();
        let n   = half_pots.len();
        let nc  = NUM_COMBOS;
        let k   = Kernels::cached();
        let (ca, cb) = combo_tables();

        let g_hero = mem_alloc(n * nc * 2); memcpy_htod(g_hero, &hero_str);
        let g_opp  = mem_alloc(n * nc * 2); memcpy_htod(g_opp,  &opp_str);
        let g_ca   = mem_alloc(nc);          memcpy_htod(g_ca,   &ca);
        let g_cb   = mem_alloc(nc);          memcpy_htod(g_cb,   &cb);

        // Precompute per-Showdown-node half-pot vectors. The root half-pots
        // are per spot; a showdown reached after a bet/call is valued at that
        // node's pot. Since all spots in this solver share one tree, the pot
        // ratio (node.pot / root.pot) is identical across spots, so we scale
        // the per-spot root half-pots by that ratio. Uploaded once (no
        // per-iteration HtoD on the hot path).
        let root_pot = tree.nodes[0].pot;
        let mut g_hpot_nodes: HashMap<usize, CUdeviceptr> = HashMap::new();
        for (nid, nd) in tree.nodes.iter().enumerate() {
            if let NodeKind::Showdown = nd.kind {
                let scale = (nd.pot / root_pot) as f32;
                let v: Vec<f32> = half_pots.iter().map(|&hp| hp * scale).collect();
                let p = mem_alloc(n * 4);
                memcpy_htod(p, &v);
                g_hpot_nodes.insert(nid, p);
            }
        }

        let flat = n * nc;
        // Pre-allocate persistent scratch GPU buffers (no alloc/free per call)
        let g_scratch_ow     = mem_alloc(flat * 4);
        let g_scratch_result = mem_alloc(flat * 4);

        BatchCfrSolver {
            n, tree, k,
            g_hero, g_opp, g_ca, g_cb,
            g_hpot_nodes,
            g_scratch_ow, g_scratch_result,
            regrets:    HashMap::new(),
            strat_sums: HashMap::new(),
            scratch_ev:   vec![0f32; flat],
            scratch_strat:vec![0f32; 8 * flat],
            opp_weight_host: vec![1.0f32; flat],
            ranges,
        }
    }

    fn flat(&self) -> usize { self.n * NUM_COMBOS }

    fn ensure_node(&mut self, id: usize, na: usize) {
        let size = na * self.flat();
        self.regrets.entry(id).or_insert_with(|| vec![0.0f64; size]);
        self.strat_sums.entry(id).or_insert_with(|| vec![0.0f64; size]);
    }

    fn current_strategy(&self, id: usize, na: usize) -> Vec<f32> {
        let flat = self.flat();
        let reg  = &self.regrets[&id];
        let mut strat = vec![0.0f32; na * flat];
        for i in 0..flat {
            let pos_sum: f64 = (0..na).map(|a| reg[a*flat+i].max(0.0)).sum();
            for a in 0..na {
                strat[a*flat+i] = if pos_sum > 0.0 {
                    (reg[a*flat+i].max(0.0) / pos_sum) as f32
                } else {
                    1.0 / na as f32
                };
            }
        }
        strat
    }

    /// Run DCFR for `iters` iterations. Returns elapsed seconds.
    pub fn run(&mut self, iters: u32) {
        set_current();
        // Seed the root reach from the per-spot ranges (which zero board-blocked
        // combos) instead of uniform 1.0 — otherwise a blocked opponent combo
        // (strength 0) enters showdown with reach 1.0 and scores as a guaranteed
        // hero win (B2). `ranges` already zeroes the blocked combos.
        let reach = self.ranges.clone();

        for t in 1..=iters {
            let aw = discount(t, ALPHA) as f32;
            let bw = discount(t, BETA)  as f32;
            for player in 0u8..2 {
                self.traverse_player(player, &reach, &reach, aw, bw);
            }
        }
        ctx_sync();
    }

    /// Run DCFR with explicit initial reach weights per player.
    /// ip_reach / oop_reach: per-combo weights [N×NC], range [0, 1].
    pub fn run_with_reach(&mut self, iters: u32, ip_reach: Vec<f32>, oop_reach: Vec<f32>) {
        set_current();
        for t in 1..=iters {
            let aw = discount(t, ALPHA) as f32;
            let bw = discount(t, BETA)  as f32;
            // player 0 = IP: traverser reach = ip_reach, opp reach = oop_reach
            self.traverse_player(0, &ip_reach, &oop_reach, aw, bw);
            // player 1 = OOP: traverser reach = oop_reach, opp reach = ip_reach
            self.traverse_player(1, &oop_reach, &ip_reach, aw, bw);
        }
        ctx_sync();
    }

    fn traverse_player(&mut self, traverser: u8,
                       reach: &[f32], opp_reach: &[f32],
                       aw: f32, bw: f32) -> Vec<f32> {
        self.traverse(0, traverser, reach, opp_reach, aw, bw)
    }

    fn traverse(&mut self, node_id: usize, traverser: u8,
                reach: &[f32], opp_reach: &[f32],
                aw: f32, bw: f32) -> Vec<f32> {
        let flat = self.flat();
        let node = self.tree.nodes[node_id].clone();

        match &node.kind {
            NodeKind::FoldTerminal { winner } => {
                let val = node.pot as f32 / 2.0;
                let sign = if *winner == traverser { val } else { -val };
                vec![sign; flat]
            }

            NodeKind::Showdown => {
                self.gpu_showdown(node_id, traverser, opp_reach)
            }

            NodeKind::Action { actor } => {
                let actor = *actor;
                let na    = node.children.len();
                self.ensure_node(node_id, na);

                let strat = self.current_strategy(node_id, na);

                if actor == traverser {
                    let mut action_vals = vec![vec![0.0f32; flat]; na];
                    for (ai, (_, child_id)) in node.children.iter().enumerate() {
                        let mut new_reach = reach.to_vec();
                        for i in 0..flat { new_reach[i] *= strat[ai*flat+i]; }
                        action_vals[ai] = self.traverse(*child_id, traverser, &new_reach, opp_reach, aw, bw);
                    }

                    let mut ev = vec![0.0f32; flat];
                    for ai in 0..na {
                        for i in 0..flat { ev[i] += strat[ai*flat+i] * action_vals[ai][i]; }
                    }

                    // Update regrets (DCFR)
                    let reg = self.regrets.get_mut(&node_id).unwrap();
                    for ai in 0..na {
                        for i in 0..flat {
                            let delta = (action_vals[ai][i] - ev[i]) * opp_reach[i];
                            if reg[ai*flat+i] >= 0.0 {
                                reg[ai*flat+i] = reg[ai*flat+i] * aw as f64 + delta as f64;
                            } else {
                                reg[ai*flat+i] = reg[ai*flat+i] * bw as f64 + delta as f64;
                            }
                        }
                    }
                    ev
                } else {
                    // Update strategy sum
                    let ss = self.strat_sums.get_mut(&node_id).unwrap();
                    for ai in 0..na {
                        for i in 0..flat {
                            ss[ai*flat+i] += strat[ai*flat+i] as f64 * reach[i] as f64 * bw as f64;
                        }
                    }
                    // Recurse
                    let mut ev = vec![0.0f32; flat];
                    for (ai, (_, child_id)) in node.children.iter().enumerate() {
                        let mut new_opp = opp_reach.to_vec();
                        for i in 0..flat { new_opp[i] *= strat[ai*flat+i]; }
                        let child_ev = self.traverse(*child_id, traverser, reach, &new_opp, aw, bw);
                        for i in 0..flat { ev[i] += strat[ai*flat+i] * child_ev[i]; }
                    }
                    ev
                }
            }
        }
    }

    /// Test/diagnostic hook: evaluate the showdown kernel at `node_id` with an
    /// explicit opponent reach vector and return per-(spot,combo) values. Exposes
    /// the same path the solver uses internally so the GPU showdown can be diffed
    /// against the CPU reference.
    pub fn showdown_values_at(&mut self, node_id: usize, traverser: u8, opp_reach: &[f32]) -> Vec<f32> {
        set_current();
        let v = self.gpu_showdown(node_id, traverser, opp_reach);
        ctx_sync();
        v
    }

    fn gpu_showdown(&mut self, node_id: usize, traverser: u8, opp_reach: &[f32]) -> Vec<f32> {
        let flat   = self.flat();
        let nc     = NUM_COMBOS as i32;
        let ns     = self.n as i32;
        let block  = 256u32;
        let grid_x = (NUM_COMBOS as u32 + block - 1) / block;
        let grid_y = self.n as u32;

        // Reuse persistent GPU buffers — no alloc/free, no ctx_sync in hot loop
        memcpy_htod(self.g_scratch_ow, opp_reach);

        let (g_hs, g_os) = if traverser == 0 {
            (self.g_hero, self.g_opp)
        } else {
            (self.g_opp, self.g_hero)
        };

        // Value the showdown at THIS node's pot (precomputed once at setup),
        // not the root pot — otherwise every post-bet/post-call showdown is
        // valued at the root half-pot (B3).
        let g_hpot = self.g_hpot_nodes[&node_id];

        unsafe {
            launch_kernel(
                self.k.showdown,
                (grid_x, grid_y, 1),
                (block, 1, 1),
                &[
                    &g_hs as *const _ as *mut c_void,
                    &g_os as *const _ as *mut c_void,
                    &self.g_ca as *const _ as *mut c_void,
                    &self.g_cb as *const _ as *mut c_void,
                    &self.g_scratch_ow     as *const _ as *mut c_void,
                    &self.g_scratch_result as *const _ as *mut c_void,
                    &g_hpot as *const _ as *mut c_void,
                    &ns as *const _ as *mut c_void,
                    &nc as *const _ as *mut c_void,
                ],
            );
        }
        // No ctx_sync here — sync once at end of run()

        let mut result = vec![0.0f32; flat];
        memcpy_dtoh(&mut result, self.g_scratch_result);
        result
    }

    /// Extract aggregate strategy at root (averaged over combos and spots).
    pub fn root_strategy(&self) -> Vec<(String, f64)> {
        let node = &self.tree.nodes[0];
        let na   = node.children.len();
        let flat = self.flat();

        let Some(ss) = self.strat_sums.get(&0) else {
            return node.children.iter().map(|(n,_)| (n.clone(), 1.0/na as f64)).collect();
        };

        let mut out = vec![];
        for (ai, (name, _)) in node.children.iter().enumerate() {
            let total: f64 = (0..flat).map(|i| {
                (0..na).map(|a| ss[a*flat+i]).sum::<f64>()
            }).sum();
            let s: f64 = (0..flat).map(|i| ss[ai*flat+i]).sum();
            out.push((name.clone(), if total > 0.0 { s / total } else { 1.0/na as f64 }));
        }
        out
    }

    /// Extract per-combo strategies for all N spots.
    pub fn combo_strategies(&self, spot: usize) -> Vec<(u8, u8, String, f32)> {
        let node = &self.tree.nodes[0];
        let na   = node.children.len();
        let nc   = NUM_COMBOS;
        let (ca, cb) = combo_tables();

        let Some(ss) = self.strat_sums.get(&0) else { return vec![]; };

        let mut out = vec![];
        for ci in 0..nc {
            let i = spot * nc + ci;
            if self.ranges[i] == 0.0 { continue; }
            let total: f64 = (0..na).map(|a| ss[a*(self.n*nc)+i]).sum();
            if total == 0.0 { continue; }
            for (ai, (name, _)) in node.children.iter().enumerate() {
                let freq = (ss[ai*(self.n*nc)+i] / total) as f32;
                if freq > 0.001 {
                    out.push((ca[ci], cb[ci], name.clone(), freq));
                }
            }
        }
        out
    }

    /// Compute root EV per combo for each spot (for backward induction).
    /// Returns flat Vec<f32> of length N × NUM_COMBOS (player-0 perspective).
    /// Call after `run()` has converged.
    pub fn root_ev_per_spot(&mut self) -> Vec<f32> {
        // Seed reach from ranges so blocked opponent combos (strength 0, reach 0)
        // do not enter the showdown normalizer as phantom wins (B2).
        let reach = self.ranges.clone();
        self.traverse(0, 0, &reach, &reach, 1.0, 1.0)
    }
}

impl Drop for BatchCfrSolver {
    fn drop(&mut self) {
        for p in [
            self.g_hero, self.g_opp, self.g_ca, self.g_cb,
            self.g_scratch_ow, self.g_scratch_result,
        ] {
            mem_free(p);
        }
        for (_, p) in &self.g_hpot_nodes { mem_free(*p); }
    }
}
