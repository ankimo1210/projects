"""Train/compare the count-based and neural bigram models on the sample corpus.

Usage:
  uv run --no-sync python jp_llm_lab/scripts/train_bigram.py --config jp_llm_lab/configs/smoke/bigram_char.yaml
"""

from __future__ import annotations

import argparse
import time

import torch
from jp_llm_lab.data.batches import sample_batch, split_tokens
from jp_llm_lab.data.sample_corpus import load_sample_corpus
from jp_llm_lab.models.bigram import CountBigramLM, NeuralBigramLM
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.training.train_config import load_yaml_config
from jp_llm_lab.utils.io import append_jsonl, repo_root, save_json
from jp_llm_lab.utils.runmeta import collect_run_metadata
from jp_llm_lab.utils.seed import make_generator, set_seed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    raw = load_yaml_config(args.config)
    t_cfg = raw["train"]

    set_seed(t_cfg["seed"])
    device = "cuda" if torch.cuda.is_available() else "cpu"
    corpus = load_sample_corpus(raw["data"]["corpus"])
    tokenizer = CharTokenizer.train([corpus])
    ids = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    train_tokens, val_tokens = split_tokens(ids, raw["data"]["val_frac"])
    val_slice = val_tokens[:8193]  # bound the [1,T,V] full-batch eval memory
    V = tokenizer.vocab_size

    run_dir = repo_root() / "experiments" / "runs" / f"{raw['run_name']}_seed{t_cfg['seed']}"
    run_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = run_dir / "metrics.jsonl"
    save_json(collect_run_metadata({"run_name": raw["run_name"]}), run_dir / "runmeta.json")
    save_json(raw, run_dir / "config.json")
    tokenizer.save(run_dir / "tokenizer.json")

    # --- count model: closed-form MLE + smoothing.
    # NOTE: with add-α smoothing, α·V pseudo-counts are added per row; for a
    # ~2000-char vocabulary even α=0.5 drowns rare rows in uniform mass, so we
    # default to a small α and additionally record a small α-sweep.
    alpha = t_cfg.get("alpha", 0.05)
    count_model = CountBigramLM(V, alpha=alpha).fit(train_tokens)
    # IMPORTANT: count and neural models are compared on the SAME val slice.
    count_train, count_val = count_model.loss(train_tokens), count_model.loss(val_slice)
    print(f"count bigram (α={alpha}): train={count_train:.4f} val={count_val:.4f} (nats/token)")
    alpha_sweep = {
        a: CountBigramLM(V, alpha=a).fit(train_tokens).loss(val_slice)
        for a in (0.001, 0.01, 0.05, 0.1, 0.5, 1.0)
    }

    # --- neural model: SGD re-derives the same table
    model = NeuralBigramLM(V).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=t_cfg["lr"])
    gen = make_generator(t_cfg["seed"] + 1)
    t0 = time.perf_counter()
    for step in range(1, t_cfg["steps"] + 1):
        x, y = sample_batch(train_tokens, t_cfg["batch_size"], t_cfg["context_len"], gen, device)
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step % t_cfg["log_interval"] == 0 or step == 1:
            with torch.no_grad():
                _, vloss = model(
                    val_slice[:-1].unsqueeze(0).to(device), val_slice[1:].unsqueeze(0).to(device)
                )
            append_jsonl(
                {
                    "type": "train",
                    "step": step,
                    "loss": float(loss.detach()),
                    "val_loss": float(vloss),
                    "elapsed_sec": round(time.perf_counter() - t0, 3),
                },
                metrics_path,
            )

    with torch.no_grad():
        _, neural_val = model(
            val_slice[:-1].unsqueeze(0).to(device), val_slice[1:].unsqueeze(0).to(device)
        )
    neural_val = float(neural_val)
    print(f"neural bigram: val={neural_val:.4f} (count val={count_val:.4f})")

    # --- samples from both models (temperature 1.0)
    gen_s = make_generator(t_cfg["seed"] + 2)
    start = tokenizer.encode("私")[0]
    count_sample = tokenizer.decode(count_model.generate(start, 100, gen_s))
    save_json(
        {
            "count": {"train_loss": count_train, "val_loss": count_val, "alpha": alpha},
            "alpha_sweep_val_loss": alpha_sweep,
            "neural": {"val_loss": neural_val, "steps": t_cfg["steps"]},
            "gap_val": neural_val - count_val,
            "n_val_slice_tokens": len(val_slice),
            "vocab_size": V,
            "sample_count_model": count_sample,
            "uniform_loss_reference": float(torch.log(torch.tensor(float(V)))),
        },
        run_dir / "summary.json",
    )
    print(f"run dir: {run_dir}")


if __name__ == "__main__":
    main()
