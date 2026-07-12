"""Train the tokenizers and build tokenized snapshot caches.

1. Educational BPE (readable Python, full merge history) on a ~300K-char
   sample (Kokoro + Wikipedia mix) at vocab 8192 — 2K/4K comparisons are
   PREFIXES of the same merge sequence (that is a property of BPE, shown in NB03).
2. Production HF-BPE vocab 8192 on the pilot snapshot (17M chars).
3. Tokenize snapshots (smoke/pilot/main/validation/calibration/test/wiki_pilot)
   into uint16 caches with <EOS> document separators.

Usage: uv run --no-sync python jp_llm_lab/scripts/train_tokenizers.py [--skip-main]
"""

from __future__ import annotations

import argparse
import time

from jp_llm_lab.data.sample_corpus import load_sample_corpus
from jp_llm_lab.data.tokenized_cache import tokenize_snapshot
from jp_llm_lab.tokenization.bpe_tokenizer import BPETokenizer
from jp_llm_lab.tokenization.hf_bpe import HFBpeTokenizer
from jp_llm_lab.utils.io import repo_root

from jp_llm_lab.data.snapshots import iter_snapshot_docs, load_snapshot_text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-main", action="store_true", help="skip tokenizing the 170M-char main pool")
    ap.add_argument("--edu-chars", type=int, default=300_000)
    args = ap.parse_args()
    root = repo_root()
    tok_dir = root / "tokenizer"

    # ---- 1. educational BPE with history
    kokoro = load_sample_corpus("kokoro")
    wiki = load_snapshot_text("wiki_pilot", max_chars=args.edu_chars // 2)
    edu_text = kokoro[: args.edu_chars // 2] + "\n" + wiki
    t0 = time.perf_counter()
    edu = BPETokenizer.train(edu_text, vocab_size=8192)
    print(f"edu BPE: vocab {edu.vocab_size} ({len(edu.merges)} merges) on {len(edu_text):,} chars "
          f"in {time.perf_counter()-t0:.1f}s")
    edu.save(tok_dir / "bpe_edu_v1.json")

    # ---- 2. production HF BPE on pilot
    t0 = time.perf_counter()
    prod = HFBpeTokenizer.train(iter_snapshot_docs("pilot"), vocab_size=8192, version="bpe8k_v1")
    print(f"prod BPE: vocab {prod.vocab_size} on pilot in {time.perf_counter()-t0:.1f}s")
    prod.save(tok_dir / "bpe8k_v1.tokenizer.json")

    demo = "私はその人を常に先生と呼んでいた。東京大学で自然言語処理を研究しています。"
    print("demo edu :", edu.encode_to_tokens(demo))
    print("demo prod:", prod.encode_to_tokens(demo))

    # ---- 3. tokenized caches
    snapshots = ["smoke", "pilot", "validation", "calibration", "test", "wiki_pilot"]
    if not args.skip_main:
        snapshots.append("main")
    for name in snapshots:
        t0 = time.perf_counter()
        path = tokenize_snapshot(name, prod)
        import numpy as np

        n = np.load(path, mmap_mode="r").size
        print(f"tokenized {name:12s} → {n/1e6:7.2f}M tokens  ({time.perf_counter()-t0:.1f}s)  {path.name}")


if __name__ == "__main__":
    main()
