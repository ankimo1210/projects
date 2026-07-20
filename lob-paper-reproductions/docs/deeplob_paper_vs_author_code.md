# DeepLOB: paper vs author code

| behavior | IEEE / arXiv v6 paper | TF2 notebook `ff14d7c` | PyTorch notebook `ff14d7c` |
|---|---|---|---|
| input normalization | exact validation construction is not stated; FI-2010 setups are named | decimal-precision, no-auction | decimal-precision, no-auction |
| split | Setup1 anchored 9 folds; Setup2 first 7 / last 3 days | CF7 train file first 80% / final 20%; CF7/8/9 tests concatenated | same 80/20 and test concatenation |
| conv / Inception width | 16 / 32 per branch | 32 / 64 | 32 / 64 |
| activation | LeakyReLU 0.01 | LeakyReLU 0.01 | block 2 Tanh; otherwise LeakyReLU 0.01 |
| BatchNorm | not stated | none | after conv and Inception convs |
| temporal padding | same, time remains 100 | same, time remains 100 | valid, time 100 -> 94 -> 88 -> 82 |
| dropout | not stated | 0.2 with `training=True` and time-shared noise shape | none |
| output / loss | three-class softmax and categorical CE | softmax + categorical CE | softmax probabilities passed to `CrossEntropyLoss` |
| Adam / batch | lr .01, eps 1, batch 32 | lr 1e-4, runtime-default eps, batch 128 | lr 1e-4, runtime-default eps, batch 64 |
| stopping / selection | validation accuracy, patience 20 | 200 epochs; best `val_loss` checkpoint | 50 epochs; best validation-loss serialized model |
| explicit seed | not stated | NumPy 1, TensorFlow 2 | none |
| framework version | paper implementation details only | exact TensorFlow/Keras version is not pinned | exact PyTorch version is not pinned |
| displayed parameter count | diagram-derived clean port: 60,947 | 142,435 | 143,907 |

TF2 の runtime-default Adam epsilon と、TF2/PyTorch の exact framework version は
repository から確定できないため、author-code profile の未解決 field として残す。通常
smoke は TF2 を解析的 shape/count spec として検証し、native TensorFlow 比較を主張しない。

DeepLOB repository の固定 commit には license file がない。したがって notebook source
自体は vendoring せず、hash 固定したローカル参照と独立 clean-room 実装だけを使う。
