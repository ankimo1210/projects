# GTO Wizard型6-max — Full Coverage実装分析

- 日付: 2026-08-09
- 対象: NLHE cash 6-max、主に100bb
- 関連: [100bb Full HU GTO分析](./2026-08-09-full-hu-gto-analysis.md)
- 目的: 数学的に完全な6-player equilibriumではなく、preflopからriverまで主要spotを途切れなく参照・再計算できる「Full Coverage」を実現する

## 1. 結論

GTO Wizard型の製品は実現可能性がある。ただし目標は、6人の全行動・全runoutを単一の非抽象化game treeで同時に解くことではない。次の層を接続して、利用者からは一続きの6-max solutionに見えるようにする。

1. 抽象化したmultiway preflop solve
2. 全1,755 canonical flopを持つHU postflop library
3. 頻出3-way postflopの限定対応
4. neural continuation valueを使うstreet-by-street re-solving
5. exact river solve

この方式ならB200×8を1〜4 node使う段階的な開発・生成が候補になる。一方、現行コードのままB200を借りてもFull HU/6-max equilibrium solverはCPU実装であり、既存CUDA kernelも`sm_120`・device 0固定なので、先にGPU portとshardingが必要である。

製品上は「Full 6-max GTO」ではなく、少なくとも内部品質表示では次を区別する。

- `exact-river`
- `tabular-bucketed`
- `ai-depth-limited`
- `chart-approximation`

## 2. GTO Wizardの「Full」の意味

GTO Wizardは全1,755 strategically unique flopのsolutionを持つ。一方、従来の6-max solution libraryは300種類以上の**heads-up postflop situation**から30万以上のflop solutionを構成している。preflopはMonkerSolverで解かれ、公開された旧設定には`30,30,30` bucketが含まれる。

GTO Wizard AIはgame全体をpreflopからriverまで毎回展開せず、street単位のdepth-limited solvingを使う。cutoff以降のEVをneural networkで推定し、次のstreetへ進んだ時点で再度solveする。riverはfuture streetがないためexact solveが可能である。

Multiway preflop AIは最大9人を扱えるが、公開説明ではflopへ進める人数を常に最大3人に制限している。例示された単一raise sizeの100bb 6-max preflop treeでも、無制限では622,000 nodesあり、最大3人に制限するとsolve時間が約20分の1になるとしている。また同社自身が、full preflop-to-river computationは現在のhardware/timeではintractableと説明している。

したがって、ここでの用語を次のように定義する。

| 用語 | 意味 | 実現性 |
|---|---|---|
| Full product coverage | 主要position・action・board・streetをUI/APIから連続して参照できる | 目標にできる |
| Full mathematical 6-max GTO | 6人、全legal action、全runout、preflop→riverを単一の整合した非抽象化均衡として解く | 現実的でない |

### 公式資料

- [All You Need To Know About Our Solutions](https://blog.gtowizard.com/all-you-need-to-know-about-our-solutions/) — 300+ HU postflop situations、30万+ flop、旧preflop bucket設定
- [Poker Subsets and Abstractions](https://blog.gtowizard.com/poker-subsets-and-abstractions/) — 全1,755 flop、bet-size/cap/bucket abstraction、solverはsubgameを解くという説明
- [GTO Wizard AI Explained](https://blog.gtowizard.com/gto-wizard-ai-explained/) — street-by-street solveとneural continuation EV
- [GTO Wizard AI Custom Multiway Solving](https://blog.gtowizard.com/gto-wizard-ai-custom-multiway-solving/) — multiway preflop、最大3人to-flop制限、depth-limited solving

## 3. 現行GTO projectとの差

| 機能 | 現在 | GTO Wizard型target |
|---|---|---|
| 6-max preflop | hardcoded chart approximation | multiway MCCFR/AI solve |
| 6-max postflop | 5 opener-vs-BB × SRP/3betのHU subgame | 全15 position pair＋主要history |
| Board coverage | canonical flop library/solver基盤あり | 各対象spotで全1,755 flop |
| River | `gto-hu` exact solve | exact solveを最終品質anchorにする |
| Turn+river | `gto-hu` exact/capped | exactまたは高精度tabular target |
| Flop | bucketed async solve | tabular target＋AI depth-limited serve |
| 3-way | 未実装 | 頻出spotから限定導入 |
| Full-hand composition | `BlueprintSolver`、M-flop抽象、CPU、`M<=8` | distributed/decomposed training＋value model |
| GPU | `gto-cuda` single-street preview | `gto-hu` inner loopとbatch target生成をGPU化 |

現行の強みは、river/turnのcorrectness anchor、全combo evaluator、flop tree builder、NashConv/exact BR、canonical flop、pack/API/UI基盤が既にあること。最大の不足は、multiway preflop、`gto-hu` GPU化、value network、3-way solver、分散job/checkpoint層である。

## 4. 実装するsolution architecture

```text
6-max hand history / custom spot
             |
             v
  Multiway preflop policy
  (MCCFR + abstraction/value model)
             |
       +-----+------------------+
       |                        |
       v                        v
  HU postflop              Selected 3-way
  1,755-flop library       depth-limited solve
       |                        |
       +-----------+------------+
                   v
        Street-by-street resolver
        + continuation value net
                   |
                   v
              Exact river
```

### 4.1 Multiway preflop

最初の6-max preflop modelは次に制限する。

- 169 starting-hand classをbaselineとする
- fixed stack/rake/action configuration
- streetごとのraise cap
- flopへ進める人数は最大3人
- 4-way以上のcall branchは削除または明示的にapproximationへroute
- MCCFR/public chance samplingを候補にする
- postflop continuation valueはHU/3-way target dataから供給する

6-maxは3人以上のgeneral-sum gameであり、通常の2-player CFRと同じNash convergence保証を主張しない。preflop outputは`multiway-approximate`として扱い、seed間安定性、deviation incentive、既知solverとの差分で評価する。

### 4.2 HU postflop coverage

6席のposition pairは

\[
\binom{6}{2}=15
\]

である。まず各pairについてSRP/3bet、全1,755 flopを生成すると、

\[
15\times2\times1{,}755=52{,}650\text{ solves}
\]

となる。その後、limped、cold-call、4betなどを実際のpreflop reachと利用頻度に基づいて追加する。同じpot/stackでもposition、initiative、range、action historyが異なる場合は別spotとして保持する。

利用者がnearest representativeを望まない方針を維持し、未計算flopはnearest solutionで代用しない。canonical suit mappingだけをlossless変換として利用する。

### 4.3 Selected 3-way

最初から全20種類の3-player subset・全historyを解かず、実戦頻度とEV impactで選ぶ。

候補例:

- BTN / SB / BB
- CO / BTN / BB
- CO / SB / BB
- UTG / BTN / BB

最初はSRP、単一または少数bet size、raise cap付きとする。3-way solverが重い場合はstreet終端をvalue networkで切る。結果はHUのNashConvと同じ意味では検証できないため、`equilibrium_claim=false`を維持する。

### 4.4 Continuation value network

Networkはstrategyを直接暗記するより、cutoff stateからのplayer別counterfactual valueを予測する。

入力候補:

- board/runout encoding
- player別range embedding
- pot、effective stack、SPR
- position、initiative、player count
- rake model
- action history / legal action set

出力候補:

- comboまたはbucket別のplayer CFV
- aggregate EV
- uncertainty / out-of-distribution score

Training targetは`gto-hu` exact river、exact turn+river、高精度flop solveから生成する。data splitはcanonical board family、action family、range familyを跨いで行い、suit-isomorphic duplicateや同一spotの近接runoutがtrain/testへ漏れないようにする。

### 4.5 Street-by-street resolving

- flop: flop actionをsolveし、turn以降はvalue networkで評価
- turn: 観測されたturnから再solveし、river valueを推定またはexact enumeration
- river: exact tabular solve

過去のrange/action historyをresolverへ引き継ぐ。historyを無視して任意の中間nodeから解くunsafe resolvingを避け、まずstreet開始時のsafe boundaryだけをproduct scopeにする。

## 5. Hardware構成

### 5.1 現行コードのblocker

1. equilibrium outputを担当する`gto-hu`はCPU実装
2. `gto-cuda`はsingle-street previewでFull HU/6-maxには使えない
3. NVRTC targetがRTX 5080向け`sm_120`固定、B200は`sm_100`
4. CUDA contextがdevice 0固定
5. multi-GPU queue、checkpoint、resume、durable shard storeがない

したがって、B200を借りる前にarchitecture自動検出、1 GPU 1 worker、`gto-hu` inner-loop port、CPU/GPU differential testを完了させる。

### 5.2 推奨node

PilotはGoogle Cloud A4 `a4-highgpu-8g` 1台を第一候補とする。

| Resource | GCP A4 |
|---|---:|
| GPU | B200 × 8 |
| HBM | 1.44TB total |
| System RAM | 3.968TB |
| Local SSD | 12TB |
| vCPU | 224 |
| 参考料金 | Spot \$37.7464/h、Flex-start \$64.44/h |

AWS `p6-b200.48xlarge`はsystem RAM 2TiB、local NVMe約30.7TB、B200×8であり、checkpoint I/Oを優先する場合の候補。Capacity Blockの公開参考料金は\$82.368/hである。価格・capacity・regionは実行直前に再確認する。

推奨worker配置:

```text
1 A4 node
├─ GPU 0..7: 独立した(flophistory, canonical flop) shard
├─ CPU coordinator: queue / preflop / CFV aggregation
├─ Local SSD: active state / resumable checkpoint cache
└─ GCS: durable checkpoint / training data / solution pack
```

初期段階では1 subgameを8 GPUへ分割せず、各GPUが別shardを処理する。これによりNCCL/NVLink依存を避け、node追加によるほぼ独立な水平scaleを狙う。

### 5.3 HU libraryの参考費用

GPU port後に1 solveあたり10分、8 GPU完全並列と仮定した未検証の参考値:

| Coverage | Solve数 | A4 1台 wall time | GCP Spot | GCP Flex-start |
|---|---:|---:|---:|---:|
| 現行5 opener-vs-BB × SRP/3bet | 17,550 | 15.2日 | 約\$13,800 | 約\$23,600 |
| 全15 pair × SRP/3bet | 52,650 | 45.7日 | 約\$41,400 | 約\$70,700 |

4 nodeならwall timeは理想上それぞれ3.8日、11.4日になるが、総GPU料金はほぼ同じ。storage、retries、exact BR、network、開発費は含まない。10分/solveはB200実測ではなく既存の最適化目標なので、契約判断には使わずPilot結果で置換する。

## 6. 品質gate

### 6.1 Tabular solver

- exact riverとのEV/strategy differential
- NashConv/exploitabilityを出せるHU caseでは必ず保存
- iteration増加によるNashConv低下
- bucket数倍増時のstrategy/EV安定性
- CPU/GPU同一設定の差分
- rare/low-reach nodeを含むvalidation

### 6.2 Value network

- held-out CFV MAE（bbおよびpot比）
- best-response EV loss
- action frequency L1 / Jensen-Shannon divergence
- board、SPR、range、history別のworst-slice error
- calibrationされたuncertainty
- out-of-distribution時は結果を拒否し、対応tabular solveをqueueする

暫定のcandidate gateとして、重要spotでCFV MAE `<=0.10bb`、best-response EV loss `<=0.10〜0.15bb/hand`を置く。ただし3-way/general-sumではHU exploitabilityと同じ意味にならないため、正式閾値はbenchmark後に決める。

### 6.3 Product honesty

各response/pack entryに最低限以下を含める。

```json
{
  "solver_method": "exact-river | tabular-bucketed | ai-depth-limited | chart-approximation",
  "equilibrium_claim": false,
  "nash_conv_bb": null,
  "player_count": 2,
  "board_coverage": "canonical-exact",
  "action_abstraction_id": "...",
  "value_model_version": "...",
  "quality_gate_version": "..."
}
```

HUで検証済みNashConvがある場合だけ`equilibrium_claim`を許可する。3-way/6-max全体には「Full Nash equilibrium」という表示をしない。

## 7. 実行roadmap

### Phase A — Measurement and portability

1. 10〜25 flop × 全8 HU leafのCPU benchmarkを確定
2. `sm_100/sm_120` runtime target selection
3. `CUDA_VISIBLE_DEVICES`またはdevice parameterによる1 GPU 1 worker
4. `gto-hu` hot loopのGPU prototype
5. CPU/GPU differential＋NashConv gate
6. A4を8〜24時間だけ借りてB200 benchmark

Go条件: B200でcorrectness gateを維持し、費用/solveとcheckpoint量が測定できること。

### Phase B — GTO Wizard型6-max v1

1. 現行5 opener-vs-BBの全1,755 flopを高品質再生成
2. 全15 position pairのrange/action taxonomyを定義
3. SRP/3betを52,650 shardへ展開
4. exact river anchorとaggregated reportを生成
5. coverage manifest/API/UIでpreflop→river navigationを接続

この時点で「6-max full-coverage HU postflop library」と呼べる。multiway postflop GTOとは呼ばない。

### Phase C — Multiway preflop

1. 169-class small tree baseline
2. max 3 players to flop
3. MCCFRとseed stability test
4. HU postflop CFVをpreflopへ接続
5. chart approximationをsolver-generated policyへ置換

### Phase D — AI depth-limited solving

1. river/turn target dataset生成
2. CFV model baseline
3. flop depth-limited resolver
4. uncertainty/OOD fallback
5. selected 3-way targetとresolver
6. continuous evaluationとmodel/version rollback

### Phase E — Coverage expansion

1. limped/cold-call/4bet family
2. stack/rake variation
3. 3-way spotの頻度順拡張
4. action-size richnessの追加
5. pack compressionとcommercial serving

## 8. 現時点でできること・できないこと

### できること

- GTO Wizardと同様に全1,755 flopを扱うHU postflop library
- 6-max preflop historyから対応HU solutionへ途切れなく遷移するUI
- exact riverをanchorにしたstreet-by-street solver
- 抽象化multiway preflop
- 頻出3-wayの限定solve
- B200 nodeをboard/history shard単位で水平scale

### まだできないこと

- 6人全員のpreflop→riverを単一の完全均衡として解く
- B200でのwall time・costをbenchmarkなしで確定する
- value networkの品質をtraining前に保証する
- general-sum 3-way/6-maxへHUと同じNash convergence claimを付ける
- 未対応spotをnearest solutionで埋めながらexactと表示する

## 9. 推奨判断

数学的Full 6-maxを追うのではなく、GTO Wizard型Full Coverageを正式目標にする。その最初の商用価値があるmilestoneは次である。

> 100bb 6-max、全15 HU position pair、SRP/3bet、全1,755 canonical flop、exact river anchor、quality metadata付きsolution library。

B200×8の本番batchはPhase Aのcorrectness・cost gate後にのみ開始する。AI/value networkはこのtabular libraryをtraining/validation sourceとして後から追加し、最初からAIだけで品質問題を隠さない。
