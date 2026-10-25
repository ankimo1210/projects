# DSINC American put reproduction

2026-10-25。実装中。市場データを使わない、privateな数値検証研究。

## 現在の状態

- Task 1: 入力型、固定上流、監査adapterの単体テスト30件と索引/docstring guardを実装。Heston先頭ケースの予算付き観測と無改変版cross-checkまで完了。
- Task 2: 固定周波数Europeanまで実装・制御検証済み。Tasks 3–5は未着手で、American研究を再現済みとは扱わない。
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

## Task 2: 数学対応とEuropean smoke

| 実装 | 原論文/独立対照 |
|---|---|
| frequency_generator / 共通matrix builder | Eq.(14)/(53)、zeta=log(v)のItô drift、混合項rho*sqrt(v)*a。割引は含まない |
| build_propagators | ghost反射Neumann、expm(dt*A_k)、k=-omega-i*chi、正周波数のパネルGauss–Legendre |
| European積分 | Eq.(61)、正減衰の+1留数、価格側で一度だけexp(-rd*T) |
| 定数分散制御 | 解析的Fourier modeと独立な正規密度payoff積分 |
| CIR平均制御 | u=1/vの解析的平均、160/240/320点の観測次数/相対誤差 |
| Heston制御 | Fellerを満たすkappa2,theta=v0=.04,xi=.2,rho=-.5、既存CF価格とoffset |

S0のEuropeanは{.102557343413,.047224262980,.019104661425}。印刷値との差の最大は3.4342e-7*K。setup3.957秒、伝播を含むEuropean評価.284秒、全体4.241秒、peak164,708,352 bytes、伝播行列44,236,800 bytes。正式なpaper_match/独立gateの判定はTask 5で行う。

zero-frequency伝播の最小成分は-.03158、max Pe=14.38、行和誤差3.9e-15。低分散側の中心差分は非単調であり、確率行列としての正値性は保証しない。flagを消さず、独立FD・採用段の感度・境界gateの全成立が必要。

厳しいBSM積分テストの1e-10基準には各パネル24点を使用する。12/16/24点の最大誤差は4.09e-8/3.44e-11/6.8e-16。論文S0の12点と6e-6 gateは変更していない。最終価格のv0評価はzeta方向のnot-a-knot CubicSpline、外挿なし。cacheは全契約/モデル/格子にbindする。

小結果はtask2_observation.json。中間のmatrixやFD面は保存しない。European APIの評価時間にはterminal-vector伝播を含み、query-onlyの時間とは呼ばない。
