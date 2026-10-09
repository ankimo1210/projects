# Actual-field call preflight

2026-10-09。**原18状態を保持した事前測定。正式pilot・teacher/position/P&L/Q精度の承認ではない。**

| 項目 | 修正前 | 修正後 |
|---|---:|---:|
| local空間格子（time960は共通） | 601 | 1201 |
| local basecallと独立2401space/1920timeの最大価格差 | 0.0014499733 | 0.0002912485 |
| Heston65spot×33v splineと独立CFの最大差 | 0.00000792075 | 同左 |
| 原状態・Heston fit unknown | 18・1 | 18・1 |
| 計算wall（import/final archive外） | 8.820928秒 | 12.480462秒 |

実fieldはinitial-quotesの257×321、T1.25。6datesは0,1/12,.25,.5,.75,11/12、3scenariosは設計に固定したS/v。全call state軸を使い、精度未測定をqualifiedへ変更しない。独立PDE比較は倍率1の価格であり、全倍率のGreek・較正後状態誤差を保証しない。

[jacobian.json](jacobian.json)では独立CFの3幅central bump・原積分receiptを保存。t11/12/S80/v.02のCv=0.30937758056、1cent/(.04*Cv)=0.808074>.25。この識別失敗は格子細分化で消えず、原18状態から除外しない。main未開封。criterionの緩和を行っていない。

[before](before/selected-calls.json)・[refined](refined/selected-calls.json)・実probe source/outputを完全保存。NPZはGit外、両保管庫の[manifest](evidence-manifest.json)/[復元](recovery.json)で参照。復元bytesの一致だけを金融semantic PASSとは扱わない。

canonical金融source `_dynamic_hedging_surfaces` の1201変更は独立BlackのlateATM反例でRED→GREEN。以前のsource checkpointは当時のSHAを保ち、現在sourceの承認は新checkpointで別に示す。
