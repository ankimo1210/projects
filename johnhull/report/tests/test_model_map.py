"""The reader map must cover the catalogue and reject stale or broken maps."""

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
GUIDE = PROJECT / "book/notebooks/guide"


def test_committed_map_passes_the_read_only_cli_check():
    result = subprocess.run(
        [sys.executable, str(PROJECT / "scripts/build_model_map.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _builder():
    # Keep missing deliverables an assertion failure during the initial RED run.
    assert (PROJECT / "scripts/build_model_map.py").is_file(), "model-map builder missing"
    from johnhull.scripts import build_model_map

    return build_model_map


@pytest.fixture
def definition():
    return json.loads((GUIDE / "model_map.json").read_text())


def test_catalogue_has_no_unmapped_or_invented_rows(definition):
    """Dropping a catalogue model or retaining a renamed row must fail."""
    expected = set()
    section = ""
    for line in (PROJECT / "MODEL_INDEX.md").read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].split()[0].rstrip(".")
        if section not in {*(str(i) for i in range(1, 15)), "P3", "P4"}:
            continue
        if line.startswith("| ") and not line.startswith(("| Model |", "| Module |")):
            expected.add(section + "/" + line.split("|")[1].strip())
    covered = {r for card in definition["cards"] for r in card["catalogue_rows"]}
    assert covered == expected


def test_committed_outputs_match_the_definition_byte_for_byte(definition):
    """Changing coordinates, text, nodes or Plotly version requires regeneration."""
    outputs = _builder().render(definition, PROJECT)
    for relative, content in outputs.items():
        assert (GUIDE / relative).read_bytes() == content, relative


def test_graph_and_card_ids_agree(definition):
    outputs = _builder().render(definition, PROJECT)
    graph = json.loads(outputs["model_map/figure.json"])
    plotted = {item for trace in graph["data"] for item in trace.get("customdata", [])}
    cards = set(re.findall(rb"\(model-([a-z0-9-]+)\)=\n### ", outputs["models.md"]))
    assert plotted == {c["id"] for c in definition["cards"]}
    assert {c.decode() for c in cards} == plotted


def test_real_map_links_resolve(definition):
    _builder().validate(definition, PROJECT)


@pytest.mark.parametrize("field", ["state", "assumptions", "method", "uses", "scope"])
def test_card_cannot_silently_lose_its_explanation(definition, field):
    altered = copy.deepcopy(definition)
    altered["cards"][0][field] = ""
    with pytest.raises(ValueError, match=field):
        _builder().validate(altered, PROJECT)


@pytest.mark.parametrize(
    "kind", ["missing-endpoint", "unknown-kind", "missing-condition", "missing-source"]
)
def test_invalid_relations_are_rejected(definition, kind):
    altered = copy.deepcopy(definition)
    edge = altered["edges"][0]
    if kind == "missing-endpoint":
        edge["to"] = "absent-model"
    elif kind == "unknown-kind":
        edge["kind"] = "similar"
    elif kind == "missing-condition":
        edge["condition"] = ""
    else:
        edge["sources"] = []
    with pytest.raises(ValueError):
        _builder().validate(altered, PROJECT)


def test_missing_card_and_duplicate_ids_are_rejected(definition):
    for mutation in ("missing", "duplicate"):
        altered = copy.deepcopy(definition)
        if mutation == "missing":
            altered["cards"].pop(0)
        else:
            altered["cards"].append(copy.deepcopy(altered["cards"][0]))
        with pytest.raises(ValueError):
            _builder().validate(altered, PROJECT)


@pytest.mark.parametrize("kind", ["book", "portal", "catalogue"])
def test_bad_local_targets_and_anchors_are_rejected(definition, kind):
    altered = copy.deepcopy(definition)
    link = next(link for card in altered["cards"] for link in card["links"] if link["kind"] == kind)
    link["anchor"] = "nonexistent-model-map-target"
    link["heading"] = "nonexistent-model-map-target"
    with pytest.raises(ValueError, match="link"):
        _builder().validate(altered, PROJECT)


def test_runtime_bundle_is_offline_and_under_added_file_limit(definition):
    outputs = _builder().render(definition, PROJECT)
    for filename, content in outputs.items():
        assert len(content) < 2_000_000, filename
    runtime = outputs["model_map/runtime.html"]
    # The library is embedded; the actual no-network/interaction contract is
    # exercised by check_model_map.cjs in Chromium, including file:// loading.
    assert b"<script src=" not in runtime


def test_cli_check_detects_stale_outputs_without_rewriting(tmp_path, definition):
    builder = _builder()
    outputs = builder.render(definition, PROJECT)
    for relative, content in outputs.items():
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    stale = tmp_path / "model_map/figure.json"
    stale.write_bytes(b"{}\n")
    assert builder.check_outputs(tmp_path, outputs) == ["model_map/figure.json"]
    assert stale.read_bytes() == b"{}\n"
