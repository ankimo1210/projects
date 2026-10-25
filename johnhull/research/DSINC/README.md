# DSINC American put reproduction

2026-10-25。実装中。市場データを使わない、privateな数値検証研究。

## 現在の状態

- Task 1: 入力型、固定上流、監査adapterの単体テスト30件と索引/docstring guardを実装。Heston先頭ケースの予算付き観測と無改変版cross-checkまで完了。
- Tasks 2–5: 未着手。新論文の3/2 pricerは未実装で、再現済みとは扱わない。
- 上流コードの観測はすべて `accepted=false`。fallbackやfloorが無くても、独立な収束・精度検証の代用にはしない。

## 入力と出典

`upstream_manifest.json` がcommit、Git blob、SHA-256を固定する。`upstream/` は無改変のMITソースで、原文の著作権表記はそのまま保持する。`heston_baseline.py` の観測用helperはこれらからの派生で、適用されるMIT通知は `upstream/LICENSE` を参照する。

`cases.json` にはHeston 11 spotケース、3/2の2満期×3spotsと文献値を保存する。価格anchorはprice/K、v0/thetaは分散率、Tは年、rd/rfは連続複利年率。EuropeanとAmericanを独立の文献照合項目とし、EEP/N=200/論文FDは診断に使う。

## 監査

adapterは単一の契約・モデルからsigma/xi、T/T2を写像する。rootの局所探索/広域scan/最小残差、予測値clip、CF非finite置換、European/EEPのfloor、Americanのpayoff下限、FD penalty最大反復を記録する。原本との値の一致はテストする。benchmark.pyはimportしない。

上流DSINCはquery-only APIがないためquery_secondsはnull。FDはsolveの後に同一面のqueryを計測する。setup、European、American、queryとtotalを混同しない。

## 資源見積もりと検証

先頭Hestonケースだけを実行する。DSINCの主要なlag配列は概算16×600×16²×16 bytes≈37.5 MiB、FDは約20,000状態のsparse演算で、全体peakを0.6 GiB程度と見積もる（未計測）。上限は1process 180秒/2 GiB、結果・audit JSONは2 MiB未満を見込む。実測と失敗はprimaryの `_data/johnhull/DSINC/implementation-2026-10-25/` に保存し、中間配列は残さない。

worktreeではprimaryの共有venvをno-syncで使い、PYTHONPATHをこのworktreeのhullkit/srcから始める。他セッションのeditable installを変更しない。

```bash
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_dsinc_baseline.py
```

元のworktree baselineはRB-F04の既存reference.npz不足で3件失敗した。primaryでは該当8件がPASSし、外部の同じ入力へのignored symlinkを置いたworktreeでも8件PASSした。入力の192,772,222 bytesはコピーしていない。新規研究の出力ではない。

[設計](../../docs/superpowers/specs/2026-10-25-dsinc-american-design.md)・[計画](../../docs/superpowers/plans/2026-10-25-dsinc-american.md)

## Task 1の観測結果

先頭ケースは7.14秒、peak RSS 153,743,360 bytes（見積もり0.6 GiBより小さい）。DSINC (European, American, EEP)=(13.6633237490,13.6853928134,.0220690644)、FD (European,American)=(13.6622464121,13.6838958737)。無改変版との最大差は0。

上流の印刷IE American 13.6749との差は+.0104928134。観測版の改変が原因ではないことを確認したが、論文との相違原因は未確定。Task 1はこの差を保存する基礎監査であり、上流の印刷値に合わせて計算を調整しない。今回の実行にはCF非finite置換・floor・root fallback・penalty未収束はなく、warningも0だった。

小さな再利用結果はtask1_observation.json。全auditは指定の_data rootに保持する。単体30件＋MODEL_INDEX/docstring guardは947 PASS、ruff check/format PASS。full baselineの3件は既存入力へのリンクで該当8件PASSとなった。全suiteの最終再実行は研究実装後に行う。
