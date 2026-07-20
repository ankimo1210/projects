from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pytest

from lob_reproductions.data import fi2010_public
from lob_reproductions.data.fi2010_public import (
    EXPECTED_FILES,
    audit_fi2010_archive,
    load_fi2010_member,
    matrix_from_values,
)
from lob_reproductions.provenance.sources import sha256_file


def _write_member(archive: zipfile.ZipFile, name: str, *, columns: int, offset: int) -> None:
    values = np.zeros((149, columns))
    for row in range(144):
        values[row] = row * 1_000.0 + np.arange(columns) + offset
    for label_index in range(5):
        values[144 + label_index] = ((np.arange(columns) + label_index + offset) % 3) + 1
    lines = "\n".join(" ".join(f"{value:.4f}" for value in row) for row in values)
    archive.writestr(name, lines + "\n")


@pytest.fixture()
def mini_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "fi2010_mini.zip"
    with zipfile.ZipFile(path, "w") as archive:
        for index, name in enumerate(sorted(EXPECTED_FILES)):
            _write_member(archive, name, columns=40, offset=index)
    digest = sha256_file(path)
    monkeypatch.setattr(
        fi2010_public,
        "dataset_manifest",
        lambda: {
            "author_archive_sha256": digest,
            "author_archive_url": "https://example.invalid/archive.zip",
            "terms_url": "https://example.invalid/terms",
            "redistribution_status": "not_redistributed",
        },
    )
    return path


def test_member_loader_parses_canonical_matrix_and_rejects_missing_member(
    mini_archive: Path,
) -> None:
    member = sorted(EXPECTED_FILES)[0]
    values = load_fi2010_member(mini_archive, member=member)
    assert values.shape == (149, 40)
    matrix = matrix_from_values(values)
    assert matrix.n_observations == 40
    np.testing.assert_array_equal(np.unique(matrix.values[144:149]), [1.0, 2.0, 3.0])
    # Author-contiguity assumption: one file is one windowing segment.
    assert np.unique(matrix.boundary_id()).size == 1
    with pytest.raises(FileNotFoundError, match=r"missing\.txt"):
        load_fi2010_member(mini_archive, member="missing.txt")


def test_audit_reports_labels_windows_and_never_claims_numbers(mini_archive: Path) -> None:
    report = audit_fi2010_archive(mini_archive, sequence_length=16, horizon=10)
    assert report["ok"] is True
    assert report["hash_matches"] is True
    assert report["members_match"] is True
    assert report["numerical_benchmark_attempted"] is False
    member = report["members"][sorted(EXPECTED_FILES)[0]]
    assert member["columns"] == 40
    assert member["contiguous_window_count"] == 40 - 16 + 1
    for horizon_distribution in member["label_distribution"].values():
        assert set(horizon_distribution) == {"up", "stationary", "down"}
        assert sum(horizon_distribution.values()) == 40
    assert member["sample_windows"]["count"] > 0
    assert member["sample_windows"]["feature_shape"] == [16, 40]


def test_audit_rejects_unsupported_horizon(mini_archive: Path) -> None:
    with pytest.raises(ValueError, match="horizon"):
        audit_fi2010_archive(mini_archive, sequence_length=16, horizon=17)


def test_cli_audit_command_reports_default_archive(
    mini_archive: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import json

    from lob_reproductions.cli import main

    monkeypatch.setattr(fi2010_public, "default_archive_path", lambda: mini_archive)
    assert main(["data", "audit-fi2010", "--sequence-length", "16", "--horizon", "10"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is True
    assert report["claim_limit"].startswith("dataset structural audit only")

    monkeypatch.setattr(
        fi2010_public, "default_archive_path", lambda: mini_archive.parent / "absent.zip"
    )
    assert main(["data", "audit-fi2010"]) == 2
