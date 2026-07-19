use gto_hu::bench::{
    geometric_schedule, peak_rss_mb, reference_cases, run_with_checkpoints, Checkpoint, RunRecord,
    RunTiming,
};

#[test]
fn schedule_is_ascending_deduped_and_ends_at_max() {
    let schedule = geometric_schedule(2_000, 8);
    assert_eq!(*schedule.last().unwrap(), 2_000);
    assert!(schedule.windows(2).all(|window| window[0] < window[1]));
    assert!(schedule.len() <= 8);
    assert_eq!(geometric_schedule(4, 8), vec![1, 2, 4]);
}

#[test]
fn river_checkpoints_are_deterministic_with_separated_timing() {
    let case = reference_cases()
        .into_iter()
        .find(|case| case.name == "river_srp100")
        .unwrap();
    let schedule = geometric_schedule(40, 4);
    let mut a = (case.build)(42);
    let mut b = (case.build)(42);
    let (checkpoints_a, timing_a) = run_with_checkpoints(&mut a, &schedule);
    let (checkpoints_b, _) = run_with_checkpoints(&mut b, &schedule);

    assert_eq!(checkpoints_a.len(), schedule.len());
    for (a, b) in checkpoints_a.iter().zip(&checkpoints_b) {
        assert_eq!(a.iters, b.iters);
        assert_eq!(a.expl.to_bits(), b.expl.to_bits());
        assert!(a.solve_s >= 0.0 && a.br_s > 0.0);
    }
    assert!(checkpoints_a.last().unwrap().expl < checkpoints_a.first().unwrap().expl);
    assert_eq!(timing_a.build_s, 0.0);
    assert!((timing_a.solve_s - checkpoints_a.last().unwrap().solve_s).abs() < 1e-9);
    let br_sum: f64 = checkpoints_a.iter().map(|checkpoint| checkpoint.br_s).sum();
    assert!((timing_a.checkpoint_br_s + timing_a.final_br_s - br_sum).abs() < 1e-9);
    assert!((timing_a.final_br_s - checkpoints_a.last().unwrap().br_s).abs() < 1e-12);
}

#[test]
fn json_has_expected_keys_metadata_and_string_escaping() {
    let record = RunRecord {
        schema_version: 1,
        case: "x".into(),
        config: "cfg".into(),
        label: "quoted \"label\"\nline".into(),
        git_commit: "deadbeef".into(),
        dirty: false,
        seed: 42,
        iterations: 10,
        points: 2,
        threads: 4,
        build_profile: "release",
        cpu: "cpu".into(),
        kernel: "k".into(),
        cmdline: "solver-bench \\\"arg\\\"".into(),
        table_bytes: 123,
        peak_rss_mb: 1.5,
        resume_count: 0,
        timing: RunTiming {
            build_s: 0.1,
            solve_s: 0.5,
            checkpoint_br_s: 0.2,
            final_br_s: 0.3,
        },
        checkpoints: vec![Checkpoint {
            iters: 1,
            solve_s: 0.5,
            br_s: 0.3,
            expl: 2.0,
            br: [1.0, 1.0],
        }],
    };
    let json = record.to_json();
    for key in [
        "\"schema_version\"",
        "\"case\"",
        "\"config\"",
        "\"label\"",
        "\"git_commit\"",
        "\"dirty\"",
        "\"seed\"",
        "\"iterations\"",
        "\"points\"",
        "\"threads\"",
        "\"build_profile\"",
        "\"cpu\"",
        "\"kernel\"",
        "\"cmdline\"",
        "\"table_bytes\"",
        "\"peak_rss_mb\"",
        "\"resume_count\"",
        "\"timing\"",
        "\"build_s\"",
        "\"solve_s\"",
        "\"checkpoint_br_s\"",
        "\"final_br_s\"",
        "\"checkpoints\"",
        "\"iters\"",
        "\"br_s\"",
        "\"expl\"",
        "\"br0\"",
        "\"br1\"",
    ] {
        assert!(json.contains(key), "missing {key} in {json}");
    }
    assert!(json.contains("quoted \\\"label\\\"\\nline"));
    assert!(json.contains("solver-bench \\\\\\\"arg\\\\\\\""));
    assert!(peak_rss_mb() > 0.0);
}
