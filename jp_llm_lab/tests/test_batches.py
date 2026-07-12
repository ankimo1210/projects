import torch
from jp_llm_lab.data.batches import sample_batch, split_tokens
from jp_llm_lab.utils.seed import make_generator


def test_shift_property():
    tokens = torch.arange(200)
    x, y = sample_batch(tokens, batch_size=8, context_len=16, generator=make_generator(0))
    assert x.shape == (8, 16) and y.shape == (8, 16)
    assert torch.equal(y, x + 1)  # arange corpus → next token is +1 everywhere


def test_seed_reproducible():
    tokens = torch.arange(500)
    x1, _ = sample_batch(tokens, 4, 8, generator=make_generator(7))
    x2, _ = sample_batch(tokens, 4, 8, generator=make_generator(7))
    x3, _ = sample_batch(tokens, 4, 8, generator=make_generator(8))
    assert torch.equal(x1, x2)
    assert not torch.equal(x1, x3)


def test_split_contiguous():
    tokens = torch.arange(100)
    train, val = split_tokens(tokens, 0.1)
    assert len(val) == 10 and len(train) == 90
    assert torch.equal(torch.cat([train, val]), tokens)
