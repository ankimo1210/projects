# Task 5 actual N1024 teacher precision preflight

## 結果

原18状態×2モデルの36 slotsを保持。35 slotsについてCE・β=1 control価格と同CRNのspot/state中央差分を計算し、1 slotは保存済みHeston fitがunknown/ill_conditionedのため未実行。全36 slotsのqualificationはunknown。

価格SE≤0.03: **18/36**、同一16blockのhS SE≤0.002: **10/36**、hQ SE≤0.005: **9/36**。3条件同時は **6/36**。標準誤差のみの診断で、数値精度を保証する合格ではない。

| モデル | 実行/元slots | 価格SE | hS SE | hQ SE | 3条件同時 |
|---|---:|---:|---:|---:|---:|
| heston | 17/18 | 7 | 5 | 4 | 3 |
| local | 18/18 | 11 | 5 | 5 | 3 |

初期(t=0)のCV価格SEはHeston 0.082–0.087、local 0.041–0.062で0.03を上回る。全ready状態の最大値は以下。

| モデル | CV価格SE最大 | hS 16block SE最大 | hQ 16block SE最大 |
|---|---:|---:|---:|
| heston | 0.0958202 (state05.heston) | 0.032804 (state08.heston) | 0.0411479 (state06.heston) |
| local | 0.0623645 (state02.local) | 0.0123385 (state02.local) | 0.0235461 (state03.local) |

## 未確定・保存境界

- underresolved 5 slots: state09.heston, state09.local, state12.heston, state12.local, state15.local。小さいSEを合格扱いしない。
- 未実行: state15.heston (t=11/12, S=80, 保存fit unknown/ill_conditioned)。latent varianceを代用しない。
- 同一モデル内でoriginal IID 1024×768×2 driverを全状態・4bumpに共用。Heston/localはcandidateの別seedで、モデル横断CRNを主張しない。
- 月次12 fixings、6 selected dates、A=100×既決定fixings数を固定、spot bump毎にthreshold=(1200-A)/Sと価格係数DS/12を再計算。
- saved current call CS/Cthetaを固定してhQ=Vtheta/Ctheta、hS=VS-CS*hQ。原1024標本・同16block covarianceを保存。
- この実験は直接の教師中央差分。production cubic cache微分とは別の推定量。
- bump bias、SDE格子、call分母/spot Greek誤差、独立Asian oracle、teacher補間誤差は未測定のままunknown。正式pilot・NN main・精度達成の承認なし。

## 費用・照合

- 35×(base+4bump)=175 calls、82,247,680 path steps。Nを増加せず、各callは1e9 path steps未満。
- 子プロセス全体 wall 45.117s、CPU 45.063s（起動・import・checkpoint・保存を含む）。
- raw配列 240,626,504 B /上限268,435,456 B、圧縮NPZ 48,764,846 B。プロセスpeak RSSは未測定。
- saved-only全175call replay PASS: 原N、compact uint8 status、global/slice ID・時間map、threshold・価格、CRN derivative・IFT、16block covariance/SEを許容誤差つきで照合。
- source/input 65 bindingsは開始→終了→照合時すべて不変。金融値にはSHA一致を使わず、SHAはprovenanceに限定。

## 原36 slots

| slot | t | S | status | CV価格SE | hS SE | hQ SE |
|---|---:|---:|---|---:|---:|---:|
| state00.heston | 0 | 99.95 | ready | 0.0852813 | 0.0311692 | 0.0347233 |
| state00.local | 0 | 99.95 | ready | 0.0412134 | 0.00842722 | 0.00930276 |
| state01.heston | 0 | 100 | ready | 0.0823702 | 0.0208898 | 0.0255279 |
| state01.local | 0 | 100 | ready | 0.0486206 | 0.00965998 | 0.00952352 |
| state02.heston | 0 | 100.05 | ready | 0.0868263 | 0.0174614 | 0.0210507 |
| state02.local | 0 | 100.05 | ready | 0.0623645 | 0.0123385 | 0.0103108 |
| state03.heston | 0.0833333 | 80 | ready | 0.0214982 | 0.00167444 | 0.028845 |
| state03.local | 0.0833333 | 80 | ready | 0.0189628 | 0.00175449 | 0.0235461 |
| state04.heston | 0.0833333 | 100 | ready | 0.0677652 | 0.0153872 | 0.0203905 |
| state04.local | 0.0833333 | 100 | ready | 0.0402187 | 0.0104686 | 0.00711554 |
| state05.heston | 0.0833333 | 120 | ready | 0.0958202 | 0.0238185 | 0.0270522 |
| state05.local | 0.0833333 | 120 | ready | 0.0285591 | 0.0122208 | 0.0120823 |
| state06.heston | 0.25 | 80 | ready | 0.0109277 | 0.00108928 | 0.0411479 |
| state06.local | 0.25 | 80 | ready | 0.006632 | 0.000515405 | 0.0149326 |
| state07.heston | 0.25 | 100 | ready | 0.0472812 | 0.015795 | 0.0198371 |
| state07.local | 0.25 | 100 | ready | 0.0229786 | 0.00718787 | 0.00628515 |
| state08.heston | 0.25 | 120 | ready | 0.0676701 | 0.032804 | 0.0353124 |
| state08.local | 0.25 | 120 | ready | 0.0197268 | 0.0091298 | 0.0072085 |
| state09.heston | 0.5 | 80 | unknown_underresolved | 1.0305e-18 | 1.3997e-20 | 0 |
| state09.local | 0.5 | 80 | unknown_underresolved | 3.66097e-19 | 3.49925e-21 | 8.95807e-19 |
| state10.heston | 0.5 | 100 | ready | 0.0211937 | 0.00481979 | 0.00720552 |
| state10.local | 0.5 | 100 | ready | 0.00969262 | 0.00258202 | 0.00303592 |
| state11.heston | 0.5 | 120 | ready | 0.0322225 | 0.0131294 | 0.0138233 |
| state11.local | 0.5 | 120 | ready | 0.0116643 | 0.00648097 | 0.00546642 |
| state12.heston | 0.75 | 80 | unknown_underresolved | 5.72027e-21 | 0 | 0 |
| state12.local | 0.75 | 80 | unknown_underresolved | 1.3771e-21 | 0 | 2.7994e-20 |
| state13.heston | 0.75 | 100 | ready | 0.00810197 | 0.00150361 | 0.00194649 |
| state13.local | 0.75 | 100 | ready | 0.00279798 | 0.000493282 | 0.000882998 |
| state14.heston | 0.75 | 120 | ready | 0.0114734 | 0.00465618 | 0.00463879 |
| state14.local | 0.75 | 120 | ready | 0.00457728 | 0.00235564 | 0.00207877 |
| state15.heston | 0.916667 | 80 | not executed: ill_conditioned | — | — | — |
| state15.local | 0.916667 | 80 | unknown_underresolved | 3.49137e-25 | 1.33486e-26 | 1.64027e-22 |
| state16.heston | 0.916667 | 100 | ready | 0.00147202 | 0.000288457 | 0.000146504 |
| state16.local | 0.916667 | 100 | ready | 0.000555888 | 0.00010264 | 0.000211603 |
| state17.heston | 0.916667 | 120 | ready | 0.0023234 | 0.00175673 | 0.00170279 |
| state17.local | 0.916667 | 120 | ready | 0.00121306 | 0.00100133 | 0.000943905 |

## 次の判断

現行N1024のまま精度を確定する条件は満たさない。教師の価格・ポジションSEとunderresolved tailを先に調整する必要がある。この実験では追加Nを実行せず、正式pilotへ進める判断は親セッションで行う。
