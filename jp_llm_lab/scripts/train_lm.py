"""Train a ClassicalGPT from a YAML experiment config.

Usage:
  uv run --no-sync python jp_llm_lab/scripts/train_lm.py --config jp_llm_lab/configs/smoke/model_s_char.yaml
"""

from __future__ import annotations

import argparse

import torch
from jp_llm_lab.data.batches import split_tokens
from jp_llm_lab.data.sample_corpus import load_sample_corpus
from jp_llm_lab.models.config import ModelConfig
from jp_llm_lab.models.transformer import ClassicalGPT
from jp_llm_lab.tokenization.char_tokenizer import CharTokenizer
from jp_llm_lab.training.train_config import TrainConfig, load_yaml_config
from jp_llm_lab.training.trainer import train_lm
from jp_llm_lab.utils.env import collect_env_report
from jp_llm_lab.utils.io import repo_root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    raw = load_yaml_config(args.config)

    env = collect_env_report()
    device = "cuda" if env.cuda_available else "cpu"
    print(f"device={device} gpu={env.gpu_name} bf16={env.bf16_supported}")

    corpus = load_sample_corpus(raw["data"]["corpus"])
    tokenizer = CharTokenizer.train([corpus])
    print(f"corpus={raw['data']['corpus']} chars={len(corpus):,} vocab={tokenizer.vocab_size}")

    ids = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    train_tokens, val_tokens = split_tokens(ids, raw["data"]["val_frac"])

    model_cfg = ModelConfig(vocab_size=tokenizer.vocab_size, **raw["model"])
    model = ClassicalGPT(model_cfg)
    bd = model.param_breakdown()
    print(f"params total={bd['total']:,}  groups={bd['groups']}")

    train_cfg = TrainConfig.from_dict(raw["train"])
    run_name = f"{raw['run_name']}_seed{train_cfg.seed}"
    run_dir = repo_root() / "experiments" / "runs" / run_name

    tokenizer.save(run_dir / "tokenizer.json")
    tokenizer.save(repo_root() / "tokenizer" / f"char_v1_{raw['data']['corpus']}.json")

    result = train_lm(
        model,
        train_tokens,
        val_tokens,
        train_cfg,
        run_dir,
        tokenizer=tokenizer,
        device=device,
        extra_meta={"run_name": run_name, "corpus": raw["data"]["corpus"], "tokenizer": tokenizer.version},
    )
    print(
        f"done: steps={result.steps} tokens={result.tokens_seen:,} "
        f"wallclock={result.wallclock_sec:.1f}s final_val_loss={result.final_eval['loss']:.4f} "
        f"ppl={result.final_eval['ppl']:.2f}"
    )
    print(f"run dir: {result.run_dir}")


if __name__ == "__main__":
    main()
