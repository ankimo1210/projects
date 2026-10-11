# #10 多曲線正式設計候補 — 独立設計レビュー v1

2026-10-11。Reviewer: multicurve_design_review。判定: **設計と工程の完成契約として承認。Critical 0 / Important 0 / Minor 1。** この判定はsource、資源prior、金融結果、pilot/main launch、研究受入の承認ではない。

対象:
- multicurve-formal-design-candidate-v1.md: SHA256 c4cb01211d607c8dad81798f425f654004a98a655b917d88bccc828e9c9a570f
- multicurve-formal-plan-candidate-v1.md: SHA256 bf7f6b67d5ad247d21e707b655e9e7b27a1c228c2915705643a48a2881f53b66

正本RESEARCH/README、既存の初回・v2再レビュー、保存された4quote spikeの範囲を読んで突合した。source85、保存検算85801、既存docs、Git、CASは変更していない。金融計算、RNG、solver、MC、pytest、ruff、spike再実行は行っていない。変更はこのレビューと対応decision JSONだけ。最初の文書生成用JavaScriptは引用符構文で解析前に失敗し、ホストcommand・書込み・金融処理は実行されていない。修正後にこの2ファイルを保存した。

## Abstract forward anchors — 元範囲の不当な置換はない

原RESEARCH §9は、P3の0×3m/3×6m term-end forward、P6の0×6m forward anchorを候補にしている。初回独立レビューの「計画へ引き継ぐ要件」は、0-start anchorについて **未reset条件またはabstract forward quoteである条件を固定**することを明示している。今回design 40–43行/plan 91・114行は後者を選び、D/P3/P6各4node、全12quote、元商品の年限とbasis依存を保持する。

abstractのforward ratioを、既に公開された実resetに対する市場感応度として扱っていない。dated actual-reset validationに既知fixingのzero-J、公表前後、公開後必須欠損の拒否を残し、known rowを主較正に残す誤器も検出する。held seasoned IRSやpartial-known OISをabstractに置き換えていない。これは既存レビューが認めた合成クオート定義の具体化であり、12quoteを小問題へ縮める変更ではない。

文書照合は実scheduleの12×12 rankを証明しない。Task1の全resolved date/quote/fixing表とTask2/5のactual coverage/J/scaled rankが必要。主結果・教材にもabstractとdated実resetの区別を保持し、実在する市場商品への検証済みラベルは付けない。

## Roll・fixing・表現移行・市場 — 既存I1の修正を保持

design §5 / plan Task4は、Vr（旧absolute knotsのexact ratio roll）、Vf（同じrolled evaluator＋実fixing）、Vg（t1新表現）、V1（同じt1表現＋新quote）を分離する。C0/Cfを同じ指定担保口座でt1へ累積し、四項の和がV1−V0+Cfへtelescopingする定義は整合する。

qg=m_t1(theta_g,fixings_t1)をmarket centerとし、q1=qgでもVg−Vfが残る元反例を必須にした。固定tenor再較正をexact rollと同一視していない。horizon/rank不足、ex-payment cash一回計上、publication/reset/payment/expiryの離散変更も保持されている。支持内のexact主ケースと一般regrid対照を分ける設計は既存v2承認と一致する。

## 二次市場クオートリスク — 全範囲を保持

design §4 / plan Task3のA=−J^{-1}Fq、随伴、直接Vq、second IFTのFθθ/Fθq/Fqq、priceのVθθ/Vθq/VqqとVθ·theta''は整合する。D→P3→P6の下三角非対角blockを保存する。12 diagonal＋66 mixedから全144要素を得る構成は、D–P3/D–P6/P3–P6各16要素と対称側を欠落させない。

固定curve gammaをAのみでsandwichする誤器、diagonal-only、隣接curve freeze、basis符号、coupon reset等を維持している。quote/PV residual、zero/logDF同一kernel座標、単位bp/bp²、同じproblem permutationを区別している。LS/GN/KKTは主exact較正へ混ぜず、式・負例の範囲を保つ。

## 完成契約の照合

| 要件 | 候補箇所と評価 |
|---|---|
| 原D/P3/P6各4node・12quote | design §3.1、plan Task1/2。維持。実日付/rank未測定を明記 |
| 元全商品・immutable保有条件 | design §3.2、plan Task1/4。bond/discount bond、forward IRS、seasoned IRS、FRA、basis、partial-known RFR、amortizingまたはstubを保持 |
| 元市場shape・±shock・stress・wrong controls10種 | design §6、plan Task1/5。分母とfailed/unknownを保持。全数値vectors/組合せ/件数はpilot前protocolへ固定 |
| 全144H・全cross-block・直接/二次較正response | design §4、plan Task3。維持。mixed bump h-sweep安定域無しはunverified |
| 日付、公表、known fixing、RFR3規約 | design §3.2、plan Task1/2/4。観測日と公表timestampを分け、既知をbump中固定。Decimal/date-table oracleを保持 |
| 独立参照 | design §4、plan Task2/3。独自schedule/CF/sequential brent、絡むstressの別simultaneous root、再較正mixed bumpを予定。main helperの共有は禁止 |
| 四項bridgeとzero-move反例 | design §5、plan Task4。既存I1解決を保持。Vg/qgがmarket center |
| 誤差・悪化・zero denominator | design §6、plan Task3/5/6。R1/R2全結果、degenerateの元方向、economic floor、undefined ratio、失敗を保持 |
| 全raw/attempt/status/source/unknown末尾 | design §7、plan Task5/6。case単位保存、全planned IDと元primitiveを検算。SHAを数値合否へ代用しない |
| whole-path費用・資源・alias | design §8、plan Task5/6。cold/warm、較正/微分/CF/IO/check/restore、wall/CPU/RSS/call countsを分け、inclusive重複加算を避ける。300/1800秒は未承認行政cap |
| savedとfresh独立context | design §7、plan Task6。全planned数値の再算出、事前fresh roster、新演算、warm memoを共有しない |
| C/F両復元 | design §7、plan Task6。各store別rootへ復元し元root不存在で全数値・費用checker、容量占有を個別確認 |
| 改変検知 | plan Task5/6。末尾/quote/fixing/CF/H/bridge/expense/source/shape/physical descriptorを個別確認 |
| 教材と採否 | design §7、plan Task7。3必須図、artifact-only fresh実行/PNG目視、支持範囲・全失敗・分母・速度不採用も明記 |
| phase最終検証・台帳/roadmap | plan Task7。対象回帰/index/docstrings、phase全suite、release/台帳不変、正本状態更新。本編306節を増やさない |
| 実施順と研究同時数 | design §8、plan status/global。#9採否記録後の#10実装・計測、同時研究1本を維持 |

各行は文書上の完成契約の照合であり、未実施の実証gateをPASSにしたものではない。fixture・source・formal result・保存検算・fresh・復元・教材は将来工程。

## Minor M1 — 24quote scalingのH出力と参照コストを明示する

design 83/106/139行、plan 127/164/166/170行。289再較正/hは12quote全Hに対して正しい（1+2×12+4×66）。24quote scalingは保持されているが、Task3の参照件数をそのまま使うと24quoteの費用が過少計数されるおそれがある。

Task5でoutput countsを固定する既存要件へ、**24quote full Hなら576要素、276混合組、1+48+4×276=1153再較正/h**を明示すること。商品1/10/100ではsnapshotの較正/因子分解共有数と商品PV評価数を分ける。directional-only scalingを追加するなら別output familyとして保存し、full-Hと同じ速度比分母にしない。実装前protocol/prior freezeまでに必要な具体化であり、設計候補の承認を止める問題ではない。数値計算はせず、列挙式を照合した。

## 一次資料と限界

既存M1/M2/M5/M7/M8の確認範囲を再利用した。今回追加でM3の公式[JacobianCalibrationMatrix](https://strata.opengamma.io/apidocs/com/opengamma/strata/market/curve/JacobianCalibrationMatrix.html)と[MarketQuoteSensitivityCalculator](https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculator.html)の本文を確認し、Jacobianの向きdtheta/dq、curve order、parameterからmarket quoteへの変換という限定的根拠を再確認した。Java実行・Strata数値一致・外部市場較正を証明していない。

M4/M6の未取得本文、最新市場規約、公表時刻、licensed data、商用market fixtureへの追加主張はしていない。数学式は候補の直接導出を読み、既存初回独立レビューとの整合を照合した。実測precision、全12quote rank、容量、所要時間、実金融改善は未検証。

## 残る実施前ゲート

1. 全quote/node/truth/保有商品/日付/fixing/fresh/scaling入力・件数を具体化し、abstractと実resetのtyped区別を固定。
2. 実coverage/J/rank、独立source数学、全H h-sweep精度、t1表現/担保cash policyをTask1–5で検証。
3. 元最大geometryとwhole-path事前資源priorを独立判断。M1の24quote output/call countsを固定。
4. #9終了条件と研究同時数を守り、別の実launch判断を経てpilot/main/fresh/check/両復元/教材へ進む。
5. 全予定結果・原費用・採否を揃えた最終研究レビューで初めて研究完了を判断する。

**権限境界:** approved_design_contract_only。formal source implementation、resource budget prior、pilot/main launch、numerical study acceptance、phase/main integration、capacity/runtime guaranteeは全てfalse。元研究の金融scopeを減らす承認ではない。

