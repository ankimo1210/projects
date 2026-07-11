"""1-batch overfit (spec §27, Milestone-1 acceptance).

A healthy model+optimizer must drive the loss on ONE fixed batch to ~0 —
if it cannot memorize 4×64 tokens, something is wrong in the forward pass,
loss wiring, or optimizer. Also sanity-checks the initialization loss ≈ ln V.
"""

import math

import torch
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.utils.seed import set_seed

TEXT = "吾輩は猫である。名前はまだ無い。どこで生れたかとんと見当がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは記憶している。" * 20


def test_one_batch_overfit():
    set_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer

    tok = CharTokenizer.train([TEXT])
    ids = torch.tensor(tok.encode(TEXT), dtype=torch.long)
    B, T = 4, 64
    x = ids[: B * T].view(B, T).to(device)
    y = ids[1 : B * T + 1].view(B, T).to(device)

    model = ClassicalGPT(
        ModelConfig(vocab_size=tok.vocab_size, d_model=64, n_heads=2, n_layers=2, context_len=T)
    ).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3)

    _, init_loss = model(x, y)
    init_loss = float(init_loss)
    # at init the model is ~uniform → loss ≈ ln(V)
    assert abs(init_loss - math.log(tok.vocab_size)) < 1.0, init_loss

    final = init_loss
    for _step in range(500):
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        final = float(loss)
        if final < 0.02 * init_loss * 0.8:  # stop only once safely past the criterion
            break

    assert final < 0.15, f"failed to overfit one batch: final loss {final:.3f} (init {init_loss:.3f})"
    assert final < 0.02 * init_loss
