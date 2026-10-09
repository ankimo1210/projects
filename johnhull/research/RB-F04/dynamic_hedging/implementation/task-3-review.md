# Task 3 独立ソースレビュー — 2026-10-09

仕様適合: 修正必要。品質: 修正必要。Task5へのソース承認: 保留。
Critical 0 / Important 2 / Minor 0。正式pilot・freeze・main・性能は未承認。

対象はTask3所有3ファイル、brief/report/review diff/source manifest、DESIGN §§3/5/6/7/11。AGENTSを確認した。ソース・テスト・Gitは変更せず、このレビュー2ファイルだけを書いた。原manifestは初回読取時に現物と一致した。17 owned tests GREEN、scoped103new + index/docguards1191 PASS、11 Python ruff/format PASSは受領証拠として扱い、suiteは再実行しない。

レビュー中にreference/testsが並行修正されたため、判定は原checkpointに固定する。原SHA256と最新観測SHA256はJSONに分けて記録した。現在のrevision全体の承認を推定しない。

## Important I1: 独立MCのxi=0が承認済みschemeと異なる

原 reference_methods.py:227–239 はxi=0でもLamperti implicit式を使う。DESIGN §4.1と承認済み _dynamic_hedging_core.py:23–24 は確定的CIR厳密遷移 theta+(v-theta)*exp(-kappa*dt) を要求する。v≠thetaでは次のstock incrementの旧varianceが異なり、direct priceとstate bumpが別のschemeになる。

独立小確認: N32、seed17、t=[11/12,23/24,1]、fixing index2、xi0、v=.08、theta=.04、kappa2。同じnormalから手計算した厳密分散遷移とのpayoff差は最大0.0007566006603276776、平均0.0000939315901748633。元N32は保持されたが、参照はmeasuredを返した。原 test_dynamic_hedging_surfaces.py:262–289 はv=thetaのGBM fixtureであり、この差を検出しない（state Greekも照合しない）。

修正: 独立のexact xi=0 branchと、v≠thetaでstock incrementを2回以上含む同一driverのprice/state-bump検証。レビュー終了前の並行revisionではxi0のexact branch追加を視認したが、原probeを再実行しておらず、本報告では解決判定しない。

## Important I2: adaptive CF未収束・積分誤差が保存されない

原 reference_methods.py:557–559 は両quadの値だけを取り、誤差推定・収束情報を捨てる。selected_call_refinement:142–151 は有限値だけからmeasuredとし、refinement差だけをerrorとする。DESIGN §§4.3/7.5/11は未収束参照を一致と数えず、reference uncertainty/failureを保存するよう要求する。

小確認: 通常candidateのK100/残存.75でquadrature_limit=1は有限価格7.848537617463641を返し、外側でcaptureしたIntegrationWarningは2件（最大分割数到達）。メモリ上だけでlimit1を強制したselected helperでもwarning78件に対してstatus=measured、積分誤差・収束fieldなし。価格refinement差.041906467765087996はこのcaseの価格gateを落とせるが、収束情報欠落を解消しない。fault injectionはファイルを変更していない。

修正: P1/P2ごとのadaptive error/convergence/configuration receiptを保存し、未収束・失敗をselected resultへ伝播する。通貨単位の積分誤差とGreek uncertaintyをcutoff/grid/finite-width差と分けて保存する。将来pilotは今回のsource defectを免除しない。

## 確認した仕様

- Heston callはcurrent S/vと残存1.25−t。localは絶対calendar coefficientを使い、ellごとに1回のsparse CN/Rannacher後退で正確なsnapshot endpointを保存する。
- 価格と全導関数は同じnot-a-knot tensor cubic。各axisは4nodes以上、日時補間なし。rootは全piece/extremaから列挙し、複数root・bound・無root・低J・独立delta-J・残差を理由付きunknownにする。
- local f_zのspot chainとlog-ell→ellの除算は各1回。production t0は専用sheet/supportを使う。
- Task2 groupは共通N（16倍数）/共有driverを検査する。CVの共有16 cluster blockをmeanと同じprice/derivative/chain operatorへ通し、mean covarianceはblock sample covariance/16。primitive/statusは原本dictionaryに保持する。
- batch root/extrema/covarianceは数値配列とNaN padding、statusは文字配列でobject arraysを作らない。raw failure/boundsはunknownとなり、clip/nearest/hold/zero repairは見つからなかった。
- 参照は別CF/adaptive integral、別banded PDE、CE/controlを使わない独自direct MC。原N/個票/SE/covarianceは保持する。

## 統合事項・未判定

fit_quote_state:551–554,582–585 のcall/Asian支持域交差はcallerがasian_state_boundsを付ける契約で、未設定時はcall-only。Task5 callerはモデル/cache revisionごとに交差を必ず設定し、欠落・不正boundsを拒否する必要がある。後段Asianがunknownを返すだけで共通支持のfitを満たしたと扱わない。

build_call_cache:237–245 はprice/derivative errorをNaN、reference_statusをunmeasuredと明記する。evaluate_call:283–285、evaluate_asian:539–544、fit_quote_state:637–654 のokは補間/solver可用性で、精度適格性ではない。fitのdelta-J gateはerrorがfiniteの場合だけ働く。Task5はokだけで資格判定せず、独立参照の収束・finite error・grid/finite-width・F07比への伝播と固定閾値を明示的に検査する。未測定状態は明示されており追加source blockerとはしないが、この統合guardは必須。

18-state正式pilot、実grid/grid doubling、N/SDE refinement、Q/P&L gate、Task5 artifact再検算、dictionary/tupleを含むcache serialization/replay、source/protocol/pilot freeze、main、runtime/memory、モデル/NN性能は未判定。将来gateで今回のsource defectを免除しない。並行修正revisionは別fix reviewで確認する。
