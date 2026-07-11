"""Shared tokenizer vocabulary conventions.

All tokenizers in this lab reserve the same 6 special tokens at ids 0-5 so
that models, SFT formatting, and analyses can rely on fixed ids regardless of
the tokenizer kind (char / BPE).
"""

from __future__ import annotations

SPECIAL_TOKENS = ["<PAD>", "<UNK>", "<BOS>", "<EOS>", "<USER>", "<ASSISTANT>"]

PAD_ID = 0
UNK_ID = 1
BOS_ID = 2
EOS_ID = 3
USER_ID = 4
ASSISTANT_ID = 5
