import itertools

import pytest
from jp_llm_lab.tokenization.base import BOS_ID, EOS_ID, SPECIAL_TOKENS, UNK_ID
from jp_llm_lab.tokenization.bpe_tokenizer import BPETokenizer, segment_text
from jp_llm_lab.tokenization.hf_bpe import HFBpeTokenizer

TEXT = (
    "私は学生です。私は学生ではありません。学生の生活は楽しい。\n"
    "東京の天気は晴れです。東京の天気は雨です。天気予報を見ます。\n"
) * 40


def test_segmentation_is_lossless():
    assert "".join(segment_text(TEXT)) == TEXT
    assert "".join(segment_text("改行なしテキスト")) == "改行なしテキスト"


@pytest.fixture(scope="module")
def edu() -> BPETokenizer:
    return BPETokenizer.train(TEXT, vocab_size=200, min_pair_freq=2)


def test_edu_round_trip(edu):
    assert edu.decode(edu.encode(TEXT)) == TEXT
    s = "私は東京の学生です。"
    assert edu.decode(edu.encode(s)) == s


def test_edu_specials_and_unknown(edu):
    for i, tok in enumerate(SPECIAL_TOKENS):
        assert edu.token_to_id(tok) == i
    ids = edu.encode("龍", add_bos=True, add_eos=True)
    assert ids[0] == BOS_ID and ids[-1] == EOS_ID and ids[1] == UNK_ID


def test_edu_merges_reduce_corpus_tokens(edu):
    counts = [h["corpus_tokens"] for h in edu.history]
    assert all(a >= b for a, b in itertools.pairwise(counts))  # monotone non-increasing
    assert counts[-1] < counts[0]  # merging actually compressed
    ratios = [h["compression_chars_per_token"] for h in edu.history]
    assert ratios[-1] > ratios[0] >= 1.0


def test_edu_demo_tokens_join_to_sentence(edu):
    for h in edu.history:
        assert "".join(h["demo_tokens"]) == "東京大学で自然言語処理を研究しています。"


def test_edu_save_load_roundtrip(edu, tmp_path):
    p = edu.save(tmp_path / "bpe.json")
    edu2 = BPETokenizer.load(p)
    s = "学生の天気予報。"
    assert edu2.encode(s) == edu.encode(s)
    assert edu2.merges == edu.merges


def test_edu_prefix_property():
    """BPE with smaller vocab == prefix of the larger vocab's merge list."""
    small = BPETokenizer.train(TEXT, vocab_size=150)
    large = BPETokenizer.train(TEXT, vocab_size=200)
    assert large.merges[: len(small.merges)] == small.merges


@pytest.fixture(scope="module")
def prod() -> HFBpeTokenizer:
    return HFBpeTokenizer.train([TEXT], vocab_size=200, version="bpe_test")


def test_prod_round_trip(prod):
    s = "私は東京の学生です。\n天気は晴れ。"
    assert prod.decode(prod.encode(s)) == s


def test_prod_specials(prod):
    for i, tok in enumerate(SPECIAL_TOKENS):
        assert prod.token_to_id(tok) == i
    ids = prod.encode("学生", add_bos=True, add_eos=True)
    assert ids[0] == BOS_ID and ids[-1] == EOS_ID
    assert prod.decode(ids, skip_special=True) == "学生"


def test_prod_save_load(prod, tmp_path):
    p = prod.save(tmp_path / "t.tokenizer.json")
    prod2 = HFBpeTokenizer.load(p, version="bpe_test")
    s = "学生の生活。"
    assert prod2.encode(s) == prod.encode(s)
