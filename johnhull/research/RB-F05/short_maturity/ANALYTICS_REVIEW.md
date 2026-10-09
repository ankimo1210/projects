# RB-F05 analytics 数学基礎レビュー

## 判定と範囲

**Importantは修正後の独立再現で解消。数学基礎を支持する。Minor 2件とcaller gateを記録。性能・pilot・NN学習・最終採否は未承認。**

2026-10-09。read-only、対象analytics.py/test_short_maturity_reference.pyと正式spec/plan。未完pilot/runnerは対象外。repository source/tests/docs/Gitは変更していない。

- 最新source SHA256: 09430708a7256774f09a73120398684db0893477111b3fd8f8af18dccc879235
- 最新test SHA256: a038e34e435587212e94bf22c56cd2789e34e0abe45681dec8be5184e9c03bc5
- 独立修正後witnessのsource: cdb8e99970f3331393b28c7f233505e21c93bfe95bc55de2f191fc07e0569646。その後root formatがある。初回7tests PASS、修正4対象tests PASS。
- 詳細証拠: /tmp/rbf05-analytics-review-probe.json（旧source再現）と /tmp/rbf05-analytics-review-verification.json（修正後）。

## 数学・契約確認

### Hermite

\(x=\log(S/K)\) なら保存nodeは \(C_x=S\Delta\)、\(C_{xx}=S^2\Gamma+S\Delta\)。返却式
\[
\Delta=C_x/S,\qquad\Gamma=(C_{xx}-C_x)/S^2
\]
は同じC² quintic価格の微分。[build_hermite](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:63)と[hermite_predict](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:124)は一致する。

独立5次多項式 \(5+e+.1\log t+2x+3x^2+4x^3+5x^4+6x^5\) の2queryで最大差[C,Delta,Gamma]=[1.78e-15,5.49e-16,8.84e-16]。時間blendはlog(seconds)に対してaffineで、Thetaの滑らかさ・正しい時間Greekは未保証。endpoint derivative matchingは[公式API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.BPoly.from_derivatives.html)とも一致する（閲覧時docs1.18、実計算は既存runtime1.17.1）。spot外、59.99秒、23400.01秒はValueError。1e-12はendpoint算術丸め幅。C²だけからaccuracyやconvexityを認定しない。

### 固定clock・oracle

UTC ACT365 carry、252 sessionsのU-clock variance、event Λ=.028 min(minutes,30)/30は別量。8times×2eventの16行でcarry、独立piecewise積分W、Λが一致した。same-day synthetic regular sessionが前提。official early closeや別contractへ一般化しない。expiry ATMはprice0・ordinary Delta/Gamma NaN。

### raw/safe・元分母

rawをcopyしてsafeを構成し、生arrayは変更しない。修正後4行でroutes=[fallback_bound,fallback_bound,expiry_undefined_atm,invalid_contract]、全4行保持、expiry/invalid NaNを確認。safe boundsだけではpricing accuracyを検知できない。error_summaryのprice/Delta/KGamma単位は分離され、inputまたは導出誤差がnonfiniteなら元countを保持してfailed_rowsとNone metricsを返す。finite巨大差にはscaled RMS。

### 費用と回収

unique expense IDs、charged rowの全祖先overlap、missing parent/cycleを検査。未計測seconds=Noneはpending_idsへ残す。measured category合計はpendingを含むtotal cold costではない。

\(Q=\max(0,(t_{NN,offline}-t_{base,offline})/(t_{base,online}-t_{NN,online}))\) はonline saving>0の場合のみquery数。10s/2s/1us/query/2us/queryでQ=8,000,000。onlineは秒/queryが前提で、batch32全体秒をそのまま渡さない。primitiveのrecoverableは性能採用ではない。precision/Greek同等性、pending/startup、main-only対pipeline cold、shared費用のmethod別1回課金はcaller gate。

## Important（解消済み）

1. **祖先越しの費用二重計上** — [expense_totals](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:292)。旧sourceはcharged pipeline10→uncharged setup8→charged teacher4を14秒として受理。全祖先・missing/cycle検査の修正後はValueError。
2. **finite入力でもInf RMSEをcomplete扱い** — [error_summary](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:167)。旧sourceでpred=[[1e200,.5,.1]],ref=0,K100がsquare overflow→complete/failed_rows0/rmse[0]=Inf。修正後はfinite1e200。1e308−(-1e308)は元count1/failed_rows1/nonfinite/metricsNone。nonfinite strikeも拒否。
3. **既知call下限をsafeが検査しない** — [safe_route](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:237)。旧sourceではS105/60秒/raw=[0,.5,0]がraw route。補償済みforwardとJensenから \(C\ge\max(S e^{-q\tau}-K e^{-r\tau},0)\) がevent双方で成立する。修正後はdiscounted-intrinsic下限を検査してfallback_bound、raw保持。64eps程度の幅は算術roundoffでありprecision緩和ではない。
4. **root発見のHermite endpoint同一log** — [build_hermite](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:63)。exp(log23400)と明示23400の別float unionがlog denominator0を生んだ。exact endpoint固定＋positive logdiff guard後、全42 last-time候補finite。実gridは33 base＋3 break=36time nodes、2×65×36=4680node values。名目33を実費用の件数としない。

## Minorと次段gate

- **M1: node自体のfinite検査不足** — [prepare_hermite](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:100)。derivatives finite/diff/logdiff>0だけではxs/tsの最後Infを拒否しない。実fixtureで受理し、ts Infでは有限の通常値を返すqueryもあった。xs/tsのisfinite.allを追加する小修正を推奨。現生成gridはfinite。
- **M2: ±2sqrtW bucket丸め** — [bucket_errors](/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F05/short_maturity/analytics.py:208)。数学上ζ=-2の1/5分等がexp→log復元の1e-17級差でtailに入る。全体元分母は維持されるがinclusive boundary件数は変わる。小さい算術幅または固定geometry labelの確認を推奨。
- bucket_errorsはpのfixed main time/event rosterの部分集計。一覧外invalid/OOD/expiry/boundaryを全bucket合計だけで認定しない。別全件summaryとoriginal boundary rosterをrunner完成後確認する。

## 未検証

正式MC観測SE/rare counts、候補N採用、6paired fit、saved checker、load/fallback実費用、offline回収、3図、full suites、DML/標準高速器採用は本レビュー外。exact Bates/PIDE/roughの検証を主張しない。
