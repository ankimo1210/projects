# RB-F08：MLMCとRQMCの誤差・費用（軽い設計メモ）

- 日付：2026-09-27。状態：設計案。RB-F04の採否記録後。P4 Ch21受入後が望ましい。
- 問い：同じ誤差目標で粗細の経路へ計算を配ると総費用を下げられるか。
- 置き場：`research/RB-F08/` とhullkit非公開モジュール。NumPy/SciPy・CPU、外部データなし。

## 1. 最小版と比較器

GBM Euler＋欧州callを最初の教材にする。GBM終端厳密生成＋BSMを最強の比較器として併記する。
この商品でEuler MLMCが厳密終端法に勝つ必要はない。目的はbias・差分分散・計算配分を見えるようにすること。
次段階はHeston算術Asian。観測日は全階層で同じにし、観測の間の時間格子だけを細分する。
F04と同じ月次12観測ではS0を平均へ含めない。既存arithmetic_asian_detailsへはS0＋月次12点の計13列を渡し、include_initial=Falseを明示する。月次12列だけを渡してさらに初列を落とさない。

| 既存 | 再利用／不足 |
|---|---|
| `hullkit.mc_advanced:plain_price`, `hullkit.mc_advanced:control_variate_price` | GBM終端厳密生成の比較。CV係数の推定費用も数える |
| `hullkit.mc_advanced:qmc_price` | scrambled Sobol一組の点推定。独立反復・CIは追加が必要 |
| `hullkit._numerical_mc:randomized_qmc_price` | 現行private実装はSeedSequenceで独立scrambleを作り、組別推定のSEを計算する。既存CIは1.96正規近似。研究では全scramble推定値・子seedを保持し、Student型CIと被覆率を追加する |
| `hullkit._numerical_mc:gbm_paths_from_normals` / `hullkit._stochastic_foundations:stock_paths` | 外から渡したBrownian乱数を再生できる。前者のdefaultはexactなので、MLMCにはscheme='euler'を明示。粗い正規乱数は隣接する細乱数の和/sqrt(2)で作る |
| `hullkit.mc_advanced:error_vs_n` | 図の形式の参考。単一seedの誤差曲線をRMSEと呼ばない |
| `hullkit.heston:heston_mc_price` | モデル規約の参考。粗細結合やAsianの専用評価器ではない |

## 2. MLMCの契約

粗細差 $Y_\ell=P_\ell-P_{\ell-1}$（$Y_0=P_0$）について、細かいBrownian増分を足して粗い増分にする。
レベル間の推定は独立にし、同レベル内の粗細だけを強く結合する。

$$
\widehat P=\sum_{\ell=0}^L\overline Y_\ell,\qquad
\widehat{\mathrm{Var}}(\widehat P)=\sum_{\ell=0}^L s_\ell^2/N_\ell.
$$

固定pilotから分散 $V_\ell$ と1組の費用 $C_\ell$ を推定し、主実験は独立streamで
$N_\ell\propto\sqrt{V_\ell/C_\ell}$ に配分する。biasとsamplingに誤差予算を分ける。
weak orderやvariance rateが実測で安定しないときは、理論の計算量改善を結果として宣言しない。
Eulerで負の株価が出た経路を黙って切り捨てない。刻み・係数・発生率を記録して粗い階層の妥当性を判断する。

## 3. RQMCは別の比較系列

独立scrambleを $R$ 組作り、各組に $2^m$ 点を使う。CIの標本数は点の総数でなく独立な $R$ 個の推定値。
Student型CIを使う場合は近似CIと明記し、解析解のある問題で多数反復による被覆率と幅を調べる。
[S020/S021](../sources/sources_S001-S031.md#s020)の有界関数向けの保証を、非有界callに無条件で移さない。
CDF逆変換の端点clipもbias源として値を固定・開示する。MLMCとの組合せは最小版に含めない。

## 4. 保存・採否

| 記録 | 評価 |
|---|---|
| レベル別平均・分散・費用・経路数 | 結合の有効性と配分の説明 |
| 独立runごとの価格・SE・CI・真値誤差 | RMSE、bias、被覆率。pilotと評価を分離 |
| 総秒数・step数・乱数数・hardware | 誤差対費用。同じ乱数数だけを同じ費用とは呼ばない |
| 商品・格子・観測日・スキーム・seed | 商品変更による偽の収束を防ぐ |

図は階層差分分散、経路配分、RMSE対費用、CI被覆率の4本。巨大pathを常時保存せず集計と再生成条件を残す。
[S004](../sources/sources_S001-S031.md#s004)の定理は条件付きの計算量境界であり、どのpayoffにも同じ速度を保証しない。
差分分散が下がらない、結合費用やpilotが重い場合は高速化として不採用。失敗の原因が説明できれば教材として残す。
残る事項：誤差目標と反復数、Hestonの分散スキーム、bias推定の停止規約を実装前に固定する。
