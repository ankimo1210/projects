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
RMSE/Wilson/固有費用/採否31件に加えprotocol48件・索引・docstringを含む1108件がPASS。basis独立レビューは修正後approved（主実験受入とは区別）。
pilot実行/保存/CLI29件・主実験fixture/改変検査35件・analytics31件の対象95件とruffがPASS。
full pilotとfresh再生（52数値列）がPASS。[独立pilotレビュー](PILOT_REVIEW.md)approved、全条件・配分・seedを主実験前にfreeze済み。全suite・主実験・教材実行・最終受入は未実施。

全phase予約は181729 slots（うちcoverage172032）。[固定条件](protocol.json)から生成した
全seedは一意で、候補生成時の32bit衝突2件を解消した。
これは同じ初期化の再使用を避ける契約で、真の独立性の数学的証明ではない。

秒数はRNG・engine・summary・その他の処理を分離し、pilot全候補とcold/amortized費用を保持する。
レビュー後に測るfreeze費用は別receiptとし、承認済みpilotを書き換えない。
F04の検証結果をF08のPASSとして扱わない。


## Full pilot（main前）

3 streams × 16384 paths × 全9levelを事前固定して実行。全候補で負株価観測は0。
全3誤差目標はL2（16steps）、経験的paired bias envelope 0.0110854944を選択した。
弱収束率alphaは未識別で、理論率達成は主張しない。CV betaは独立pilotから0.6391930617。
全主条件と181729 seedは独立レビュー後にfreezeした（digest 12055b2e…）。

| epsilon | MLMC N0/N1/N2 | plain Euler N | exact N | CV N |
|---:|---|---:|---:|---:|
| 0.4 | 2670 / 118 / 71 | 2403 | 2533 | 425 |
| 0.2 | 10680 / 472 / 284 | 9611 | 10131 | 1699 |
| 0.1 | 42720 / 1888 / 1133 | 38442 | 40521 | 6793 |

pilot/checker/source/費用の保存を含む主実験前段階で、pilot総計測費用21.7376秒。
5,071,444 bytesのpilot NPZは20MB閾値未満のためGit管理とする。
[再生検査](pilot_fresh_check.json)は52数値列を固定seedから許容誤差つきで再計算した。

### 費用の解釈

coldはこの凍結研究pipelineの検証込み初回費用。全台帳・pilotの検証費用も識別可能なIDで含める。
解析BSMや厳密終端単独の計算に数学的に必須の起動費用とは呼ばない。
main-only、cold、amortized 1/10/100と、独立BSMの単回評価時間を並記する。
単回解析時間は記述値で、頑健な速度benchmarkではない。

C_lはpilot較正workload（fine/coarse/exact/bias等の5種momentsと共分散）の計測費用。
主runは差分1種momentsを集計するため、C_lを用いた固定配分が主run実時間の厳密な最適配分とは主張しない。
主run速度比は固定配分の実測値から判定する。BLAS backendはpilot時に直接保存していないため、
同一source/依存versionでのレビュー時の補足と主実験前確認を区別して残す。

保存recordのfull_research_s_before_freshは記録したカテゴリの合計で、CLI全工程のwall総秒ではない。post-run数値checker/採否集計・JSON出力・Python起動等の未計上overheadは、reference digestに結び付けた独立CLI wall receiptへ保存して区別する。

freeze数値gate PASS。freeze内部計測20.9841秒、whole CLI25.2386秒。元pilot whole CLI23.6824秒との差も[独立wall記録](pilot_execution_wall.json)で保持する。artifact-only builderは金融/ bootstrap乱数を禁止したfixtureで4PNG・対象5件/ruff PASS。実主成果の4図は未生成。
