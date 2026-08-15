# 100bb Full HU GTO — coverage・pattern数・計算資源分析

- 日付: 2026-08-09
- 基準commit: `ec0205ad`
- 対象: NLHE cash HU、100bb、全street（preflop→river）
- 方針: 未解決flopをnearest representativeで代用せず、全1,755 canonical flopを直接扱う
- 注意: 本稿の「Full HU GTO」は、合理的な離散bet treeを持つ**実用的な抽象ゲーム均衡**を意味する。連続bet sizeを含む数学的な非抽象化NLHE全体ではない。

## 1. 結論

全1,755 flopを個別に解くpostflop libraryは、現在の1台でも長時間batchとして実現可能である。一方、preflopから全flopを同時に結合した一貫したFull HU equilibriumを、現行のdense CFR tableのまま保持することは現実的ではない。

現行100bb preflop treeの全8 postflop到達経路、全1,755 canonical flop、`K_t=16`、`K_r=128`では、必要なstate-action cell数は

\[
4{,}657{,}867{,}402{,}032\approx4.66\text{兆}
\]

となる。各cellにf64のregretとstrategy sumを保存すると、CFR numeric slabだけで

\[
4.6579\times10^{12}\times 2\times8
=74.53\text{ TB}
\]

である。f32化しても37.26TBであり、現行48GB RAMではdense simultaneous solveはできない。実装にはCFR-D/subgame decomposition、sparse・disk-backed state、flop単位のshardingが必要である。

## 2. 「全flop」の定義

raw flopは

\[
\binom{52}{3}=22{,}100
\]

通りある。suit名の置換は戦略的に同型なので、[`flop_canon.py`](../src/gto/library/flop_canon.py)の完全なsuit isomorphismにより1,755 canonical flopへlosslessに縮約できる。

これはnearest-flop近似ではない。actual boardをcanonical boardへ変換し、同じsuit permutationをprivate cardsにも適用すれば、22,100 raw flopsを1,755 solvesで完全にカバーできる。

## 3. 現行100bb preflop treeの到達経路

[`preflop_builder.rs`](../crates/gto-hu/src/tree/preflop_builder.rs)は、次の8個のnon-all-in postflop leafを生成する。

| # | Preflop history | Pot | Remaining stack | Postflop tree |
|---:|---|---:|---:|---|
| 1 | Limp–check | 2bb | 99bb | SRP config |
| 2 | Limp–raise 4–call | 8bb | 96bb | SRP config |
| 3 | Limp–raise 4–3bet 12–call | 24bb | 88bb | 3bet config |
| 4 | Limp–raise 6–call | 12bb | 94bb | SRP config |
| 5 | Limp–raise 6–3bet 12–call | 24bb | 88bb | 3bet config |
| 6 | Open 2.5–call | 5bb | 97.5bb | SRP config |
| 7 | Open 2.5–3bet 9–call | 18bb | 91bb | 3bet config |
| 8 | Open–3bet–4bet 22–call | 44bb | 78bb | 4bet config |

同じ24bb/88bbでも到達historyが異なるため、equilibrium rangeは別になる。単純なpot/stack一致だけでsubgame strategyを共有してはいけない。preflop all-in leafはpostflop betting treeを持たず、equity terminalとして処理される。

Preflop structural treeは43 nodes、action edgeは42本である。private combo vectorを1,326とすると、preflop CFR cellは

\[
42\times1{,}326=55{,}692
\]

で、postflopの兆単位cellと比べれば無視できる。

## 4. Pattern数の算出方法

1つのCFR cellを次のtupleとして数える。

\[
(\text{preflop leaf},\ \text{canonical flop},\ \text{bet history},\
\text{public context},\ \text{private state},\ \text{action})
\]

総数は

\[
N=\sum_{n\in\text{action nodes}} A_nC_nB_n
\]

である。

- \(A_n\): node \(n\) のlegal action数
- \(C_n\): public-card context数
- \(B_n\): private comboまたはbucket数

### 4.1 Public context数

固定flopから見たcontext数は次の通り。

| Street | \(C\) | 根拠 |
|---|---:|---|
| Flop | 1 | flopは固定 |
| Turn | 49 | flopの3枚を除く |
| River | \(49\times48=2{,}352\) | turnとriverは順序を持つ |

実際にはprivate-card blockerで到達不能な組み合わせがあるが、現行dense tableはcontext領域を予約し、unreachable rowをmaskする。

### 4.2 Private-state dimension

候補設定は次の通り。

| Street | \(B\) |
|---|---:|
| Flop | 1,326 combo vector |
| Turn | \(K_t=16\) mean-river-percentile buckets |
| River | \(K_r=128\) strength-percentile buckets |

`K=0`はexact combo storage（1,326 dimension）を意味する。

### 4.3 Action edge数

現行tree builderを100bbで実行し、8 leafを合計すると次になる。

| Street | 全8 leafのaction edge合計 |
|---|---:|
| Flop | 250 |
| Turn | 1,812 |
| River | 8,810 |

したがって、1 canonical flopあたりのcell数は

\[
\begin{aligned}
P(K_t,K_r)
&=250\times1\times1{,}326\\
&\quad+1{,}812\times49\times K_t\\
&\quad+8{,}810\times2{,}352\times K_r\\
&=331{,}500+88{,}788K_t+20{,}721{,}120K_r.
\end{aligned}
\]

### 4.4 `K_t=16`, `K_r=128`

\[
\begin{aligned}
P_f&=331{,}500,\\
P_t&=88{,}788\times16=1{,}420{,}608,\\
P_r&=20{,}721{,}120\times128=2{,}652{,}303{,}360.
\end{aligned}
\]

よって

\[
P_{1\text{ flop}}=2{,}654{,}055{,}468.
\]

Riverが全cellの約99.93%を占める。全1,755 flopとpreflopを加えると

\[
\begin{aligned}
P_{\text{total}}
&=55{,}692+1{,}755\times2{,}654{,}055{,}468\\
&=4{,}657{,}867{,}402{,}032.
\end{aligned}
\]

## 5. Leaf別内訳

`K_t=16`, `K_r=128`における1 canonical flopあたりのdense table内訳。

| Leaf | Tree nodes | Action nodes | CFR cells | f64 regret+strategy |
|---|---:|---:|---:|---:|
| Limped 2bb | 3,555 | 1,304 | 915,528,756 | 14.65GB |
| SRP 8bb | 2,091 | 780 | 479,590,260 | 7.67GB |
| 3bet 24bb (history A) | 533 | 196 | 83,853,484 | 1.34GB |
| SRP 12bb | 1,643 | 616 | 359,139,636 | 5.75GB |
| 3bet 24bb (history B) | 533 | 196 | 83,853,484 | 1.34GB |
| SRP 5bb | 2,619 | 976 | 633,740,340 | 10.14GB |
| 3bet 18bb | 557 | 204 | 91,078,828 | 1.46GB |
| 4bet 44bb | 89 | 32 | 7,270,680 | 0.12GB |
| **合計/1 flop** | **11,620** | **4,304** | **2,654,055,468** | **42.46GB** |

全1,755 flopではstructural nodesが

\[
43+1{,}755\times11{,}620=20{,}393{,}143
\]

となる。tree structure自体より、river contextに付くCFR numeric slabが支配的である。

## 6. Bucket解像度とtraining table容量

1 cellはregretとstrategy sumの2値を持つ。

- f64: \(2\times8=16\) bytes/cell
- f32: \(2\times4=8\) bytes/cell

| \(K_t\) | \(K_r\) | Total cells | f64 table | f32 table |
|---:|---:|---:|---:|---:|
| 16 | 128 | 4.66兆 | 74.53TB | 37.26TB |
| 32 | 256 | 9.32兆 | 149.04TB | 74.52TB |
| 64 | 512 | 18.63兆 | 298.08TB | 149.04TB |
| 1,326 | 1,326 | 48.43兆 | 774.85TB | 387.42TB |

この表はCFR slabのみであり、tree metadata、equity tables、scratch buffer、allocator overhead、checkpoint generationを含まない。M=3 baselineでは23.95GB tableに対してpeak RSSが約27.2GBだったため、full solveの実process memoryは表より大きくなる。

Full HUの「必要サイズ」は固定値ではない。最小の`K_t`, `K_r`で次の品質gateを通る点を測定して決める。

1. Full-game NashConv/exploitability \(\le0.10\)〜\(0.15\) bb/hand
2. exact river solveとのEV-loss MAE \(\le0.10\) bb
3. bucket数を倍にしてもstrategy/EVが実質的に安定
4. rare/low-reach nodeを含むspot-level validation

## 7. 計算時間

### 7.1 全flopの独立postflop solve

各flopを1本ずつ解けば、RAMは最大subgame分だけ再利用できる。現行実測は標準flopで約49分、最適化目標は約10分/flopである。

| Coverage | Solve数 | 49分/solve | 10分/solve |
|---|---:|---:|---:|
| SRPのみ | 1,755 | 59.7日 | 12.2日 |
| SRP＋3bet | 3,510 | 119.4日 | 24.4日 |
| 全8 preflop leaf | 14,040 | 約477.8日 | 約97.5日 |

最後の行は全leafを同一時間と仮定した粗い上限寄りの見積もりである。実際にはlimped treeが重く、4bet treeは軽いので、leaf別benchmarkが必要。

独立solveは全flop postflop libraryを作れるが、固定input rangeで解くだけではpreflop戦略との相互整合がないため、Full HU equilibriumではない。

### 7.2 一貫したpreflop→river solve

P0aのM=3 baseline（`K_t=16`, `K_r=24`）は、1500 iterationsのsolve部分が約2,366秒である。Mだけを線形に1,755へ外挿すると、同じ粗いbucket設定でも

| Iterations | 単純外挿wall time |
|---:|---:|
| 1,500 | 約16日 |
| 15,000 | 約160日 |
| 30,000 | 約320日 |

となる。これはmemoryが収まり、完全な線形scalingが成立すると仮定した下限寄りの見積もりで、exact best response、checkpoint、より大きい`K_r`のcostを十分に含まない。

## 8. 配布solution容量

学習終了後はregretを捨て、strategy frequencyだけをu8化できる。全8 leaf・全1,755 flopについて全action cellをそのまま1 byteで保存するraw上限は

\[
4.6579\times10^{12}\text{ bytes}=4.66\text{ TB}
\]

である。SRP 5bb＋3bet 18bbの2 familyだけならraw u8 strategyは約1.27TB。

実際には以下で削減できる。

- reachしないcontextの省略
- default/uniform rowの省略
- action probabilityの最後の1要素を省略
- subtree・bucket-map共有
- zstd compression
- low-reach pruning（品質bound必須）

ただし、既存設計の「15MB/flop」は未検証の目標である。完全treeのdense countから見ると強いsparsity/compressionを前提としており、pack prototypeで実測する必要がある。過去の「約53〜105GB」というstorage見積もりも15MB/file目標からの外挿で、確定値ではない。

## 9. 現行実装上のblocker

1. [`BlueprintSolver`](../crates/gto-hu/src/solver/blueprint.rs)は`M<=8`をassertしている。
2. blocker normalizationに`zsum: Vec<f64>` of length \(2^M\) を使うため、M=1,755へそのまま拡張できない。
3. 全leaf×全flopのregretをdense simultaneous allocationしている。
4. 全subgameへ同一input rangeを渡す現行構造を、preflop reach rangeとcounterfactual valueが整合する分解へ改める必要がある。
5. exact best responseも全flop・全leafへ分散可能な形にする必要がある。

`2^M` normalizationは、combo pairごとのcompatible board massを直接計算・cacheする方式へ置換できる。1,326×1,326のf64 tableでも約14MBで、指数配列より十分小さい。

## 10. 推奨アーキテクチャ

nearest-flop近似を使わずFull HUを目指す場合は、次の構成が妥当。

1. **Lossless board coverage**: 1,755 canonical flop＋suit mapping
2. **Subgame sharding**: `(preflop leaf, canonical flop)`ごとに永続shard
3. **CFR-D/decomposition**: global preflop iterationが各subgameからcounterfactual continuation valueを受け取る
4. **Warm start**: reach range更新後も前iterationのsubgame regretを再利用
5. **Disk-backed/sparse tables**: active shardだけRAMへloadし、safe checkpointでrotate
6. **Distributed exact BR**: flop/leaf単位にmap-reduce
7. **Pack export**: 個別solve済みflopだけをexactとして提供し、未生成flopをnearestで代用しない

この構成ならworking RAMを最大subgame規模（候補設定ではlimped leaf約14.65GB＋overhead）へ抑えられる。ただし、全regret stateの永続storage・I/O量と収束速度が新しいbottleneckになる。

## 11. 推奨実行順序

1. 10〜25 canonical flopで全8 leafのbenchmarkを取り、leaf別wall timeとpeak RSSを確定
2. `K_t/K_r` sensitivityを測り、品質gateを満たす最小bucket数を選定
3. 1 flop分の完全pack prototypeを作り、u8/f16/zstd後の実file sizeを測定
4. `2^M zsum`を除去し、flop shard formatとresume protocolを設計
5. 100bb HU SRP＋3betの全1,755個別solveを先行生成
6. limped/4bet familyを追加
7. CFR-Dでpreflop reachとpostflop continuation valueを結合
8. Full-game NashConvとexact-river differential gateを通過後にのみ「Full HU GTO」と表示

## 12. 現時点で言えること・言えないこと

言えること:

- nearest-flopなしで全1,755 canonical flopを扱うことは可能。
- 個別postflop libraryは単一マシンで長期batchとして現実的。
- dense full-game solveは現行構造では非現実的で、分解が必須。

まだ言えないこと:

- `K_t=16`, `K_r=128`が品質gateを通るか。
- sparse化後の実storage size。
- CFR-D実装後の収束時間。
- 15MB/flop pack目標が成立するか。

これらは推測で埋めず、P0a/P0b benchmarkとpack prototypeで測定する。
