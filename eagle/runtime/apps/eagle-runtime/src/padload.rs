//! yaYUL symbol-table parsing and pad-load manifest resolution (Task 5).
//!
//! `SymTab` parses the ECADR-bearing lines of a yaYUL assembly listing.
//! See `docs/agc-channel-map.md` ("Symbol Table / ECADR Notation") for the
//! notation rule (switched `E<bank>,<offset>` vs unswitched plain octal)
//! and the citations backing it. `PadloadManifest` is a TOML pad-load
//! description (raw octal word, or a physical value + B-scale resolved via
//! `eagle_agc_protocol::words::to_pulses`) resolved against a `SymTab` (by
//! symbol) or an explicit ECADR (by `addr`) into `PadWord`s, which
//! `script::DskyScript::load_erasable` uplinks over V21N01.

use anyhow::{anyhow, bail, Context, Result};
use eagle_agc_protocol::words::{dp_encode, sp_encode, to_pulses};
use eagle_dynamics::constants::{DPS_FTP_N, DPS_MIN_N, R_SITE};
use eagle_dynamics::frames::{mci_to_mcmf, Mci, Mcmf, V3};
use std::collections::HashMap;
use std::path::Path;

/// Parsed yaYUL symbol table: symbol name -> ECADR (0..=0o3777).
///
/// Recognizes the two symbol-DEFINITION line shapes yaYUL prints (see
/// `docs/agc-channel-map.md`): `ERASE` (one address column) and `EQUALS`
/// (two — a throwaway running location counter, then the resolved
/// address). Every listing line, including blank/comment/header lines, is
/// prefixed `%06d,%06d: ` (a line-counter pair, *not* an address —
/// `vendor/virtualagc/yaYUL/Pass.c:1744`); that prefix is discarded, not
/// parsed.
///
/// Known limitation (acceptable for the fixture-driven scope of this
/// parser): a numeric-constant `EQUALS` definition (yaYUL's 7-digit `C`
/// symbol-table type, e.g. `RHCSCFLG EQUALS 0000313` — not a memory
/// address at all) would be mis-parsed as a small unswitched-erasable
/// ECADR if fed through `from_listing`, because both look like bare octal
/// tokens. The curated fixture contains no such lines; a full-listing
/// parser would need to distinguish them (e.g. by tracking the `C`/`E`/`F`
/// type letter yaYUL prints in its "SUMMARY OF SYMBOL TABLE LISTINGS").
#[derive(Debug, Default, Clone)]
pub struct SymTab {
    by_name: HashMap<String, u16>,
}

impl SymTab {
    pub fn from_listing(text: &str) -> Result<SymTab> {
        let mut by_name = HashMap::new();
        for line in text.lines() {
            // The trailing `\t# comment` column never contains ERASE/EQUALS
            // for a real definition line; drop it before tokenizing so
            // comment text can't be mistaken for a code token.
            let code = line.split('\t').next().unwrap_or(line);
            let tokens: Vec<&str> = code.split_whitespace().collect();
            let Some(kw_idx) = tokens.iter().position(|t| *t == "ERASE" || *t == "EQUALS") else {
                continue;
            };
            if kw_idx < 2 {
                continue; // no address column present (e.g. bare "X EQUALS")
            }
            let name = tokens[kw_idx - 1];
            let addr_tok = tokens[kw_idx - 2];
            if let Some(ecadr) = parse_ecadr(addr_tok) {
                by_name.insert(name.to_string(), ecadr);
            }
        }
        Ok(SymTab { by_name })
    }

    pub fn ecadr(&self, symbol: &str) -> Option<u16> {
        self.by_name.get(symbol).copied()
    }
}

/// Parse one yaYUL erasable-address column: `E<bank>,<offset>` (switched,
/// `offset` in 1400-1777 octal) or plain octal (unswitched, 0000-1377).
/// `None` for anything else (fixed-bank `bb,oooo`, 7-digit constants, or
/// malformed tokens) — see the `SymTab` doc comment for the one known
/// false-positive case this does *not* reject.
fn parse_ecadr(tok: &str) -> Option<u16> {
    if let Some(rest) = tok.strip_prefix('E') {
        let (bank_s, offset_s) = rest.split_once(',')?;
        if bank_s.len() != 1 {
            return None;
        }
        let bank = u16::from_str_radix(bank_s, 8).ok()?;
        if bank > 7 {
            return None;
        }
        let offset = u16::from_str_radix(offset_s, 8).ok()?;
        if !(0o1400..=0o1777).contains(&offset) {
            return None;
        }
        Some(bank * 0o400 + (offset - 0o1400))
    } else {
        let offset = u16::from_str_radix(tok, 8).ok()?;
        if offset > 0o1377 {
            return None;
        }
        Some(offset)
    }
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PadloadManifest {
    pub word: Vec<ManifestWord>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ManifestWord {
    pub symbol: Option<String>,
    pub addr: Option<String>,
    pub octal: Option<String>,
    pub physical: Option<Physical>,
    pub provenance: String,
    pub comment: Option<String>,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Physical {
    pub value: f64,
    pub b: i32,
    pub dp: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct PadWord {
    pub ecadr: u16,
    pub word: u16,
}

impl PadloadManifest {
    pub fn load(path: &Path) -> Result<Self> {
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("reading pad-load manifest {}", path.display()))?;
        toml::from_str(&text)
            .with_context(|| format!("parsing pad-load manifest {}", path.display()))
    }

    pub fn resolve(&self, symtab: &SymTab) -> Result<Vec<PadWord>> {
        let mut out = Vec::new();
        for (i, w) in self.word.iter().enumerate() {
            let resolved = w.resolve(symtab).with_context(|| w.label(i))?;
            out.extend(resolved);
        }
        Ok(out)
    }
}

impl ManifestWord {
    /// Names this entry for error messages: prefer the symbol/addr the
    /// author wrote, falling back to a positional index.
    fn label(&self, i: usize) -> String {
        match (&self.symbol, &self.addr) {
            (Some(s), _) => format!("word[{i}] (symbol={s:?})"),
            (_, Some(a)) => format!("word[{i}] (addr={a:?})"),
            (None, None) => format!("word[{i}]"),
        }
    }

    fn resolve(&self, symtab: &SymTab) -> Result<Vec<PadWord>> {
        let ecadr = match (&self.symbol, &self.addr) {
            // `symbol` accepts an optional "+N" suffix (N DECIMAL, matching
            // the listing's "+17D" idiom minus the D): "REFSMMAT+4" is the
            // word at REFSMMAT's ECADR + 4. Used by `generate_state` to
            // address components of multi-word erasables.
            (Some(s), None) => {
                let (base, offset) = match s.split_once('+') {
                    Some((base, off)) => (
                        base.trim(),
                        off.trim()
                            .parse::<u16>()
                            .with_context(|| format!("bad decimal offset in symbol {s:?}"))?,
                    ),
                    None => (s.as_str(), 0),
                };
                symtab
                    .ecadr(base)
                    .ok_or_else(|| anyhow!("symbol {base:?} not found in symbol table"))?
                    + offset
            }
            (None, Some(a)) => u16::from_str_radix(a, 8)
                .with_context(|| format!("addr {a:?} is not a valid octal ECADR"))?,
            (Some(_), Some(_)) => {
                bail!("exactly one of `symbol`/`addr` must be set, but both were given")
            }
            (None, None) => {
                bail!("exactly one of `symbol`/`addr` must be set, but neither was given")
            }
        };

        // octal wins over physical when both are present.
        let words: Vec<u16> = match (&self.octal, &self.physical) {
            (Some(o), _) => {
                let w = u16::from_str_radix(o, 8)
                    .with_context(|| format!("octal {o:?} is not a valid octal word"))?;
                vec![w]
            }
            (None, Some(p)) => {
                let pulses = to_pulses(p.value, p.b, p.dp);
                if p.dp {
                    if pulses.unsigned_abs() >= (1 << 28) {
                        bail!(
                            "physical value {} at b={} (dp) encodes to {pulses} pulses, \
                             out of DP range (±2^28)",
                            p.value,
                            p.b
                        );
                    }
                    let [hi, lo] = dp_encode(pulses);
                    vec![hi, lo]
                } else {
                    if pulses.unsigned_abs() >= (1 << 14) {
                        bail!(
                            "physical value {} at b={} (sp) encodes to {pulses} pulses, \
                             out of SP range (±2^14)",
                            p.value,
                            p.b
                        );
                    }
                    vec![sp_encode(pulses as i16)]
                }
            }
            (None, None) => bail!("one of `octal`/`physical` must be set"),
        };

        Ok(words
            .into_iter()
            .enumerate()
            .map(|(k, word)| PadWord {
                ecadr: ecadr + k as u16,
                word,
            })
            .collect())
    }
}

// ---------------------------------------------------------------------
// P66 scenario pad-load generation (Step 5 / padload_gen CLI).
//
// Real ECADRs below were derived by hand in Step 0 from the actual
// yaYUL listing (`build/agc/Luminary099.log`, virtualagc/Luminary099 —
// the shipped-binary source per `build/agc/manifest.json`) using the
// rule pinned in `docs/agc-channel-map.md`. Each constant's doc comment
// cites the listing line and the real symtab comment (word-count sanity
// check, e.g. "I(6)" = 3xDP).
// ---------------------------------------------------------------------

/// RLS: `Luminary099.log:4504`, `E4,1422 RLS ERASE +5  # I(6) LANDING SITE
/// VECTOR -MOON REF`. ecadr = 4*0o400 + (0o1422-0o1400) = 0o2022.
const RLS_ECADR: u16 = 0o2022;
/// RN: `Luminary099.log:4127`, unswitched `1220 RN ERASE +5  # B(6)PRM`.
const RN_ECADR: u16 = 0o1220;
/// VN: `Luminary099.log:4128`, unswitched `1226 VN ERASE +5  # B(6)PRM`.
const VN_ECADR: u16 = 0o1226;
/// PIPTIME: `Luminary099.log:4129`, unswitched `1234 PIPTIME ERASE +1
/// # B(2)PRM (MUST BE FOLLOWED BY GDT/2)`.
const PIPTIME_ECADR: u16 = 0o1234;
/// REFSMMAT: `Luminary099.log:4433`, `E3,1733 REFSMMAT ERASE +17D
/// # I(18D)PRM` (18 = 9x2 DP -> 3x3 matrix, row-major). ecadr =
/// 3*0o400 + (0o1733-0o1400) = 0o1733 (base of a 9-DP/18-word block).
const REFSMMAT_ECADR: u16 = 0o1733;
/// TLAND: `Luminary099.log:4812`, `E5,1400 TLAND EQUALS W
/// # I(2) NOMINAL TIME OF LANDING`. ecadr = 5*0o400 + (0o1400-0o1400)
/// = 0o2400.
const TLAND_ECADR: u16 = 0o2400;
/// RODSCALE: `Luminary099.log:4859`, `E5,1537 RODSCALE EQUALS LRWVFF +1
/// # I(1) CLICK SCALE FACTOR FOR ROD`. ecadr = 5*0o400 + (0o1537-0o1400)
/// = 0o2537.
const RODSCALE_ECADR: u16 = 0o2537;
/// TAUROD: `Luminary099.log:4860`, `E5,1540 TAUROD EQUALS RODSCALE +1
/// # I(2) TIME CONSTANT FOR R.O.D.`. ecadr = 0o2540.
const TAUROD_ECADR: u16 = 0o2540;
/// LAG/TAU: `Luminary099.log:4861`, `E5,1542 LAG/TAU EQUALS TAUROD +2
/// # I(2) LAG TIME DIVIDED BY TAUROD (P66)`. ecadr = 0o2542.
const LAG_TAU_ECADR: u16 = 0o2542;
/// MINFORCE: `Luminary099.log:4862`, `E5,1544 MINFORCE EQUALS LAG/TAU +2
/// # I(2) MINIMUM FORCE P66 WILL COMMAND.`. ecadr = 0o2544.
const MINFORCE_ECADR: u16 = 0o2544;
/// MAXFORCE: `Luminary099.log:4863`, `E5,1546 MAXFORCE EQUALS MINFORCE +2
/// # I(2) MAXIMUM FORCE P66 WILL COMMAND.`. ecadr = 0o2546.
const MAXFORCE_ECADR: u16 = 0o2546;

/// Whether a b-scale hypothesis below has been empirically confirmed.
/// Spike A is the authority (display read-back + alarm-driven iteration
/// against the live AGC); this generator only has to produce a plausible
/// first cut.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BScaleStatus {
    Verified,
    Unverified,
}

pub struct BScaleEntry {
    pub symbol: &'static str,
    pub status: BScaleStatus,
    pub note: &'static str,
}

/// b-scale hypothesis table for every pad-loaded quantity `padload_gen`
/// emits. `RLS`/`RN`/`VN`/`PIPTIME`/`REFSMMAT`/`TLAND`/`RODSCALE` use
/// b-scales given directly by the Task 5 brief (working hypotheses, but
/// not asked to be independently derived here). `TAUROD`, `LAG/TAU`,
/// `MINFORCE`, `MAXFORCE` are the four the brief asks to be derived from
/// their in-rope usage in
/// `vendor/virtualagc/Luminary099/LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1044-1090,174`;
/// none of the four can be pinned from that excerpt alone (each is a
/// `DDV`/`DMP` operand paired with a quantity — `VDGVERT`, `/AFC/`,
/// `MASS` — whose own scale isn't established there), so all four are
/// marked `Unverified` per the brief's explicit escape hatch.
pub const P66_BSCALE_TABLE: &[BScaleEntry] = &[
    BScaleEntry {
        symbol: "RLS",
        status: BScaleStatus::Verified,
        note: "b=27 DP meters (task spec); real symtab \"I(6)\" = 3xDP matches.",
    },
    BScaleEntry {
        symbol: "RN/VN",
        status: BScaleStatus::Verified,
        note: "b=27 DP m (RN) / b=7 DP m/cs (VN) (task spec); real symtab \"B(6)PRM\" each matches 3xDP.",
    },
    BScaleEntry {
        symbol: "PIPTIME",
        status: BScaleStatus::Verified,
        note: "b=28 DP centiseconds, reusing TLAND's cs convention (not independently given by the task \
               spec for PIPTIME specifically -- see task-5 report concerns).",
    },
    BScaleEntry {
        symbol: "REFSMMAT",
        status: BScaleStatus::Verified,
        note: "b=1 DP direction cosine in [-1,1] (task spec); real symtab \"I(18D)\" = 9x2 DP matches.",
    },
    BScaleEntry {
        symbol: "TLAND",
        status: BScaleStatus::Verified,
        note: "b=28 DP centiseconds (task spec).",
    },
    BScaleEntry {
        symbol: "RODSCALE",
        status: BScaleStatus::Verified,
        note: "b=7 SP, -0.3048 m/s per click (task spec working hypothesis).",
    },
    BScaleEntry {
        symbol: "TAUROD",
        status: BScaleStatus::Unverified,
        note: "LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1042-1044 (\"BDSU DDV / VDGVERT / TAUROD\") divides \
               a VDGVERT-derived quantity by TAUROD; VDGVERT's own b-scale is not established in the \
               cited excerpt, so TAUROD's can't be pinned in isolation.",
    },
    BScaleEntry {
        symbol: "LAG/TAU",
        status: BScaleStatus::Unverified,
        note: "LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1083-1085 (\"DMP DAD / LAG/TAU / /AFC/\") multiplies \
               LAG/TAU by /AFC/; /AFC/'s b-scale is not established in the cited excerpt.",
    },
    BScaleEntry {
        symbol: "MINFORCE",
        status: BScaleStatus::Unverified,
        note: "LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1089-1091 (\"PDDL DDV / MINFORCE / MASS\") divides \
               MINFORCE by MASS to bound /AFC/; MASS's b-scale is not established in the cited excerpt. \
               Value 4560 N matches eagle_dynamics::constants::DPS_MIN_N.",
    },
    BScaleEntry {
        symbol: "MAXFORCE",
        status: BScaleStatus::Unverified,
        note: "LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:1086-1088 (\"PDDL DDV / MAXFORCE / MASS\"), same \
               MASS-scale ambiguity as MINFORCE. Value 42500 N matches eagle_dynamics::constants::DPS_FTP_N.",
    },
];

/// Hard-fail if any b-scale hypothesis is still `Unverified`, unless the
/// caller passed `--allow-unverified` (Spike A iterating live).
pub fn check_bscales(allow_unverified: bool) -> Result<()> {
    let unverified: Vec<&str> = P66_BSCALE_TABLE
        .iter()
        .filter(|e| e.status == BScaleStatus::Unverified)
        .map(|e| e.symbol)
        .collect();
    if !unverified.is_empty() && !allow_unverified {
        bail!(
            "padload_gen: UNVERIFIED b-scale hypotheses for [{}] -- pass --allow-unverified \
             to generate anyway (see the P66_BSCALE_TABLE doc comments in \
             runtime/apps/eagle-runtime/src/padload.rs for the in-rope usage notes)",
            unverified.join(", ")
        );
    }
    Ok(())
}

/// Scenario inputs for `generate_p66_manifest`, matching `padload_gen`'s
/// CLI flags.
#[derive(Debug, Clone, Copy)]
pub struct P66ScenarioInputs {
    pub site_lat_deg: f64,
    pub site_lon_deg: f64,
    pub alt_m: f64,
    pub vz_ms: f64,
    pub epoch_cs: f64,
}

fn dp_word(addr: u16, value: f64, b: i32, comment: impl Into<String>) -> ManifestWord {
    ManifestWord {
        symbol: None,
        addr: Some(format!("{addr:05o}")),
        octal: None,
        physical: Some(Physical { value, b, dp: true }),
        provenance: "derived".to_string(),
        comment: Some(comment.into()),
    }
}

fn sp_word(addr: u16, value: f64, b: i32, comment: impl Into<String>) -> ManifestWord {
    ManifestWord {
        symbol: None,
        addr: Some(format!("{addr:05o}")),
        octal: None,
        physical: Some(Physical {
            value,
            b,
            dp: false,
        }),
        provenance: "derived".to_string(),
        comment: Some(comment.into()),
    }
}

/// Unit site vector in MCMF from geographic lat/lon (standard spherical
/// -> Cartesian; MCMF `+z` is the lunar pole per
/// `docs/coordinate-frames.md`).
fn site_unit_mcmf(lat_deg: f64, lon_deg: f64) -> V3<Mcmf> {
    let (lat, lon) = (lat_deg.to_radians(), lon_deg.to_radians());
    V3::new(lat.cos() * lon.cos(), lat.cos() * lon.sin(), lat.sin())
}

/// Generate a first-cut P66 pad-load manifest from scenario parameters.
/// All math via `eagle_dynamics` (frames/constants) per the interface
/// contract; b-scales are the hypotheses in `P66_BSCALE_TABLE` (call
/// `check_bscales` first to enforce the `--allow-unverified` gate).
pub fn generate_p66_manifest(inp: &P66ScenarioInputs) -> PadloadManifest {
    let up_mcmf = site_unit_mcmf(inp.site_lat_deg, inp.site_lon_deg);
    let epoch_s = inp.epoch_cs / 100.0;
    let up_mci: V3<Mci> = mci_to_mcmf(epoch_s).inverse().apply(up_mcmf);

    let rls_mcmf = up_mcmf.scale(R_SITE);
    let rn_mci = up_mci.scale(R_SITE + inp.alt_m);
    let vz_m_per_cs = inp.vz_ms / 100.0; // AGC state-vector velocity convention: m/centisecond.
    let vn_mci = up_mci.scale(vz_m_per_cs);

    // BODY(t=0): +X = up (thrust axis, docs/coordinate-frames.md), East =
    // pole x Up, North = Up x East (right-handed). SM == BODY(t=0), so
    // these are also REFSMMAT's rows (SM axes expressed in MCI).
    let pole = V3::<Mci>::new(0.0, 0.0, 1.0);
    let east = pole.cross(up_mci).unit();
    let north = up_mci.cross(east);
    let refsmmat_rows = [
        [up_mci.x, up_mci.y, up_mci.z],
        [east.x, east.y, east.z],
        [north.x, north.y, north.z],
    ];

    let tland_cs = inp.epoch_cs + 12000.0; // epoch + 120 s, centiseconds.

    let mut words = Vec::new();

    for (i, v) in [rls_mcmf.x, rls_mcmf.y, rls_mcmf.z].into_iter().enumerate() {
        words.push(dp_word(
            RLS_ECADR + (2 * i) as u16,
            v,
            27,
            format!(
                "RLS[{i}]: site unit vector * R_SITE, MCMF meters (Luminary099.log:4504, E4,1422)"
            ),
        ));
    }
    for (i, v) in [rn_mci.x, rn_mci.y, rn_mci.z].into_iter().enumerate() {
        words.push(dp_word(
            RN_ECADR + (2 * i) as u16,
            v,
            27,
            format!(
                "RN[{i}]: initial state-vector position guess = (R_SITE+alt)*up, MCI meters \
                 (Luminary099.log:4127, unswitched 1220)"
            ),
        ));
    }
    for (i, v) in [vn_mci.x, vn_mci.y, vn_mci.z].into_iter().enumerate() {
        words.push(dp_word(
            VN_ECADR + (2 * i) as u16,
            v,
            7,
            format!(
                "VN[{i}]: initial state-vector velocity guess = vz*up, MCI m/cs \
                 (Luminary099.log:4128, unswitched 1226)"
            ),
        ));
    }
    words.push(dp_word(
        PIPTIME_ECADR,
        inp.epoch_cs,
        28,
        "PIPTIME: state-vector time tag = scenario epoch, DP centiseconds; b reuses TLAND's \
         cs convention (not independently given -- see task-5 report concerns) \
         (Luminary099.log:4129, unswitched 1234)",
    ));
    for (i, v) in refsmmat_rows
        .iter()
        .flat_map(|row| row.iter().copied())
        .enumerate()
    {
        let (row, col) = (i / 3, i % 3);
        words.push(dp_word(
            REFSMMAT_ECADR + (2 * i) as u16,
            v,
            1,
            format!(
                "REFSMMAT[{row}][{col}]: row-major direction cosine, SM<-MCI (SM == initial \
                 BODY attitude, +X=up at site) (Luminary099.log:4433, E3,1733)"
            ),
        ));
    }
    words.push(dp_word(
        TLAND_ECADR,
        tland_cs,
        28,
        "TLAND: nominal landing time = epoch + 120s, DP centiseconds \
         (Luminary099.log:4812, E5,1400)",
    ));
    words.push(sp_word(
        RODSCALE_ECADR,
        -0.3048,
        7,
        "RODSCALE: click scale factor, SP m/s per R.O.D. click (-0.3048 m/s = -1 ft/s), \
         working hypothesis (Luminary099.log:4859, E5,1537)",
    ));
    words.push(dp_word(
        TAUROD_ECADR,
        1.5,
        14,
        "TAUROD: R.O.D. time constant, seconds. b=14 is a PLACEHOLDER -- UNVERIFIED, see \
         P66_BSCALE_TABLE (Luminary099.log:4860, E5,1540)",
    ));
    words.push(dp_word(
        LAG_TAU_ECADR,
        0.2,
        14,
        "LAG/TAU: lag time / TAUROD, seconds. b=14 is a PLACEHOLDER -- UNVERIFIED, see \
         P66_BSCALE_TABLE (Luminary099.log:4861, E5,1542)",
    ));
    words.push(dp_word(
        MINFORCE_ECADR,
        DPS_MIN_N,
        21,
        "MINFORCE: minimum P66 commanded force, Newtons (eagle_dynamics::constants::DPS_MIN_N). \
         b=21 is a PLACEHOLDER (chosen only to keep ~4560 N in DP range with headroom) -- \
         UNVERIFIED, see P66_BSCALE_TABLE (Luminary099.log:4862, E5,1544)",
    ));
    words.push(dp_word(
        MAXFORCE_ECADR,
        DPS_FTP_N,
        21,
        "MAXFORCE: maximum P66 commanded force, Newtons (eagle_dynamics::constants::DPS_FTP_N). \
         b=21 is a PLACEHOLDER (chosen only to keep ~42500 N in DP range with headroom) -- \
         UNVERIFIED, see P66_BSCALE_TABLE (Luminary099.log:4863, E5,1546)",
    ));

    PadloadManifest { word: words }
}

// ---------------------------------------------------------------------
// Spike A (Task 6): live state-vector generation.
//
// P63's ignition algorithm (THE_LUNAR_LANDING.agc, IGNALG) does NOT read
// RN/VN/PIPTIME — it calls LEMPREC, which integrates the PERMANENT LM
// state vector (RRECTLEM/VRECTLEM/TETLEM..., ERASABLE_ASSIGNMENTS.agc:945-955),
// and BURNBABY additionally integrates the PERMANENT CSM state via
// CSMPREC because P63's FLAGORGY sets MUNFLAG
// (BURN,_BABY,_BURN_--_MASTER_IGNITION_ROUTINE.agc:196-201). RN/VN/PIPTIME
// are *outputs* of MIDTOAV at TIG-30. So `generate_state` emits the
// permanent state vectors (both vehicles), plus the three other
// time-dependent quantities: RLS (moon-fixed, via the AGC's own MOONMX
// model), REFSMMAT, and TLAND.
// ---------------------------------------------------------------------

/// GUIDDURN, the nominal guidance duration P63 subtracts from TLAND to
/// seed its ignition-time iteration: `2DEC +66440` centiseconds = 664.40 s
/// (THE_LUNAR_LANDING.agc:277, "GUIDDURN +6.64400314 E+2").
pub const GUIDDURN_CS: f64 = 66440.0;

/// ZOOMTIME, the throttle-up delay BURNBABY subtracts from the converged
/// ignition-point time to get TIG (DDUMGOOD, THE_LUNAR_LANDING.agc:186-192):
/// 26 s = 2600 cs (P40-P47.agc `ZOOMTIME DEC 2600`).
pub const ZOOMTIME_CS: f64 = 2600.0;

/// Luminary's lunar orientation model, MOONMX
/// (PLANETARY_INERTIAL_ORIENTATION.agc:145-262): computes M(t) such that
/// RP = M(t)·R maps the basic reference (MCI) into the moon-fixed frame.
/// RP-TO-R applies the transpose: R = Mᵀ(t)·(RP + L×RP); we take the
/// libration vector L (padload 504LM, |L| ~ 1e-4 rad) as zero.
///
/// Angle polynomials X = X0 + Ẋ·t are evaluated with TEPHEM = 0 (our
/// padload leaves it zero), so t is the raw AGC clock. Constants from
/// CONTROLLED_CONSTANTS.agc:552-561 (rad / rad/s values from the source
/// comments; the octal words encode the same values):
///   COSI/SINI: I = 5521.5″ = 1°32′01.5″ (mean lunar equator vs ecliptic)
///   NODIO = 6.19653663041 rad, NODDOT = -1.07047011e-8 rad/s
///   FSUBO = 5.20932947829 rad, FDOT   =  2.67240410e-6 rad/s
///   BSUBO = 0.40916190299 rad, BDOT   = -7.19757301e-14 rad/s
/// Matrix assembly (MOONMX/MOONMXA, PLANETARY_INERTIAL_ORIENTATION.agc:229-262):
///   A = ( cosN, cosB·sinN, sinB·sinN )
///   B = (-sinN, cosB·cosN, sinB·cosN )
///   C = ( 0,        -sinB,      cosB )
///   M2 = B·sinI + C·cosI          (row 2)
///   D  = B·cosI - C·sinI
///   M1 = A·sinF - D·cosF          (row 1)
///   M0 = -(A·cosF + D·sinF)       (row 0)
pub fn moon_mx(t_cs: f64) -> [[f64; 3]; 3] {
    const COSI: f64 = 0.99964173;
    const SINI: f64 = 0.02676579;
    const NODIO: f64 = 6.19653663041;
    const NODDOT: f64 = -1.07047011e-8;
    const FSUBO: f64 = 5.20932947829;
    const FDOT: f64 = 2.67240410e-6;
    const BSUBO: f64 = 0.40916190299;
    const BDOT: f64 = -7.19757301e-14;

    let t_s = t_cs / 100.0;
    let node = NODIO + NODDOT * t_s;
    let f = FSUBO + FDOT * t_s;
    let b = BSUBO + BDOT * t_s;
    let (sn, cn) = node.sin_cos();
    let (sf, cf) = f.sin_cos();
    let (sb, cb) = b.sin_cos();

    let av = [cn, cb * sn, sb * sn];
    let bv = [-sn, cb * cn, sb * cn];
    let cv = [0.0, -sb, cb];
    let m2 = [
        bv[0] * SINI + cv[0] * COSI,
        bv[1] * SINI + cv[1] * COSI,
        bv[2] * SINI + cv[2] * COSI,
    ];
    let dv = [
        bv[0] * COSI - cv[0] * SINI,
        bv[1] * COSI - cv[1] * SINI,
        bv[2] * COSI - cv[2] * SINI,
    ];
    let m1 = [
        av[0] * sf - dv[0] * cf,
        av[1] * sf - dv[1] * cf,
        av[2] * sf - dv[2] * cf,
    ];
    let m0 = [
        -(av[0] * cf + dv[0] * sf),
        -(av[1] * cf + dv[1] * sf),
        -(av[2] * cf + dv[2] * sf),
    ];
    [m0, m1, m2]
}

/// Scenario inputs for `generate_state` (Spike A live regeneration from
/// the measured AGC clock).
///
/// Geometry: the landing site is placed on the MCI +X axis (its
/// moon-fixed RLS is derived from that via `moon_mx(tland)`), the orbit
/// plane is the MCI XY plane with the LM travelling toward +Y ("east").
/// The LM permanent state is time-tagged at the *geometric ignition
/// point*: `tet = epoch_now + burn_lead`, positioned uprange of the site
/// by exactly the padloaded ignition-target geometry
/// (rign_x/rign_z/v_ign below, which must match the RIGNX/RIGNZ/VIGN
/// words in the static manifest), so that P63's first TDEC1 guess
/// (TLAND - GUIDDURN = tet) lands on a state already satisfying the DDUM
/// criterion and the Newton iteration converges immediately
/// (THE_LUNAR_LANDING.agc, DDUMCALC). TIG then comes out at
/// tet - ZOOMTIME ≈ epoch_now + burn_lead - 26 s.
#[derive(Debug, Clone, Copy)]
pub struct StateCfg {
    /// AGC clock (TIME2:TIME1) measured just before generation, cs.
    pub epoch_now_cs: f64,
    /// Time from `epoch_now_cs` to the geometric ignition point, cs.
    /// Budget everything that still has to happen before BURNBABY's
    /// TIG-35 gate here (remaining pad-load, flag set, V37E63E, IGNALG,
    /// dialog responses) plus the >=45 s pre-TIG check margin
    /// (BURN,_BABY,_BURN:64). A too-small value is survivable: BURNBABY
    /// slips TIG to integration-time + 29.9 s (CALLT-35 slip path).
    pub burn_lead_cs: f64,
    /// Desired ignition-point 'altitude' component, m (pad RIGNX,
    /// LUM69R2/PADLOADS.agc:473: -4.09432231e4).
    pub rign_x_m: f64,
    /// Desired ignition-point ground-range component, m (pad RIGNZ,
    /// LUM69R2/PADLOADS.agc:480: -4.40014934e5).
    pub rign_z_m: f64,
    /// Desired ignition speed, m/s (pad VIGN, LUM69R2/PADLOADS.agc:468:
    /// 16.9952182 m/cs = 1699.52 m/s).
    pub v_ign_ms: f64,
    /// CSM circular-orbit altitude above R_SITE, m (~111 km nominal).
    pub csm_alt_m: f64,
}

impl Default for StateCfg {
    fn default() -> Self {
        StateCfg {
            epoch_now_cs: 0.0,
            burn_lead_cs: 24_000.0,
            rign_x_m: -4.09432231e4,
            rign_z_m: -4.40014934e5,
            v_ign_ms: 1699.52182,
            csm_alt_m: 111_000.0,
        }
    }
}

fn sym_dp(symbol: &str, value: f64, b: i32, comment: impl Into<String>) -> ManifestWord {
    ManifestWord {
        symbol: Some(symbol.to_string()),
        addr: None,
        octal: None,
        physical: Some(Physical { value, b, dp: true }),
        provenance: "derived".to_string(),
        comment: Some(comment.into()),
    }
}

/// Generate the time-dependent pad-load words for a P63 ignition run:
/// permanent LM + CSM state vectors, RLS, REFSMMAT, TLAND. All entries
/// are symbol-based (resolved against the live `SymTab` by the caller).
///
/// Scalings (all DP): moon-centered position m b=27 (RP-TO-R "METERS
/// B-27 FOR MOON"), **velocity m/cs b=5** — NOT the b=7 of the SERVICER
/// RN/VN state. Pinned two ways (spike-A iters 16-17): statically, the
/// interpreter scale chain VGU@2^10 ← ANGTERM@2^9 (VSR2) ← V@2^7 ←
/// (VSR1·MXV REFSMMAT) ← VATT1@2^5 (LUNAR_LANDING_GUIDANCE_EQUATIONS.agc
/// :429-470, CALCRGVG/RGVGCALC); empirically, b=7 encoding made the AGC
/// read v/4 (425 m/s) — a plunge orbit with 58 km perilune radius and
/// 1223 s half-period that exactly reproduced the RGU/TPIP forensics of
/// iter 16. Time cs b=28; REFSMMAT rows b=1.
pub fn generate_state(cfg: &StateCfg) -> Vec<ManifestWord> {
    let tland_cs = cfg.epoch_now_cs + cfg.burn_lead_cs + GUIDDURN_CS;
    let tet_cs = tland_cs - GUIDDURN_CS; // == epoch_now + burn_lead

    // Ignition-point geometry in the orbit plane (see StateCfg docs):
    // radial component r·cosθ = R_SITE + rign_x (rign_x < 0), downrange
    // arc r·sinθ = |rign_z|. With the LUM69R2 targets this lands at
    // θ ≈ 0.2539 rad, r ≈ 1752.6 km — h ≈ 15.2 km, the historical PDI
    // altitude.
    let a = R_SITE + cfg.rign_x_m;
    let b = -cfg.rign_z_m; // rign_z < 0 => LM is uprange (short of site)
    let theta = b.atan2(a);
    let r_orb = a.hypot(b);
    let (st, ct) = theta.sin_cos();

    // LM at tet: site direction is +X, LM is θ uprange; travelling +Y.
    //
    // Speed: VIGN is compared against |VGU|, the SURFACE-RELATIVE velocity
    // (VGU = CG·(V - WM×R), LUNAR_LANDING_GUIDANCE_EQUATIONS.agc:433), so
    // the generated INERTIAL speed must be VIGN + ω·r (eastward equatorial
    // orbit: WM×R is exactly eastward, ω·r ≈ 4.67 m/s). Without this the
    // ignition criterion has no root — the orbit starts at perilune, so
    // |VGU| < VIGN everywhere and IGNALG's DDUM Newton iteration marches
    // TDEC1 forward forever (spike-A iter 16: TPIP/PIPTIME1 ran away
    // +20 min, RGU showed the state integrated far past the site).
    let r_lm = [r_orb * ct, -r_orb * st, 0.0];
    let omega_r = eagle_dynamics::constants::OMEGA_MOON * r_orb;
    let v_ign_mcs = (cfg.v_ign_ms + omega_r) / 100.0; // m/cs, inertial
    let v_lm = [v_ign_mcs * st, v_ign_mcs * ct, 0.0];

    // CSM: circular orbit, same plane, directly over the site at tet.
    let r_csm_mag = R_SITE + cfg.csm_alt_m;
    let v_csm_mcs = (eagle_dynamics::constants::MU_MOON / r_csm_mag).sqrt() / 100.0;
    let r_csm = [r_csm_mag, 0.0, 0.0];
    let v_csm = [0.0, v_csm_mcs, 0.0];

    // REFSMMAT rows = SM axes in MCI, chosen to COINCIDE with the descent
    // guidance frame: X = up at the landing site, Y = -orbit normal,
    // Z = downrange (CGCALC erects exactly this frame from LAND and R:
    // row1 = unit((LAND-R)×LAND), LUNAR_LANDING_GUIDANCE_EQUATIONS.agc
    // :678-690). This is not a nicety: IGNALG's FIRST guidance pass runs
    // RGVGCALC/TTF-8CL with CG = identity (initialized UNITX/UNITY/UNITZ,
    // THE_LUNAR_LANDING.agc:102-108; CGCALC only erects CG at the END of
    // a pass), so RGU/VGU land in SM axes — with any other REFSMMAT the
    // TTF cubic sees radial data where it expects downrange and ROOTPSRS
    // aborts 1406 (spike-A iter 14, FAILREG=01406 1.2 s after P63 entry).
    // The historical descent REFSMMAT is the same "landing site" frame.
    let sm_x = [1.0, 0.0, 0.0];
    let sm_y = [0.0, 0.0, -1.0];
    let sm_z = [0.0, 1.0, 0.0];

    // RLS: moon-fixed site vector such that the AGC's own RP-TO-R at
    // TLAND reproduces "site on MCI +X": RLS = M(TLAND)·(R_SITE·x̂) =
    // R_SITE · column 0 of M.
    let m = moon_mx(tland_cs);
    let rls = [m[0][0] * R_SITE, m[1][0] * R_SITE, m[2][0] * R_SITE];

    let mut w = Vec::new();
    // A DP vector symbol resolves to its base ECADR; component i lives at
    // base + 2i, addressed with resolve()'s "SYM+N" decimal-offset form.
    let vec_dp = |w: &mut Vec<ManifestWord>, sym: &str, v: [f64; 3], b: i32, what: &str| {
        for (i, val) in v.into_iter().enumerate() {
            w.push(sym_dp(
                &format!("{sym}+{}", 2 * i),
                val,
                b,
                format!("{what}[{i}]"),
            ));
        }
    };

    vec_dp(&mut w, "RRECTLEM", r_lm, 27, "LM permanent position, MCI m");
    vec_dp(
        &mut w,
        "VRECTLEM",
        v_lm,
        5,
        "LM permanent velocity, MCI m/cs (b=5!)",
    );
    w.push(sym_dp(
        "TETLEM",
        tet_cs,
        28,
        "LM state epoch, cs (= epoch_now + burn_lead)",
    ));
    vec_dp(
        &mut w,
        "RCVLEM",
        r_lm,
        27,
        "LM conic position = RRECTLEM (just-rectified)",
    );
    vec_dp(
        &mut w,
        "VCVLEM",
        v_lm,
        5,
        "LM conic velocity = VRECTLEM (just-rectified)",
    );

    vec_dp(
        &mut w,
        "RRECTCSM",
        r_csm,
        27,
        "CSM permanent position, MCI m",
    );
    vec_dp(
        &mut w,
        "VRECTCSM",
        v_csm,
        5,
        "CSM permanent velocity, MCI m/cs (b=5!)",
    );
    w.push(sym_dp("TETCSM", tet_cs, 28, "CSM state epoch, cs"));
    vec_dp(&mut w, "RCVCSM", r_csm, 27, "CSM conic position = RRECTCSM");
    vec_dp(&mut w, "VCVCSM", v_csm, 5, "CSM conic velocity = VRECTCSM");

    vec_dp(
        &mut w,
        "RLS",
        rls,
        27,
        "landing site, moon-fixed m (M(TLAND)·R_SITE·x̂)",
    );
    for (r, (name, row)) in [("row0/X", sm_x), ("row1/Y", sm_y), ("row2/Z", sm_z)]
        .into_iter()
        .enumerate()
    {
        for (c, val) in row.into_iter().enumerate() {
            w.push(sym_dp(
                &format!("REFSMMAT+{}", 2 * (3 * r + c)),
                val,
                1,
                format!("REFSMMAT {name}[{c}] (SM axis in MCI)"),
            ));
        }
    }
    w.push(sym_dp("TLAND", tland_cs, 28, "nominal landing time, cs"));
    w
}

/// Render a manifest to TOML text with a b-scale-verification-status
/// header comment (not part of the serde shape -- prepended as plain
/// text so the file is self-documenting without a hand round-trip
/// through `PadloadManifest::load`).
pub fn render_manifest_toml(m: &PadloadManifest, allow_unverified: bool) -> Result<String> {
    let mut out = String::new();
    out.push_str("# Generated by padload_gen (Task 5) -- first-cut, unvalidated pad-load.\n");
    out.push_str("# ECADRs derived by hand in Step 0 from build/agc/Luminary099.log; see\n");
    out.push_str("# docs/agc-channel-map.md for the notation rule and citations.\n#\n");
    out.push_str("# b-scale verification status:\n");
    for e in P66_BSCALE_TABLE {
        out.push_str(&format!(
            "#   {:<10} {:?}: {}\n",
            e.symbol, e.status, e.note
        ));
    }
    if allow_unverified {
        out.push_str(
            "#\n# Generated with --allow-unverified: UNVERIFIED entries above are provisional;\n\
             # Spike A owns live validation before this ships as scenarios/p66-padload.toml.\n",
        );
    }
    out.push('\n');
    out.push_str(&toml::to_string_pretty(m).context("serializing pad-load manifest to TOML")?);
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn symtab_parses_fixture() {
        let text = include_str!("../tests/fixtures/symtab_excerpt.txt");
        let st = SymTab::from_listing(text).unwrap();
        let rodscale = st.ecadr("RODSCALE").unwrap();
        assert!(rodscale <= 0o3777, "ECADR range");
        // Hand-computed from the fixture's RLS line (real yaYUL listing,
        // build/agc/Luminary099.log:4504, byte-identical to fixture line 3):
        //   004605,001043: E4,1422  ...  RLS  ERASE  +5  # I(6) LANDING SITE VECTOR -MOON REF
        // Rule (docs/agc-channel-map.md): switched E<bank>,<offset>,
        // ecadr = bank*0o400 + (offset - 0o1400).
        // RLS: bank=4, offset=0o1422 -> ecadr = 4*0o400 + (0o1422-0o1400)
        //                                     = 0o2000 + 0o22 = 0o2022.
        // Independently cross-checked by hand-counting ERASE words from
        // EBANK-4's `SETLOC 2000` (ERASABLE_ASSIGNMENTS.agc:1008) forward
        // to RLS (:1043) — see docs/agc-channel-map.md for the full count.
        let rls = st.ecadr("RLS").unwrap();
        assert_eq!(rls, 0o2022, "RLS ECADR hand-computed from E4,1422");
    }

    #[test]
    fn manifest_resolves_physical_and_octal_words() {
        let toml_text = r#"
            [[word]]
            symbol = "RODSCALE"
            physical = { value = -0.3048, b = 7, dp = false }
            provenance = "derived"

            [[word]]
            addr = "01234"
            octal = "00042"
            provenance = "assumed"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st =
            SymTab::from_listing(include_str!("../tests/fixtures/symtab_excerpt.txt")).unwrap();
        let words = m.resolve(&st).unwrap();
        assert_eq!(
            words.last().unwrap(),
            &PadWord {
                ecadr: 0o1234,
                word: 0o42
            }
        );
        // SP physical: pulses = round(-0.3048 / 2^(7-14)) = round(-39.01) = -39
        assert_eq!(words[0].word, eagle_agc_protocol::words::sp_encode(-39));
    }

    #[test]
    fn physical_rejects_unknown_fields() {
        // deny_unknown_fields must hold on every struct, not just the two
        // outer ones -- an unrecognized key nested inside `physical = {...}`
        // (e.g. a typo'd `bb` instead of `b`) should fail to parse rather
        // than silently ignoring it.
        let toml_text = r#"
            [[word]]
            addr = "00001"
            physical = { value = 1.0, b = 7, dp = false, bb = 99 }
            provenance = "assumed"
        "#;
        let err = toml::from_str::<PadloadManifest>(toml_text).unwrap_err();
        let msg = err.to_string();
        assert!(
            msg.contains("bb") || msg.to_lowercase().contains("unknown"),
            "expected an unknown-field error, got: {msg}"
        );
    }

    #[test]
    fn manifest_dp_emits_two_consecutive_words() {
        let toml_text = r#"
            [[word]]
            addr = "02000"
            physical = { value = 1000000.0, b = 27, dp = true }
            provenance = "derived"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st = SymTab::from_listing("").unwrap();
        let w = m.resolve(&st).unwrap();
        assert_eq!(w.len(), 2);
        assert_eq!((w[0].ecadr, w[1].ecadr), (0o2000, 0o2001));
        let pulses = eagle_agc_protocol::words::dp_decode([w[0].word, w[1].word]);
        assert_eq!(pulses, 2_000_000);
    }

    #[test]
    fn manifest_octal_wins_when_both_octal_and_physical_are_set() {
        // Same entry sets BOTH `octal` and `physical`; the physical value
        // (b=27 dp, 1_000_000.0) would decode to a completely different,
        // two-word DP pair if it were used, so this pins that `octal` (a
        // single word, 0o00042) wins outright, per the manifest contract.
        let toml_text = r#"
            [[word]]
            addr = "02000"
            octal = "00042"
            physical = { value = 1000000.0, b = 27, dp = true }
            provenance = "derived"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st = SymTab::from_listing("").unwrap();
        let words = m.resolve(&st).unwrap();
        assert_eq!(
            words,
            vec![PadWord {
                ecadr: 0o2000,
                word: 0o42
            }]
        );
    }

    #[test]
    fn symtab_parses_unswitched_erasable() {
        // RESTREG (fixture line 1, real listing:
        // build/agc/Luminary099.log:3906): "0366 RESTREG ERASE" — plain
        // octal, no bank prefix, unswitched -> ecadr = offset as-is.
        let text = include_str!("../tests/fixtures/symtab_excerpt.txt");
        let st = SymTab::from_listing(text).unwrap();
        assert_eq!(st.ecadr("RESTREG"), Some(0o0366));
        assert_eq!(st.ecadr("REQRET"), Some(0o1013));
    }

    #[test]
    fn manifest_rejects_both_symbol_and_addr() {
        let toml_text = r#"
            [[word]]
            symbol = "RLS"
            addr = "01234"
            octal = "00001"
            provenance = "assumed"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st = SymTab::from_listing("").unwrap();
        let err = m.resolve(&st).unwrap_err();
        let msg = format!("{err:#}");
        assert!(
            msg.contains("word[0]"),
            "error should name the entry: {msg}"
        );
        assert!(msg.contains("symbol=") || msg.contains("RLS"), "got: {msg}");
    }

    #[test]
    fn manifest_rejects_unknown_symbol_by_name() {
        let toml_text = r#"
            [[word]]
            symbol = "NOSUCHSYM"
            octal = "00001"
            provenance = "assumed"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st =
            SymTab::from_listing(include_str!("../tests/fixtures/symtab_excerpt.txt")).unwrap();
        let err = m.resolve(&st).unwrap_err();
        let msg = format!("{err:#}");
        assert!(
            msg.contains("NOSUCHSYM"),
            "error should name the entry: {msg}"
        );
    }

    #[test]
    fn manifest_sp_overflow_errors_instead_of_panicking() {
        let toml_text = r#"
            [[word]]
            addr = "00001"
            physical = { value = 1.0e9, b = 14, dp = false }
            provenance = "assumed"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st = SymTab::from_listing("").unwrap();
        let err = m.resolve(&st).unwrap_err();
        assert!(format!("{err:#}").contains("word[0]"));
    }

    #[test]
    fn check_bscales_hard_fails_without_allow_unverified() {
        let err = check_bscales(false).unwrap_err();
        let msg = format!("{err:#}");
        assert!(
            msg.contains("TAUROD"),
            "should name unverified entries: {msg}"
        );
        assert!(check_bscales(true).is_ok());
    }

    #[test]
    fn generate_p66_manifest_produces_expected_word_count_and_addresses() {
        let inp = P66ScenarioInputs {
            site_lat_deg: 0.674,
            site_lon_deg: 23.473,
            alt_m: 500.0,
            vz_ms: 0.0,
            epoch_cs: 0.0,
        };
        let m = generate_p66_manifest(&inp);
        // RLS(3) + RN(3) + VN(3) + PIPTIME(1) + REFSMMAT(9) + TLAND(1) +
        // RODSCALE(1) + TAUROD(1) + LAG/TAU(1) + MINFORCE(1) + MAXFORCE(1)
        assert_eq!(m.word.len(), 25);

        // Every entry resolves cleanly (addr-based, no symtab needed) and
        // DP entries land on consecutive addresses with no overlap.
        let st = SymTab::default();
        let resolved = m.resolve(&st).unwrap();
        let mut ecadrs: Vec<u16> = resolved.iter().map(|w| w.ecadr).collect();
        let before = ecadrs.len();
        ecadrs.sort_unstable();
        ecadrs.dedup();
        assert_eq!(ecadrs.len(), before, "no two pad-load words share an ECADR");

        // Spot-check the real, hand-verified addresses.
        assert!(resolved.iter().any(|w| w.ecadr == RLS_ECADR));
        assert!(resolved.iter().any(|w| w.ecadr == TLAND_ECADR));
        assert!(resolved.iter().any(|w| w.ecadr == RODSCALE_ECADR));
    }

    #[test]
    fn generate_p66_manifest_rls_matches_analytic_site_vector() {
        // At lat=0, lon=0, RLS should be (R_SITE, 0, 0) in MCMF.
        let inp = P66ScenarioInputs {
            site_lat_deg: 0.0,
            site_lon_deg: 0.0,
            alt_m: 0.0,
            vz_ms: 0.0,
            epoch_cs: 0.0,
        };
        let m = generate_p66_manifest(&inp);
        let rls_words: Vec<&ManifestWord> = m
            .word
            .iter()
            .filter(|w| w.addr.as_deref() == Some(&format!("{RLS_ECADR:05o}")))
            .collect();
        let p = rls_words[0].physical.as_ref().unwrap();
        assert!(
            (p.value - R_SITE).abs() < 1e-6,
            "RLS[0] should be R_SITE at lat=lon=0: {}",
            p.value
        );
    }

    #[test]
    fn generate_p66_manifest_refsmmat_row0_is_sm_x_axis_up_in_mci() {
        // Pins the row-major convention v_SM = REFSMMAT * v_MCI, row 0 =
        // SM's +X axis (== "up" at the site, per docs/coordinate-frames.md
        // and the task brief's "body +X = up at site"), expressed in MCI.
        // The expected "up" vector is computed here with plain trig (NOT
        // via eagle_dynamics::frames), and epoch_cs=0 makes MCI and MCMF
        // coincide (mci_to_mcmf(0) is the identity rotation), so this is
        // an independent check: a row/column transposition bug in the
        // generator (e.g. writing east/north into row 0 instead of up, or
        // emitting column-major instead of row-major) would fail this.
        let (lat_deg, lon_deg) = (12.0, -34.0);
        let inp = P66ScenarioInputs {
            site_lat_deg: lat_deg,
            site_lon_deg: lon_deg,
            alt_m: 500.0,
            vz_ms: 0.0,
            epoch_cs: 0.0,
        };
        let (lat, lon) = (lat_deg.to_radians(), lon_deg.to_radians());
        let expected_up = [lat.cos() * lon.cos(), lat.cos() * lon.sin(), lat.sin()];

        let m = generate_p66_manifest(&inp);
        let words = m.resolve(&SymTab::default()).unwrap();
        let word_at = |ecadr: u16| -> u16 { words.iter().find(|w| w.ecadr == ecadr).unwrap().word };

        for (col, expected) in expected_up.iter().enumerate() {
            let addr = REFSMMAT_ECADR + (2 * col) as u16;
            let pulses = eagle_agc_protocol::words::dp_decode([word_at(addr), word_at(addr + 1)]);
            // b=1 DP: value = pulses * 2^(1-28).
            let decoded = pulses as f64 * 2f64.powi(1 - 28);
            assert!(
                (decoded - expected).abs() < 1e-6,
                "REFSMMAT[0][{col}] decoded to {decoded}, expected up-vector component {expected} \
                 (within DP quantization ~2^-27 ~= 7.5e-9)"
            );
        }
    }

    #[test]
    fn generate_p66_manifest_tland_equals_epoch_plus_120s_exact_pulses() {
        let epoch_cs = 4321.0;
        let inp = P66ScenarioInputs {
            site_lat_deg: 0.674,
            site_lon_deg: 23.473,
            alt_m: 500.0,
            vz_ms: 0.0,
            epoch_cs,
        };
        let m = generate_p66_manifest(&inp);
        let words = m.resolve(&SymTab::default()).unwrap();
        let word_at = |ecadr: u16| -> u16 { words.iter().find(|w| w.ecadr == ecadr).unwrap().word };
        let pulses =
            eagle_agc_protocol::words::dp_decode([word_at(TLAND_ECADR), word_at(TLAND_ECADR + 1)]);
        // b=28 DP: 1 pulse = 1 centisecond exactly, so TLAND's pulses must
        // equal epoch_cs + 12000 (120 s) exactly, not just "close".
        assert_eq!(pulses, (epoch_cs + 12000.0) as i64);
    }

    /// Real yaYUL listing, if the AGC artifacts have been built (`make
    /// agc`); `None` skips listing-dependent assertions in fast runs.
    fn real_symtab() -> Option<SymTab> {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../build/agc/Luminary099.log");
        let text = std::fs::read_to_string(path).ok()?;
        Some(SymTab::from_listing(&text).unwrap())
    }

    #[test]
    fn moon_mx_is_orthonormal_and_rotates_at_lunar_rate() {
        for t_cs in [0.0, 1.0e6, 5.0e8] {
            let m = moon_mx(t_cs);
            for i in 0..3 {
                for j in 0..3 {
                    let dot: f64 = (0..3).map(|k| m[i][k] * m[j][k]).sum();
                    let expect = if i == j { 1.0 } else { 0.0 };
                    // Tolerance 1e-7, not 1e-12: Luminary's COSI/SINI are
                    // rounded to 8 decimals (COSI²+SINI² ≈ 1 - 3e-9), and
                    // we reproduce the AGC's constants, not ideal ones.
                    assert!(
                        (dot - expect).abs() < 1e-7,
                        "row{i}·row{j} = {dot} at t={t_cs}"
                    );
                }
            }
        }
        // A moon-fixed equatorial direction should sweep at roughly the
        // lunar sidereal rate (F-dot ≈ 2.672e-6 rad/s dominates; node and
        // B rates are 1e-8 and 1e-14).
        let dt_s = 1000.0;
        let (m0, m1) = (moon_mx(0.0), moon_mx(dt_s * 100.0));
        // Transport the MCI +X direction into moon-fixed at both times;
        // the angle between the images is the rotation swept.
        let v0 = [m0[0][0], m0[1][0], m0[2][0]];
        let v1 = [m1[0][0], m1[1][0], m1[2][0]];
        let dot: f64 = (0..3).map(|k| v0[k] * v1[k]).sum();
        let angle = dot.clamp(-1.0, 1.0).acos();
        let rate = angle / dt_s;
        assert!(
            (rate - 2.6724e-6).abs() < 2e-7,
            "swept rate {rate} rad/s vs FDOT 2.672e-6"
        );
    }

    #[test]
    fn generate_state_geometry_and_scaling() {
        let cfg = StateCfg {
            epoch_now_cs: 100_000.0,
            ..StateCfg::default()
        };
        let words = generate_state(&cfg);
        let Some(st) = real_symtab() else {
            eprintln!("skipping listing-dependent assertions (run `make agc`)");
            return;
        };
        let m = PadloadManifest { word: words };
        let resolved = m.resolve(&st).unwrap();

        let word_at = |sym: &str, off: u16| -> [u16; 2] {
            let base = st.ecadr(sym).unwrap() + off;
            [
                resolved.iter().find(|w| w.ecadr == base).unwrap().word,
                resolved.iter().find(|w| w.ecadr == base + 1).unwrap().word,
            ]
        };
        let dp_val = |sym: &str, off: u16, b: i32| -> f64 {
            eagle_agc_protocol::words::dp_decode(word_at(sym, off)) as f64 * 2f64.powi(b - 28)
        };

        // TETLEM decodes to exactly epoch + burn_lead centiseconds.
        assert_eq!(
            eagle_agc_protocol::words::dp_decode(word_at("TETLEM", 0)),
            (cfg.epoch_now_cs + cfg.burn_lead_cs) as i64
        );
        // TLAND = TET + GUIDDURN.
        assert_eq!(
            eagle_agc_protocol::words::dp_decode(word_at("TLAND", 0)),
            (cfg.epoch_now_cs + cfg.burn_lead_cs + GUIDDURN_CS) as i64
        );

        // |RRECTLEM| reproduces the ignition-point radius (~1752.6 km)
        // and |VRECTLEM| the ignition speed, through the b=27 / b=7
        // encodings.
        let r: f64 = (0..3)
            .map(|i| dp_val("RRECTLEM", 2 * i as u16, 27).powi(2))
            .sum::<f64>()
            .sqrt();
        let a = R_SITE + cfg.rign_x_m;
        let expect_r = a.hypot(cfg.rign_z_m);
        assert!((r - expect_r).abs() < 1.0, "r = {r}, expect {expect_r}");
        let v: f64 = (0..3)
            .map(|i| dp_val("VRECTLEM", 2 * i as u16, 5).powi(2))
            .sum::<f64>()
            .sqrt();
        // Inertial speed = VIGN + ω·r (surface-relative VIGN compensation).
        let expect_v = cfg.v_ign_ms + eagle_dynamics::constants::OMEGA_MOON * expect_r;
        assert!(
            (v * 100.0 - expect_v).abs() < 0.01,
            "v = {} m/s vs {}",
            v * 100.0,
            expect_v
        );

        // RLS: moon-fixed, magnitude R_SITE (rotation preserves length).
        let rls: f64 = (0..3)
            .map(|i| dp_val("RLS", 2 * i as u16, 27).powi(2))
            .sum::<f64>()
            .sqrt();
        assert!((rls - R_SITE).abs() < 1.0, "|RLS| = {rls}");

        // REFSMMAT rows orthonormal after encode/decode (b=1).
        for row in 0..3u16 {
            let n: f64 = (0..3)
                .map(|c| dp_val("REFSMMAT", 2 * (3 * row + c), 1).powi(2))
                .sum::<f64>()
                .sqrt();
            assert!((n - 1.0).abs() < 1e-6, "REFSMMAT row {row} norm {n}");
        }

        // Permanent-state conic copies match the rectification state.
        assert_eq!(word_at("RCVLEM", 0), word_at("RRECTLEM", 0));
        assert_eq!(word_at("VCVLEM", 4), word_at("VRECTLEM", 4));

        // No two words share an ECADR.
        let mut ecadrs: Vec<u16> = resolved.iter().map(|w| w.ecadr).collect();
        let n_before = ecadrs.len();
        ecadrs.sort_unstable();
        ecadrs.dedup();
        assert_eq!(ecadrs.len(), n_before);
    }

    #[test]
    fn static_p66_manifest_resolves_against_real_listing() {
        let Some(st) = real_symtab() else {
            eprintln!("skipping listing-dependent assertions (run `make agc`)");
            return;
        };
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../../scenarios/p66-padload.toml");
        let m = PadloadManifest::load(&path).unwrap();
        let words = m.resolve(&st).unwrap();

        // E5 overlay layout spot checks (ERASABLE_ASSIGNMENTS.agc:1360-1411,
        // TLAND = E5,1400 -> 0o2400): RBRFG = TLAND+2, RODSCALE = 0o2537.
        assert_eq!(st.ecadr("RBRFG"), Some(0o2402));
        assert_eq!(st.ecadr("VIGN"), Some(0o2472));
        assert_eq!(st.ecadr("RODSCALE"), Some(0o2537));
        assert_eq!(st.ecadr("MAXFORCE"), Some(0o2546));
        assert!(words.iter().any(|w| w.ecadr == 0o2402));

        // VIGN encodes 16.9952182 m/cs at b=10: hand value check.
        let vign = [
            words.iter().find(|w| w.ecadr == 0o2472).unwrap().word,
            words.iter().find(|w| w.ecadr == 0o2473).unwrap().word,
        ];
        let decoded = eagle_agc_protocol::words::dp_decode(vign) as f64 * 2f64.powi(10 - 28);
        assert!((decoded - 16.9952182).abs() < 1e-4, "VIGN {decoded}");
    }

    #[test]
    fn symbol_plus_offset_resolution() {
        let toml_text = r#"
            [[word]]
            symbol = "RLS+4"
            octal = "00042"
            provenance = "assumed"
        "#;
        let m: PadloadManifest = toml::from_str(toml_text).unwrap();
        let st =
            SymTab::from_listing(include_str!("../tests/fixtures/symtab_excerpt.txt")).unwrap();
        let words = m.resolve(&st).unwrap();
        assert_eq!(
            words,
            vec![PadWord {
                ecadr: 0o2022 + 4,
                word: 0o42
            }]
        );
    }

    #[test]
    fn padload_manifest_load_reads_toml_from_disk() {
        let path =
            std::env::temp_dir().join(format!("padload_load_test_{}.toml", std::process::id()));
        std::fs::write(
            &path,
            r#"
                [[word]]
                addr = "00001"
                octal = "00042"
                provenance = "assumed"
            "#,
        )
        .unwrap();
        let m = PadloadManifest::load(&path).unwrap();
        std::fs::remove_file(&path).ok();
        let st = SymTab::default();
        let words = m.resolve(&st).unwrap();
        assert_eq!(
            words,
            vec![PadWord {
                ecadr: 0o1,
                word: 0o42
            }]
        );
    }

    #[test]
    fn padload_manifest_load_missing_file_names_the_path() {
        let path = std::env::temp_dir().join("padload_load_test_does_not_exist.toml");
        let err = PadloadManifest::load(&path).unwrap_err();
        assert!(format!("{err:#}").contains("padload_load_test_does_not_exist.toml"));
    }

    #[test]
    fn render_manifest_toml_round_trips_through_load() {
        let inp = P66ScenarioInputs {
            site_lat_deg: 0.674,
            site_lon_deg: 23.473,
            alt_m: 500.0,
            vz_ms: 0.0,
            epoch_cs: 0.0,
        };
        let m = generate_p66_manifest(&inp);
        let text = render_manifest_toml(&m, true).unwrap();
        let reparsed: PadloadManifest = toml::from_str(&text).unwrap();
        assert_eq!(reparsed.word.len(), m.word.len());
        let st = SymTab::default();
        assert_eq!(reparsed.resolve(&st).unwrap(), m.resolve(&st).unwrap());
    }
}
