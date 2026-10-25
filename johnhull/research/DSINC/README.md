# DSINC American put reproduction

2026-10-25。ローカルv1の実装・検証終了。**Americanは未再現・不採用、mainは停止。** [全6ケース・費用・採否](RESULTS.md)。市場データを使わないprivateな数値検証研究。

## 現在の状態

- Task 1: 入力型、固定上流、監査adapterの単体テスト30件と索引/docstring guardを実装。Heston先頭ケースの予算付き観測と無改変版cross-checkまで完了。
- Task 2: 固定周波数Europeanまで実装・制御検証済み。Task 3の独立FDまで実装・基礎検証済み。Task 4のEEP/境界も実装。S0は複数根で停止し、Task 5の33job pilotはmain不可を判定。Opus最終APPROVEと再実行同一性/是正後関連1024PASSを確認済み。American研究を再現済みとは扱わない。
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


## Task 3: 独立FD

作用素をx,zetaのSDEから別導出し、中心差分・Neumann ghost・短い次元の内側配置・Rannacher 4 half-steps→CNを実装した。Americanは[Ikonen–Toivanen splitting](https://doi.org/10.1016/j.aml.2004.06.010)で障害条件を処理する。lambda、payoff gap、相補性と分割後の離散方程式欠損は別々に保存する。Europeanのpayoff未満や負のpredictorもraw診断として残す。

基礎10テストはSDE作用・独立BSM/CRR・障害条件・不等比分散細分の観測次数・境界bracket/mask・時間/RSS予算を検査する。BSM fixtureのx801/1001/1601点誤差は5.845e-6/3.756e-6/1.493e-6で二次的に減少したため、5e-6基準を維持してfixtureを1001点とした。自己比較で精度を認定しない。

European smokeのpaper fineは{.102552411,.047215339,.019098937}、DSINCとの差は最大8.924e-6*K。広い独立分散領域[log(1e-5),log8]ではx481→961の最大変化6.674e-6*Kで、正式referenceの5e-6基準は未達。x領域のh固定倍拡大は最大1.35e-13*K差だった。これはEuropeanの準備観測で、American主実験への移行承認ではない。主実験の停止条件はTask 5で機械判定する。

観測10jobは計23.6秒程度、最大peak RSS約489 MB。小結果はtask3_observation.json。全FD面を保存しない。時間上限は内部検査と観測用外部subprocessの両方で監視した。


## Task 4: American境界の停止

Eq.(57)のterminal半重みと正減衰のEEP留数、Eq.(58)だけのdt*g/4を別々に検査した。local_boundaryはresidual(x,node)を受け、scanを64点ずつ処理する。prepare_americanでboundary/Q/Gを一度解き、PreparedAmerican.priceが本当のquery-only評価を行う。新しい公開APIは追加していない。

定数分散の解析伝播によるAmericanはCRR4000と2e-5*K以内、strike同次性・spot順・接触領域を検査した。T=.1の3/2 interior-domain制御は独立FDの価格2e-5*K・境界bracket±2dx・coverage条件を満たした。これをS0の再現認定に流用しない。

S0のT=.5/N100は最初の逆向き時間slice(n=99)でmultiple_roots22/160、ok138/160。N200ではmultiple_roots44/160、ok116/160だった。残差走査が複数の符号変化を検出したため、設計どおり全sliceを記録して停止し、失敗境界は伝播していない。価格・EEPは未計算で、印刷価格との一致も未確認。波数打切りと低分散の影響は候補だが、原因確定・root選別・許容差の緩和は行っていない。小観測はtask4_observation.json、全statusは_data rootにある。


## 再実行CLI

WSLでmonorepo/worktree rootから、共有venvをno-syncで使い、このworktreeのhullkit/srcをPYTHONPATH先頭にする。出力はprimaryの_data以下の新しい空rootを指定する。

```bash
export UV_PROJECT_ENVIRONMENT=/home/kazumasa/projects/.venv
export PYTHONPATH=/home/kazumasa/worktrees/dsinc-american/johnhull/hullkit/src:/home/kazumasa/worktrees/dsinc-american/deep_hedge_price/src:/home/kazumasa/worktrees/dsinc-american/johnhull/report
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
uv run --no-sync python johnhull/research/DSINC/run.py --phase pilot --output /home/kazumasa/projects/_data/johnhull/DSINC/<new-run>/pilot
uv run --no-sync python johnhull/research/DSINC/run.py --replay /home/kazumasa/projects/_data/johnhull/DSINC/<new-run>/pilot
uv run --no-sync python johnhull/research/DSINC/plot.py --results /home/kazumasa/projects/_data/johnhull/DSINC/<new-run>/pilot/results.json --output /home/kazumasa/projects/_data/johnhull/DSINC/<new-run>/pilot/figures
```

mainには--manifestが必要で、現行のineligible freezeでは拒否する。README/RESULTSの文書更新は数値source hashに含めず、実行コード変更はreplayで拒否する。

Opusの初回実装レビューは重要4点（main replayの採否再計算、終了時RSS/wall判定、import先とのhash一致、EU/AM/EEPの相殺検出）。回帰テストで再現して是正し、R1 APPROVEを確認済み。元のpilotの数値結果は変えていないが、source hashを保つため最終コードでpilotを再実行し、33入力/価格と32NPZのbit一致を確認した。

Opus R1はAPPROVE、残存Critical/Important0。最終pilotの同一性照合を条件に承認し、その条件を満たした。[実装レビュー記録](../../docs/superpowers/reviews/2026-10-25-dsinc-american-implementation-opus.md)。runtime固定はPython/NumPy/SciPy版とworkerで実際に検査するthread環境変数までで、BLAS実装/版や他のhullkit全体のhashは固定していない。
