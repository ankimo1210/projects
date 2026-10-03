# §28.1 市場リスクの価格：受入記録

日付2026-10-03。Hull 11e Global Edition pp.671–674、RP01–RP06の5軸。
[原典照合・レビュー](SECTION_28_1_REVIEW_2026-10-03.md)・[M26統合記録](validation/section-28-1/m26-check.json)。
数値・教材・画面の検証済み。全suiteと独立最終レビューは最終確認中。

## 実装と原典

専用 `hullkit.risk_premium.market_price_of_risk(mu,r,loading)` と
`required_return(r,risk_price,loading)`。単因子・無配当の取引証券に対して
$\lambda=(\mu-r)/s$、$\mu=r+\lambda s$。
$s$は符号付き拡散係数、通常のvolatilityは$|s|$。
$\mu,r$は年$^{-1}$、$s,\lambda$は年$^{-1/2}$。負の係数・負λ・負rを許可する。
原典のλは一般には状態/時点に依存し、定数GBMは以下の検証用設定。
有限実数・市場broadcast、scalar float/ndarray。逆算s=0はμ=rでもValueError、順算s=0はr。
非実数・非有限・表現不能な計算はValueError。空batchでも不正設定を検査。
root exports・既存API・production依存を変えていない。

原典の株数$h_1=s_2 f_2$、$h_2=-s_1 f_1$による拡散の相殺を本文で導出。
教材の金額weights(.6,.4)は別の表示。s=(.2,-.3)、r=.04、λ=.25、μ=(.09,-.035)で
リスク寄与 .12−.12=0、収益寄与 .054−.014=.04。
同じsでportfolio価値0となる場合は利回りの除算をしない。
相殺は瞬間的であり、固定holdingsを満期まで放置する説明ではない。
消費財spotに期待収益/volatilityの比を機械適用しない。

## 印刷値と独立数値

Example28.1: (.12−.08)/.2=.2。
Example28.2: (.03−.06)/.2=−.15、第二証券は.06−.15×.3=.015（1.5%）。
独立参照はhullkitをimportせず、12市場、6power給付、Gaussian求積からItô drift/感応度を比較。
power0のloading0ではλを特定しない。印刷値以外は合成市場。
最大API差5.551115e−17、密度差2.220446e−16、局所portfolio差0。
求積誤差見積り最大6.883658e−9（power価格約1万通貨を含む）。
MCは262144標本×4、seed281、T=2、r=.06、f0=100。
raw RN $L=\exp(-\lambda W_T-\lambda^2T/2)$を正規化せずに用い、直接Q標本と同じ正規乱数でペア比較。
期待値100と重み期待値1の独立求積、平均とペア差のSEを照合し、最大2.762972SE（許容6SE）。
負sの場合も既存girsanov_weightsを|s|で呼ぶとBrownian座標が反転し、raw RN期待値が一致。
95%区間は平均の標本誤差で、求積/モデル誤差を含まない。
保存4改変（印刷ピン/power drift/RN正規化/密度）と実API4変異（abs loading/λdrop/微小bias/NaN）を拒否。
全参照builderの到達可能importのAST検査と実行時API禁止もPASS。

## 教材と実画面

vol10 §6.1–6.6、新11セル・共有4図。基点32751a0dの旧213セルの本文/出力/Plotlyを保持し計224セル。
新セルの実行、全文fresh出力一致、旧本文/新見出し/保存図/末尾見出しの4改変拒否。
旧Ch26の歴史pytestは後続6.1–6.6だけを除き、M26が旧213セル全体を検査する。
Book/portal×1440/1000px、16状態/16画像、全trace・カテゴリ・誤差棒・r/平均基準線・値改変拒否がPASS。
1000pxのportal density/validationを目視し、凡例/軸/ラベルの切れや重なりを確認。
Book buildは132warnings（M25基点128、追加4はPlotly MIMEの重複出力警告）。HTML図を全4図で実表示確認。

## 回帰・ゲート

既受入25節のbrowser・runtime probe・個別pytest計1,931件・C:/F:両保管庫復元はPASS。24節再利用・1節再描画。採用記録の再描画画像は456,055バイト（保管庫の実際の増加容量とは区別）。採用D1パスとSHA-256を固定。
参照/数値/notebook/受入の4--check、ruff、台帳--check-artifacts、全hullkit+report pytest、tracked releaseを検査。
FULL_SUITE_PENDING

## 範囲と次

λの実市場推定、多因子、income補正、確率的金利/numeraire比較は後続範囲。
P0/P1/P2完了、本ブランチ受入26・未評価280、P3は1/37。
次はM27 §28.2 Several State Variables。M26のmain統合・pushは別の選択。
