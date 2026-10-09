# RB-F08：MLMC・RQMCの誤差と費用

更新日：2026-10-09。状態：GBM v1完了・独立受入approved、main統合・push済み。

## 目的・範囲

GBM Euler欧州callの粗細結合と固定pilot配分について、bias・sampling誤差・総費用を分離する。
厳密終端plain/CVとBSMを比較器に保持する。別系列の独立scramble RQMCでは、Student近似区間の被覆率と幅を調べる。
研究完了は固定条件・独立検算・費用・教材・レビュー・採否の記録で判定する。外部データ・公開API変更・新しいproduction依存はない。

## 実施順序

1. private粗細pair・MLMC統計、独立scramble CI、独立Black/Euler/clip参照とseed台帳。
2. 全候補pilot、isolated費用計測、独立pilotレビュー。全主条件・配分・seedをfreeze。
3. Euler系列256反復／予算、RQMC全18cell各512反復。失敗cellも保持。
4. 保存配列からの再検算、fresh再生、artifact-only4図、独立最終レビュー、採否、main統合。

[実施計画](../../docs/superpowers/plans/2026-10-09-mlmc-rqmc-ci.md)が契約の正本。
主実験はapproved pilotから全条件をfreezeした後に実行。candidateやfixtureから主成果へ昇格しない。
Heston月次Asianは専用revisionで進める後続段階として保持する。

## 検証

基礎実装はテスト先行で検証した。粗細pair・負状態・安定moments・固定配分60件、
Student区間・確定seed・費用内訳43件、独立Black/Euler/clip参照35件、
基礎段階のRMSE/Wilson/固有費用/採否26件に加えprotocol48件・索引・docstringを含む1108件がPASS。basis独立レビューは修正後approved（主実験受入とは区別）。
pilot実行/保存/CLI29件・主実験fixture/改変検査35件・analytics31件の対象95件とruffがPASS。
full pilotとfresh再生（52数値列）がPASS。[独立pilotレビュー](PILOT_REVIEW.md)approved、全条件・配分・seedを主実験前にfreeze済み。主実験・fresh再生は完了。関連3suiteは7616 passed・6 skipped（415.43秒）、変更Python16files ruff/format PASS。
[独立最終レビュー](REVIEW.md)approved、実4図・両復元semantic検査・最終guard5件もPASS。
[検証記録](validation.json)に範囲を保存し、本編306節の新しい全面再受入とは扱わない。

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

freeze数値gate PASS。freeze内部計測20.9841秒、whole CLI25.2386秒。元pilot whole CLI23.6824秒との差も[独立wall記録](pilot_execution_wall.json)で保持する。artifact-only builderは金融/ bootstrap乱数を禁止したfixtureで4PNG・対象5件/ruff PASS。[実主成果の4図](mlmc_rqmc_ci.ipynb)は実行/目視/最終レビューを完了。


## 主結果（独立受入済み）

全3epsilon × 4method × 256原run = 3072 run、全18RQMC cell × 512原outer runを保存。
有効cellを結果から選び直さず、失敗0・Euler負状態観測0・RQMC退化0を元の分母で保持した。

| epsilon | MLMC RMSE | plain Euler RMSE | MLMC/Euler時間比median | paired bootstrap95% |
|---:|---:|---:|---:|---|
| 0.4 | 0.2921429 | 0.2790944 | 0.95909 | [0.94786, 0.96805] |
| 0.2 | 0.1284040 | 0.1506290 | 0.70234 | [0.69789, 0.70520] |
| 0.1 | 0.0719563 | 0.0708196 | 0.60991 | [0.60669, 0.61263] |

3/3epsilonで両Euler比較器がRMSE目標を満たし、時間比のbootstrap上端も1未満。
厳密終端/CVは全epsilonで精度条件を満たしてより速く、検証込みcold費用も低い。
**教材として保持し、GBM callの標準高速器には採用しない**。他モデル・別機器へ速度結果を外挿しない。

### RQMCの区間

Student名目95%の実測被覆率は89.0625–95.703125%。
18固定cell中12では個別Wilson95%区間の上端も95%未満だった。
これは各cellの不確実性で、多重同時保証ではない。分布の歪み等を原因と断定する追加診断は未実施。
全m/R/Kを保持し、実測から最良cellを選ばない。clip積分/BSMの両truthで検査し、
有界integrand向け理論保証を非有界callに移さない。

| K | m | R | hits/512 | coverage | Wilson95% | median幅 |
|---:|---:|---:|---:|---:|---|---:|
| 80 | 8 | 8 | 460/512 | 89.844% | [86.923, 92.171]% | 0.062950 |
| 80 | 8 | 16 | 473/512 | 92.383% | [89.756, 94.378]% | 0.044058 |
| 80 | 8 | 32 | 477/512 | 93.164% | [90.641, 95.044]% | 0.030408 |
| 80 | 10 | 8 | 460/512 | 89.844% | [86.923, 92.171]% | 0.015108 |
| 80 | 10 | 16 | 475/512 | 92.773% | [90.198, 94.712]% | 0.010236 |
| 80 | 10 | 32 | 490/512 | 95.703% | [93.580, 97.146]% | 0.007402 |
| 100 | 8 | 8 | 462/512 | 90.234% | [87.356, 92.514]% | 0.063971 |
| 100 | 8 | 16 | 476/512 | 92.969% | [90.419, 94.878]% | 0.041674 |
| 100 | 8 | 32 | 476/512 | 92.969% | [90.419, 94.878]% | 0.030658 |
| 100 | 10 | 8 | 466/512 | 91.016% | [88.224, 93.197]% | 0.015085 |
| 100 | 10 | 16 | 468/512 | 91.406% | [88.660, 93.536]% | 0.010469 |
| 100 | 10 | 32 | 480/512 | 93.750% | [91.310, 95.538]% | 0.007413 |
| 120 | 8 | 8 | 473/512 | 92.383% | [89.756, 94.378]% | 0.065759 |
| 120 | 8 | 16 | 471/512 | 91.992% | [89.316, 94.042]% | 0.041848 |
| 120 | 8 | 32 | 481/512 | 93.945% | [91.534, 95.702]% | 0.030493 |
| 120 | 10 | 8 | 456/512 | 89.062% | [86.063, 91.481]% | 0.014974 |
| 120 | 10 | 16 | 483/512 | 94.336% | [91.984, 96.028]% | 0.010795 |
| 120 | 10 | 32 | 478/512 | 93.359% | [90.864, 95.209]% | 0.007319 |

### 再現・保管と計時

- [主成果](reference.json)／[不変配列manifest](reference_manifest.json)。
  NPZ 22,255,119 bytes、SHA fb5c05d57271b9e601f818cdafed63b39127165d82f3be0fe53ad57aec53f3a3。
  20MB超のため両CASへ保管し、Gitはmanifestと記録を保持する。
- [root fresh](fresh_check.json)：105group・追加独立256path/level、mainへpoolなし。
- [両復元semantic検査](storage_validation.json)：primary/mirrorそれぞれの26,417非object配列・3072run/18cellを検査してPASS。
  C/F別物理diskを今回新たに読み取り確認した。将来の故障耐性の保証ではない。
- [主CLI wall](main_execution_wall.json)：88.813960秒。記録カテゴリは62.999967秒、
  未計上post-run検証/集計/JSON/起動等25.813992秒を別に保持。
- 元recordの研究カテゴリ合計（fresh前）は105.721669秒、CLI総wallではない。
  full pilot＋freeze＋mainの実験CLI wall合計137.735017秒。
  root main freshは別receiptの26.187587秒。計画・開発・独立レビューの人的/LLM費用はこの計算会計に含めない。

## 次段階

Heston固定月次12観測Asianは専用revisionの未完段階（本v1の完了に数えない）。
解析Asian真値はないため、独立高解像度参照のrefinementとsamplingSEを分ける。
次の研究順はRB-F06固定beta SABR識別可能性。Student区間の被覆率を厳密保証と扱う改変や公開API昇格はしない。

独立最終検算は自前28,990数値比較・全原始block/scramble集計・代表fresh再生・金融/ bootstrap乱数を禁止したnonfresh checker・全4図を確認しapproved。未解決Critical/Important/Minorは0。受入と標準高速器への採用は別で、Heston拡張は未完として保持する。

## main反映

`255f4a61`をmainへfast-forward統合してpushした。統合後の`verify_release.py --require-tracked`はPASS。
mainで保管庫から22,255,119 bytesの原始配列を復元し、3072 main runs・18 coverage cellsを保存値から再検算してPASS。
関連3suiteは統合前に1回実行（7616 passed・6 skipped）；統合後はreleaseと保存成果の検査を実施した。
研究のfinancial source・固定条件・元の費用計測を受入後に変更していない。
