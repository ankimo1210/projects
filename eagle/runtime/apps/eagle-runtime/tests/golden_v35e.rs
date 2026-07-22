use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::{keys::DskyKey, Packet};
use eagle_runtime::agc_session::{AgcConfig, AgcSession};
use eagle_runtime::server::to_msg;
use eagle_runtime::trace::milestones;
use eagle_schema::{DskyStateMsg, ServerMsg};
use std::collections::HashSet;
use std::path::PathBuf;

fn root() -> PathBuf { PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..") }

/// Drain and discard events until the DSKY-relevant channels (010 display
/// relay / 011 lamps / 0163 flash-lamp — the only ones the golden
/// comparison reads) have been quiet for 100 ms.
///
/// Scoped to those channels rather than "wait for total silence on the
/// wire": yaAGC's simulated environment free-runs several channels
/// forever, even at idle (confirmed via a throwaway diagnostic against the
/// live AGC: ch034 CDUZ and ch035 OPTY tick every ~16 ms indefinitely, and
/// ch010 itself carries a periodic no-op "row 0" heartbeat every
/// ~112-123 ms). A naive all-channel quiet check never observes 100 ms of
/// silence and hangs forever; scoping to the channels that matter
/// terminates reliably (observed ~120-200 ms per call across repeated
/// runs), since their idle period is comfortably above the threshold.
async fn settle_dsky(s: &mut AgcSession) {
    let start = tokio::time::Instant::now();
    let mut last_relevant = tokio::time::Instant::now();
    loop {
        match tokio::time::timeout(
            std::time::Duration::from_millis(20), s.events().recv()).await {
            Ok(Some(p)) if matches!(p.channel, 0o10 | 0o11 | 0o163) => {
                last_relevant = tokio::time::Instant::now();
            }
            Ok(Some(_)) => {}
            Ok(None) => break,
            Err(_) => {}
        }
        if last_relevant.elapsed() >= std::time::Duration::from_millis(100) { break; }
        // Defense in depth: never hang forever even if boot/echo behavior
        // changes (e.g. a different core image with denser DSKY traffic).
        assert!(start.elapsed() < std::time::Duration::from_secs(5),
            "settle_dsky did not settle within 5s safety cap");
    }
}

#[derive(serde::Serialize, serde::Deserialize, PartialEq, Debug)]
struct GoldenV35e {
    milestones: Vec<(String, String)>,
    final_state: DskyStateMsg,
}

async fn run_v35e() -> GoldenV35e {
    let mut s = AgcSession::start(AgcConfig {
        yaagc_bin: root().join("build/agc/yaAGC"),
        core_bin: root().join("build/agc/Luminary099.bin"),
        port: 19900,
    }).await.unwrap();
    tokio::time::sleep(std::time::Duration::from_secs(2)).await;

    // Flush boot-time traffic so the capture starts at the keying point.
    // (Flushing AFTER keying would race the AGC's immediate response to ENTR.)
    settle_dsky(&mut s).await;

    let mut packets: Vec<Packet> = Vec::new();
    let keys = [DskyKey::Verb, DskyKey::D3, DskyKey::D5, DskyKey::Entr];
    let last = keys.len() - 1;
    for (i, k) in keys.into_iter().enumerate() {
        s.send(k.packet()).unwrap();
        tokio::time::sleep(std::time::Duration::from_millis(200)).await;
        // Drain each digit-entry keystroke's echo (e.g. VERB briefly
        // showing "3 " after D3, before D5 completes it to "35") before
        // sending the next key. These pre-ENTR echoes are typing noise,
        // not part of the V35E signal, and whether one happens to still be
        // sitting in the (undrained, 1024-deep) events channel when the
        // capture loop below starts reading is a race against the AGC's
        // own redraw-cycle timing — observed to flip a golden run from 14
        // to 13 milestones across otherwise-identical replays. Stop one
        // key short of the end: settling right after ENTR would race the
        // AGC's immediate response to it, per the flush note above.
        if i != last { settle_dsky(&mut s).await; }
    }
    // Capture 3 s only: the V35 lamp test auto-reverts after ~5 s, and the
    // final-state check must land inside the all-8s window deterministically.
    let deadline = tokio::time::Instant::now() + std::time::Duration::from_secs(3);
    while tokio::time::Instant::now() < deadline {
        if let Ok(Some(p)) = tokio::time::timeout(
            std::time::Duration::from_millis(500), s.events().recv()).await {
            packets.push(p);
        }
    }
    s.shutdown();

    let mut state = DskyState::default();
    // Track the (verb_noun_flash, key_rel, opr_err) triple after every
    // applied packet. yaAGC drives these 3 bits via ch0163 flash
    // modulation (vendor agc_engine.c:1727-1744, DSKY_FLASH_PERIOD: 1.28s
    // cycle, 75% duty): during the V35 lamp test they oscillate
    // phase-coherently between (false,true,true) [75% of cycle] and
    // (true,false,false) [25%]. Recording starts only once the first ch
    // 0o163 packet has been applied: before that, DskyState::default()'s
    // (false,false,false) is just the pre-flash-test default, not an
    // observed flash phase, and would spuriously fail the phase-coherence
    // assert below.
    let mut seen_triples: HashSet<(bool, bool, bool)> = HashSet::new();
    let mut seen_0163 = false;
    for p in &packets {
        state.apply(p);
        if p.channel == 0o163 { seen_0163 = true; }
        if seen_0163 {
            seen_triples.insert((state.verb_noun_flash, state.key_rel, state.opr_err));
        }
    }

    const FLASH_OFF: (bool, bool, bool) = (false, true, true);
    const FLASH_ON: (bool, bool, bool) = (true, false, false);
    for t in &seen_triples {
        assert!(*t == FLASH_OFF || *t == FLASH_ON,
            "observed (verb_noun_flash, key_rel, opr_err) triple {t:?} is not one of \
             the two phase-coherent ch0163 flash states {FLASH_OFF:?} / {FLASH_ON:?} \
             (agc_engine.c:1727-1744)");
    }
    // The 3s capture window is >= 2 full 1.28s DSKY_FLASH_PERIOD cycles, so
    // both flash phases are deterministically observed regardless of which
    // phase the capture happened to start in.
    assert!(seen_triples.contains(&FLASH_OFF) && seen_triples.contains(&FLASH_ON),
        "expected both flash phases {FLASH_OFF:?} and {FLASH_ON:?} within the 3s \
         capture (>= 2 DSKY_FLASH_PERIOD cycles); saw {seen_triples:?}");

    let ServerMsg::DskyState(final_state) = to_msg(&state);
    GoldenV35e { milestones: milestones(&packets), final_state }
}

/// Exclude the 3 ch0163 flash-modulated bits (verb_noun_flash/key_rel/
/// opr_err) from the final-state equality check: their value at the
/// capture deadline depends on blink phase (agc_engine.c:1727-1744), which
/// `run_v35e` pins instead via the phase-coherence and both-phases-observed
/// assertions above. comp_acty (ch011) is also environment-modulated in
/// principle but has been stable (false) across ~15 recorded runs, so it
/// stays in strict equality below — first suspect if this golden ever
/// flakes again.
fn normalize(mut m: DskyStateMsg) -> DskyStateMsg {
    m.verb_noun_flash = false;
    m.key_rel = false;
    m.opr_err = false;
    m
}

#[tokio::test]
#[ignore = "needs make agc artifacts"]
async fn golden_v35e_milestones_and_final_state() {
    let golden_path = root().join("tests/golden-agc/v35e.golden.json");
    let got = run_v35e().await;
    assert!(!got.milestones.is_empty(), "no display milestones captured");
    // Sanity even in record mode: mid-lamp-test the displays must be all 8s.
    assert_eq!(got.final_state.verb, "88");
    assert_eq!(got.final_state.noun, "88");
    assert_eq!(got.final_state.prog, "88");
    if std::env::var("GOLDEN_RECORD").is_ok() {
        std::fs::write(&golden_path,
            serde_json::to_string_pretty(&got).unwrap()).unwrap();
        eprintln!("recorded golden to {golden_path:?}");
        return;
    }
    let want: GoldenV35e = serde_json::from_str(
        &std::fs::read_to_string(&golden_path)
            .expect("golden file missing — run with GOLDEN_RECORD=1 first"),
    ).unwrap();
    assert_eq!(got.milestones, want.milestones, "V35E display sequence diverged");
    assert_eq!(normalize(got.final_state), normalize(want.final_state),
        "final DSKY state (displays/lamps) diverged from golden \
         (verb_noun_flash/key_rel/opr_err excluded — pinned separately above)");
}
