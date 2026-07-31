//! Read the AGC's navigation state out of a yaAGC core dump, by symbol.
//!
//! Usage: `cargo run -p eagle-runtime --bin agc_state -- [core] [Luminary099.log]`
//!
//! Every value here comes straight from the AGC's erasable memory — no
//! downlink decoding, no frame anchoring, no b-scale search. Symbols
//! resolve through the same `SymTab` the pad-load generator uses, so a
//! renamed or moved erasable cannot silently read the wrong word.
use anyhow::{Context, Result};
use eagle_dynamics::constants::R_SITE;
use eagle_runtime::coredump::CoreDump;
use eagle_runtime::padload::SymTab;

/// Erasables worth printing for a descent, with their b-scales.
///
/// Scales are the ones this project has established and cited:
/// position `RN`/`RRECTLEM` b=27 m (RP-TO-R "METERS B-27 FOR MOON"),
/// velocity `VN` b=7 m/cs, `LAND`/`RLS` b=24 m, clocks b=28 cs,
/// `HDOTDISP`/`VDGVERT` b=7 m/cs (spike-B live read-back),
/// `HCALC` b=24 m (`SERVICER.agc:822-827`, "NEW HCALC*2(24)M").
const VECTORS: &[(&str, i32, &str)] = &[
    ("RN", 27, "state-vector position, MCI m"),
    ("VN", 7, "state-vector velocity, MCI m/cs"),
    ("LAND", 24, "landing site, m"),
    ("RGU", 24, "guidance-frame position, m"),
    ("VGU", 10, "guidance-frame velocity, m/cs"),
];

const SCALARS: &[(&str, i32, &str)] = &[
    ("HCALC", 24, "computed altitude, m"),
    ("HDOTDISP", 7, "displayed altitude rate, m/cs"),
    ("VDGVERT", 7, "commanded descent rate, m/cs"),
    ("TAUROD", 11, "ROD time constant, cs"),
    ("PIPTIME", 28, "state-vector time tag, cs"),
    ("TIME2", 28, "AGC clock, cs"),
];

fn mag(v: [f64; 3]) -> f64 {
    (v[0] * v[0] + v[1] * v[1] + v[2] * v[2]).sqrt()
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let core_path = args.first().map(String::as_str).unwrap_or("build/agc/core");
    let log_path = args
        .get(1)
        .map(String::as_str)
        .unwrap_or("build/agc/Luminary099.log");

    let dump = CoreDump::load(std::path::Path::new(core_path))?;
    let symtab = SymTab::from_listing(
        &std::fs::read_to_string(log_path).with_context(|| format!("reading {log_path}"))?,
    )?;

    println!("# {core_path}");
    for (sym, b, what) in SCALARS {
        match symtab.ecadr(sym).and_then(|e| dump.dp_at(e, *b)) {
            Some(v) => println!("{sym:<10} {v:>18.4}   {what}"),
            None => println!("{sym:<10} {:>18}   {what}", "(not found)"),
        }
    }
    println!();
    for (sym, b, what) in VECTORS {
        match symtab.ecadr(sym).and_then(|e| dump.vec_at(e, *b)) {
            Some(v) => {
                println!(
                    "{sym:<10} [{:>14.2},{:>14.2},{:>14.2}]  |v| {:>14.2}   {what}",
                    v[0],
                    v[1],
                    v[2],
                    mag(v)
                );
            }
            None => println!("{sym:<10} {:>18}   {what}", "(not found)"),
        }
    }

    // The two derived quantities item 3 is about.
    if let (Some(rn), Some(land)) = (
        symtab.ecadr("RN").and_then(|e| dump.vec_at(e, 27)),
        symtab.ecadr("LAND").and_then(|e| dump.vec_at(e, 24)),
    ) {
        println!();
        println!("|RN| - R_SITE      = {:>14.2} m", mag(rn) - R_SITE);
        println!("|RN| - |LAND|      = {:>14.2} m", mag(rn) - mag(land));
    }
    Ok(())
}
