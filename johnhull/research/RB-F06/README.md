# RB-F06：固定beta SABR較正の識別可能性

更新日：2026-10-09。状態：主実験・保存値/fresh検算・両保管庫復元・3図・独立最終レビューを完了。最終テストfixture修正済み、release・main統合を進行中。

## 問いと範囲

小さいクオート残差だけでパラメータと未使用strikeのvanilla価格が安定して決まるかを調べる。
固定β=.5、F=100、T=1年、discount=1のHagan近似IV写像の逆問題である。
exact SABR価格・動学・exotic・大域識別・保証被覆の受入は含めない。
[設計](../../docs/prep/design/RB-F06_DESIGN.md)／[実施計画](../../docs/superpowers/plans/2026-10-09-sabr-identifiability.md)。

## 条件と実験

- θ=(a,ρ,ν)、a=α/F^(1−β)。真値は(.20,−.30,.40)と(.20,−.30,.02)。
- fullはlog(K/F)=[−.20,−.10,−.01,0,.01,.10,.20]の7クオート。ATMは中心3点、sparseは±.10の2点。
- 各真値・クオート群にnoiseless1条件と5 vol bpのGaussian noise16反復。master noiseを共用して部分集合を作る。
- 9固定starts、scaled座標のbounded TRF。主max_nfev400、profile nuisance250。pilot後に全条件と金融source6件を固定し、主比較後は拡張しない。
- holdoutはlog(K/F)=[−.15,−.05,.05,.15]の補間4点と[−.25,.25]の外挿2点。pilot・較正入力から隔離する。
- 102 dataset、918 unrestricted＋3480 profile＝4398 solver calls。上限4830のうち432未使用。

全96 noisy slotでconverged baselineを得た。元の失敗5件（noiseless弱ν ATMの予算到達）、境界、unknownを保存する。
noisy最良解のJacobian未解決は6/96（weak full2、weak ATM4）。全unrestricted918件では48件がnumerical_unresolved。

## 主結果

下表は各16 noisy反復の最良converged fit。IV 1 vol bp=0.0001。
価格はF=100の合成モデル単位。通貨建ての実市場価格ではない。

| 真値 / クオート群 | 最大クオート残差 (vol bp) | 最大holdout IV誤差 (vol bp) | 最大価格誤差 | J未解決/16 |
|---|---:|---:|---:|---:|
| 通常 / full | 10.1451 | 17.1238 | 0.0338856 | 0 |
| 通常 / atm | 4.88396 | 883.056 | 2.13619 | 0 |
| 通常 / sparse | 3.63598e-10 | 545.437 | 1.20287 | 0 |
| 弱ν / full | 13.2618 | 19.9013 | 0.0370223 | 2 |
| 弱ν / atm | 7.41338 | 954.349 | 2.39471 | 4 |
| 弱ν / sparse | 8.77076e-11 | 269.378 | 0.556141 | 0 |

fullではパラメータが不安定でも価格誤差が比較的小さい。ATM・sparseでは小さいクオート残差がholdout価格の安定性を保証しない。
参考実用線（IV10bp、価格/F=2e-4）は用途別の合格値ではなく、fullでも各真値3/16がIV線、2/16が価格線を超える。

弱ATM rep0の最小特異値は独立5point差分1.863e-5に対し保存値9.909e-5、Jacobian全体の相対差は2.27e-7だった。
全体差だけの検査では弱方向の不確実性を見落とす。保存されたnumerical_unresolvedがこの条件を捕捉する。

## 支持域と制限

- profileは残るパラメータを再最適化したもの。真値/推定値を固定したsliceとは区別する。
- noisyのχ²₁参考線はpointwiseの記述的診断であり、保証95%区間や3次元同時支持域ではない。
- noiseless curve/tableの成分はΔQ≤1e-6のみで分類する。同等fitの価格訪問集合には、さらにmax IV residual≤1e-9を要求する。
- 有限訪問点の価格範囲は連続域全体の包絡ではない。未探索gap、境界打切り、全start失敗とbaseline不足を明示する。
- 16反復の真値含有は14–16件。included/excluded/unknownと元分母を保持し、known-only Wilsonを被覆保証と扱わない。
- local multi-start・有限格子は大域最小値、固定bounds外、exact SABR近似誤差や市場noiseを検証しない。

## 保存値・独立検証・採否

[主記録](reference.json)は全slotと原価を保持する。23,154,318-byte NPZは[保管庫manifest](reference_manifest.json)から復元する。
[fresh](fresh_check.json)は32 master noise vectorsと12指定fitを再計算し、主推定へpoolしない。
[両保管庫検査](cas_validation.json)はprimary/mirrorからそれぞれ復元して全102 dataset/4398 fitを数値再検査した記録である。

[独立最終レビュー](REVIEW.md)／[成果binding](review.json)：教材scopeでapproved、残Critical/Important0。
全4398 fitの独立Hagan＋math.erfc Black、全918多step Jacobian、870 slice witness/102 datasetの支持判定、代表10 SLSQP、両復元copyを検査。
最大IV差2.1131e-11、holdout価格差6.8587e-10。独立解析極限はβ=1/ν=0の正規密度積分で、一般exact SABRへ拡張しない。

[実行済み教材](sabr_identifiability.ipynb)はartifact-onlyの4 code cells・3 PNG。optimizer/RNGを禁止し、saved checker実行と実3図の目視を完了。
[教材検証](notebook_validation.json)にΔQ-only表示と同等fitの追加IV条件も記録する。

元の全3suiteは7742 PASS/2 FAIL/6 skip。条件固定に依存したテストfixture2件を修正し、関係56件と索引込み777件がPASS。重複なし7744 PASS/6 skipはこの再確認を合わせた数で、全suiteの再実行結果ではない。変更12Python ruff/format PASS。

採否：較正残差・パラメータ回復・価格安定性を分ける教材として保持する。
万能な較正器、exact SABR、保証被覆、完全な価格包絡としての採用はしない。
原始JSONのteaching_acceptance=Falseは書き換えず、外部レビューと[最終検証](validation.json)で受入を判断する。

## 原価

| 記録した量 | 主実験の実測 |
|---|---:|
| 元CLI全体（imports・pilot事前検査・保存込み） | 196.74秒 |
| fit attempt（内包時間） | 20.3809秒 |
| solver（内包時間） | 18.5884秒 |
| diagnostic（内包時間） | 0.5895秒 |
| checkpoint I/O | 169.4003秒 |
| residual / diagnostic calls | 440061 / 32343 |
| fit scalar IV / stability scalar IV評価 | 1709394 / 46506 |
| fit holdout IV / Black評価 | 各26388 |
| 評価回数unknown / 例外 | 0 / 0 |

[全CLI receipt](process_cost.json)と[最終圧縮/保存receipt](serialization_cost.json)は別記する。
内包時間をすべて足し合わせない。今回のwall timeはcheckpoint I/Oが大半で、fitだけの費用を実用速度と扱わない。

## 再検査

repository rootから、既存primary/mirror環境変数を設定して実行する。
worktreeでは共有環境のPython `/home/kazumasa/projects/.venv/bin/python` を使う。

```bash
.venv/bin/python johnhull/scripts/evidence_store.py restore \
  johnhull/research/RB-F06/reference_manifest.json --dest johnhull/research/RB-F06
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=johnhull/hullkit/src .venv/bin/python \
  johnhull/research/RB-F06/build_reference.py --check johnhull/research/RB-F06
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=johnhull/hullkit/src .venv/bin/python \
  johnhull/research/RB-F06/build_notebook.py --artifacts johnhull/research/RB-F06 --execute
```

`--fresh`は追加検算として別receiptに保存し、元の成果・費用を上書きしない。

## 一次資料とpilot監査

- [Hagan et al. 2002](https://lesniewski.us/papers/published/ManagingSmileRisk.pdf)：SABRと近似IV写像。
- [Raue et al. 2009](https://www.jeti.uni-freiburg.de/papers/Raue_Bioinformatics_printed_1923.pdf)：nuisance再最適化profile。
- [Self & Liang 1987](https://pages.stat.wisc.edu/~larget/Stat998/Fall2015/Self-Liang-1987.pdf)：境界・非正則性。
- [SciPy 1.17 least_squares](https://docs.scipy.org/doc/scipy-1.17.0/reference/generated/scipy.optimize.least_squares.html)：cost・bounds・nfev仕様。

[基礎レビュー](BASIS_REVIEW.md)／[独立参照](REFERENCE_METHODS.md)／[pilotレビュー](PILOT_REVIEW.md)を保持する。
pilot-initial/は保存group順序修正前、pilot-pre-invalid-fix/はnonfinite分類guard修正前の不変成果。
最新pilot/の30 dataset/386 callsを独立確認後、[freeze記録](freeze_check.json)で全条件・原始pilot・承認・金融sourceを固定した。
原著ATM式のOCR誤読sigma²/rho²は画像と照合しrho²を採用。原著/抽出ファイルを変更していない。
本編306節の台帳は変更しない。
