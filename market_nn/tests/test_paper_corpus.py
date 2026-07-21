from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "build_paper_corpus.py"
SPEC = importlib.util.spec_from_file_location("build_paper_corpus", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_normalize_document_artifact_paths() -> None:
    paper_id = "sample-paper"
    document = {
        "pictures": [
            {"uri": ("/tmp/paper-corpus/docling/sample-paper_artifacts/image_000001_deadbeef.png")}
        ],
        "pages": {"1": {"image": {"uri": "sample-paper_artifacts/page_000001_deadbeef.png"}}},
        "source": {"filename": "sample-paper.pdf"},
    }

    normalized = MODULE.normalize_document_artifact_paths(document, paper_id)

    assert normalized["pictures"][0]["uri"] == "images/image_000001_deadbeef.png"
    assert normalized["pages"]["1"]["image"]["uri"] == "images/page_000001_deadbeef.png"
    assert normalized["source"]["filename"] == "sample-paper.pdf"
