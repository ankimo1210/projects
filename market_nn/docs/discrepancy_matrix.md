# Discrepancy matrix

| target | paper | official code at pin | preserved profiles |
|---|---|---|---|
| DeepLOB conv width | 16 | TF2/PyTorch 32 | paper, TF2 author, PyTorch author |
| DeepLOB Inception width | 32/branch | 64/branch | paper, author |
| DeepLOB temporal padding | preserve time | TF2 same; PyTorch valid (100 -> 82) | separate author profiles |
| DeepLOB activation/BN | LeakyReLU .01; BN not stated | TF2 LeakyReLU/no BN; PyTorch block2 Tanh + BN | separate profiles |
| DeepLOB dropout | not stated | TF2 `.2` forced with `training=True`; PyTorch none | TF2 exact + corrected audit |
| DeepLOB optimizer/batch | Adam `.01`, eps `1`, batch32 | TF2/PyTorch `.0001`; batch128/64 | separate lifecycle specs |
| DeepLOB output/loss | softmax + categorical CE | PyTorch returns softmax into `CrossEntropyLoss` | oddity retained |
| TLOB MLPLOB learning rate | `.003` | `.0003` | paper constrained + repository exact |
| TLOB MLPLOB sequence | `384` | `384` | no discrepancy (`CORR-001`) |
| TLOB/MLPLOB hidden dimension on FI-2010 | not disclosed in Table10 | static config `40`, then `main.py` overrides to feature count `144` | author exact uses runtime `144`; paper profile remains constrained |
| TLOB BiN negative weights | mathematical nonnegative mixture intent | Parameter replacement with CUDA tensor inside forward | reference + corrected audit |
| TLOB BiN zero variance | not specified | temporal std `<1e-4` becomes 1; feature std unguarded | reference behavior retained |
| TLOB BiN autograd | not specified | in-place temporal-std guard invalidates gradients w.r.t. inputs | reference behavior retained; corrected audit is autograd-safe |
| TLOB order-type embedding | trainability not discussed | `.detach()` blocks gradients | exact + trainable-embedding audit |
| TLOB attention mask | not described as causal | no mask passed to `MultiheadAttention` | no-mask exact behavior |
| TLOB EMA decay schedule | flat `.999` implied | `torch_ema` default `use_num_updates=True`: effective decay `min(.999,(1+n)/(10+n))` warms up over ~9k updates | lifecycle port reproduces warm-up (`training.ema_use_num_updates`) |
| TLOB label threshold | paper says mean percentage change | code uses `mean(abs(change))/2`, per split | separate paper/code semantics |
| TLOB/MLPLOB parameter count | Table2: about `1e7` / `6.3e7` | FI-2010 runtime: `2,656,724` / `6,327,908`; static hidden-40 config: `1,140,342` / `3,016,782` | all values reported; no silent reconciliation |
| Sirignano input/lifecycle | high-level only | no official code found in primary-source audit | paper-constrained only |
