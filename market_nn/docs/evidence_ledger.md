# Evidence ledger

locator は PDF の印刷ページ、または `repository@commit:path:line-range` を指す。

| ID | decision | evidence |
|---|---|---|
| GB2015-E001 | response は上昇=1、下降=0 | PAPER: arXiv:1512.03492v1 p.11, Eq.9 |
| GB2015-E002 | sampling time は連続時間の open interval `(t_{i-1},t_i)` | PAPER: p.11, Eq.10; p.12 event-time alternative |
| GB2015-E003 | 100 observations/day、252日、random 80/20 | PAPER: p.12, Sec.5.2 |
| GB2015-E004 | null probability 0.5、ROC-AUC、mean squared residual | PAPER: p.14, Eq.18-20 |
| GB2015-E005 | tricube nearest-neighbour、5-fold CV、MSR、reported bandwidth 0.65 | PAPER: p.14 Sec.5.5; p.22 Sec.6.4 |
| DL2019-E001 | input は直近100 states x 40 features、各levelは ask price/volume, bid price/volume | PAPER: arXiv:1808.03668v6 p.4-5, Eq.6 |
| DL2019-E002 | paper conv=16、Inception branch=32、LSTM=64、same temporal padding、LeakyReLU 0.01 | PAPER: p.5 Fig.3; p.5-6 Fig.4 and text |
| DL2019-E003 | categorical CE、Adam lr=.01 eps=1、batch32、val accuracy patience20 | PAPER: p.6 Sec.V-A |
| DL2019-E004 | Setup1 anchored 9 folds、Setup2 first7/train last3/test | PAPER: p.6 Sec.V-B |
| DL-AUTH-E001 | TF2 uses 32/64 channels, forced-training dropout .2, Adam 1e-4, batch128 | AUTHOR_CODE: `zcakhaa/...@ff14d7c:jupyter_tensorflow/run_train_tensorflow-version2.ipynb` code cells around source lines 183-308 |
| DL-AUTH-E002 | TF2 displayed total parameters = 142,435 | AUTHOR_CODE: same notebook output `Total params` |
| DL-AUTH-E003 | PyTorch valid temporal convs, BN, block2 Tanh, softmax output, CE, Adam 1e-4, batch64 | AUTHOR_CODE: `zcakhaa/...@ff14d7c:jupyter_pytorch/run_train_pytorch.ipynb` extracted code lines 181-408 |
| DL-AUTH-E004 | PyTorch displayed total parameters = 143,907 | AUTHOR_CODE: same notebook output `Total params` |
| FI2010-E001 | five stocks/order: KESBV, OUT1V, SAMPO, RTRKS, WRT1V | DATASET_DOC: arXiv:1705.03233v5 p.9 Table1 |
| FI2010-E002 | 144 features = raw 40 + engineered 104 | DATASET_DOC: p.12-13 Table4 |
| FI2010-E003 | label rows map downstream event horizons 10,20,30,50,100; source class 1/2/3 = up/stable/down | DATASET_DOC: p.13-14 Eq.8; AUTHOR_CODE: DeepLOB notebook `get_label`, `k=4`; TLOB `preprocessing/fi_2010.py:17-36` |
| TLOB-E001 | dual temporal then spatial attention and MLPLOB block | PAPER: arXiv:2502.15757v3 p.4 Fig.2/Sec.5.2 |
| TLOB-E002 | TLOB Adam/128/1e-4/4 layers; MLPLOB Adam/384/.003/3 layers; heads=1 | PAPER: p.9 Table10 |
| TLOB-E003 | paper uses FI-2010 144 features and original labels, horizons 10/20/50/100, F1 | PAPER: p.5-6 Sec.6.1/6.4 |
| TLOB-E004 | TSLA/INTC Jan 2-30 2015, 17/1/2 days, volume sampling 500 shares | PAPER: p.5 Sec.6.3 |
| TLOB-AUTH-E001 | QKV/MHA/residual/post-norm/MLP, no mask, axis permutation | AUTHOR_CODE: `LeonardoBerti00/TLOB@f1c0af4:models/tlob.py:12-121` |
| TLOB-AUTH-E002 | BiN uses torch.std default, temporal zero guard only, mutates negative mixture params | AUTHOR_CODE: `...:models/bin.py:5-85` |
| TLOB-AUTH-E003 | static config: MLPLOB 384/.0003/3、TLOB 128/.0001/4/head1、hidden40; FI-2010 entrypoint overrides hidden to144 | AUTHOR_CODE: `...:config/config.py:14-24`; `...:main.py:27-29` |
| TLOB-AUTH-E004 | EMA=.999, CE, Adam eps=1e-8, validation/test EMA, LR halving rule | AUTHOR_CODE: `...:models/engine.py:18-57,80-104,138-150,201-228` |
| TLOB-AUTH-E008 | torch_ema is constructed with default `use_num_updates=True`, so effective EMA decay is `min(.999,(1+n)/(10+n))` at update n | AUTHOR_CODE: `...:models/engine.py:12,55`; `...:requirements.txt:17`; torch_ema `ExponentialMovingAverage.update` |
| TLOB-AUTH-E005 | LOBSTER label uses half mean absolute change; up/stable/down = 0/1/2 | AUTHOR_CODE: `...:utils/utils_data.py:127-160` |
| TLOB-AUTH-E006 | FI-2010 runtime semantics instantiate 2,656,724 TLOB and 6,327,908 MLPLOB parameters; static hidden-40 values are 1,140,342 / 3,016,782 | AUTHOR_CODE: clean-room execution of `main.py`, `models/tlob.py`, `models/mlplob.py`, `config/config.py` semantics under PyTorch 2.11 |
| TLOB-AUTH-E007 | pinned BiN and clean-room `reference_compat` match output, parameter gradients, and one SGD update; pinned in-place std guard prevents input gradients | AUTHOR_CODE: executable golden comparison against `...@f1c0af4:models/bin.py:39-72`; `tests/test_tlob.py` |
| SC2019-E001 | 3 LSTM layers + ReLU + softmax; regularized NLL, SGD, truncated BPTT | PAPER: arXiv:1803.06917v1 p.5-7 |
| SC2019-E002 | main comparison 50 units/layer; 150-unit universal variant | PAPER: p.12-13 Fig.6/8 |
| SC2019-E003 | pooled stocks, completely unseen stocks, 100 vs 5,000 histories | PAPER: p.7-8, p.13-16 |

## Seed corrections

- `CORR-001`: prompt seed claimed a paper/repository MLPLOB sequence-length conflict
  (128 vs 384). TLOB v3 Table10 states MLPLOB sequence 384. Repository also uses 384.
  The confirmed conflict is learning rate only: paper `.003`, repository `.0003`.
- `CORR-002`: prompt seed suggested TLOB paper could be `B_PAPER_EXACT`. Exact BiN
  edge behavior, full initialization, and lifecycle are not fully stated in the paper, so the
  paper profile is conservatively `C_PAPER_CONSTRAINED`.
- `CORR-003`: TLOB v3 Table2 reports approximately `1e7` TLOB and `6.3e7` MLPLOB
  parameters. The pinned FI-2010 path overrides hidden dimension 40 to 144 and instantiates
  `2,656,724` / `6,327,908`; without that runtime override the counts are `1,140,342` /
  `3,016,782`. Parameter definitions/configuration behind the paper table remain unresolved.
- `CORR-004`: reading only `config/config.py` misses `main.py`'s FI-2010 hidden-dimension
  override. Repository-exact profiles therefore encode both the static value and runtime value,
  and use the latter for executable golden counts.
