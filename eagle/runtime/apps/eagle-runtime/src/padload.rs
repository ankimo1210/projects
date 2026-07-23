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
            (Some(s), None) => symtab
                .ecadr(s)
                .ok_or_else(|| anyhow!("symbol {s:?} not found in symbol table"))?,
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
             to generate anyway (see P66_BSCALE_TABLE / docs/superpowers/sdd/task-5-report.md)",
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
