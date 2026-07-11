import torch
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.training.train_config import TrainConfig
from jp_llm_lab.training.trainer import load_checkpoint, make_optimizer, save_checkpoint


def _cfg():
    return ModelConfig(vocab_size=40, d_model=32, n_heads=2, n_layers=2, context_len=8)


def _batch():
    g = torch.Generator().manual_seed(0)
    x = torch.randint(0, 40, (4, 8), generator=g)
    y = torch.randint(0, 40, (4, 8), generator=g)
    return x, y


def _step(model, opt, x, y):
    opt.zero_grad(set_to_none=True)
    _, loss = model(x, y)
    loss.backward()
    opt.step()


def test_save_restore_identical_logits(tmp_path):
    torch.manual_seed(0)
    model = ClassicalGPT(_cfg())
    x, y = _batch()
    opt = make_optimizer(model, TrainConfig())
    for _ in range(3):
        _step(model, opt, x, y)
    path = save_checkpoint(tmp_path / "ck.pt", model, opt, step=3, tokens_seen=96)

    torch.manual_seed(123)  # fresh model, different init
    model2 = ClassicalGPT(_cfg())
    payload = load_checkpoint(path, model2)
    assert payload["step"] == 3
    with torch.no_grad():
        l1, _ = model.eval()(x)
        l2, _ = model2.eval()(x)
    assert torch.equal(l1, l2)


def test_optimizer_resume_matches_uninterrupted_run(tmp_path):
    """3 steps → checkpoint → 2 steps must equal 5 uninterrupted steps."""
    torch.manual_seed(0)
    model = ClassicalGPT(_cfg())
    x, y = _batch()
    opt = make_optimizer(model, TrainConfig())

    for _ in range(3):
        _step(model, opt, x, y)
    path = save_checkpoint(tmp_path / "ck.pt", model, opt, step=3, tokens_seen=96)
    for _ in range(2):
        _step(model, opt, x, y)  # uninterrupted continuation

    torch.manual_seed(999)
    model2 = ClassicalGPT(_cfg())
    opt2 = make_optimizer(model2, TrainConfig())
    load_checkpoint(path, model2, opt2)
    for _ in range(2):
        _step(model2, opt2, x, y)  # resumed continuation

    for (n1, p1), (n2, p2) in zip(
        model.named_parameters(), model2.named_parameters(), strict=True
    ):
        assert n1 == n2
        assert torch.equal(p1, p2), f"{n1} diverged after resume"
