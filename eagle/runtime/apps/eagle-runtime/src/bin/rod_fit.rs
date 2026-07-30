//! Offline estimator for the effective P66 ROD time constant.
//!
//! Reads a telemetry JSONL written by `EAGLE_TELEM_OUT` and fits the slope
//! of the rope's P66 force law
//! (`vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1041-1050`)
//!
//! ```text
//!   a_cmd = [ (VDGVERT - HDOTDISP) / TAUROD + g ] / cos(tilt)
//! ```
//!
//! `VDGVERT` is not telemetered. Differencing across one `HDOTDISP`
//! repaint cancels it and the gravity term — leaving
//! `d(a_cmd·cosθ) = -(1/tau)·d(HDOTDISP)` — **but only where `VDGVERT` is
//! constant across the difference.**
//!
//! Differencing rather than a level regression is deliberate: `agc_hdot_ms`
//! is parsed from the DSKY display (`sim.rs:122`), which repaints about
//! once a second, while telemetry is 10 Hz. Regressing fresh 10 Hz
//! `a_cmd` on a ~1 Hz staircase is errors-in-variables and attenuates the
//! slope toward zero — i.e. it would make a fast loop look slow.
//!
//! # This does NOT resolve runs 4-6
//!
//! Measured 2026-07-31: r² = 0.15 / 0.05 / 0.04 on
//! `telem-m1-run{4,5,6}.jsonl`, i.e. no usable fit. The cause is the
//! constant-`VDGVERT` premise: those scenarios drive a ROD *schedule*
//! (`pdi-descent.toml`, e.g. run 4's `[[245,-5.3],[50,-0.3],[12,0.7]]`),
//! so the sim is clicking `VDGVERT` throughout the fitted window and the
//! cancellation does not happen. The tool is kept because it is correct
//! for a segment with no clicks, and because a future run that telemeters
//! the cumulative click count can subtract the ramp and recover the fit.
//! Do not quote a tau from it without checking r².
//!
//! Usage: `cargo run -p eagle-runtime --bin rod_fit -- <telem.jsonl>...`

use std::env;
use std::fs::File;
use std::io::{BufRead, BufReader};

use anyhow::{bail, Context, Result};
use eagle_dynamics::constants::{DPS_MIN_N, THRUST_N_PER_PULSE};

/// One repaint-instant observation.
#[derive(Debug, Clone, Copy)]
pub struct Sample {
    #[allow(dead_code)]
    pub t_s: f64,
    /// Commanded acceleration projected back onto the vertical, m/s².
    pub a_cmd_cos: f64,
    /// The AGC's own displayed altitude rate, m/s.
    pub hdot_ms: f64,
    /// Cumulative signed ROD clicks at this frame. `None` on traces
    /// written before the field existed (M1 runs 1-6).
    pub rod_clicks_cum: Option<i64>,
}

#[derive(Debug, Clone, Copy)]
pub struct Fit {
    pub tau_s: f64,
    pub slope: f64,
    pub r2: f64,
    pub n: usize,
}

/// OLS of `Δ(a_cmd·cosθ)` on `ΔHDOTDISP` between consecutive samples.
/// Returns `None` if fewer than 8 usable differences survive.
pub fn fit_tau(samples: &[Sample]) -> Option<Fit> {
    // Only differences across a real rate change carry signal; a repaint
    // that did not move the display is all noise and no leverage.
    const MIN_DHDOT_MS: f64 = 0.5;
    let mut dx = Vec::new();
    let mut dy = Vec::new();
    for w in samples.windows(2) {
        let d_h = w[1].hdot_ms - w[0].hdot_ms;
        if d_h.abs() < MIN_DHDOT_MS {
            continue;
        }
        dx.push(d_h);
        dy.push(w[1].a_cmd_cos - w[0].a_cmd_cos);
    }
    if dx.len() < 8 {
        return None;
    }
    let n = dx.len() as f64;
    let mx = dx.iter().sum::<f64>() / n;
    let my = dy.iter().sum::<f64>() / n;
    let sxx: f64 = dx.iter().map(|x| (x - mx) * (x - mx)).sum();
    let sxy: f64 = dx.iter().zip(&dy).map(|(x, y)| (x - mx) * (y - my)).sum();
    if sxx <= 0.0 {
        return None;
    }
    let slope = sxy / sxx;
    if slope >= 0.0 {
        // A rate loop must push back: a non-negative slope means the model
        // does not describe this data, and a "tau" from it is meaningless.
        return None;
    }
    let intercept = my - slope * mx;
    let ss_tot: f64 = dy.iter().map(|y| (y - my) * (y - my)).sum();
    let ss_res: f64 = dx
        .iter()
        .zip(&dy)
        .map(|(x, y)| {
            let e = y - (slope * x + intercept);
            e * e
        })
        .sum();
    let r2 = if ss_tot > 0.0 {
        1.0 - ss_res / ss_tot
    } else {
        0.0
    };
    Some(Fit {
        tau_s: -1.0 / slope,
        slope,
        r2,
        n: dx.len(),
    })
}

/// One ROD click moves VDGVERT by 1 ft/s — live-verified in spike B and
/// carried as `RODSCALE` in `scenarios/p66-padload.toml`.
const ROD_CLICK_MS: f64 = 0.3048;

/// Fit tau with VDGVERT reconstructed from the click count.
///
/// This is the PRIMARY method and it needs `rod_clicks_cum`. Writing
/// `VDGVERT(t) = VDGVERT_0 + k·(clicks(t) - clicks_0)`, the rope's law
///
/// ```text
///   a_cmd·cosθ = (VDGVERT - HDOTDISP)/tau + g
/// ```
///
/// becomes a straight line in the fully-observed regressor
/// `x = k·Δclicks - HDOTDISP`:
///
/// ```text
///   y = x/tau + (VDGVERT_0/tau + g)
/// ```
///
/// so `tau = 1/slope`, and the intercept recovers VDGVERT_0 as a
/// consistency check (it must land near the AGC's rate at P66 entry).
/// Unlike `fit_tau` this needs no segment of constant VDGVERT, which is
/// what made the differencing method unusable on the M1 runs.
pub fn fit_tau_with_clicks(samples: &[Sample]) -> Option<Fit> {
    let clicks0 = samples.first()?.rod_clicks_cum?;
    let pts: Vec<(f64, f64)> = samples
        .iter()
        .filter_map(|s| {
            let c = s.rod_clicks_cum?;
            let x = ROD_CLICK_MS * (c - clicks0) as f64 - s.hdot_ms;
            Some((x, s.a_cmd_cos))
        })
        .collect();
    if pts.len() < 8 {
        return None;
    }
    let n = pts.len() as f64;
    let mx = pts.iter().map(|p| p.0).sum::<f64>() / n;
    let my = pts.iter().map(|p| p.1).sum::<f64>() / n;
    let sxx: f64 = pts.iter().map(|p| (p.0 - mx) * (p.0 - mx)).sum();
    let sxy: f64 = pts.iter().map(|p| (p.0 - mx) * (p.1 - my)).sum();
    if sxx <= 0.0 {
        return None;
    }
    let slope = sxy / sxx;
    if slope <= 0.0 {
        // More thrust must follow a larger (commanded - actual) rate
        // error. A non-positive slope means the model does not describe
        // this data, and a "tau" from it would be meaningless.
        return None;
    }
    let intercept = my - slope * mx;
    let ss_tot: f64 = pts.iter().map(|p| (p.1 - my) * (p.1 - my)).sum();
    let ss_res: f64 = pts
        .iter()
        .map(|p| {
            let e = p.1 - (slope * p.0 + intercept);
            e * e
        })
        .sum();
    let r2 = if ss_tot > 0.0 {
        1.0 - ss_res / ss_tot
    } else {
        0.0
    };
    Some(Fit {
        tau_s: 1.0 / slope,
        slope,
        r2,
        n: pts.len(),
    })
}

/// Pull the P66 segment out of a telemetry JSONL, keeping only frames
/// where the throttle is off both stops (the law is linear only there) and
/// only the first frame after each `HDOTDISP` change (a repaint).
fn load(path: &str, max_force_n: f64) -> Result<Vec<Sample>> {
    let file = File::open(path).with_context(|| format!("open {path}"))?;
    let mut out = Vec::new();
    let mut last_hdot: Option<f64> = None;
    let mut in_p66 = false;
    for line in BufReader::new(file).lines() {
        let line = line?;
        let Ok(v) = serde_json::from_str::<serde_json::Value>(&line) else {
            continue;
        };
        if v.get("type").and_then(|t| t.as_str()) != Some("telemetry") {
            continue;
        }
        if v.get("mm").and_then(|m| m.as_str()) == Some("66") {
            in_p66 = true;
        }
        if !in_p66 || v.get("touchdown").map(|t| !t.is_null()).unwrap_or(false) {
            continue;
        }
        let (Some(hdot), Some(pulses), Some(mass), Some(tilt)) = (
            v.get("agc_hdot_ms").and_then(|x| x.as_f64()),
            v.get("throttle_cmd_pulses").and_then(|x| x.as_i64()),
            v.get("mass_kg").and_then(|x| x.as_f64()),
            v.get("tilt_deg").and_then(|x| x.as_f64()),
        ) else {
            continue;
        };
        // Repaint detector: the display only moves when the AGC repaints.
        if last_hdot == Some(hdot) {
            continue;
        }
        last_hdot = Some(hdot);
        let force_n = pulses as f64 * THRUST_N_PER_PULSE;
        // Off both stops: at either stop the command is clipped and the
        // slope carries no information about tau.
        if force_n <= DPS_MIN_N * 1.02 || force_n >= max_force_n * 0.98 {
            continue;
        }
        if mass <= 0.0 {
            continue;
        }
        let cos = tilt.to_radians().cos();
        out.push(Sample {
            t_s: v.get("t_s").and_then(|x| x.as_f64()).unwrap_or(0.0),
            a_cmd_cos: force_n / mass * cos,
            hdot_ms: hdot,
            rod_clicks_cum: v.get("rod_clicks_cum").and_then(|x| x.as_i64()),
        });
    }
    Ok(out)
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        bail!("usage: rod_fit <telem.jsonl>...");
    }
    // MAXFORCE as the runs actually flew it: the committed pad load's
    // 42500 N (scenarios/p66-padload.toml MAXFORCE), not DPS_FTP_N.
    const FLOWN_MAXFORCE_N: f64 = 42_500.0;
    for path in &args {
        let samples = load(path, FLOWN_MAXFORCE_N)?;
        println!("{path}: {} unsaturated P66 repaints", samples.len());
        match fit_tau_with_clicks(&samples) {
            Some(f) => println!(
                "  clicks (PRIMARY): tau = {:.4} s   r2 {:.3}, n {}",
                f.tau_s, f.r2, f.n
            ),
            None => println!(
                "  clicks (PRIMARY): no fit -- needs rod_clicks_cum, \
                 absent from traces written before 2026-07-31"
            ),
        }
        match fit_tau(&samples) {
            Some(f) => println!(
                "  differencing (cross-check): tau = {:.4} s   r2 {:.3}, n {}",
                f.tau_s, f.r2, f.n
            ),
            None => println!("  differencing (cross-check): no fit"),
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Synthesize `a_cmd·cosθ` from the rope's law with a known tau and a
    /// VDGVERT step partway through, sampled only at repaint instants.
    fn synth(tau_s: f64) -> Vec<Sample> {
        const G: f64 = 1.62;
        let mut out = Vec::new();
        for i in 0..60 {
            let t_s = i as f64 * 0.9;
            // A limit-cycle-ish rate history: swings tens of m/s.
            let hdot_ms = -7.0 + 12.0 * (t_s * 0.6).sin();
            // VDGVERT steps once, at the halfway point: -3.0 m/s, then
            // one click's worth (1 ft/s) lower.
            let clicks: i64 = if i < 30 { 0 } else { -1 };
            let vdg = -3.0 + 0.3048 * clicks as f64;
            let a_cmd_cos = (vdg - hdot_ms) / tau_s + G;
            out.push(Sample {
                t_s,
                a_cmd_cos,
                hdot_ms,
                rod_clicks_cum: Some(clicks),
            });
        }
        out
    }

    #[test]
    fn fit_recovers_a_known_tau() {
        let fit = fit_tau(&synth(1.5)).expect("enough samples");
        assert!(
            (fit.tau_s - 1.5).abs() < 0.05,
            "recovered tau {} from a synthetic 1.5 s segment",
            fit.tau_s
        );
        assert!(fit.r2 > 0.99, "r2 {}", fit.r2);
    }

    #[test]
    fn fit_separates_the_two_candidate_scales() {
        let fast = fit_tau(&synth(0.1875)).expect("enough samples");
        let slow = fit_tau(&synth(1.5)).expect("enough samples");
        assert!(
            fast.tau_s < 0.4 && slow.tau_s > 0.8,
            "the b=14 and b=11 hypotheses must not be confusable: {} vs {}",
            fast.tau_s,
            slow.tau_s
        );
    }

    #[test]
    fn fit_needs_samples() {
        assert!(fit_tau(&[]).is_none());
        assert!(fit_tau_with_clicks(&[]).is_none());
    }

    #[test]
    fn click_fit_recovers_tau_through_a_vdgvert_change() {
        // The case that defeats `fit_tau`: VDGVERT moves inside the
        // window. Reconstructing it from the click count makes the same
        // data a clean straight line.
        for want in [0.1875, 0.375, 1.5] {
            let fit = fit_tau_with_clicks(&synth(want)).expect("enough samples");
            assert!(
                (fit.tau_s - want).abs() < 0.01,
                "recovered {} for a synthetic {want} s loop",
                fit.tau_s
            );
            assert!(fit.r2 > 0.99, "r2 {} at tau {want}", fit.r2);
        }
    }

    #[test]
    fn click_fit_declines_traces_without_the_field() {
        // M1 runs 1-6 predate `rod_clicks_cum`; the fitter must say so
        // rather than silently fall back to a biased answer.
        let mut old_trace = synth(1.5);
        for s in &mut old_trace {
            s.rod_clicks_cum = None;
        }
        assert!(fit_tau_with_clicks(&old_trace).is_none());
    }
}
