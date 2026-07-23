//! Thin CLI wrapper around `eagle_runtime::padload`'s pad-load generation.
//! All real logic (b-scale table, state math, TOML rendering) lives in
//! `padload.rs` so it's reachable from library code too (e.g. a future
//! ScenarioRunner calling generation at runtime, not just this binary).
//!
//! ```text
//! cargo run -p eagle-runtime --bin padload_gen -- \
//!   --site-lat-deg 0.674 --site-lon-deg 23.473 \
//!   --alt-m 500 --vz-ms 0.0 --epoch-cs 0 --out scenarios/p66-padload.toml
//! ```
use anyhow::{Context, Result};
use clap::Parser;
use eagle_runtime::padload::{
    check_bscales, generate_p66_manifest, render_manifest_toml, P66ScenarioInputs,
};
use std::path::PathBuf;

/// Generate a first-cut P66 pad-load manifest (TOML) from scenario
/// parameters. b-scales are working hypotheses (see
/// `eagle_runtime::padload::P66_BSCALE_TABLE`); by default this refuses
/// to emit a manifest containing any UNVERIFIED b-scale -- pass
/// `--allow-unverified` while Spike A iterates against the live AGC.
#[derive(Parser)]
struct Args {
    #[arg(long)]
    site_lat_deg: f64,
    #[arg(long)]
    site_lon_deg: f64,
    #[arg(long)]
    alt_m: f64,
    #[arg(long)]
    vz_ms: f64,
    #[arg(long)]
    epoch_cs: f64,
    #[arg(long)]
    out: PathBuf,
    #[arg(long, default_value_t = false)]
    allow_unverified: bool,
}

fn main() -> Result<()> {
    let args = Args::parse();
    check_bscales(args.allow_unverified)?;

    let manifest = generate_p66_manifest(&P66ScenarioInputs {
        site_lat_deg: args.site_lat_deg,
        site_lon_deg: args.site_lon_deg,
        alt_m: args.alt_m,
        vz_ms: args.vz_ms,
        epoch_cs: args.epoch_cs,
    });
    let toml_text = render_manifest_toml(&manifest, args.allow_unverified)?;

    if let Some(parent) = args.out.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .with_context(|| format!("creating {}", parent.display()))?;
        }
    }
    std::fs::write(&args.out, toml_text)
        .with_context(|| format!("writing {}", args.out.display()))?;
    eprintln!(
        "padload_gen: wrote {} ({} words)",
        args.out.display(),
        manifest.word.len()
    );
    Ok(())
}
