"""Compute corpus statistics for all snapshots → reports/figures/corpus_stats.json.

Reads snapshot shards from disk (no HF re-stream). Used by NB02.

Usage: uv run --no-sync python jp_llm_lab/scripts/corpus_report.py
"""

from __future__ import annotations

from collections import Counter

from jp_llm_lab.data.corpus_stats import class_counts, japanese_ratio
from jp_llm_lab.utils.io import repo_root, save_json

from jp_llm_lab.data.snapshots import iter_snapshot_docs, snapshot_summary


def analyze(name: str, max_docs: int = 6000) -> dict:
    doc_lens = []
    total_class: Counter[str] = Counter()
    jp_ratios = []
    char_freq: Counter[str] = Counter()
    n = 0
    for doc in iter_snapshot_docs(name):
        doc_lens.append(len(doc))
        cc = class_counts(doc)
        total_class += cc
        jp_ratios.append(japanese_ratio(doc, cc))
        if n < 2000:
            char_freq.update(doc)
        n += 1
        if n >= max_docs:
            break
    doc_lens.sort()
    total_chars = sum(total_class.values())
    return {
        "n_docs_sampled": n,
        "total_chars": total_chars,
        "doc_len": {
            "min": doc_lens[0],
            "p25": doc_lens[len(doc_lens) // 4],
            "median": doc_lens[len(doc_lens) // 2],
            "p75": doc_lens[3 * len(doc_lens) // 4],
            "max": doc_lens[-1],
            "mean": round(sum(doc_lens) / len(doc_lens), 1),
        },
        "doc_len_hist": doc_lens[:: max(1, len(doc_lens) // 200)],  # thinned for plotting
        "class_fraction": {k: round(v / total_chars, 4) for k, v in total_class.most_common()},
        "japanese_ratio_mean": round(sum(jp_ratios) / len(jp_ratios), 4),
        "top_chars": [
            {"char": c, "count": n} for c, n in char_freq.most_common(40) if not c.isspace()
        ][:30],
    }


def main() -> None:
    root = repo_root()
    manifest = snapshot_summary()
    names = ["pilot", "validation", "calibration", "test", "wiki_pilot"]
    out = {"snapshots": {}, "manifest_counts": {}}
    for name in names:
        if name in manifest["snapshots"]:
            print(f"analyzing {name}…", flush=True)
            out["snapshots"][name] = analyze(name)
    # token-level info from the tokenized manifest
    out["tokenized"] = manifest.get("tokenized", {})
    save_json(out, root / "reports" / "figures" / "corpus_stats.json")
    print("saved reports/figures/corpus_stats.json")


if __name__ == "__main__":
    main()
