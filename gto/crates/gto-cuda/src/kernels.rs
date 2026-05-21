/// CUDA kernel source strings (compiled at runtime via NVRTC for sm_120).

/// Batch showdown kernel: computes EV for N_spots × NUM_COMBOS simultaneously.
/// Grid: (ceil(NUM_COMBOS/256), N_spots, 1)
/// Block: (256, 1, 1)
pub const BATCH_SHOWDOWN: &str = r#"
extern "C" __global__ void batch_showdown(
    const unsigned short* __restrict__ hero_str,  // [N_spots × NC]
    const unsigned short* __restrict__ opp_str,   // [N_spots × NC]
    const unsigned char*  __restrict__ card_a,    // [NC]
    const unsigned char*  __restrict__ card_b,    // [NC]
    const float*          __restrict__ opp_weight,// [N_spots × NC]
    float*                             result,    // [N_spots × NC]
    const float*          __restrict__ half_pots, // [N_spots]
    int N_spots,
    int NC
) {
    int hero_i = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int spot   = (int)blockIdx.y;
    if (hero_i >= NC || spot >= N_spots) return;

    int base = spot * NC;
    unsigned char ca = card_a[hero_i];
    unsigned char cb = card_b[hero_i];
    unsigned short hs = hero_str[base + hero_i];
    if (hs == 0) { result[base + hero_i] = 0.0f; return; }

    float ev = 0.0f, total = 0.0f;
    float hp = half_pots[spot];

    for (int j = 0; j < NC; j++) {
        unsigned char oa = card_a[j], ob = card_b[j];
        if (oa == ca || oa == cb || ob == ca || ob == cb) continue;
        float ow = opp_weight[base + j];
        if (ow == 0.0f) continue;
        unsigned short os = opp_str[base + j];
        float outcome = (hs > os) ? hp : (hs < os) ? -hp : 0.0f;
        ev    += outcome * ow;
        total += ow;
    }
    result[base + hero_i] = (total > 0.0f) ? ev / total : 0.0f;
}
"#;

/// Regret-matching kernel: compute strategy from cumulative regrets.
/// One thread per (spot, combo), reads regrets for all actions.
/// Grid: (ceil(N_spots × NC / 256), 1, 1)
/// Block: (256, 1, 1)
pub const REGRET_MATCH: &str = r#"
extern "C" __global__ void regret_match(
    const double* __restrict__ regrets,  // [N_actions × N_spots × NC]
    float*                     strategy, // [N_actions × N_spots × NC]
    int N_actions,
    int N_spots,
    int NC
) {
    int idx = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;

    // Sum positive regrets across actions
    float pos_sum = 0.0f;
    for (int a = 0; a < N_actions; a++) {
        float r = (float)regrets[a * total + idx];
        if (r > 0.0f) pos_sum += r;
    }

    float uniform = 1.0f / (float)N_actions;
    for (int a = 0; a < N_actions; a++) {
        float r = (float)regrets[a * total + idx];
        strategy[a * total + idx] = (pos_sum > 0.0f) ? fmaxf(r, 0.0f) / pos_sum : uniform;
    }
}
"#;

/// Regret update kernel: update cumulative regrets from action values and EV.
/// One thread per (spot, combo).
/// Grid: (ceil(N_spots × NC / 256), 1, 1)
pub const REGRET_UPDATE: &str = r#"
extern "C" __global__ void regret_update(
    double*       __restrict__ regrets,       // [N_actions × N_spots × NC] (in/out)
    const float*  __restrict__ action_vals,   // [N_actions × N_spots × NC]
    const float*  __restrict__ ev,            // [N_spots × NC]
    const float*  __restrict__ opp_reach,     // [N_spots × NC]
    float alpha_w,
    float beta_w,
    int N_actions,
    int N_spots,
    int NC
) {
    int idx = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;

    float ev_i    = ev[idx];
    float opp_w   = opp_reach[idx];

    for (int a = 0; a < N_actions; a++) {
        double old_r = regrets[a * total + idx];
        double delta = (double)((action_vals[a * total + idx] - ev_i) * opp_w);
        double new_r;
        if (old_r >= 0.0) {
            new_r = old_r * (double)alpha_w + delta;
        } else {
            new_r = old_r * (double)beta_w  + delta;
        }
        regrets[a * total + idx] = new_r;
    }
}
"#;

/// EV reduction: ev[node] = sum_a strategy[a] * ev[child_a]
/// Called bottom-up at Action nodes.
/// Grid: (ceil(N_spots × NC / 256), 1, 1)
pub const REDUCE_EV: &str = r#"
extern "C" __global__ void reduce_ev(
    const float* __restrict__ strategy,   // [N_actions × N_spots × NC]
    const float* __restrict__ child_evs,  // [N_actions × N_spots × NC]
    float*                    node_ev,    // [N_spots × NC]
    int N_actions,
    int N_spots,
    int NC
) {
    int idx = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;

    float ev = 0.0f;
    for (int a = 0; a < N_actions; a++) {
        ev += strategy[a * total + idx] * child_evs[a * total + idx];
    }
    node_ev[idx] = ev;
}
"#;

/// Fold terminal EV: ev = sign × pot/2  (broadcast across all spots/combos)
/// sign = +1 if winner == traverser, -1 otherwise
/// Grid: (ceil(N_spots × NC / 256), 1, 1)
pub const FOLD_EV: &str = r#"
extern "C" __global__ void fold_ev(
    float*      node_ev,    // [N_spots × NC]
    const float* half_pots, // [N_spots]
    int    sign,            // +1 or -1
    int    N_spots,
    int    NC
) {
    int idx   = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;
    int spot  = idx / NC;
    node_ev[idx] = (float)sign * half_pots[spot];
}
"#;

/// Top-down reach propagation: child_reach[a][i] = parent_reach[i] × strategy[a][i]
/// Grid: (ceil(N_spots × NC / 256), 1, 1)
pub const SPREAD_REACH: &str = r#"
extern "C" __global__ void spread_reach(
    const float* __restrict__ parent_reach, // [N_spots × NC]
    const float* __restrict__ strategy,     // [N_actions × N_spots × NC]
    float*                    child_reach,  // [N_actions × N_spots × NC]
    int N_actions,
    int N_spots,
    int NC
) {
    int idx   = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;

    for (int a = 0; a < N_actions; a++) {
        child_reach[a * total + idx] = parent_reach[idx] * strategy[a * total + idx];
    }
}
"#;

/// Strategy sum update kernel.
pub const STRATEGY_SUM_UPDATE: &str = r#"
extern "C" __global__ void strategy_sum_update(
    double*       __restrict__ strat_sum,  // [N_actions × N_spots × NC] (in/out)
    const float*  __restrict__ strategy,   // [N_actions × N_spots × NC]
    const float*  __restrict__ reach,      // [N_spots × NC]
    float beta_w,
    int N_actions,
    int N_spots,
    int NC
) {
    int idx = (int)(blockIdx.x * blockDim.x + threadIdx.x);
    int total = N_spots * NC;
    if (idx >= total) return;

    float r = reach[idx];
    for (int a = 0; a < N_actions; a++) {
        strat_sum[a * total + idx] += (double)(strategy[a * total + idx] * r * beta_w);
    }
}
"#;
