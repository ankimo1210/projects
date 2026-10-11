"""Separate historical producer and current verifier using tiny source trees."""

import copy
import importlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[2] / "johnhull/research/RB-F04/dynamic_hedging"
sys.path.insert(0, str(RESEARCH))
import _pilot_saved_storage as storage  # noqa: E402
import run_reference as runner  # noqa: E402

MODULES = (
    "reference_methods",
    "run_fresh",
    "check_fresh",
    "run_pilot",
    "check_pilot",
    "run_main",
    "check_main",
    "run_reference",
    "check_initial_quotes",
    "check_selected_calls",
    "_pilot_transport",
    "_tiny_helper",
)


def reader():
    assert importlib.util.find_spec("_pilot_saved_provenance") is not None, (
        "saved producer/verifier provenance boundary is not implemented"
    )
    return importlib.import_module("_pilot_saved_provenance")


def make_source(root, label):
    base = root / "johnhull/research/RB-F04/dynamic_hedging"
    base.mkdir(parents=True)
    for name in MODULES:
        text = f"# tiny {label} source: {name}\n"
        if name == "run_pilot":
            text += "import _tiny_helper\n"
        (base / f"{name}.py").write_text(text)
    closure = root / "deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_closure.py"
    closure.parent.mkdir(parents=True)
    closure.write_text(f"# tiny {label} closure\n")


def bind_loaded_aliases(root, monkeypatch):
    # Only loaded-path metadata is simulated. The real AST closure walker,
    # required-entrypoint checks, alias refusal, and source_registry run unchanged.
    base = root / "johnhull/research/RB-F04/dynamic_hedging"
    for name in MODULES:
        for alias in (name, "dynamic_research." + name):
            module = types.ModuleType(alias)
            module.__file__ = str(base / f"{name}.py")
            if name == "run_reference":
                module.execution_source_identity = runner.execution_source_identity
                module.payload_digest = runner.payload_digest
                module.protocol = runner.protocol
            monkeypatch.setitem(sys.modules, alias, module)
    name = "deep_hedge_price._dynamic_hedging_closure"
    module = types.ModuleType(name)
    module.__file__ = str(
        root / "deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_closure.py"
    )
    monkeypatch.setitem(sys.modules, name, module)


@pytest.fixture
def sources(tmp_path, monkeypatch):
    producer, verifier = tmp_path / "producer", tmp_path / "verifier"
    make_source(producer, "original")
    make_source(verifier, "corrected")
    bind_loaded_aliases(producer, monkeypatch)
    original = runner.execution_source_identity(producer)
    bind_loaded_aliases(verifier, monkeypatch)
    actual = runner.execution_source_identity(verifier)
    bindings = {"parameters": "1" * 64, "original_grid": "2" * 64}
    plan = {
        "source": original,
        "input_bindings": bindings,
        "jobs": [{"id": "original:0", "original_n": 65536}],
        "history": [{"original_failed_cost_seconds": None}],
    }
    recipe = {
        "schema": "rb-f04-saved-producer-verifier-binding-v1",
        "planned_before_check": True,
        "root_preapproved": True,
        "scope": "saved_original_raw_only",
        "producer_source_sha256": storage.payload_digest(original),
        "producer_source_files": dict(original["files"]),
        "producer_plan_sha256": storage.payload_digest(plan),
        "producer_input_bindings_sha256": storage.payload_digest(bindings),
        "verifier_source_sha256": storage.payload_digest(actual),
    }
    return {
        "producer": producer,
        "verifier": verifier,
        "source": original,
        "actual_verifier": actual,
        "plan": plan,
        "bindings": bindings,
        "recipe": recipe,
    }


def authenticate(fixture):
    return reader().authenticate_saved_sources(
        fixture["source"],
        producer_root=fixture["producer"],
        verifier_root=fixture["verifier"],
        locked_plan=fixture["plan"],
        input_bindings=fixture["bindings"],
        trusted_binding=fixture["recipe"],
    )


def test_original_producer_and_current_verifier_remain_separate(sources):
    before = copy.deepcopy(sources["plan"])
    result = authenticate(sources)
    assert result["producer_source"] == sources["source"]
    assert result["verifier_source"] == sources["actual_verifier"]
    assert result["producer_source_sha256"] != result["verifier_source_sha256"]
    assert result["locked_plan"] is sources["plan"]
    assert result["input_bindings"] == sources["bindings"]
    assert sources["plan"] == before
    assert result["provenance"]["scope"] == "saved_original_raw_only"
    assert not {"financial_qualification", "qualified", "closed", "financial_cap"} & result.keys()
    assert result["locked_plan"]["history"][0]["original_failed_cost_seconds"] is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("root_preapproved", False),
        ("planned_before_check", False),
        ("scope", "fresh_financial_run"),
        ("schema", "unrelated-schema"),
    ],
)
def test_pending_or_wrong_scope_is_refused_before_source_access(sources, monkeypatch, key, value):
    sources["recipe"][key] = value
    monkeypatch.setattr(
        runner.protocol,
        "source_registry",
        lambda *args: pytest.fail("pending authority touched source bytes"),
    )
    with pytest.raises(ValueError, match="trusted saved"):
        authenticate(sources)


def test_producer_cannot_be_replaced_with_current_verifier(sources):
    sources["source"] = sources["actual_verifier"]
    with pytest.raises(ValueError, match="producer source"):
        authenticate(sources)


def test_role_reversal_does_not_inherit_trusted_recipe(sources):
    sources["producer"], sources["verifier"] = sources["verifier"], sources["producer"]
    with pytest.raises(ValueError):
        authenticate(sources)


@pytest.mark.parametrize("kind", ["changed", "missing", "symlink"])
def test_full_archived_producer_bytes_are_verified(sources, tmp_path, kind):
    relative = next(iter(sources["source"]["files"]))
    path = sources["producer"] / relative
    if kind == "changed":
        path.write_text("# tampered original source\n")
    elif kind == "missing":
        path.unlink()
    else:
        outside = tmp_path / "outside.py"
        path.rename(outside)
        path.symlink_to(outside)
    with pytest.raises((ValueError, FileNotFoundError)):
        authenticate(sources)


def test_extra_expected_producer_roster_row_is_refused(sources):
    sources["recipe"]["producer_source_files"]["extra.py"] = "0" * 64
    with pytest.raises(ValueError, match=r"producer.*roster"):
        authenticate(sources)


def test_original_plan_source_cannot_be_relabelled(sources):
    sources["plan"]["source"] = sources["actual_verifier"]
    # Even a newly approved digest cannot make the declared original source agree.
    sources["recipe"]["producer_plan_sha256"] = storage.payload_digest(sources["plan"])
    with pytest.raises(ValueError, match="original plan source"):
        authenticate(sources)


def test_original_plan_roster_change_does_not_inherit_expected_digest(sources):
    sources["plan"]["jobs"][0]["original_n"] = 1024
    with pytest.raises(ValueError, match="producer plan"):
        authenticate(sources)


def test_actual_input_identities_cannot_inherit_original_bindings(sources):
    sources["bindings"] = {**sources["bindings"], "parameters": "0" * 64}
    with pytest.raises(ValueError, match="input bindings"):
        authenticate(sources)


def test_current_verifier_stale_bytes_are_refused(sources):
    path = sources["verifier"] / "johnhull/research/RB-F04/dynamic_hedging/check_pilot.py"
    path.write_text("# changed after prior review\n")
    with pytest.raises(ValueError, match="verifier source"):
        authenticate(sources)


def test_current_verifier_loaded_alias_from_old_archive_is_refused(sources, monkeypatch):
    module = types.ModuleType("check_pilot")
    module.__file__ = str(
        sources["producer"] / "johnhull/research/RB-F04/dynamic_hedging/check_pilot.py"
    )
    monkeypatch.setitem(sys.modules, "check_pilot", module)
    with pytest.raises(ValueError, match="loaded source differs"):
        authenticate(sources)


def test_current_verifier_missing_required_entrypoint_is_refused(sources):
    (sources["verifier"] / "johnhull/research/RB-F04/dynamic_hedging/run_main.py").unlink()
    with pytest.raises(ValueError, match="required execution source missing"):
        authenticate(sources)


def test_current_verifier_dynamic_import_is_never_silently_certified(sources):
    path = sources["verifier"] / "johnhull/research/RB-F04/dynamic_hedging/check_pilot.py"
    path.write_text('__import__("math")\n')
    sources["recipe"]["verifier_source_sha256"] = storage.payload_digest(
        runner.execution_source_identity(sources["verifier"])
    )
    with pytest.raises(ValueError, match=r"dynamic.*verifier"):
        authenticate(sources)


def test_original_producer_is_authenticated_without_running_its_loaded_alias_check(sources):
    # All loaded research aliases deliberately belong to the NEW verifier.
    with pytest.raises(ValueError, match="loaded source differs"):
        runner.execution_source_identity(sources["producer"])
    result = authenticate(sources)
    assert result["producer_source_sha256"] == sources["recipe"]["producer_source_sha256"]


def test_approval_flags_alone_cannot_supply_trusted_expected_bindings(sources):
    sources["recipe"] = {
        key: sources["recipe"][key]
        for key in ("schema", "planned_before_check", "root_preapproved", "scope")
    }
    with pytest.raises(ValueError, match=r"trusted saved.*digests"):
        authenticate(sources)


def test_typed_actual_inputs_are_not_reloaded_by_this_source_boundary(sources, monkeypatch):
    # The actual-input caller passes computed identities; this helper only binds
    # them to the original plan and externally trusted expected recipe.
    monkeypatch.setattr(
        runner.protocol,
        "read_artifact",
        lambda *args: pytest.fail("typed input/raw artifact reloaded"),
    )
    result = authenticate(sources)
    assert result["input_bindings"] == sources["plan"]["input_bindings"]
