import torch
from jp_llm_lab.tokenization.base import ASSISTANT_ID, BOS_ID, EOS_ID, USER_ID
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.training.sft import IGNORE, build_batch, format_example


def _tok():
    return CharTokenizer.train(["日本の首都は東京です。質問と回答のテキスト。"])


def test_format_has_special_tokens():
    tok = _tok()
    ids, n_prompt = format_example(tok, "首都は", "東京です")
    assert ids[0] == BOS_ID and ids[1] == USER_ID
    assert ids[n_prompt - 1] == ASSISTANT_ID
    assert ids[-1] == EOS_ID


def test_assistant_only_masks_prompt_targets():
    tok = _tok()
    examples = [("首都は", "東京です")]
    _, n_prompt = format_example(tok, "首都は", "東京です")
    x_ao, y_ao = build_batch(examples, tok, context_len=32, assistant_only=True, device="cpu")
    x_full, y_full = build_batch(examples, tok, context_len=32, assistant_only=False, device="cpu")

    # assistant-only: prompt-predicting targets are masked (IGNORE)
    assert (y_ao[0, : n_prompt - 1] == IGNORE).all()
    # response region has real targets in BOTH regimes
    assert (y_ao[0, n_prompt - 1] != IGNORE)
    # full-sequence: fewer masked targets than assistant-only (only padding masked)
    assert (y_full[0] == IGNORE).sum() < (y_ao[0] == IGNORE).sum()
    # inputs identical regardless of regime
    assert torch.equal(x_ao, x_full)


def test_padding_is_masked():
    tok = _tok()
    x, y = build_batch([("あ", "い")], tok, context_len=32, assistant_only=False, device="cpu")
    # trailing padding target positions are IGNORE
    assert (y[0, -5:] == IGNORE).all()


def test_loss_ignores_masked_positions():
    """A model's loss must not depend on masked (IGNORE) target values."""
    from jp_llm_lab.models.config import ModelConfig
    from jp_llm_lab.models.transformer import ClassicalGPT

    torch.manual_seed(0)
    tok = _tok()
    model = ClassicalGPT(ModelConfig(vocab_size=tok.vocab_size, d_model=32, n_heads=2, n_layers=1, context_len=32))
    x, y = build_batch([("首都は", "東京です")], tok, context_len=32, assistant_only=True, device="cpu")
    _, loss1 = model(x, y)
    y2 = y.clone()
    y2[y2 == IGNORE] = 0  # change masked entries to a real id
    # loss uses ignore_index=-100, so changing -100 entries changes nothing;
    # but changing them to 0 makes them count → loss differs. Verify masking is active:
    _, loss2 = model(x, y2)
    assert not torch.allclose(loss1, loss2)  # masked positions were indeed excluded
