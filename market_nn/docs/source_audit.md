# Phase 0 source audit

監査日時: 2026-07-20T09:11:11Z

## 固定した一次資料

| paper | fixed version | local SHA-256 |
|---|---|---|
| Gould & Bonart | arXiv:1512.03492v1 | `a5051285adfe2d8a2d7f46a758486f357d556a46a964bc89b245de7e7a0bc338` |
| DeepLOB | arXiv:1808.03668v6 / IEEE 2019 reference | `f50d57a80644ac427433824b540c9bc713ffd2249c2042ba975d986078295913` |
| Sirignano & Cont | arXiv:1803.06917v1 | `8ae07ac2ae3bd803210f36acfca5a4ceb298acdd1b8f9a9d44a036822dd964fd` |
| TLOB | arXiv:2502.15757v3 | `da90d24cfcc7a0074187fd7d2c6d27c4a7ffbcc86cece5dd4d5ba12901e2e03b` |
| FI-2010 | arXiv:1705.03233v5 | `22d856cd9e1d951ddcec917bd7fcaf7e83f233b39c05f6a990617f32d201b31d` |

PDF は自己完結した監査資料として `sources/papers/` で Git 管理し、必要に応じて
`lob-repro sources fetch` で再取得できる。版履歴は arXiv abs page で確認した。
DeepLOB v6 は2020年の最終 arXiv 版で、IEEE 2019 paper の書誌情報と DOI
`10.1109/TSP.2019.2907260` を併記する。

## 公式コード

| repository | commit | commit date | license at commit | policy |
|---|---|---|---|---|
| `zcakhaa/DeepLOB-Deep-Convolutional-Neural-Networks-for-Limit-Order-Books` | `ff14d7c2fd38bdfc143389786993d0f0236d4eb8` | 2021-07-15 | absent | substantial source is not vendored |
| `LeonardoBerti00/TLOB` | `f1c0af4d81067978914361766db0457a7d8b6a46` | 2026-02-24 | MIT | clean-room port with locator/hash evidence |

両 commit は GitHub commits API で full SHA と tree を確認した。取得した tarball は
`sources/references/`（Git 管理外）でのみ比較に使う。

## profile classification

- Gould & Bonart: 明示された標本化・評価を `B_PAPER_EXACT` とする。
- DeepLOB paper: 明示された architecture / optimizer / split を `B_PAPER_EXACT` とし、
  未開示の numerical training choice を必要とする run は許可しない。
- DeepLOB TF2 / PyTorch: 指定 notebook の挙動を別々の `A_AUTHOR_CODE_EXACT` target とする。
- TLOB / MLPLOB paper: BiN と lifecycle の一部が論文だけでは確定しないため
  `C_PAPER_CONSTRAINED` とする。
- TLOB / MLPLOB repository: 指定 commit を `A_AUTHOR_CODE_EXACT` target とする。
- Sirignano & Cont: input state vector などが不足するため `C_PAPER_CONSTRAINED` とする。

## 監査上の制約

親 workspace の Git object `148d090affd2e106a2720d79fd1fca69896c57be` は Phase 0
開始時に読み取り失敗し、初期 `git status` も失敗した。本作業では修復していない。
最終確認時には同 object が commit として読め、`git status` も成功したため、現在の
blocker ではない。初期 run metadata だけは当時の error を保持し得る。

TLOB の repository audit は model files と `config.py` だけでなく `main.py` / `run.py`
まで追跡する。FI-2010 branch が static `hidden_dim=40` を `144` に上書きするため、
author-exact architecture は実行時値を採用する。
