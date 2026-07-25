//! Task 14 Step 2: the full sim plumbing against a STUB AGC (no live
//! yaAGC). A tokio task plays the AGC — it turns the engine on after
//! 200 ms and answers the sim's THRUST DINC strobes with hover-consistent
//! POUT pulses — while the sim thread runs the closed loop and broadcasts
//! telemetry. Asserts the telemetry cadence, that frames parse as
//! `ServerMsg::Telemetry`, that `frozen` flips false after engine-on, and
//! that everything shuts down cleanly. Fast (not `#[ignore]`).
use eagle_agc_protocol::dsky::DskyState;
use eagle_agc_protocol::Packet;
use eagle_runtime::scenario::Scenario;
use eagle_runtime::sim::{agc_packet_to_simin, spawn_sim, SimCore, SimIn};
use eagle_schema::ServerMsg;
use std::path::PathBuf;
use std::time::Duration;

fn scenario() -> Scenario {
    Scenario::load(
        &PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../../scenarios/p66-gate.toml"),
    )
    .unwrap()
}

#[tokio::test]
async fn sim_pipeline_with_stub_agc_streams_telemetry() {
    let sc = scenario();
    let core = SimCore::new(&sc, 0.0);
    let hover_pulses = (core_mass(&sc) * 1.62 / 12.0).round() as i64;

    let (sim_in_tx, sim_in_rx) = std::sync::mpsc::channel::<SimIn>();
    // sim → AGC (to_agc packets: PIPA/CDU/DINC)
    let (agc_tx, mut agc_rx) = tokio::sync::mpsc::unbounded_channel::<Packet>();
    let (telem_tx, mut telem_rx) = tokio::sync::broadcast::channel::<String>(1024);
    let (rod_tx, _rod_rx) = tokio::sync::mpsc::unbounded_channel::<i32>();

    let handle = spawn_sim(core, sim_in_rx, agc_tx, telem_tx, rod_tx);

    // --- Stub AGC ------------------------------------------------------
    // Forwards its "outputs" to the sim through the real decode path.
    let stub_in = sim_in_tx.clone();
    let feed = move |pkt: Packet, dsky: &mut DskyState| {
        for ev in agc_packet_to_simin(&pkt, dsky) {
            let _ = stub_in.send(ev);
        }
    };
    let stub = tokio::spawn(async move {
        let mut dsky = DskyState::default();
        // Arm the throttle and prime a hover command up front.
        feed(Packet::io(0o14, 1 << 3).unwrap(), &mut dsky); // THRUST DRIVE
        for _ in 0..hover_pulses {
            feed(Packet::counter(0o55, 0o15).unwrap(), &mut dsky); // POUT
        }
        // Engine on after 200 ms (frozen must flip false only now).
        tokio::time::sleep(Duration::from_millis(200)).await;
        feed(Packet::io(0o11, 1 << 12).unwrap(), &mut dsky); // ENGINE ON
        // Then keep answering DINC strobes with POUT so thrust holds.
        while let Ok(Some(p)) =
            tokio::time::timeout(Duration::from_millis(500), agc_rx.recv()).await
        {
            // A DINC strobe is a counter write to 055; answer POUT.
            if p.channel == 0o55 {
                feed(Packet::counter(0o55, 0o15).unwrap(), &mut dsky);
            }
        }
    });

    // --- Collect telemetry for ~1 s -----------------------------------
    let mut frames: Vec<String> = Vec::new();
    let deadline = tokio::time::Instant::now() + Duration::from_millis(1000);
    while tokio::time::Instant::now() < deadline {
        if let Ok(Ok(f)) = tokio::time::timeout(Duration::from_millis(200), telem_rx.recv()).await {
            frames.push(f);
        }
    }

    // ~10 telemetry frames/s (every 10th of 100 ticks/s); require >= 8.
    assert!(frames.len() >= 8, "telemetry too slow: {} frames", frames.len());

    // Every frame is a well-formed Telemetry message.
    let parsed: Vec<eagle_schema::TelemetryMsg> = frames
        .iter()
        .map(|f| match serde_json::from_str::<ServerMsg>(f).unwrap() {
            ServerMsg::Telemetry(t) => t,
            _ => panic!("non-telemetry frame on the sim broadcast"),
        })
        .collect();

    // Frozen at the start, false once the stub turned the engine on.
    assert!(parsed.first().unwrap().frozen, "should start frozen");
    assert!(
        parsed.iter().any(|t| !t.frozen),
        "frozen never cleared after stub engine-on"
    );

    // --- Clean shutdown ------------------------------------------------
    handle.stop.send(()).unwrap();
    let joined = tokio::task::spawn_blocking(move || handle.join.join());
    let res = tokio::time::timeout(Duration::from_millis(500), joined)
        .await
        .expect("sim thread did not join")
        .unwrap();
    assert!(res.is_ok(), "sim thread panicked");
    drop(sim_in_tx);
    stub.abort();
}

fn core_mass(sc: &Scenario) -> f64 {
    sc.gate.mass_dry_kg + sc.gate.fuel_dps_kg + sc.gate.fuel_rcs_kg
}
