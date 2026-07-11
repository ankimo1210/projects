"""Educational char-level BPE with a fully recorded merge history (spec §5.2).

The algorithm, readable version:

    1. 語彙 = 特殊トークン + 学習テキストの全文字
    2. コーパスを「セグメント」（。・改行で区切った短い断片）の文字列リストにする
    3. 最頻の隣接ペア (a, b) を見つける
    4. 新トークン ab を語彙に追加し、コーパス中の a,b を ab に置換
    5. 目標語彙サイズまで 3-4 を繰り返す

Merges never cross segment boundaries (the analogue of "words" in space-
delimited languages). Every merge is recorded, and periodically the state of
a demo sentence's tokenization is snapshotted so the "日本語の単語が徐々に
1トークンになる" process can be replayed and visualized.

This implementation optimizes just enough to train vocab 8K on a few hundred
KB of text in ~a minute (incremental pair-count updates via a pair→segments
index) while staying readable. The PRODUCTION tokenizer for large corpora is
trained with the HuggingFace `tokenizers` Rust library (see hf_bpe.py) and
compared against this one in notebook 03.
"""

from __future__ import annotations

import itertools
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

from .base import BOS_ID, EOS_ID, SPECIAL_TOKENS, UNK_ID

_SEGMENT_RE = re.compile(r"[^\n。]*[\n。]?")


def segment_text(text: str) -> list[str]:
    """Partition text into short segments (clause-ish), losslessly:
    ''.join(segment_text(x)) == x. Merges never cross these boundaries."""
    return [seg for seg in _SEGMENT_RE.findall(text) if seg]


class BPETokenizer:
    version = "bpe_edu_v1"

    def __init__(self, itos: list[str], merges: list[tuple[str, str]], history: list[dict] | None = None):
        assert itos[: len(SPECIAL_TOKENS)] == SPECIAL_TOKENS
        self.itos = list(itos)
        self.stoi = {s: i for i, s in enumerate(self.itos)}
        self.merges = [tuple(m) for m in merges]
        self.merge_ranks = {pair: r for r, pair in enumerate(self.merges)}
        self.history = history or []
        self._special_ids = set(range(len(SPECIAL_TOKENS)))

    # ------------------------------------------------------------------ train
    @classmethod
    def train(
        cls,
        text: str,
        vocab_size: int,
        min_pair_freq: int = 2,
        record_every: int = 64,
        demo_sentence: str = "東京大学で自然言語処理を研究しています。",
    ) -> BPETokenizer:
        segments = [list(seg) for seg in segment_text(text)]
        base_chars = sorted({c for seg in segments for c in seg})
        itos = SPECIAL_TOKENS + base_chars
        stoi = {s: i for i, s in enumerate(itos)}

        # pair counts + index of which segments contain each pair
        pair_counts: Counter[tuple[str, str]] = Counter()
        pair_where: dict[tuple[str, str], set[int]] = defaultdict(set)
        for i, seg in enumerate(segments):
            for p in itertools.pairwise(seg):
                pair_counts[p] += 1
                pair_where[p].add(i)

        n_chars = sum(len(s) for s in segments)
        corpus_tokens = n_chars
        merges: list[tuple[str, str]] = []
        history: list[dict] = []

        def record(rank: int, pair, count: int) -> None:
            history.append(
                {
                    "rank": rank,
                    "pair": list(pair),
                    "new_token": pair[0] + pair[1],
                    "pair_count": count,
                    "vocab_size": len(itos),
                    "corpus_tokens": corpus_tokens,
                    "compression_chars_per_token": round(n_chars / corpus_tokens, 4),
                    "demo_tokens": _apply_merges(list(demo_sentence), merges),
                }
            )

        record(-1, ("", ""), 0)  # initial state (pure characters)
        target_merges = vocab_size - len(itos)
        for rank in range(max(0, target_merges)):
            if not pair_counts:
                break
            # deterministic: highest count, ties broken lexicographically
            best, count = max(pair_counts.items(), key=lambda kv: (kv[1], kv[0]))
            if count < min_pair_freq:
                break
            new_tok = best[0] + best[1]

            # merge in every segment containing the pair, updating counts locally
            for i in sorted(pair_where.get(best, ())):
                seg = segments[i]
                out: list[str] = []
                j = 0
                while j < len(seg):
                    if j < len(seg) - 1 and seg[j] == best[0] and seg[j + 1] == best[1]:
                        out.append(new_tok)
                        j += 2
                    else:
                        out.append(seg[j])
                        j += 1
                if len(out) == len(seg):
                    continue
                for p in itertools.pairwise(seg):
                    pair_counts[p] -= 1
                    if pair_counts[p] <= 0:
                        del pair_counts[p]
                    pair_where[p].discard(i)
                for p in itertools.pairwise(out):
                    pair_counts[p] += 1
                    pair_where[p].add(i)
                corpus_tokens -= len(seg) - len(out)
                segments[i] = out

            merges.append(best)
            if new_tok not in stoi:  # rare collision: two merge paths, same string
                stoi[new_tok] = len(itos)
                itos.append(new_tok)
            if rank < 20 or rank % record_every == 0:
                record(rank, best, count)

        record(len(merges), ("", ""), 0)  # final state
        return cls(itos, merges, history)

    # ----------------------------------------------------------- encode/decode
    def _encode_segment(self, seg: str) -> list[str]:
        tokens = list(seg)
        while len(tokens) >= 2:
            ranked = [
                (self.merge_ranks.get((a, b), float("inf")), k)
                for k, (a, b) in enumerate(itertools.pairwise(tokens))
            ]
            best_rank = min(ranked)[0]
            if best_rank == float("inf"):
                break
            pair = self.merges[int(best_rank)]
            tokens = _merge_once(tokens, pair)
        return tokens

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids: list[int] = []
        for seg in segment_text(text):
            for tok in self._encode_segment(seg):
                ids.append(self.stoi.get(tok, UNK_ID))
        if add_bos:
            ids.insert(0, BOS_ID)
        if add_eos:
            ids.append(EOS_ID)
        return ids

    def encode_to_tokens(self, text: str) -> list[str]:
        """Token strings (not ids) — for visualization."""
        out: list[str] = []
        for seg in segment_text(text):
            out.extend(self._encode_segment(seg))
        return out

    def decode(self, ids: Iterable[int], skip_special: bool = False) -> str:
        parts = []
        for i in ids:
            if skip_special and i in self._special_ids:
                continue
            parts.append(self.itos[i])
        return "".join(parts)

    @property
    def vocab_size(self) -> int:
        return len(self.itos)

    def token_to_id(self, token: str) -> int:
        return self.stoi.get(token, UNK_ID)

    def id_to_token(self, i: int) -> str:
        return self.itos[i]

    # ---------------------------------------------------------------- persist
    def save(self, path: Path | str) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "kind": "bpe_edu",
            "version": self.version,
            "itos": self.itos,
            "merges": [list(m) for m in self.merges],
            "history": self.history,
        }
        p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path | str) -> BPETokenizer:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert payload["kind"] == "bpe_edu"
        return cls(payload["itos"], [tuple(m) for m in payload["merges"]], payload.get("history"))


def _merge_once(tokens: list[str], pair: tuple[str, str]) -> list[str]:
    out: list[str] = []
    j = 0
    while j < len(tokens):
        if j < len(tokens) - 1 and tokens[j] == pair[0] and tokens[j + 1] == pair[1]:
            out.append(pair[0] + pair[1])
            j += 2
        else:
            out.append(tokens[j])
            j += 1
    return out


def _apply_merges(tokens: list[str], merges: list[tuple[str, str]]) -> list[str]:
    for pair in merges:
        if len(tokens) < 2:
            break
        tokens = _merge_once(tokens, pair)
    return tokens
