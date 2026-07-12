import torch
from jp_llm_lab.models.bigram import CountBigramLM, NeuralBigramLM
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.utils.seed import set_seed

TEXT = "すもももももももものうち。となりの客はよく柿食う客だ。" * 30


def _ids():
    tok = CharTokenizer.train([TEXT])
    return torch.tensor(tok.encode(TEXT), dtype=torch.long), tok.vocab_size


def test_count_rows_sum_to_one():
    ids, V = _ids()
    m = CountBigramLM(V, alpha=0.5).fit(ids)
    rows = m.log_probs.exp().sum(dim=1)
    assert torch.allclose(rows, torch.ones(V), atol=1e-5)


def test_neural_bigram_converges_to_count_model():
    """SGD on the V×V logit table re-derives the count solution (same loss)."""
    set_seed(0)
    ids, V = _ids()
    count = CountBigramLM(V, alpha=0.5).fit(ids)
    count_loss = count.loss(ids)

    model = NeuralBigramLM(V)
    opt = torch.optim.AdamW(model.parameters(), lr=0.1)
    x, y = ids[:-1].unsqueeze(0), ids[1:].unsqueeze(0)  # full-batch GD
    for _ in range(300):
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    with torch.no_grad():
        _, final = model(x, y)
    # unsmoothed SGD solution may dip slightly BELOW the smoothed count loss
    assert float(final) <= count_loss + 0.1


def test_generation_returns_valid_ids():
    ids, V = _ids()
    m = CountBigramLM(V).fit(ids)
    g = torch.Generator().manual_seed(0)
    out = m.generate(int(ids[0]), 50, g)
    assert len(out) == 51
    assert all(0 <= t < V for t in out)
