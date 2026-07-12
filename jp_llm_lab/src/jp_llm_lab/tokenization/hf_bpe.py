"""Production BPE tokenizer — HuggingFace `tokenizers` (Rust) with the SAME
conventions as the educational implementations:

- special tokens at ids 0..5 (<PAD> <UNK> <BOS> <EOS> <USER> <ASSISTANT>)
- char-level BPE (no byte-level mangling): token strings are literal character
  sequences, so decode == concatenation of token strings
- merges never cross 。、improve-newline boundaries (Split pre-tokenizer,
  the same boundary rule as the educational BPE's segments — different
  regex granularity is one of the behavior differences examined in NB03)

The educational BPETokenizer (bpe_tokenizer.py) explains the algorithm; this
class exists because Python BPE cannot encode 170M chars in reasonable time.
Behavioral differences between the two are measured, not assumed.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from tokenizers import Regex, Tokenizer, models, pre_tokenizers, trainers

from .base import BOS_ID, EOS_ID, SPECIAL_TOKENS, UNK_ID


class HFBpeTokenizer:
    def __init__(self, tk: Tokenizer, version: str):
        self._tk = tk
        self.version = version
        for i, s in enumerate(SPECIAL_TOKENS):
            got = tk.token_to_id(s)
            assert got == i, f"special {s} at id {got}, expected {i}"
        self._special_ids = set(range(len(SPECIAL_TOKENS)))

    @classmethod
    def train(cls, texts: Iterator[str] | Iterable[str], vocab_size: int = 8192, version: str | None = None) -> HFBpeTokenizer:
        tk = Tokenizer(models.BPE(unk_token="<UNK>"))
        tk.pre_tokenizer = pre_tokenizers.Split(Regex(r"[。、\n]"), behavior="merged_with_previous")
        trainer = trainers.BpeTrainer(
            vocab_size=vocab_size,
            special_tokens=SPECIAL_TOKENS,
            min_frequency=2,
            show_progress=False,
        )
        tk.train_from_iterator(texts, trainer)
        return cls(tk, version or f"bpe{vocab_size // 1024}k_v1")

    # ----------------------------------------------------------- encode/decode
    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids = self._tk.encode(text).ids
        if add_bos:
            ids.insert(0, BOS_ID)
        if add_eos:
            ids.append(EOS_ID)
        return ids

    def encode_batch(self, texts: list[str]) -> list[list[int]]:
        return [e.ids for e in self._tk.encode_batch(texts)]

    def encode_to_tokens(self, text: str) -> list[str]:
        return self._tk.encode(text).tokens

    def decode(self, ids: Iterable[int], skip_special: bool = False) -> str:
        # token strings are literal character sequences → decode = concatenation
        parts = []
        for i in ids:
            if skip_special and i in self._special_ids:
                continue
            parts.append(self._tk.id_to_token(int(i)) or "")
        return "".join(parts)

    # ---------------------------------------------------------------- info
    @property
    def vocab_size(self) -> int:
        return self._tk.get_vocab_size()

    def token_to_id(self, token: str) -> int:
        i = self._tk.token_to_id(token)
        return UNK_ID if i is None else i

    def id_to_token(self, i: int) -> str:
        return self._tk.id_to_token(int(i)) or "<UNK>"

    # ---------------------------------------------------------------- persist
    def save(self, path: Path | str) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._tk.save(str(p))
        return p

    @classmethod
    def load(cls, path: Path | str, version: str | None = None) -> HFBpeTokenizer:
        p = Path(path)
        tk = Tokenizer.from_file(str(p))
        return cls(tk, version or p.stem.replace(".tokenizer", ""))
