"""Character-level tokenizer — the smallest possible educational tokenizer.

Every distinct character becomes one token. That makes the token↔text mapping
trivially inspectable (one char = one id), at the cost of long sequences and a
vocabulary that grows with the character inventory (kanji!). The BPE tokenizer
(Milestone 2) is motivated by exactly these costs.

Invariant (tested): decode(encode(x)) == x for any x whose characters are all
in the vocabulary. Out-of-vocabulary characters map to <UNK> and are the one
documented way the round trip can fail.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from .base import BOS_ID, EOS_ID, SPECIAL_TOKENS, UNK_ID


class CharTokenizer:
    version = "char_v1"

    def __init__(self, itos: list[str]):
        assert itos[: len(SPECIAL_TOKENS)] == SPECIAL_TOKENS, "specials must occupy ids 0..5"
        self.itos = list(itos)
        self.stoi = {s: i for i, s in enumerate(self.itos)}
        self._special_ids = set(range(len(SPECIAL_TOKENS)))

    # ---------------------------------------------------------------- build
    @classmethod
    def train(cls, texts: Iterable[str], min_freq: int = 1) -> CharTokenizer:
        """Vocabulary = specials + all characters with count >= min_freq.

        Characters are sorted by codepoint, so training on the same corpus
        always yields the same vocabulary (determinism is tested).
        """
        counts: Counter[str] = Counter()
        for text in texts:
            counts.update(text)
        chars = sorted(c for c, n in counts.items() if n >= min_freq)
        return cls(SPECIAL_TOKENS + chars)

    # ------------------------------------------------------------ encode/decode
    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids = [self.stoi.get(ch, UNK_ID) for ch in text]
        if add_bos:
            ids.insert(0, BOS_ID)
        if add_eos:
            ids.append(EOS_ID)
        return ids

    def decode(self, ids: Iterable[int], skip_special: bool = False) -> str:
        parts = []
        for i in ids:
            if skip_special and i in self._special_ids:
                continue
            parts.append(self.itos[i])
        return "".join(parts)

    # ---------------------------------------------------------------- info
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
        payload = {"kind": "char", "version": self.version, "itos": self.itos}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path | str) -> CharTokenizer:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        assert payload["kind"] == "char"
        return cls(payload["itos"])
