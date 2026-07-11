import torch
from jp_llm_lab.evaluation.eval_prompts import EVAL_CATEGORIES, build_eval_set
from jp_llm_lab.evaluation.eval_runner import run_eval
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer


def test_eval_set_size_and_shape():
    prompts = build_eval_set()
    assert len(prompts) >= 200
    ids = [p["id"] for p in prompts]
    assert len(ids) == len(set(ids))  # unique ids
    for p in prompts:
        assert p["category"] in EVAL_CATEGORIES
        assert p["kind"] in ("completion", "cloze", "probe")
        assert p["prompt"]


def test_run_eval_smoke():
    torch.manual_seed(0)
    tok = CharTokenizer.train(["日本の首都は東京です。私は学校に行く。1, 2, 3, 4, 5。"])
    model = ClassicalGPT(ModelConfig(vocab_size=tok.vocab_size, d_model=32, n_heads=2, n_layers=1, context_len=64))
    res = run_eval(model, tok, "cpu", max_new_tokens=8)
    assert res["overall"]["n_prompts"] >= 200
    assert "by_category" in res
    assert all("n" in v for v in res["by_category"].values())
    # cloze accuracy is a fraction or None
    for v in res["by_category"].values():
        assert v["cloze_accuracy"] is None or 0.0 <= v["cloze_accuracy"] <= 1.0
