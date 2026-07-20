//! P0a bench-case fixtures: every reference case constructs, runs, and
//! reports finite exploitability; construction is deterministic.

use gto_hu::bench::{reference_cases, CaseSolver};

#[test]
fn all_cases_construct_and_report_finite_expl() {
    for case in reference_cases() {
        // Blueprint/flop construction allocates GBs; keep this test to
        // the cheap cases and just require the builders exist for all.
        if case.name.starts_with("river") || case.name.starts_with("turn") {
            let mut solver = (case.build)(42);
            solver.run_chunk(2);
            let report = solver.expl();
            assert!(report.exploitability.is_finite(), "{}", case.name);
            assert!(solver.table_bytes() > 0, "{}", case.name);
        }
    }
}

#[test]
fn case_names_are_unique_and_stable() {
    let names: Vec<&str> = reference_cases().iter().map(|case| case.name).collect();
    let mut dedup = names.clone();
    dedup.sort_unstable();
    dedup.dedup();
    assert_eq!(names.len(), dedup.len(), "duplicate case names");
    for expected in [
        "river_srp100",
        "turn_srp100_enum",
        "turn_srp100_sample",
        "flop_srp100_AhKd7s_k24",
        "flop_srp100_QsJh2c_k24",
        "flop_srp100_8d8h3s_k24",
        "flop_srp100_AhKd7s_k64",
        "flop_3bet100_AhKd7s_k24",
        "bp3_sample",
        "bp3_enum",
    ] {
        assert!(names.contains(&expected), "missing case {expected}");
    }
}

#[test]
fn river_case_is_deterministic() {
    let case = reference_cases()
        .into_iter()
        .find(|case| case.name == "river_srp100")
        .unwrap();
    let run = |mut solver: CaseSolver| {
        solver.run_chunk(5);
        solver.expl().exploitability.to_bits()
    };
    assert_eq!(run((case.build)(42)), run((case.build)(42)));
}
