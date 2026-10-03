# M27 §28.2 Several State Variables

日付2026-10-03。本人の「push to main」「move to next」に従い、M26統合後のmainからP3の節受入を継続する。原典はHull 11e GE pp.674–675を本文と画像で確認。

## 意図・範囲

式28.11–28.13の符号付き因子係数とリスク価格から、超過収益 μ−r=Σλᵢsᵢ を計算する。Example28.3の石油・金・株価指数の係数(.05,.1,.15)、λ=(.2,−.1,.4)は、寄与(+1%,−1%,+6%)、合計6%の**超過収益**。総期待収益はr+6%であり、教材ではr=4%を追加した合成例の10%を印刷値と区別する。正負の寄与・価格ゼロの追加因子、APT、CAPMの条件付きの結論（市場と無相関なリスクに価格ゼロ）を説明する。一般の無相関因子が必ず無価格とはしない。

## API契約

専用hullkit.factor_riskにfactor_contributions(risk_prices,loadings)、factor_excess_return(risk_prices,loadings)、factor_required_return(r,risk_prices,loadings)。最後の軸が因子、入力ベクトル以上、因子数は同じ正整数。先行batch軸のみbroadcast。rは合計のbatchへbroadcast。scalarの合計はfloat、寄与とbatch合計はndarray。正負係数・価格・金利、全ゼロ係数、空batchは有効。空因子・scalar因子・長さ不一致・非実数・非有限・overflowはValueError。object配列内complexも拒否。既存one-factor API/root exports/production依存を変更しない。

λとsは同一のリスク基底で与える。教材の線形代数は独立Brownian基底。直交回転でλ,sを両方回転し、内積と拡散normの不変性を示す。相関状態変数の各spot volatilityをそのままsとして入れたり、相関を内積へ二重に掛けない。相関行列の一般的な白色化・λ推定・多因子測度変更は§28.5以降。

## 独立参照・教材

hullkitを呼ばないPython math.fsumの参照：印刷例、正負/価格ゼロ/単因子の12市場例、独立2因子3証券の局所hedge（金額比率(.25,.25,.5)、係数(.2,0),(0,.2),(−.1,−.1)、λ=(.3,−.2)、r=.04）、4直交回転、無価格の追加因子とCAPM例。APIとの差1e−12。実API変異abs/sum-axis/drop-factor/+r誤りと保存値改変を拒否。

旧M26の224セルの本文/出力/Plotlyを保持し、##6A. 複数状態変数（§28.2）、###6A.1–6A.6の11セルを##7の直前へ追加する（235セル）。4共有図factor_risk_contributions/loading/hedge/validationをBook/portalへ追加。過去のnotebook pytestは新6A範囲だけを除き、M27検査が旧224セル全体を担保する。

## 受入条件

Book/portal×1440/1000pxの16状態/16画像。全trace・印刷値/合成総収益・MathJax・配置・数値改変拒否。186図/exotics74、public72/private27。FR01–FR06の5軸、既受入26節D1とC:/F:復元、必須依存hash集合と採用path/SHA固定、受入27/未評価279/P3 2/37。4--check、ruff、全hullkit+report、台帳--check-artifacts、tracked releaseとfresh最終レビューを実行。Important/Criticalは一度のRED→GREEN修正+全suite、Minor保留。本人の指示に従って検証後mainへ統合・pushする。
