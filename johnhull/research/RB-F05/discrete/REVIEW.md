# RB-F05 discrete 主結果の独立レビュー

2026-10-09。主 fit と計時付き最終結果 `reference.json` / `reference.npz` を対象とする。
教師コード自体の独立承認ではなく、研究 runner の接続、保存結果の再生、
独立 PDE との照合、採否の解釈を確認した。

## 判定

主計算・保存結果に受入を止める問題は見つからなかった。
DML は price-only NN を全 3 seed で改善した。一方、固定 2 入力問題の強い Hermite 補間より
価格・Delta とも大幅に粗いため、標準高速器としての採用は見送る。
現在の `standard_speed_adopted=false` は妥当。計時・宣言した費用範囲の評価は済み、詳細を後半に記録した。

## 実行範囲と独立確認

- 実際に `mode=main`、`status=complete`、失敗 0。smoke ではない。
- train 512 / validation 128、各行 4,096 MC paths、test 200 点（25 spots × 8 maturities）。
- 主 6 fits は price/dml × seeds 11/29/47。全 fit が 512/512 updates、budget failure なし。
- 保存 NN を NumPy で再生し、保存予測と raw test RMSE に許容誤差内で一致した。
- 同 seed の初期 price loss は両方式で一致。最終 objective は方式ごとの price/Delta loss を足したもので、
  DML と price-only の総 loss をそのまま優劣比較していない。
- train/validation の保存 MC 平均・SEと高精度 GL 参照を別集計した。
  raw draw からの MC 再生成・最終 loss 再計算は親の `--check --fresh` でも PASS と報告されている。
- 独立 log-PDE を全 test 200 点へ同じ固定設定で再計算した。再学習・再計時は行っていない。
  この独立集計プロセスでは Torch を import していない。

## 主 raw 品質

RMSE は物理単位。price は契約 1 単位の価格、Delta は価格/spot。

| Seed | price-only price RMSE | DML price RMSE | price-only Delta RMSE | DML Delta RMSE | 全 seed の対 NN 品質条件 |
|---|---:|---:|---:|---:|---|
| 11 | 0.0554402654 | 0.0231837497 | 0.0173015862 | 0.0056977989 | PASS |
| 29 | 0.0580776789 | 0.0279957402 | 0.0205832918 | 0.0060841200 | PASS |
| 47 | 0.0656552051 | 0.0266066826 | 0.0213355565 | 0.0067177653 | PASS |

DML / price-only の RMSE 比は価格 0.405–0.482、Delta 0.296–0.329。
これは raw NN 同士の比較であり、fallback の正確な値を raw 品質へ混ぜていない。

強い Hermite 基準は price RMSE **0.000363766661**、Delta RMSE **0.0000576622445**。
DML の誤差は Hermite に対して価格 **63.7–77.0 倍**、Delta **98.8–116.5 倍**。
NN 対 NN の改善を、参照補間に対する品質達成と読み替えてはいけない。

## 独立 PDE 全 test 照合

契約は GBM、K=100/H=120/r=.03/sigma=.2、rebate/dividend=0、監視 `{0,T/12,...,T}`。
独立 PDE は space=4800、steps/monitor=256、log half-width=1.5、barrier phase=.5、
固定 K/H の bump=.0005。全 test 点を保存 GL 参照と比較した。

| T | 最大 price 差 | 最大 Delta 差 |
|---:|---:|---:|
| 0.25 | 1.53798408235e-4 | 3.11899153330e-5 |
| 1/3 | 1.07840294783e-4 | 1.85561323814e-5 |
| 0.5 | 6.29223246777e-5 | 8.68043190561e-6 |
| 0.75 | 3.60163109765e-5 | 3.97002365643e-6 |
| 1 | 2.40327673642e-5 | 2.26141450915e-6 |
| 1.25 | 1.74956676788e-5 | 1.46158327596e-6 |
| 1.5 | 1.34920881119e-5 | 1.03386467130e-6 |
| 2 | 8.94618553005e-6 | 5.96290651508e-7 |

全体最大 price 差は **0.00015379840823515067**（S=115.75,T=.25）、
Delta 差は **0.000031189915333018625**（S=119,T=.25）。
固定した独立照合許容差 price=5e-4 / Delta=2e-4 の内側にある。
PDE の空間・時間・領域・barrier phase・bump 誤差を一つの MC SE として扱っていない。
これは固定 midpoint/精細 PDE と GL の照合であり、node-aligned phase の精度保証ではない。

## 実 MC 診断

- train ラベル：価格・Delta の **1,024/1,024** 比較が 6SE + GL 数値誤差の内側。
- validation ラベル：**256/256** が同条件の内側。
- 両 split の label SE=0 は 0 件。raw positive-payoff 最小件数は train=76、validation=103。
- 別 seed の主診断正対照：**116/116** が 6SE + GL 誤差の内側、SE=0 は 0 件。
- naive PW 負対照は **19/20**、最終条件付き PW 負対照は **17/18** を同基準の外側として識別。
  未識別はいずれも S=80,T=.25,m=12。有限 MC で識別できないことを正しい Greek の証拠とはしない。
- m1 conditioned 系は `analytic_reference/not_MC`。MC の 0 分散教師として比較していない。
- OSS probability/quantile/weight underflow・numerical failure は全 20 診断点で 0。
  条件付き proposal の有効件数、生存確率重み、正 payoff 件数を区別している。
  例えば S80/T.25 の raw survival=65,534 に対して positive payoff=948、OSS valid=65,536 に対して
  positive payoff=912。proposal の有効件数を元契約の生存確率や精度保証として扱わない。
- 6SE は固定 seed の診断であり、全域の誤差上界や信頼区間の証明ではない。

## Raw / safe / 境界

test 200 点での NN fallback 件数は price seeds=1/2/2、DML seeds=0/0/2。
raw と safe の保存予測・指標は別である。価格 bounds の通過は Greek 精度を保証しない。

全方式の safe probe は、域内推論、OOD fallback、S=H の Delta 未定義、
S>H の即 KO、無効入力、変更契約 unsupported を明示した。

S=119.999 の参照価格は T=.25/1/2 でそれぞれ
**1.30909157892 / 0.548897915415 / 0.331388000912** と正であり、
S=120 は price=0 / Delta=NaN、S>120 は price=Delta=0。
有限回監視の初期 barrier ジャンプを連続的なゼロへ矯正していない。


## 最終計時・費用監査

計時付き最終 JSON/NPZ を再読し、再学習・再計時せず確認した。
保存 weights を独自に decode した NN/Hermite callbacks と checked GL128/256 batch oracle で、
**32/32 measurements の価格・physical Delta・route が数値 replay に一致**した。
100 load samples の median/p95、32 比較の offline 会計・ceil による whole-batch 数・回収式も
保存 raw samples と成分から独自に再計算して一致。Torch は import していない。

### 推論速度

以下は全 3 DML seed の範囲。単位は **microseconds / whole batch**。
20 repeats の p95 は観測分位点であり、3 seed の信頼区間ではない。

| 呼出 | DML median | DML p95 | Hermite median/p95 | checked GL median/p95 |
|---|---:|---:|---:|---:|
| raw batch1 | 14.14–15.36 | 15.63–32.65 | 27.08 / 42.52 | 7,839.19 / 8,183.21 |
| raw batch32 | 28.35–28.75 | 30.06–31.77 | 40.68 / 43.94 | 11,993.10 / 12,371.60 |
| safe batch1 | 33.36–35.12 | 37.40–44.76 | 51.06 / 57.54 | 8,046.39 / 8,519.38 |

raw DML の中央値速度比は GL 対比 510–554 倍（batch1）、417–423 倍（batch32）。
Hermite 対比は 1.76–1.91 倍、1.41–1.44 倍にとどまる。
これらは同じ保存入力・契約・price+Delta 演算の比較で、GL の scalar 逐次呼出を弱い対照にしていない。
ただし raw batch1 は S80/T.25、safe batch1 は S100/T1、batch32 は test grid の先頭 subset を使う。
全満期・全 test 点に対する速度上界や均一な優位を示すものではない。

safe batch32 は各呼出に OOD 2 行、S=H、S>H を含む。NN の bounds fallback 追加で
方式・seed ごとに route が変わる。S=H の ordinary Delta は未定義なので、
**全 8 方式の当該 price+ordinary-Delta 比較が unsupported** となり、
保存費用表の training-only/deployment と回収数は null。failure/未定義出力の短い処理時間を
成功した価格・Greek の速度改善として採用していない。

### 準備費用を含む回収

中央値では DML の standalone offline+load は **2.159–2.202s**、
Hermite は **0.175535s**。NN は conditioned train labels、fit elapsed、export、
CPU/Adam 共通初期化 1.110264s、1 回の load を負担する。
setup/training は elapsed の内訳であり、重複加算されない。
実験では共有教師を 1 回生成し、standalone 方式ごとの比較では各方式へその費用を配賦している。

| 対 checked GL・median | DML の初回回収 calls | Hermite の初回回収 calls |
|---|---:|---:|
| raw batch1 | 276–282 | 23 |
| raw batch32 | 181–185（5,792–5,920 rows） | 15（480 rows） |
| safe batch1 | 270–275 | 22 |
| safe batch32 | unsupported | unsupported |

raw p95 成分シナリオでも DML 回収は batch1 265–270 calls、batch32 176–179 calls。
これは各成分の観測 p95 を組み合わせたシナリオで、総時間の実測 p95 や信頼区間ではない。

Hermite 自体を比較相手として offline 差額を引いた独立計算では、raw median の DML 回収は
batch1 約 **15.5–16.9 万 calls**、batch32 約 **16.4–16.6 万 calls**（約 **525–532 万 rows**）。
この計算は精度差を補償しない。大幅な精度低下を許容できる別の用途がある場合に限る
時間シナリオであり、同等精度の経済性を示さない。

### 来歴と未計測範囲

主生成 source 7 件の SHA は Git **35fe9280** の内容と一致し、計時 source 2 件も
保存 fingerprint と一致した。SHA は実行源の来歴に用い、金融数値の一致判定には用いていない。

load は **計時配列追加前の主 fit 研究 bundle（287,346 bytes、SHA 177ef9c8…）** の
warm decode 100 回から median=0.00584733s / p95=0.00619737s を測ったもの。
最終 332,089 bytes の NPZ を測ったという意味ではない。JSON の historical source_note は
この区別を明示している。最小 standalone package、cold IO、process start、module import、
protocol/source 準備、benchmark/report 作成などは未計測として保持され、ゼロ費用と扱わない。
元の計測入力 archive の保存は来歴を補強できるが、現数値の再計時は必要ない。

## 最終採否

**研究結果は受入可。標準高速器への DML 採用は見送る。**
全 3 seed で微分教師が price-only NN の価格・Delta を改善するという結果は支持される。
標準方式としては、固定 2 入力領域で Hermite の品質が価格約 64–77 倍、Delta 約 99–117 倍良く、
準備費用も小さい。GL 対比の大きな推論速度比だけでは、この強い比較対象を上回る採用根拠にならない。
`standard_speed_adopted=false` は最終結果に整合する。
この結果は固定 GBM 契約・指定領域の研究であり、多パラメータ較正やヘッジ改善の証拠へ外挿しない。
