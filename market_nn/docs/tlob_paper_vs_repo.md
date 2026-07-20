# TLOB / MLPLOB: paper vs repository

TLOB v3 Table10 と repository `f1c0af4` は TLOB の主要 hyperparameters
（Adam、sequence 128、lr 1e-4、4 layers）で一致する。MLPLOB は sequence 384 と
3 layers が一致し、learning rate が paper `.003`、repository `.0003` で相違する。

Repository profile は次も挙動として固定する。

- `config.py` の `hidden_dim=40` を、FI-2010 実行入口 `main.py` が feature count
  `144` に上書きする。author-exact profile は実行時の `144` を使い、静的値も別欄に残す。
- post-attention residual -> LayerNorm -> MLP、dimension一致時だけ2つ目の residual。
- temporal/feature axis を各 layer 後の permutation で交互化。
- causal/attention mask なし、dropout なし。
- BiN の unbiased `torch.std`、非対称な zero-variance guard、forward中の負 mixture
  parameter replacement。
- BiN の temporal std に対する in-place guard。このため入力 tensor 自体に gradient を
  要求すると pinned source と `reference_compat` は backward に失敗する。通常の model
  parameter gradient は一致し、`corrected_port` はこの autograd hazard を除く。
- LOBSTER order-type embedding の `.detach()`。
- CE、EMA decay `.999`、validation/testの EMA swap、validation loss による LR 半減。
- EMA は `torch_ema` をデフォルト `use_num_updates=True` で構築するため、実効 decay は
  update n で `min(.999, (1+n)/(10+n))` とウォームアップし、約9,000 update 後に初めて
  `.999` に到達する。lifecycle port はこのスケジュールを再現する
  （profile field `training.ema_use_num_updates`）。
- LOBSTER label threshold `mean(abs(change))/2` と class `up=0/stable=1/down=2`。

Parameter count も一致しない。paper Table2 は TLOB 約 `1e7`、MLPLOB
`6.3e7` とするが、FI-2010 runtime override を含む clean-room instantiation は
`2,656,724`、`6,327,908` である。static `hidden_dim=40` だけを使った値は
`1,140,342`、`3,016,782`。paper table の configuration/counting definition は
未解決であり、repository profile の golden count には runtime 値を用いる。

Paper profiles は exact BiN edge behavior と full lifecycle が論文から決まらないため
`C_PAPER_CONSTRAINED` とする。

固定 source を取得済みの場合、テストは同一 state/input に対する BiN の出力、parameter
gradient、SGD 1-step update、および小型 TLOB/MLPLOB の logits を直接比較する。
