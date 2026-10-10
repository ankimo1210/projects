# 教師専用保存表現：数学・整合性の独立検討

更新：2026-10-10T03:41:51.340052+00:00
範囲：保存設計の静的確認のみ。source/tests/Git/solver/RNG/全suite/追加agentの変更・実行なし。

## 結論

**全Nの原primitivesとthresholdsを保持し、教師専用readerで10種類の個票を再生成する表現は、現在の数式上は実現可能。** 省略してよいのは明示した派生個票の「保存上の重複」であり、原N・case・失敗・返却payloadの範囲を減らすことではない。

以下の条件を満たす実装・限定検証が必要。現時点で実装、金融範囲の変更、金融資格、formal lockを承認するメモではない。容量・最小実装案は別担当の調査対象。

## 1. 現sourceの復元式と必須入力

DESIGN §7.2–7.4、Task 2、および primitive_labels の定義では、各元path i、threshold x_jについて、

\[
L_i=b_i+c_i e^{\mu_i+\sigma_i z_i},\qquad
A_i=m e^{a_i+\lambda z_i},
\]

ここで z_i=last_z、a_i=aux_logG_prefix、lambda=aux_last_loading、m=len(fixing_delays)。
同じ最後のstock Zをmodel/aux双方に使う。

\[
R_{ij}=(L_i-x_j)^+,\quad
C_{ij}=E[(L_i-x_j)^+\mid b_i,c_i,\mu_i,\sigma_i],\quad
U_{ij}=E[(A_i-x_j)^+\mid a_i,\lambda],
\]

\[
W_{ij}=C_{ij}-U_{ij}+K_j,\qquad
K_j=E[(mG_{\rm GBM}-x_j)^+].
\]

KはHeston/local自身のgeometric価格ではなく、control_variance・残存月次fixing_delays・r−qで決まる別auxiliary GBMの解析平均。β=1固定。raw_xは −1{L>x}、conditioned_xはconditional_tailのordinary threshold微分、CV_xは同じ価格の差の微分。

### 10 distinct標本とalias

| 保存label名 | 復元対象 |
|---|---|
| raw_samples | R |
| conditioned_samples | C |
| cv_samples | exact branch適用後のW |
| f_x_samples | exact branch適用後のW_x |
| raw_x_samples | raw threshold微分、invalid pathはNaN |
| conditioned_x_samples | conditioned threshold微分、invalid pathはNaN |
| unreplaced_cv_samples | exact branch適用前のW |
| unreplaced_cv_x_samples | exact branch適用前のW_x |
| aux_raw_samples | (A−x)+ |
| aux_conditioned_samples | U |

全てshape(N,K)、K=元threshold数。f_samplesはcv_samplesと同じ値を返すaliasで、11番目の独立推定量ではない。読込後のPython object identity/shared-memoryは金融契約ではなく、値・shape・keyを守る。

x≤0かつ全path validなら主cv_samples/f_x_samplesはexact Q linear値へ置換される。置換前CVは別保存名で残る。invalid original pathがあるとexact branchで救済しない。m=0、threshold=0のatom、unknown_underresolved、all-zero/SE0も現分岐をそのまま復元する。負CV個票はclipしない。

### 6成分だけの保存では不足

DESIGN §7.4の短い列挙はCE/CVの要約であり、全raw/Greek/監査payloadを保持するための削除リストではない。

- **raw個票にはlast_zが必須**。これを消すと同じ(b,c,mu,sigma)でも元raw payoffが決まらない。
- 全path配列：b/c/mu/sigma/last_z、last_left_spot/last_left_variance/last_left_coefficient、aux_logG_prefix、path_mask、primitive_status、failure_reasons、local_step_statusを元Nで残す。
- compact statusならuint8 codesとlocal_step_status_labels/encodingを一緒に残し、dictionaryの意味・全step範囲を保持。
- scalars/metadata：model、spot/state、memory_count/total_fixings、calendar_times/fixing_indices/fixing_delays/expiry_delay、rate/dividend_yield、control_variance/control_status/aux_first_midpoint/aux_last_loading、analytic_conditional/deterministic_model、f_units、N/original_path_count、shared_driver_id/scope。
- teacher外包も保存対象：全path_ids/cluster_ids、seed、restart、chunks/driver_mapping/global_driver_id/stream_identity、driver参照と由来、thresholds/date_index、source・raw receipt・expense・qualification。
- primitive_labelsはslice driver IDを引き継ぐが、run_teacher_jobはlabelのshared_driver_idを**global_driver_idへ上書き**しdate_indexを付ける。専用recipeはこの2つの既存metadata操作も明示して原返却payloadを戻す。slice IDをglobal IDへ混同しない。

## 2. 原N・16block・共分散・Greekを保つ条件

- 各nodeの分母は元N。Nprefix1024/4096/16384/65536、coarse/high、全date/state/spot/threshold/caseの範囲は不変。表現を変えてdomain外や未qualified nodeを消さない。
- 全chunkを元path順にmergeしてからprimitive_labels(..., blocks=16)を1つの元Nに適用。chunk毎のlabel平均や成功pathのみの再標本化を使わない。
- cluster_idsはfloor(path_id/(N/16))。全node・date・modelで元shared-driver CRN対応を保ち、path順の並べ替えも拒否する。
- block_mean M_bのmean-estimator covarianceは
  \[
  \widehat{\mathrm{Cov}}(\bar Y)=
  \frac{1}{16\cdot15}\sum_{b=1}^{16}(M_b-\bar M)(M_b-\bar M)^\top .
  \]
  price(raw/conditioned/CV)とthreshold derivativeのflatten順、joint_orderとjoint covarianceを保持。individual SE=sample SD/sqrt(N)とblock covariance対角の平方根は別推定量で、有限標本で完全一致を要求しない。
- 小さい原summaryを独立に保存：f/f_x/f_se/f_x_se、status/status_reasons、aux_mean/aux_mean_x、component_order/means/se、derivative_component_means/se、blocks/block_path_count、block_means/block_covariance、f_x_block_means、derivative_block_means/covariance、joint_block_means/covariance/joint_order、path_maskと全label metadata。readerがこれらを再計算値で上書きしてからcheckする方式は不可。
- 各nodeの同じ16block曲線へ固定not-a-knot tensor operatorを適用する現cache境界を維持。単一nodeの周辺varianceだけではcross-node risk covarianceを復元できない。
- HestonのV_S=D(f−xf_x)/12、localのV_S=D(f+f_z−xf_x)/12、V_v=DSf_v/12、V_ell=DSf_w/(12ell)を同じsmooth価格面から作る。threshold derivative標本をstate Greekやlocal f_zの代用品にしない。call denominatorの独立deterministic精度は別問題のまま。

**反例（実行していない解析例）**：16blockでnode1のM_b=b、node2をM_b=bから17−bへ並べ替えると、両nodeのmean/varianceは同じでもcross-node covarianceの符号が反転する。周辺means/SEだけの保存・検査は不十分。primitives・元path順・共用cluster対応が必要。

## 3. writer / read / check の境界

| 境界 | 必要条件 |
|---|---|
| writer前 | 完了teacher、全N primitives・thresholds・原returned labelsが存在する場合だけ専用表現を選ぶ。元dictを破壊的変更しない |
| writer照合 | 全10distinct個票＋alias・全summary・metadata・NaN/inf位置・status・shapeを原returned payloadと再計算payloadでapprox照合してから明示whitelistだけを省略。meansだけの照合では不足 |
| 永続化 | 小さい原summaryと全primitive/外包をnative immutable JSON/NPZ/receiptで保存。新しい教師専用schema/version、固定recipe ID、対象key/shape/dtype、source/driver/threshold/原N由来をbind。一般encoder/APIを変更しない |
| reader | native receipt/parts/shape/dtype/coverageを検査後、固定recipeだけを呼び、全N×Kの個票を全て戻す。arbitrary callable/eval、動的import、欠落keyの既定値補充は禁止 |
| reader数値境界 | 保存した原summary/status/16blocks/covarianceに再生成結果をapprox照合。数値をSHA一致で合否判定しない。返却payloadは旧teacher rawの全key/全個票サイズを保持 |
| teacher checker | replay_teacherによるcalendar/last-left law/flags/control/failure mask検査を残す。driverがある場合のsaved-driver SDE→primitive検査も落とさない。単なるprimitive_labels再実行を前段SDE検証と呼ばない |
| grid/selector/resume | 原node roster・producer source・principal/reference/next/grid purpose・driver/N・receipt prior bindingを保持し、missing/capを成功へ昇格しない。旧full-array teacherも読める境界を残す |
| qualification/費用 | 収納形式は金融資格を上げない。reconstruction/load/savedcheck/serializationの測定費用とRSSを別に記録し、元worker・失敗・overrunの費用を保持 |

### reader自己一致だけでは足りない

readerが再生成したlabelsをcheckerが同じprimitive_labelsで再生成して一致させるだけでは、writerが誤った派生個票を削除したことを検出できない。writerの**原returned全個票との照合**と、readerの**独立に保存された原summaryとの照合**の両方が必要。

また、receiptを自己申告で全部作り直すだけでは、別teacherへの全入力差し替えを防げない。正式priorのsource/input/producer/driver/threshold/N/receipt bindingへ照合する境界が必要。金融approx合否と由来認証を分離する。

### 現digest消費者との整合は具体的な未実装条件

現run_teacher_grid_jobはraw全payloadのpayload_digestをnodes.raw_sha256に保存し、check_teacher_grid_recordは読込後のrawを再hashする。selectorにもinput_identity(raw)の結合がある。

数式から再生成したfloat値は許容差内で同じでも、実行環境/NumPy/SciPy変更による微小差で全payload SHAが変わり得る。**新表現を一般read_pilot_artifactへ足すだけで既存の由来境界も自動的に成立するとは言えない。**

最小実装候補でも、teacher専用のstored-origin receiptを既存producer/node/selector priorへ結合する方法、旧raw provenanceとの関係、再構成値のapprox照合を明示する必要がある。reader出力を再hashすることで金融floatのビット一致を要求する回避策は不可。一方、残してあるorigin stampを無条件に信頼して由来照合を省くのも不可。これを全encoderの一般refactorへ広げない。

## 4. unknown/failure を落とさない

- invalid1pathでも元Nを維持。全微分channelの当該行NaN、主status=unknown_invalid_primitives、mean/SE/block/joint未知性を現定義どおり保持。nanmean/nan_to_num/drop/filterによる救済は禁止。
- atom/underresolved/nonfinite、原負CV、linear/settledの非必須statusは別々に保持。stored statusやprimitive flagsをreadyへ書き換えない。
- failed_at_declared_cap / unclosed_source_or_solver_defect / unused / inspection / inherited-cap等では、完成primitives/labelsがない記録を専用replay表現へ通さない。元raw_chunks/failed_driver/executed IDs/unexecuted count/path_status/cap evidence/reason/expensesを従来のnative表現で残す。
- partial primitiveを少ないNでlabel化して元fullN teacherに戻すこと、未実行pathを0またはgenerated値で埋めることは禁止。数値NaN配列を構成しても「未実行」の元statusと分母を置き換えない。
- 外部driverとfieldを削除しない。共有CAS参照の保持とduplicate bytesの回避は可能だが、失敗chunk・global/slice source identity・saved-driver checkerの対象は維持する。

## 5. 拒否が必要な悪変形・tamper（将来の限定検証要件）

これは実行済みテスト結果ではなく、実装時の必要反例。

1. recipe/version/source identityの変更、未知recipe、dynamic callable、旧schemaを新schemaと偽る。
2. primitive field1つ欠落、last_zを省略/別streamへ差し替え、path配列のtruncate/重複/reorder、N/path_count/16cluster分母の変更。
3. thresholds削減/並替え/別dateのthreshold、model/state/spot/calendar/fixing/memory/global・slice driver/seed/purpose差し替え。metadataを自己整合に変更してもprior bindingで拒否。
4. left-stateとmu/sigma/cの整合性破壊、aux loading/variance/known mean/calendar変更、analytic/deterministic flag偽装。primitive replayで拒否。
5. invalid pathをvalidに変更、NaN→0、失敗理由/step-status辞書を欠落、未知code、cap/source-defectをcomplete化。
6. writer入力のraw/cond/CV/Greek個票を1値変更、threshold列の交換、unreplaced CVをprimary CVで置換、負CVをclip。全個票のwriter approx照合で拒否。
7. 保存summary/status/16block/joint covarianceの変更、marginal mean/SEを保つpath並替え、node間CRN mapping変更。
8. f_samples aliasの値/shape不一致、local f_zを捨てるcache縮小、domain外・未qualified case削除。
9. receipt byte tamper、dtype float64→float32量子化、shape偽装、parts gap/overlap/reorder/extra/unreferenced arrays、欠けたpack、既存immutable directory上書き。
10. reader復元由来と原producer raw bindingの不一致、旧全array payloadとの全key/summary差異、未知金融資格/未測定費用をready/0へ置き換える。

比較はshape/key/元分母/status/NaN・inf位置をまず確認し、有限金融値を既存許容差付き比較へ渡す。NaN同士は同一未知性として扱い、NaNとfinite・+infと−infの交換は拒否。SHAは保存bytes/source/inputs/driver/receiptの由来だけに使う。

## 6. 判断と未検証

- DESIGN §7／Task 2の数学要件には条件付きで沿う。これは「10個票を捨てる」承認ではなく、「同じ全Nの10個票を必ず復元する教師専用保存表現」の必要条件。
- 実装・native roundtrip・悪変形拒否・旧payload互換・新storage-originとselector/resumeの結合は未検証。
- 新金融実行・saved solver replay・RNG・全suiteを行っていない。数学式と現sourceを静的に照合しただけで、金融accuracy/格子収束/全case qualificationはunknown。
- 最初のrg読込はPowerShell→bash引用に失敗し、Python subprocess argvで読み直した。sourceの問題ではない。読込・メモ作成の費用は未測定unknown。

## 参照した固定source

- johnhull/research/RB-F04/dynamic_hedging/DESIGN.md: SHA256 8fbef30a824aa0b4e4153ad0e559255a6fe77b102d8fde223adb25f6138248ce
- johnhull/hullkit/src/hullkit/_dynamic_hedging_conditional.py: SHA256 9007e30a45375fbb7c8b4afe5fa4e4f694b5bc68e924b138bd993d8bdbf2b025
- johnhull/research/RB-F04/dynamic_hedging/run_pilot.py: SHA256 4e4765f4bc7ae1cc0a7020fa3bb1fab1ad4eabec4e89fca511589cd5a799b829
- johnhull/research/RB-F04/dynamic_hedging/check_pilot.py: SHA256 a36e691498a92a4e7ee13deb1f7a2f51e25b511e760ca7150fe814a83cb7f5a7
- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_replay.py: SHA256 cb6aa06426f93705cf5613c57e8966fc7d8b0395d33e990abc95c7fe8b18a12b
