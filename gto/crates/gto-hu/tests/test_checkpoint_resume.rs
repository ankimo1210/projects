//! P0a Task 4A: durable checkpoints must resume long sampled solves with
//! bit-identical mutable state and retain a valid prior generation.

use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use gto_core::eval::parse_card;
use gto_hu::game::{Action, BettingState, PotType, BB};
use gto_hu::ranges::{combo_index, Range};
use gto_hu::solver::{Abstraction, BlueprintSolver, CfrVariant, ChanceMode, FlopSolver};
use gto_hu::tree::{
    build_flop_tree, FlopTreeConfig, Node, NodeKind, RaiseRule, StreetConfig, Tree,
};

const BUILD_ID: &str = "checkpoint-test-build";

struct TestDir(PathBuf);

impl TestDir {
    fn new(label: &str) -> Self {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "gto-hu-checkpoint-{label}-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir_all(&path).unwrap();
        Self(path)
    }

    fn path(&self) -> &Path {
        &self.0
    }
}

impl Drop for TestDir {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn card(value: &str) -> u8 {
    parse_card(value).unwrap()
}

fn board() -> [u8; 3] {
    [card("2c"), card("7d"), card("9h")]
}

fn other_board() -> [u8; 3] {
    [card("3c"), card("8d"), card("Th")]
}

fn tiny_ranges() -> [Range; 2] {
    let mut range0 = Range::new_empty();
    let mut range1 = Range::new_empty();
    for (a, b) in [
        (card("Qc"), card("Tc")),
        (card("Ah"), card("Ad")),
        (card("6s"), card("5s")),
    ] {
        range0.weights[combo_index(a, b)] = 1.0;
    }
    for (a, b) in [
        (card("Kh"), card("Qh")),
        (card("8s"), card("8d")),
        (card("As"), card("Js")),
    ] {
        range1.weights[combo_index(a, b)] = 1.0;
    }
    [range0, range1]
}

fn tiny_cfg(_pot_type: PotType) -> FlopTreeConfig {
    let passive = || StreetConfig {
        bet_pcts: vec![],
        allow_allin_bet: false,
        raise: RaiseRule::None,
        max_raises: 0,
    };
    FlopTreeConfig {
        flop: passive(),
        turn: passive(),
        river: StreetConfig {
            bet_pcts: vec![100],
            allow_allin_bet: false,
            raise: RaiseRule::None,
            max_raises: 0,
        },
    }
}

fn abstraction() -> Abstraction {
    Abstraction {
        buckets_river: 8,
        buckets_turn: 4,
    }
}

fn flop_solver(
    flop: [u8; 3],
    seed: u64,
    variant: CfrVariant,
    abs: Abstraction,
    pot: i64,
) -> FlopSolver {
    FlopSolver::new_abstracted(
        build_flop_tree(pot, 90 * BB, &tiny_cfg(PotType::Srp)),
        flop,
        tiny_ranges(),
        variant,
        ChanceMode::Sample { seed },
        abs,
    )
}

fn forced_line_tree() -> Tree {
    let root_state = BettingState::preflop_root(100 * BB);
    let raise = Action::Raise { to: 10 * BB };
    let facing_call = root_state.apply(raise);
    let closed = facing_call.apply(Action::Call);
    Tree {
        nodes: vec![
            Node {
                kind: NodeKind::Action { actor: 0 },
                state: root_state,
                children: vec![(raise, 1)],
            },
            Node {
                kind: NodeKind::Action { actor: 1 },
                state: facing_call,
                children: vec![(Action::Call, 2)],
            },
            Node {
                kind: NodeKind::NextStreet {
                    pot_type: PotType::Srp,
                },
                state: closed,
                children: vec![],
            },
        ],
    }
}

fn blueprint(flops: Vec<[u8; 3]>, seed: u64) -> BlueprintSolver {
    let weights = vec![1.0; flops.len()];
    BlueprintSolver::new_with_configs(
        forced_line_tree(),
        tiny_ranges(),
        CfrVariant::cfr_plus_default(),
        flops,
        weights,
        abstraction(),
        true,
        seed,
        tiny_cfg,
    )
}

fn assert_flop_equal(left: &FlopSolver, right: &FlopSolver) {
    assert_eq!(left.iteration(), right.iteration());
    assert_eq!(left.state_checksum(), right.state_checksum());
    let left_expl = left.exploitability_bb();
    let right_expl = right.exploitability_bb();
    assert_eq!(
        left_expl.exploitability.to_bits(),
        right_expl.exploitability.to_bits()
    );
    assert_eq!(
        left_expl.br_value[0].to_bits(),
        right_expl.br_value[0].to_bits()
    );
    assert_eq!(
        left_expl.br_value[1].to_bits(),
        right_expl.br_value[1].to_bits()
    );
}

#[test]
fn sampled_flop_resume_is_bit_identical() {
    let dir = TestDir::new("flop-exact");
    let mut uninterrupted = flop_solver(
        board(),
        17,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    let mut partial = flop_solver(
        board(),
        17,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    uninterrupted.run(80);
    partial.run(30);

    let saved = partial.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    assert_eq!(saved.iteration, 30);
    assert!(saved.bytes > 0);

    let mut restored = flop_solver(
        board(),
        17,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    let loaded = restored.restore_checkpoint(&saved.path, BUILD_ID).unwrap();
    assert_eq!(loaded.iteration, 30);
    restored.run(50);

    assert_flop_equal(&uninterrupted, &restored);
}

#[test]
fn blueprint_resume_restores_preflop_and_every_subgame() {
    let dir = TestDir::new("blueprint-exact");
    let flops = vec![board(), [card("Qs"), card("Jh"), card("2d")]];
    let mut uninterrupted = blueprint(flops.clone(), 91);
    let mut partial = blueprint(flops.clone(), 91);
    uninterrupted.run(20);
    partial.run(7);

    let saved = partial.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    let mut restored = blueprint(flops, 91);
    restored.restore_checkpoint(&saved.path, BUILD_ID).unwrap();
    restored.run(13);

    assert_eq!(uninterrupted.iteration(), restored.iteration());
    assert_eq!(uninterrupted.state_checksum(), restored.state_checksum());
    let left = uninterrupted.exploitability_bb();
    let right = restored.exploitability_bb();
    assert_eq!(
        left.exploitability.to_bits(),
        right.exploitability.to_bits()
    );
    assert_eq!(left.br_value[0].to_bits(), right.br_value[0].to_bits());
    assert_eq!(left.br_value[1].to_bits(), right.br_value[1].to_bits());
}

#[test]
fn sampled_dcfr_resume_preserves_lazy_discount_and_rng_state() {
    let dir = TestDir::new("dcfr-exact");
    let mut uninterrupted = flop_solver(
        board(),
        0xB7,
        CfrVariant::dcfr_default(),
        abstraction(),
        20 * BB,
    );
    let mut partial = flop_solver(
        board(),
        0xB7,
        CfrVariant::dcfr_default(),
        abstraction(),
        20 * BB,
    );
    uninterrupted.run(60);
    partial.run(13);

    let saved = partial.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    let mut restored = flop_solver(
        board(),
        0xB7,
        CfrVariant::dcfr_default(),
        abstraction(),
        20 * BB,
    );
    restored.restore_checkpoint(&saved.path, BUILD_ID).unwrap();
    restored.run(47);

    assert_flop_equal(&uninterrupted, &restored);
}

#[test]
fn incompatible_flop_configuration_is_rejected_before_mutation() {
    let dir = TestDir::new("config-mismatch");
    let mut source = flop_solver(
        board(),
        7,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    source.run(5);
    let saved = source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();

    let variants = [
        flop_solver(
            other_board(),
            7,
            CfrVariant::cfr_plus_default(),
            abstraction(),
            20 * BB,
        ),
        flop_solver(
            board(),
            8,
            CfrVariant::cfr_plus_default(),
            abstraction(),
            20 * BB,
        ),
        flop_solver(
            board(),
            7,
            CfrVariant::cfr_plus_default(),
            Abstraction {
                buckets_river: 7,
                buckets_turn: 4,
            },
            20 * BB,
        ),
        flop_solver(
            board(),
            7,
            CfrVariant::dcfr_default(),
            abstraction(),
            20 * BB,
        ),
        flop_solver(
            board(),
            7,
            CfrVariant::cfr_plus_default(),
            abstraction(),
            22 * BB,
        ),
    ];
    for mut candidate in variants {
        let before = candidate.state_checksum();
        let error = candidate
            .restore_checkpoint(&saved.path, BUILD_ID)
            .unwrap_err();
        assert!(error.to_string().contains("configuration fingerprint"));
        assert_eq!(candidate.state_checksum(), before);
    }

    let mut correct = flop_solver(
        board(),
        7,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    let before = correct.state_checksum();
    let error = correct
        .restore_checkpoint(&saved.path, "different-build")
        .unwrap_err();
    assert!(error.to_string().contains("build id"));
    assert_eq!(correct.state_checksum(), before);
}

#[test]
fn incompatible_blueprint_flop_list_is_rejected_before_mutation() {
    let dir = TestDir::new("blueprint-config");
    let mut source = blueprint(vec![board()], 5);
    source.run(3);
    let saved = source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();

    let mut candidate = blueprint(vec![other_board()], 5);
    let before = candidate.state_checksum();
    let error = candidate
        .restore_checkpoint(&saved.path, BUILD_ID)
        .unwrap_err();
    assert!(error.to_string().contains("configuration fingerprint"));
    assert_eq!(candidate.state_checksum(), before);
}

#[test]
fn auto_resume_falls_back_from_truncated_newest_generation() {
    let dir = TestDir::new("fallback");
    let mut source = flop_solver(
        board(),
        22,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    source.run(10);
    let previous = source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    source.run(10);
    let newest = source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    fs::OpenOptions::new()
        .write(true)
        .open(&newest.path)
        .unwrap()
        .set_len(32)
        .unwrap();

    let mut restored = flop_solver(
        board(),
        22,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    let loaded = restored.resume_latest(dir.path(), BUILD_ID).unwrap();
    assert_eq!(loaded.path, previous.path);
    assert_eq!(restored.iteration(), 10);

    // A subsequent save must retain the prior VALID generation, not merely
    // the two numerically newest filenames (the corrupt iter-20 file must go).
    source.run(10);
    let current = source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    assert_eq!(current.iteration, 30);
    assert!(current.path.exists());
    assert!(previous.path.exists());
    assert!(!newest.path.exists());
    let generations = fs::read_dir(dir.path())
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .starts_with("checkpoint-")
                && entry.path().extension().is_some_and(|ext| ext == "bin")
        })
        .count();
    assert_eq!(generations, 2);
}

#[test]
fn interrupted_tmp_does_not_advance_latest_or_remove_prior_generations() {
    let dir = TestDir::new("interrupted-write");
    let mut source = flop_solver(
        board(),
        44,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    source.run(4);
    source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();
    source.run(4);
    source.save_checkpoint(dir.path(), BUILD_ID, 2).unwrap();

    let latest_before = fs::read_to_string(dir.path().join("LATEST")).unwrap();
    let generations_before = fs::read_dir(dir.path())
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .starts_with("checkpoint-")
                && entry.path().extension().is_some_and(|ext| ext == "bin")
        })
        .count();
    fs::write(dir.path().join("checkpoint.tmp"), b"partial snapshot").unwrap();

    assert_eq!(
        fs::read_to_string(dir.path().join("LATEST")).unwrap(),
        latest_before
    );
    let generations_after = fs::read_dir(dir.path())
        .unwrap()
        .filter_map(Result::ok)
        .filter(|entry| {
            entry
                .file_name()
                .to_string_lossy()
                .starts_with("checkpoint-")
                && entry.path().extension().is_some_and(|ext| ext == "bin")
        })
        .count();
    assert_eq!(generations_after, generations_before);

    let mut restored = flop_solver(
        board(),
        44,
        CfrVariant::cfr_plus_default(),
        abstraction(),
        20 * BB,
    );
    restored.resume_latest(dir.path(), BUILD_ID).unwrap();
    assert_eq!(restored.iteration(), 8);
}
