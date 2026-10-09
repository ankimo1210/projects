# RB-F08：MLMC・RQMCの誤差と費用

更新日：2026-10-09。状態：実装中（candidate、主実験未実施）。

## 目的・範囲

GBM Euler欧州callの粗細結合と固定pilot配分について、bias・sampling誤差・総費用を分離する。
厳密終端plain/CVとBSMを比較器に保持する。別系列の独立scramble RQMCでは、Student近似区間の被覆率と幅を調べる。
速さやNNの勝利を研究完了の条件にしない。外部データ・公開API変更・新しいproduction依存はない。

## 実施順序

1. private粗細pair・MLMC統計、独立scramble CI、独立Black/Euler/clip参照とseed台帳。
2. 全候補pilot、isolated費用計測、独立pilotレビュー。全主条件・配分・seedをfreeze。
3. Euler系列256反復／予算、RQMC全18cell各512反復。失敗cellも保持。
4. 保存配列からの再検算、fresh再生、artifact-only4図、独立最終レビュー、採否、main統合。

[実施計画](../../docs/superpowers/plans/2026-10-09-mlmc-rqmc-ci.md)が契約の正本。
現在の候補値は実測結果ではなく、candidateから主比較を実行できない。
Heston月次Asianは専用revisionで進める後続段階として保持する。

## 検証

基礎実装はテスト先行で検証した。粗細pair・負状態・安定moments・固定配分60件、
Student区間・確定seed・費用内訳43件、独立Black/Euler/clip参照35件、
RMSE/Wilson/固有費用/採否26件に加えprotocol48件・索引・docstringを含む1108件がPASS。全suite・pilot・主実験・教材実行・独立受入は未実施。

全phase予約は181729 slots（うちcoverage172032）。[固定条件](protocol.json)から生成した
全seedは一意で、候補生成時の32bit衝突2件を解消した。
これは同じ初期化の再使用を避ける契約で、真の独立性の数学的証明ではない。

秒数はRNG・engine・summary・その他の処理を分離し、pilot全候補とcold/amortized費用を保持する。
レビュー後に測るfreeze費用は別receiptとし、承認済みpilotを書き換えない。
F04の検証結果をF08のPASSとして扱わない。
