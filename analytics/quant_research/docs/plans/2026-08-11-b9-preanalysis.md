# B9 SEC Filing Text & Fundamentals Forecast — pre-analysis specification

- 決定日: 2026-08-11
- 状態: candidate evaluation前に固定
- data contract: [`b9-m6-protocol.json`](../contracts/b9-m6-protocol.json)
- analysis contract: [`b9-preanalysis-v1.json`](../contracts/b9-preanalysis-v1.json)

## 結論

B9は原典のDeep Learning / Financial NLPの数学・実装目標を維持しつつ、取得不能な中央銀行
intraday market targetを使わない。M6で固定したSEC cohortを使い、**前回filingが利用可能になった
時点から次四半期のlog-Assets成長を予測する**。

numeric-onlyは必須baselineであり、B9 Coreからtextを外さない。TF-IDF、MLP、LSTM、TCN、
small self-attention、text+numericを同じdevelopment dataで比較する。pretrained embeddingと
encoder fine-tuningは、新依存・外部model・大きい計算予算を必要とするためAdvancedへ分離する。

## 既知情報と未開封情報

pre-registration前にM6のdata-quality結果と4 baselineは既に観測している。これは隠さずcontractへ
列挙した。candidate model、text feature、inner-validation結果、outer testは未評価である。

| partition | rule | rows | CIK | availability dates |
|---|---|---:|---:|---:|
| development | date < 2023-10-23、`cik % 3 != 0` | 2,195 | 102 | 534 |
| inner train | development、date < 2021-01-01 | 1,504 | 102 | — |
| inner validation | 2021-01-01 ≤ date < 2023-10-23、`cik % 3 != 0` | 691 | 68 | 190 |
| locked outer | date ≥ 2023-10-23、`cik % 3 == 0` | 413 | 38 | 183 |

outerを開く前にcandidate family、hyperparameter grid、seed、feature manifest、code commitを固定する。
outer結果を見たarchitecture交換、threshold変更、feature追加、再学習はしない。

## Estimandと情報集合

targetは

\[
y_{i,t}=\log A_{i,t}-\log A_{i,t-1}
\]

である。予測時点は前回filingの保守的availability dateである`known_at`とする。targetや過去growthを
使うfeatureは、各行の`known_at`より**前**にtarget availabilityを持つ履歴だけから計算する。

主張はfixed-anchor feasibility cohort上のpredictive associationに限定する。filing languageの因果効果、
abnormal return、取引収益、米国企業全体への代表性は主張しない。

## Feature contract

### Numeric Core

- previous Assetsのlog
- 1期・2期lag growth
- 過去growthのexpanding mean / standard deviation / count
- 前回filing lag、period gap、fiscal quarter
- lag不足で行を落とさず、missing indicatorとtraining-only medianを使う
- scaling、imputation、feature selectionはactive training partitionだけでfitする

### Text Core

前回Assets factと同じ`previous_accession`のSEC primary documentだけを使う。target accessionの
documentはfeatureへ入れない。visible body textからscript、style、hidden inline XBRL、exhibit、
markupを除き、headingとparagraph順序を保持する。legacy filingのlayout tableは構造を除くが、可視cell
textは保持する。

candidate評価前のinput-quality auditで、table subtreeを丸ごと除くと80文書が100 tokens未満となり、
可視cell textを保持すれば同じ80文書が全て500 tokens以上になることを確認した。このためcleaning contract
だけを修正した。split、candidate、metric、selection ruleは変更していない。

現在のderived panelはaccession・filing date・acceptance datetime・primary documentをrowへ保持して
いない。modeling前にこれらをmaterializeし、raw/normalized hashを持つ別manifestを作る。この拡張で
M6のtarget row集合、target値、outer splitを変更してはならない。

text coverageが90%未満、duplicate familyがpartitionを跨ぐ、target documentが混入する、または
manifest integrityが通らない場合、text trackは開始しない。

## Model comparison

| 層 | model | 役割 |
|---|---|---|
| 固定baseline | zero / pooled drift / seasonal / company mean | M6と同じ比較基準 |
| 線形baseline | numeric ridge / TF-IDF ridge | deep modelより先に固定 |
| Week 33 | NumPy MLP | forward、backprop、gradient check、training loop |
| Week 34 | NumPy LSTM / TCN | 同じtoken sequenceとbudgetで比較 |
| Week 35 | small self-attention | attention、position、mask、gradient audit |
| Week 36 | text+numeric MLP | text-only / numeric-only / joint ablation |

familyごとのtraining runは最大12、1 runは最大200 epoch、trainable parameterは10万以下とする。
contractにridge、TF-IDF、hidden width、learning rate、kernel、attention head、seedの探索集合を列挙した。
inner-validation MAE、次にmedAE、次にparameter数で、全familyのoverall nomineeとneural familyの
neural nomineeを各1件までouterへ進める。両者が同一modelならouter candidateは1件である。

## Metric、uncertainty、採用規則

- primary: row-level MAE
- secondary: medAE
- reference: RMSE
- guardrail: company-macro MAE、90% interval coverage / width、text coverage、duplicate family
- primary comparator: pooled drift
- deep-learning comparator: TF-IDF ridge

model selectedとするには、pooled driftよりMAEを1%以上改善し、medAEとcompany-macro MAEを悪化させず、
company-cluster paired bootstrapによる\(\Delta\mathrm{MAE}\)の95% interval上端が0未満でなければならない。
deep-learningの追加価値を主張するには、同じgateをTF-IDF ridgeに対して満たす。満たさない場合の正式な
結論は`no_model_selected`または`no_incremental_deep_learning_gain`である。

## B9実装へ進む前のgate

1. panel rowへprevious filing provenanceを追加し、M6 row/hash不変を検査する。**実装・実データ照合済み。4631行、欠損0、target accession混入0。**
2. SEC primary document downloaderをstaging + atomic publish + bounded retryで実装する。**実装・実取得済み。4,631 / 4,631成功。**
3. text retrieval manifest、coverage、duplicate-family、target-text exclusionを監査する。**raw / normalized coverage 100%、空文書0、partition跨ぎduplicate 0、target混入0でpass。**
4. B9のWeek 33–36とProjectを`curriculum_map.yml`へ追加する。
5. builder / Notebook / library / testsを実装し、outerを開く前にnominee manifestを固定する。

## Development tournament milestone（2026-08-11）

M6のdevelopment partition（2,195行、inner train 1,504行、inner validation 691行）で、
`numeric_ridge`、`tfidf_ridge`、`numpy_mlp`の固定gridを実行した。outer 413行は未開封である。
実装済みfamilyではzero baselineを1%以上改善する候補がなく、interim結果は
`no_model_selected`。LSTM / TCN / self-attention / joint text+numericはtraining loop未実装のため、
この結果を全Core familyの最終nominee freezeとは扱わない。次は未実装familyを同じbudget・inner splitへ
追加し、全Core比較後にのみnominee manifestをfreezeする。

raw SEC response、normalized text、contact情報はrepositoryへcommitしない。

実装状況と実測fingerprintは
[B9 filing provenance and retrieval gate update](../updates/2026-08-11-b9-filing-provenance.md)に記録する。
