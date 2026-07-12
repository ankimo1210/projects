"""Compute analysis artifacts from a saved run's checkpoints → analysis/ dir.

Runs once after training; notebooks and the report read the saved JSON/NPZ so
no re-analysis (or retraining) is needed. Works for both char and BPE runs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch

from ..instrumentation import attention_analysis as aa
from ..instrumentation import embedding_analysis as ea
from ..instrumentation.causal_analysis import head_ablation_effect
from ..models.config import ModelConfig
from ..models.transformer import ClassicalGPT
from ..training.trainer import load_checkpoint
from ..utils.io import save_json


def _load_model(ckpt: Path) -> ClassicalGPT:
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = ClassicalGPT(ModelConfig.from_dict(payload["model_cfg"]))
    load_checkpoint(ckpt, model)
    return model.eval()


def _load_tokenizer(run_dir: Path):
    from ..tokenization.char_tokenizer import CharTokenizer
    from ..tokenization.hf_bpe import HFBpeTokenizer

    bpe = list(run_dir.glob("*.tokenizer.json"))
    if bpe:
        return HFBpeTokenizer.load(bpe[0])
    return CharTokenizer.load(run_dir / "tokenizer.json")


def build_analysis(run_dir: Path | str, probe_text: str | None = None) -> Path:
    run_dir = Path(run_dir)
    out = run_dir / "analysis"
    out.mkdir(exist_ok=True)
    tokenizer = _load_tokenizer(run_dir)
    ckpts = sorted(run_dir.glob("checkpoints/*.pt"))
    init_ckpt = ckpts[0]
    final_ckpt = ckpts[-1]
    model_init = _load_model(init_ckpt)
    model_fin = _load_model(final_ckpt)

    probe_text = probe_text or "日本の首都は東京です。私はその街に住んでいます。"
    ids = torch.tensor([tokenizer.encode(probe_text)[:64]])
    tokens = [tokenizer.id_to_token(int(i)) for i in ids[0]]

    # ---- attention analysis (init vs final)
    attn = {
        "probe_text": probe_text,
        "tokens": tokens,
        "init": aa.summarize(model_init.attention_maps(ids)),
        "final": aa.summarize(model_fin.attention_maps(ids)),
    }
    # store the actual maps of the final model (layer 0 & last) for heatmaps
    maps_fin = model_fin.attention_maps(ids)
    np.savez_compressed(
        out / "attention_maps.npz",
        layer0=maps_fin[0][0].numpy(),
        layer_last=maps_fin[-1][0].numpy(),
        tokens=np.array(tokens, dtype=object),
    )
    save_json(attn, out / "attention_stats.json")

    # ---- head ablation (causal importance) on a real batch
    probe_ids = torch.tensor(tokenizer.encode(probe_text))
    reps = (8 * 33) // max(1, len(probe_ids)) + 1
    flat = probe_ids.repeat(reps)[: 8 * 33]
    x = flat.view(8, 33)[:, :-1]
    y = flat.view(8, 33)[:, 1:]
    eff = head_ablation_effect(model_fin, x, y)
    save_json({"head_ablation_delta_loss": eff.tolist()}, out / "head_ablation.json")

    # ---- embedding analysis
    norms_fin = ea.token_norms(model_fin)
    drift = ea.drift(model_init, model_fin)
    # frequency from tokenized cache if available
    emb = {
        "norm_mean": float(norms_fin.mean()),
        "norm_std": float(norms_fin.std()),
        "drift_mean": float(drift.mean()),
        "drift_max": float(drift.max()),
    }
    # PCA of a sample of embeddings colored by token class (BPE: first char)
    n_sample = min(1500, model_fin.cfg.vocab_size)
    sample_ids = list(range(6, 6 + n_sample))  # skip specials
    coords = ea.pca_2d(model_fin, sample_ids)
    np.savez_compressed(
        out / "embedding_pca.npz",
        coords=coords.astype(np.float32),
        ids=np.array(sample_ids),
        norms=norms_fin[sample_ids].numpy(),
        drift=drift[sample_ids].numpy(),
    )
    save_json(emb, out / "embedding_stats.json")

    save_json(
        {
            "init_ckpt": init_ckpt.name,
            "final_ckpt": final_ckpt.name,
            "n_layers": model_fin.cfg.n_layers,
            "n_heads": model_fin.cfg.n_heads,
            "tokenizer": tokenizer.version,
        },
        out / "meta.json",
    )
    return out


if __name__ == "__main__":
    import sys

    print(build_analysis(sys.argv[1]))
