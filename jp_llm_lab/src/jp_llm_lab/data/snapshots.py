"""Reproducible corpus snapshots (spec §4.1).

One deterministic pass over a streaming source assigns cleaned, deduplicated
documents to splits:

    doc index i (post-filter):  i % 50 == 0 → validation
                                i % 50 == 1 → calibration
                                i % 50 == 2 → test        (until each is full)
                                otherwise   → train pool

The train pool is written as ~5M-char JSONL.GZ shards. The `smoke`, `pilot`
and `main` snapshots are NESTED PREFIXES of the train pool (smoke ⊂ pilot ⊂
main), so smaller experiments use exactly the beginning of the larger corpus
— while validation / calibration / test are disjoint from all of them by
construction (different documents).

Everything is recorded in data/manifests/snapshots_v1.json: source dataset +
config, license, per-file sha256, doc/char counts, filter settings. Analysis
code loads shards from disk only — the HF stream is never re-read.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from ..utils.io import load_json, repo_root, save_json
from .corpus_stats import japanese_ratio

SNAP_DIR_REL = Path("data/snapshots")
MANIFEST_REL = Path("data/manifests/snapshots_v1.json")

SHARD_CHARS = 5_000_000
# char targets ≈ token targets × 1.7 chars/token (measured ratio recorded later)
SPLIT_TARGETS = {"validation": 1_700_000, "calibration": 1_700_000, "test": 1_700_000}
NESTED_TARGETS = {"smoke": 1_700_000, "pilot": 17_000_000, "main": 170_000_000}

FILTER_SETTINGS = {"min_chars": 200, "max_chars": 100_000, "min_japanese_ratio": 0.5}


def clean_doc(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()


def keep_doc(text: str) -> bool:
    n = len(text)
    if n < FILTER_SETTINGS["min_chars"] or n > FILTER_SETTINGS["max_chars"]:
        return False
    return japanese_ratio(text) >= FILTER_SETTINGS["min_japanese_ratio"]


class _ShardWriter:
    """Accumulates docs into fixed-size JSONL.GZ shards."""

    def __init__(self, directory: Path, prefix: str, shard_chars: int = SHARD_CHARS):
        self.dir = directory
        self.prefix = prefix
        self.shard_chars = shard_chars
        self.docs: list[str] = []
        self.chars = 0
        self.total_chars = 0
        self.total_docs = 0
        self.files: list[dict] = []

    def add(self, text: str) -> None:
        self.docs.append(text)
        self.chars += len(text)
        self.total_chars += len(text)
        self.total_docs += 1
        if self.chars >= self.shard_chars:
            self.flush()

    def flush(self) -> None:
        if not self.docs:
            return
        idx = len(self.files)
        path = self.dir / f"{self.prefix}_{idx:03d}.jsonl.gz"
        payload = "".join(json.dumps({"text": d}, ensure_ascii=False) + "\n" for d in self.docs)
        raw = payload.encode("utf-8")
        with gzip.open(path, "wb", compresslevel=6) as f:
            f.write(raw)
        self.files.append(
            {
                "file": path.name,
                "n_docs": len(self.docs),
                "n_chars": self.chars,
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        self.docs, self.chars = [], 0


def _iter_fineweb2ja() -> Iterator[str]:
    from datasets import load_dataset

    ds = load_dataset("HuggingFaceFW/fineweb-2", name="jpn_Jpan", split="train", streaming=True)
    for doc in ds:
        yield doc["text"]


def _iter_wikipedia_ja() -> Iterator[str]:
    from datasets import load_dataset

    ds = load_dataset("wikimedia/wikipedia", "20231101.ja", split="train", streaming=True)
    for doc in ds:
        yield doc["text"]


SOURCES = {
    "fineweb2ja": {
        "iter": _iter_fineweb2ja,
        "dataset": "HuggingFaceFW/fineweb-2 (config jpn_Jpan, split train, streaming order)",
        "license": "ODC-By 1.0 (subject to CommonCrawl ToU)",
    },
    "wikipedia_ja": {
        "iter": _iter_wikipedia_ja,
        "dataset": "wikimedia/wikipedia (config 20231101.ja, split train, streaming order)",
        "license": "CC-BY-SA-4.0 / GFDL",
    },
}


def _load_manifest(root: Path) -> dict:
    path = root / MANIFEST_REL
    if path.exists():
        return load_json(path)
    return {"version": "snapshots_v1", "filter": FILTER_SETTINGS, "sources": {}, "snapshots": {}}


def build_fineweb2ja_snapshots(
    root: Path | None = None,
    main_chars: int = NESTED_TARGETS["main"],
    progress_every: int = 20_000,
) -> dict:
    """Single deterministic pass building validation/calibration/test + train pool."""
    root = root or repo_root()
    out_dir = root / SNAP_DIR_REL / "fineweb2ja"
    out_dir.mkdir(parents=True, exist_ok=True)

    splits = {name: _ShardWriter(out_dir, name, shard_chars=10**12) for name in SPLIT_TARGETS}
    train = _ShardWriter(out_dir, "train", SHARD_CHARS)
    seen: set[str] = set()
    n_stream = n_kept = n_dup = n_filtered = 0

    for raw in SOURCES["fineweb2ja"]["iter"]():
        n_stream += 1
        text = clean_doc(raw)
        if not keep_doc(text):
            n_filtered += 1
            continue
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in seen:
            n_dup += 1
            continue
        seen.add(h)

        slot = n_kept % 50
        n_kept += 1
        if slot == 0 and splits["validation"].total_chars < SPLIT_TARGETS["validation"]:
            splits["validation"].add(text)
        elif slot == 1 and splits["calibration"].total_chars < SPLIT_TARGETS["calibration"]:
            splits["calibration"].add(text)
        elif slot == 2 and splits["test"].total_chars < SPLIT_TARGETS["test"]:
            splits["test"].add(text)
        else:
            train.add(text)

        if n_kept % progress_every == 0:
            print(
                f"[snapshots] streamed={n_stream:,} kept={n_kept:,} "
                f"train={train.total_chars/1e6:.0f}M chars "
                f"(dup={n_dup:,} filtered={n_filtered:,})",
                flush=True,
            )
        if train.total_chars >= main_chars and all(
            splits[s].total_chars >= SPLIT_TARGETS[s] for s in splits
        ):
            break

    train.flush()
    for w in splits.values():
        w.flush()

    manifest = _load_manifest(root)
    manifest["sources"]["fineweb2ja"] = {
        **{k: v for k, v in SOURCES["fineweb2ja"].items() if k != "iter"},
        "fetched_at": datetime.now(UTC).isoformat(),
        "streamed_docs": n_stream,
        "kept_docs": n_kept,
        "duplicates_removed": n_dup,
        "filtered_out": n_filtered,
        "assignment": "post-filter doc index i%50: 0→validation, 1→calibration, 2→test, else train pool",
    }
    for name, writer in splits.items():
        manifest["snapshots"][name] = {
            "source": "fineweb2ja",
            "files": writer.files,
            "n_docs": writer.total_docs,
            "n_chars": writer.total_chars,
        }
    manifest["snapshots"]["train_pool"] = {
        "source": "fineweb2ja",
        "files": train.files,
        "n_docs": train.total_docs,
        "n_chars": train.total_chars,
    }
    # nested prefixes of the train pool
    for name, target in NESTED_TARGETS.items():
        if target <= train.total_chars:
            manifest["snapshots"][name] = {
                "source": "fineweb2ja",
                "nested_prefix_of": "train_pool",
                "char_limit": target,
            }
    save_json(manifest, root / MANIFEST_REL)
    print(f"[snapshots] done: train {train.total_chars/1e6:.1f}M chars, {len(train.files)} shards")
    return manifest


def build_wikipedia_snapshot(root: Path | None = None, chars: int = 17_000_000) -> dict:
    root = root or repo_root()
    out_dir = root / SNAP_DIR_REL / "wikipedia_ja"
    out_dir.mkdir(parents=True, exist_ok=True)
    writer = _ShardWriter(out_dir, "wiki", SHARD_CHARS)
    seen: set[str] = set()
    for raw in SOURCES["wikipedia_ja"]["iter"]():
        text = clean_doc(raw)
        if not keep_doc(text):
            continue
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        writer.add(text)
        if writer.total_chars >= chars:
            break
    writer.flush()
    manifest = _load_manifest(root)
    manifest["sources"]["wikipedia_ja"] = {
        **{k: v for k, v in SOURCES["wikipedia_ja"].items() if k != "iter"},
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    manifest["snapshots"]["wiki_pilot"] = {
        "source": "wikipedia_ja",
        "files": writer.files,
        "n_docs": writer.total_docs,
        "n_chars": writer.total_chars,
    }
    save_json(manifest, root / MANIFEST_REL)
    print(f"[snapshots] wiki_pilot: {writer.total_chars/1e6:.1f}M chars, {writer.total_docs:,} docs")
    return manifest


# ------------------------------------------------------------------ loading
def _read_shard(path: Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line)["text"] for line in f if line.strip()]


def iter_snapshot_docs(name: str, root: Path | None = None) -> Iterator[str]:
    """Yield documents of a snapshot in canonical order (nested prefixes resolve
    to the train pool with a char budget; the last doc may overshoot slightly)."""
    root = root or repo_root()
    manifest = load_json(root / MANIFEST_REL)
    entry = manifest["snapshots"][name]
    if "nested_prefix_of" in entry:
        parent = manifest["snapshots"][entry["nested_prefix_of"]]
        src_dir = root / SNAP_DIR_REL / parent["source"]
        budget = entry["char_limit"]
        emitted = 0
        for file_info in parent["files"]:
            for doc in _read_shard(src_dir / file_info["file"]):
                yield doc
                emitted += len(doc)
                if emitted >= budget:
                    return
        return
    src_dir = root / SNAP_DIR_REL / entry["source"]
    for file_info in entry["files"]:
        yield from _read_shard(src_dir / file_info["file"])


def load_snapshot_text(name: str, root: Path | None = None, max_chars: int | None = None) -> str:
    parts: list[str] = []
    total = 0
    for doc in iter_snapshot_docs(name, root):
        parts.append(doc)
        total += len(doc)
        if max_chars is not None and total >= max_chars:
            break
    return "\n\n".join(parts)


def snapshot_summary(root: Path | None = None) -> dict:
    root = root or repo_root()
    return load_json(root / MANIFEST_REL)
