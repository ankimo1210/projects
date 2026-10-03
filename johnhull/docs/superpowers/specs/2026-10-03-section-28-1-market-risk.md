# M26 §28.1 The Market Price of Risk

日付2026-10-03、main基点32751a0d。本人の「push to main」「move to next」に従い、M25を統合・pushし、承認済みP3設計と節受入工程を継続する。

## 意図・原典・範囲

Hull 11e GE pp.671–674をPDFで確認。共通の一因子Wienerリスクに依存する無配当の取引可能な証券について、拡散を相殺する局所ポートフォリオからλ=(μ−r)/sとμ=r+λsを導く。sは符号付きの係数、通常のvolatilityは|s|。λの単位は年^−1/2。消費財oil spotの成長率・volatilityにこの式を機械適用しない。多因子・測度の推定・確率金利のnumeraire比較は後続節。

Examples28.1/28.2の印刷値は0.2、−0.15、第二証券の期待収益1.5%。定数GBMの測度変更ではλを変えドリフトを変え、拡散の大きさは保つ。実世界の期待収益と価格測度の期待収益を区別する。

## 契約

- 専用 `hullkit.risk_premium.market_price_of_risk(mu,r,loading)` と `required_return(r,risk_price,loading)`。有限実数、市場broadcast、scalar float/ndarray。負loading/負λ/負rを許可する。
- λの逆算ではloading=0をValueError（μ=rでもλを特定できない）。required_returnではloading=0ならr。無効・表現不能な計算はValueError。空batchでも不正な有限/非実数入力を検査する。
- NumPy complex scalarを含むobject配列、巨大整数、NaN/Inf、不整合shape、overflowを拒否する。実数object配列は利用可能。
- 既存API/root exports/production依存を変更しない。MCは既存sde.girsanov_weightsを|s|で使用し、負sのBrownian座標の向きを説明する。

## 独立参照と教材

build_risk_premium_reference.pyはhullkitを呼ばず、印刷値を独立算術で再計算する。正負loadingを含む12市場例、6種類のpower給付のQ期待値求積とItô微分、局所無リスクportfolioを保存する。portfolioの重みは株数ではなく現在の金額比率。

seed281・262144標本×4ケースのP再重み付けとQ直接標本、重み期待値1、ペア差SEを保存する。RN重みを標本平均で正規化しない。価格対象は無配当GBM証券の割引終値で解析期待値100。年率/log-returnの標準偏差を混同しない。独立求積/API/密度/portfolioの差は1e−8、MCは6SE。95%区間は標本平均の誤差のみ。

vol10の旧213セルの本文・出力・Plotlyを保持。既存§6の正係数のcallデモに続け、###6.1–6.6の11セルを追加して224セルとする。旧表記σの意味を符号付きsとして明確化。4共有図risk_premium_loading/hedge/density/validationをBookとportalに置く。歴史pytestは新6.1–7手前だけを除き、自節の数値・保存出力を再検査する。M26は旧213セル全体保存を担保する。

## 受入条件

Book/portal×1440/1000pxの16状態/16画像、全trace、portfolio・密度、MC誤差棒、印刷値、MathJax・配置、価格改変拒否を確認する。178→182図、exotics66→70、public70→71/private25→26。

台帳RP01–RP06の5軸、既受入25節のD1と両保管庫復元、現在依存の必須hash集合と採用path/SHAを照合。受入26・未評価280、P3 1/37に更新する。4--check、ruff、全hullkit+report pytest、台帳--check-artifacts、release--require-trackedを通す。fresh最終レビュー一度、Important/Criticalは一度のRED→GREEN+全suite、Minorは保留。M26の統合方法は最後に選択する。
