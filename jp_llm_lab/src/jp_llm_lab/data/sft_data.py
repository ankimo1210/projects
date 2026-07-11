"""SFT instruction dataset (spec §21): databricks-dolly-15k-ja (public).

Downloads a fixed subset once, filters to short single-turn instruction→
response pairs (so they fit context 256 for the small models), and caches to
data/sft/dolly_ja_v1.json with a manifest entry. A clearly-labeled synthetic
fallback is used if the download fails, so measured vs illustrative is never
ambiguous.
"""

from __future__ import annotations

from pathlib import Path

from ..utils.io import load_json, repo_root, save_json

SFT_REL = Path("data/sft/dolly_ja_v1.json")

_SYNTHETIC = [
    ("日本の首都はどこですか？", "日本の首都は東京です。"),
    ("水は何度で沸騰しますか？", "水は標準的な気圧のもとで摂氏100度で沸騰します。"),
    ("「ありがとう」を英語で言うと？", "「ありがとう」は英語で Thank you と言います。"),
    ("三角形の内角の和は？", "三角形の内角の和は180度です。"),
    ("犬について一文で説明してください。", "犬は人間に飼われることの多い、忠実で社会的な動物です。"),
]


def build_sft_dataset(n: int = 1200, max_chars: int = 180, force: bool = False) -> dict:
    root = repo_root()
    out = root / SFT_REL
    if out.exists() and not force:
        return load_json(out)
    examples = []
    synthetic = False
    try:
        from datasets import load_dataset

        ds = load_dataset("kunishou/databricks-dolly-15k-ja", split="train", streaming=True)
        for ex in ds:
            instr = (ex.get("instruction") or "").strip()
            inp = (ex.get("input") or "").strip()
            resp = (ex.get("output") or "").strip()
            # keep closed-book style (no long context) short pairs
            if inp or not instr or not resp:
                continue
            if len(instr) > max_chars or len(resp) > max_chars:
                continue
            examples.append([instr, resp])
            if len(examples) >= n:
                break
    except Exception as e:
        print(f"[sft] download failed: {e!r} → synthetic fallback")
        synthetic = True
        examples = [list(p) for p in _SYNTHETIC] * 40

    payload = {
        "source": "kunishou/databricks-dolly-15k-ja (closed-book, len<=%d)" % max_chars if not synthetic else "synthetic (in-repo)",
        "license": "CC-BY-SA-3.0 (dolly-15k-ja)" if not synthetic else "synthetic",
        "synthetic": synthetic,
        "n_examples": len(examples),
        "examples": examples,
    }
    save_json(payload, out)
    return payload


def load_sft_examples() -> list[tuple[str, str]]:
    payload = load_json(repo_root() / SFT_REL)
    return [(i, r) for i, r in payload["examples"]]
