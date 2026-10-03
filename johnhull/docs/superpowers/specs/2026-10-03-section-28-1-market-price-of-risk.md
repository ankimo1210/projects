# M26 §28.1 The Market Price of Risk

日付2026-10-03。main基点32751a0d。P3（金利、Ch 28–34）の最初の節。承認済みの節受入工程を継続する。

## 契約と範囲

Hull 11e GE pp.671–674。単一のリスク源dzに依存する無配当証券fは df/f = m dt + s dz。
sは符号付きloadingで、fがuと逆に動けば負、volatilityは|s|。
同じdzを持つ2証券から、f1をs2 f2単位・f2を−s1 f1単位持つportfolioはdzを消し（式28.4）、無裁定なら利回りrを得る。
これから(m−r)/s=λは証券によらない（式28.6–28.8）。m=r+λs（式28.9–28.10）。
λを選ぶことは測度を選ぶことで、成長率は変わりloadingは変わらない（Girsanov）。
印刷値はExample 28.1のλ=0.2、Example 28.2のλ=−0.15と期待収益1.5%。
消費財（原油）の価格そのものに式28.8を機械的に当てはめない。他の数値はすべて合成。
多因子（§28.2）、martingale（§28.3）、numeraire変更（§28.4以降）、λの推定（Ch36）、配当のある証券（Problem 28.7）は対象外。

## インターフェース

専用 `hullkit.market_price_of_risk`。
`market_price_of_risk(m,s,r)`、`required_growth(r,lam,s)`、`riskless_holdings(f1,s1,f2,s2)`、
`ito_growth_and_loading(f,f_t,f_u,f_uu,u,m,s)`。
有限実数がbroadcastし、scalarはfloat・配列はndarray。s=0のλ、非正の価格、等しいloading、複素数・非有限・表現不能はValueError。
既存API・root exports・production依存は変えない。

独立 `build_market_price_of_risk_reference.py` はhullkitを呼ばない。
erfcの請求権価格を実世界drift μで1ステップGauss–Hermite求積し、平均とZ共分散を2次Richardsonで極限化して成長率とloadingを得る。
2市場（λ=0.35、λ=−0.1）の38請求権（株式、call/put、cash/asset-or-nothing）で共通λを確認する。
無リスク2組の利回りとdz残差の√h縮小、5つのλの世界でloading不変、原油callの例、seed281・524288経路のdirect/尤度比MC。
API・Itô（hullkit.bsmのGreek）・保有量は1e−8、MCは6標準誤差。保存参照・実APIの誤りと非有限を負の対照で拒否する。

## 教材・受入

vol10 §6.1–6.6を「## 7.」の前に挿入する。
mpr_line/mpr_riskless/mpr_worlds/mpr_validationの4共有図。基点32751a0dの旧213セル・本文・保存出力を完全に保持する。
Book/portal×1440/1000pxの実画面、台帳MP01–MP06の5軸。D1・C:/F:保管庫の復元は所有者の環境で行う。
