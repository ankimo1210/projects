import pytest
from jp_llm_lab.tokenization.base import BOS_ID, EOS_ID, SPECIAL_TOKENS, UNK_ID
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer

TEXT = "私はその人を常に先生と呼んでいた。\n吾輩は猫である。Hello, world! 123\nカタカナもある。"


@pytest.fixture()
def tok() -> CharTokenizer:
    return CharTokenizer.train([TEXT])


def test_round_trip(tok):
    assert tok.decode(tok.encode(TEXT)) == TEXT


def test_unknown_char_maps_to_unk(tok):
    ids = tok.encode("龍")  # not in TEXT
    assert ids == [UNK_ID]
    assert tok.decode(ids) == "<UNK>"


def test_specials_have_fixed_ids(tok):
    for i, s in enumerate(SPECIAL_TOKENS):
        assert tok.token_to_id(s) == i
    ids = tok.encode("私は", add_bos=True, add_eos=True)
    assert ids[0] == BOS_ID and ids[-1] == EOS_ID
    assert tok.decode(ids, skip_special=True) == "私は"


def test_save_load_roundtrip(tok, tmp_path):
    p = tok.save(tmp_path / "tok.json")
    tok2 = CharTokenizer.load(p)
    assert tok2.itos == tok.itos
    assert tok2.decode(tok2.encode(TEXT)) == TEXT


def test_training_deterministic():
    a = CharTokenizer.train([TEXT])
    b = CharTokenizer.train([TEXT[::-1]])  # same char set, different order
    assert a.itos == b.itos
