"""End-to-end CPU smoke test of the instrumented training loop (spec §27)."""

import random

import torch
from jp_llm_lab.data.batches import split_tokens
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.training.train_config import TrainConfig
from jp_llm_lab.training.trainer import train_lm
from jp_llm_lab.utils.io import read_jsonl


def test_cpu_smoke_train(tmp_path):
    rng = random.Random(0)
    text = "".join(rng.choice("あいうえおかきくけこ。\n") for _ in range(3000))
    tok = CharTokenizer.train([text])
    ids = torch.tensor(tok.encode(text), dtype=torch.long)
    train_tokens, val_tokens = split_tokens(ids, 0.2)

    model = ClassicalGPT(
        ModelConfig(vocab_size=tok.vocab_size, d_model=32, n_heads=2, n_layers=2, context_len=32)
    )
    cfg = TrainConfig(
        seed=0,
        steps=5,
        batch_size=4,
        context_len=32,
        lr=1e-3,
        dtype="fp32",
        log_interval=1,
        eval_interval=2,
        eval_batches=2,
        ratio_interval=2,
        checkpoint_fracs=(0.0, 1.0),
        fixed_prompts=["あい"],
        max_new_tokens=8,
    )
    run_dir = tmp_path / "run"
    result = train_lm(model, train_tokens, val_tokens, cfg, run_dir, tokenizer=tok, device="cpu")

    assert result.tokens_seen == 5 * 4 * 32
    records = read_jsonl(run_dir / "metrics.jsonl")
    types = {r["type"] for r in records}
    assert types == {"train", "eval", "checkpoint"}
    evals = [r for r in records if r["type"] == "eval"]
    assert evals[0]["step"] == 0  # initialization snapshot exists
    assert all(not r["nonfinite"] for r in evals)
    assert all("rms" in next(iter(r["activation_stats"].values())) for r in evals)
    trains = [r for r in records if r["type"] == "train"]
    assert any("update_ratios" in r for r in trains)

    ckpts = sorted((run_dir / "checkpoints").glob("*.pt"))
    assert len(ckpts) == 2  # 0% and 100%
    samples = read_jsonl(run_dir / "samples.jsonl")
    assert len(samples) == 2  # 1 prompt × 2 checkpoints
    assert (run_dir / "config.json").exists()
    assert (run_dir / "runmeta.json").exists()
    assert (run_dir / "summary.json").exists()
