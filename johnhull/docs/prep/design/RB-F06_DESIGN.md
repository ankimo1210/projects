# RB-F06：逆問題の識別可能性（軽い設計メモ）

- 日付：2026-09-27。状態：設計案。RB-F08の採否記録後、rough版はR1解決後。
- 問い：価格残差が小さくても、パラメータと下流価格がどこまで安定して決まるか。
- 置き場：`research/RB-F06/`、数値実験はhullkit非公開モジュール。学習する場合だけdeep_hedge_price。

## 1. 最小版の選択

| 案 | 利点・制約 | 判断 |
|---|---|---|
| 固定betaのSABR（alpha/rho/nu） | 既存関数が小さく、目的関数の断面を描ける | v1 |
| Heston5パラメータ | 下流Asianへの接続が自然だが計算費用・数値誤差が増える | v2候補 |
| direct inverse/flow/SBI | 学習分布・事前分布・費用という別の問題を加える | 基準診断の後に個別判断 |

v1は正のforwardとstrike、固定満期・beta、合成smile。ノイズなし→quoteを減らす→観測ノイズを加える順。
学習器を先に入れず、目的関数の谷と多点初期化で識別の弱さを確認する。

## 2. 既存資産

- `hullkit.sabr:sabr_implied_vol`：Hagan近似のteacher。teacher自身の近似誤差とoptimizerの誤差を分ける。
- `hullkit.sabr:calibrate_sabr`：固定betaのleast-squares。現在は最終3パラメータのみ返し、成功フラグ・残差・Jacobianは返さない。
  公開APIを変えず、研究用の非公開runnerでSciPyの診断も保存する。
  現行実装は3quote以上・非重み付きraw残差で、nuの下限は1e-9。2quoteの未識別診断は研究用runnerで扱い、この公開関数の条件を変えない。
- `hullkit.stochastic_volatility:heston_price`：v2の再価格付け。M11の独立積分で計算誤差を把握する。
- vol19のmulti-startと直接逆写像：教材・artifact形式の再利用候補。既存の保存集計だけを新しい実験の証拠にしない。

## 3. 実験と評価

1. 真値・quote群・ノイズ生成過程を固定する。単位はIV絶対値、必要に応じてvol bp（$10^{-4}$）。価格へ変換した残差も併記する。
2. 初期値集合とparameter境界を固定し、成功・失敗・境界解を全件保存する。悪い解を結果から消さない。
3. 全quote・ATM付近のみ・疎なquoteを比較する。Jacobianはquoteノイズの尺度とparameterの尺度で正規化し、特異値だけでなく目的関数断面を読む。
4. 観測ノイズを再生成して較正を反復する。test quoteへの再価格付けとパラメータ分布の両方を比較する。
5. 下流商品へ伝播するときは、SABRの近似smileだけで任意のexotic dynamicsが決まるとは扱わない。
   v1は未使用strikeのvanilla価格、exoticはHeston等の動学を明示したv2で扱う。

| 指標 | 注意 |
|---|---|
| 価格/IV残差 | 観測ノイズより小さいfitが高い識別性を意味するとは限らない |
| parameter距離 | 単位・scaleを明示。非識別条件でこれだけを主指標にしない |
| 初期値別解の散らばり | optimizerの局所解と、同程度に良い解の広がりを分ける |
| 区間幅・被覆率 | 合成ノイズ反復で真値を含む率を測る。bootstrapの区間をBayesian posteriorと呼ばない |
| 下流価格の範囲 | calibration誤差とモデル仮定の差を区別 |

## 4. 成果物と採否

保存する配列は、全初期値、最終parameter、成功状態・評価回数、quote residual、目的値、Jacobian、ノイズseed。
目的関数断面・特異値と弱い方向・quote削減/ノイズ対区間幅の3図を作る。
独立参照は目的関数のgrid/profileと再価格付け、固定betaの既存較正、必要なら解析極限。
Hagan近似とその同じ式を二重に呼ぶだけでは価格モデルの独立検証にならない。

2026-10-09の実装前監査：scaled JacobianはW J D_parameterとして単位を明記し、noiselessのnoise SD=0で割らない尺度を固定する。
profileは対象parameterを固定し、残りを各点multi-startで再最適化する。真値で他parameterを止めた断面とは別に表示する。
status/active_mask/optimality、全初期値・失敗・境界解を保存する。
quote/holdout、noiseで負IVが出た場合の扱い、starts/境界/予算、同程度fitの目的値幅、区間・外側反復を本比較前に固定する。

小さな独立検算はbeta=1・nu=0の解析極限。全strikeでIV=alphaとなりrhoは識別されないことを、Blackの価格極限と併せて確認する。
nu=0はboundaryであり、公開calibrate_sabrの正のnu下限とは区別する。
このfixtureだけで研究を終えず、full/ATM/sparse＋noisy smileの本比較へ進む。

教材採用には、どの条件で何が決まらないかを説明できることを求める。
速い点推定でも不安定・過信・費用劣後なら標準器には昇格しない。
未決はparameter/quote範囲、ノイズモデル、multi-start予算と許容差。pilot後・本実験前に固定する。
