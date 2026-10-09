# RB-F08 最終独立レビュー

2026-10-09。reviewer: independent `/root/f08_execution_review`。

## 結論

**凍結したGBM v1研究・教材を受け入れる。未解決Critical / Important / Minorは0件。**
`teaching_retained=true`、`speedup_supported_vs_euler=true`（3/3誤差目標）、
`standard_accelerator_rejected=true`。厳密終端plain/CVは精度を満たしてMLMCより速く、
GBM callの標準高速器へは採用しない。RQMCの被覆不足も成果として保持する。
Heston、公開API昇格、別モデルへの速度外挿は本受入の範囲外。

採否と自前検算プログラム・数値証跡は[review.json](review.json)に保存した。
原始[reference.json](reference.json)の最終レビュー前のflagは書き換えていない。

## 対象の固定と完全性

- 金融source fingerprint: `d14e7b141275a6f988c309da1bedcfee579932addb910599ac0f2ee47660a004`。10ファイルの現在のSHAを凍結記録と照合。
- protocol frozen digest: `12055b2e301897dd49155e1cb6a1b58f19d62e24a6810e2ce2eb038e95f44957`。
- reference canonical digest: `97cf13a08cfea740c089b5d3c984cc9ae070667b562f267454b46b789cde3c3f`。
- NPZ: 22,255,119 bytes、SHA `fb5c05d57271b9e601f818cdafed63b39127165d82f3be0fe53ad57aec53f3a3`。
- mainは3epsilon × 4method × 256原run = **3072 run**、4608 level、24064原block。
  coverageはK80/100/120 × m8/10 × R8/16/32の全18cell × 512原outer run。
  全runがcompleteで失敗0。未選択candidateも予約台帳に残り、失敗補充・主結果によるcell選定はない。
- 全181729 logical / physical seedが一意。7phaseのtyped台帳、全candidate / spawn key、
  32bit衝突2件の決定的解消を独立再生。seed一意性を数学的な独立性の証明とは扱わない。

## 原始観測からの独立再計算

作者の集計関数を使わず、blockのcount・mean・centered M2を重み付きで結合した。
全pilot levelの5種moments、paired bias / SE、固定CV beta、L / N、全mainの価格・分散・
Satterthwaite自由度・sampling / bias-aware区間、全RQMCのStudent区間を再計算した。
全runのRNG / engine / summary / overhead秒と整数counterを原始blockに照合し、
RMSE（MSEの分母B）、両truthのhit / Wilson、幅median / p95、費用と採否を検算した。

自前の標準正規積分によるBSM値は9.413403383853009。
clip積分は固定両端の質量を加えた別計算とし、全18cellのBSM / clip参照に一致した。
28,693数値比較が `rtol=1e-10, atol=1e-12` でPASS。
最大絶対差3.73e-09は大きなM2で、相対許容誤差内。
無条件の絶対1e-12一致という意味ではない。

独立freshでは通常Eulerの自前scalar / vector漸化式、厳密終端 / frozen CV式、
独立に構築したSciPy Sobolと逆正規変換を使用した。
全method / epsilonのrun0・255（24group、188block、345188path）と、
全18RQMC cellのrun0・255・511（54group、1008scramble、645120point）を再生。
追加fresh_reviewは全K / levelの27group × 256path = 6912path、粗細normalと保存payoffも一致した。
297比較PASS。追加標本はmainへpoolしていない。計時値の再現は要求していない。

実recordの`fresh=False` checkerを`default_rng`、Sobol / GBM / MLMC / RQMC生成、
`run_reference`の禁止hook付きで実行しPASS。
SeedSequence候補の決定的再生成は台帳の検証で、金融観測の新規drawではない。
rootの[fresh_check.json](fresh_check.json)（105group、独立256path/level、poolなし）も同じrecordに結合した。

## MLMCの精度・速度と強い比較器

| epsilon | MLMC RMSE | plain Euler RMSE | paired時間比median | bootstrap95% |
|---:|---:|---:|---:|---|
| 0.4 | 0.2921429 | 0.2790944 | 0.95909 | [0.94786, 0.96805] |
| 0.2 | 0.1284040 | 0.1506290 | 0.70234 | [0.69789, 0.70520] |
| 0.1 | 0.0719563 | 0.0708196 | 0.60991 | [0.60669, 0.61263] |

両Eulerが同じepsilonのRMSEを満たし、paired ratioのmedian / 2000固定resampleの
95%上端が全3条件で1未満。原始bootstrap indexを確定seedから再生し、採否flagと理由を独立再計算した。
exact plain / CVも全epsilonでRMSEを満たす。
CVのmain平均秒はepsilon順に0.000118968 / 0.000143361 / 0.000310644、
MLMCは0.000680168 / 0.001657870 / 0.005350477。
この強い比較器によるmain-onlyの劣位だけでも標準高速器不採用の判断を支持する。

全epsilonは固定L2。paired bias envelopeは0.0110854944、alphaはunresolvedのまま。
差分分散の減少は観測されるが、理論的な率の達成は主張しない。
MLMC sampling CIの対象はE(P_L)で、BSM被覆はbias込みの診断。
固定pilot envelopeによるbias-aware区間を厳密bias保証とは呼ばない。

## RQMCの被覆不足

Student名目95%の実測被覆率は**89.0625–95.703125%**。
**18cell中12cellで個別Wilson95%区間の上端も95%未満**。
以下は個別区間で、多重同時保証ではない。主結果からR / mを選び直さない。
原因を分布の歪み等と断定する追加診断は未実施。

| K | m | R | hits/512 | coverage | Wilson95% |
|---:|---:|---:|---:|---:|---|
| 80 | 8 | 8 | 460/512 | 89.844% | [86.923, 92.171]% |
| 80 | 8 | 16 | 473/512 | 92.383% | [89.756, 94.378]% |
| 80 | 8 | 32 | 477/512 | 93.164% | [90.641, 95.044]% |
| 80 | 10 | 8 | 460/512 | 89.844% | [86.923, 92.171]% |
| 80 | 10 | 16 | 475/512 | 92.773% | [90.198, 94.712]% |
| 80 | 10 | 32 | 490/512 | 95.703% | [93.580, 97.146]% |
| 100 | 8 | 8 | 462/512 | 90.234% | [87.356, 92.514]% |
| 100 | 8 | 16 | 476/512 | 92.969% | [90.419, 94.878]% |
| 100 | 8 | 32 | 476/512 | 92.969% | [90.419, 94.878]% |
| 100 | 10 | 8 | 466/512 | 91.016% | [88.224, 93.197]% |
| 100 | 10 | 16 | 468/512 | 91.406% | [88.660, 93.536]% |
| 100 | 10 | 32 | 480/512 | 93.750% | [91.310, 95.538]% |
| 120 | 8 | 8 | 473/512 | 92.383% | [89.756, 94.378]% |
| 120 | 8 | 16 | 471/512 | 91.992% | [89.316, 94.042]% |
| 120 | 8 | 32 | 481/512 | 93.945% | [91.534, 95.702]% |
| 120 | 10 | 8 | 456/512 | 89.062% | [86.063, 91.481]% |
| 120 | 10 | 16 | 483/512 | 94.336% | [91.984, 96.028]% |
| 120 | 10 | 32 | 478/512 | 93.359% | [90.864, 95.209]% |

BSM / clipped truthの両方で同じ結論を再検算。全原分母で退化runは0。
固定clipはnextafterの両端、Sobolはpoint0を保持してrandom_base2(m)。
SciPy LMS+shiftをOwenの完全nested scrambleと同一とは扱わない。
非有界callに有界integrand向けEBCI / HBCI保証を移していない。

## 費用の照合と解釈

全331 unique expenseをmethod / epsilonの必要集合へ照合し、12行のmain / cold /
amortized(K=1/10/100)を再計算。研究総費用はunique IDを一度だけ数えた。
exact比較器にEuler専用pilot / calibration / allocationを直接計上していない。

coldは**この凍結研究pipelineの検証込み初回費用**。
全台帳 / pilot検証の共通費用を含み、厳密終端単独や解析BSMに数学的に必要な最小費用ではない。
C_lはpilotで5種moments / covarianceを集計するworkloadの較正費用で、mainは差分moments。
したがって固定配分を主run実時間の厳密最適配分とは主張しない。
BSM単回評価0.000271606秒は記述値で、頑健なbenchmarkではない。

| 計測範囲 | 秒 | 解釈 |
|---|---:|---|
| 保存カテゴリ合計、fresh前 | 105.721669 | CLI全wallではない |
| 元full pilot whole CLI | 23.682436 | 内部計上21.737607秒 |
| freeze whole CLI | 25.238622 | 内部計上20.984095秒 |
| main whole CLI | 88.813960 | 当該CLI計上62.999967秒、残差25.813992秒 |
| 上記3CLIの合計 | 137.735018 | prior pilot / freezeをmainへ二重計上しない |
| root fresh検査 | 26.187587 | 別の再現性検査費用 |

main wall receiptのrecord / frozen digest、各内訳と残差を照合。
残差にはpost-run checker / decision、JSON、起動等が含まれる。
計画・開発・人的 / LLMレビュー費用をこの計算会計に含めない。
pilot BLASは当時の直接記録がなく、[pilot_backend_review.json](pilot_backend_review.json)は
同一source / dependencyでの後日の観測という制限を保持する。

## 4図・保管・検証ゲート

[実行済みノート](mlmc_rqmc_ci.ipynb)のnbformatと埋め込み4PNGを独立照合、
各図1PNG、error / stderr出力0。実画像4図を目視し、文字欠落・主要ラベル / legend衝突なし。
図1の負状態0は元49152path/level、図4の退化0は元512outer run/cellを明記。
全18cell、alpha unresolved、pilot費用の適用範囲を表示した。
保存観測だけで生成し、金融 / bootstrap samplingを行わない。[画像証跡](visual_validation.json)に結合済み。

[storage_validation.json](storage_validation.json)の独立担当によるprimary / mirror別復元を照合。
それぞれfallbackなしで同一SHA / bytes、26417非object配列、実checkerの3072run / 18cellがPASS。
現在のC / F別物理disk確認を保存したが、将来の故障耐性を保証する試験ではない。
原JSON / manifest / NPZ / 金融sourceはレビュー前後で不変。

root最終実行の関連3suiteは7616 passed / 6 skipped（415.43秒、whole process418.53秒）、
変更Python16ファイルのruff check / format、ノート禁止guard5件はPASSとの実行証拠を受領。
本reviewerはsuiteを重複実行せず、上記独立全観測検算とfresh再生を行った。

## 残る範囲

未解決の実装欠陥はない。被覆不足、経験的bias envelope、計時環境、
pilot backend記録時点の制限を保持して受け入れる。
Heston固定月次12観測Asianは専用protocol revisionの未実装段階。
本受入はGBM v1の研究と教材の受入で、公開APIや標準高速器への昇格を含めない。
