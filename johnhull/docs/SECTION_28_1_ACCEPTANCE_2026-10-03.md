# §28.1 市場リスクの価格：受入記録

日付2026-10-03。Hull 11e Global Edition pp.671–674、RP01–RP06の5軸。
[原典照合・レビュー](SECTION_28_1_REVIEW_2026-10-03.md)・[M26統合記録](validation/section-28-1/m26-check.json)。
数値・教材・画面・全suiteと独立最終レビューを完了。レビューの対応は下記と原典照合記録を参照。

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
全hullkit+report pytestは3,843 passed・6 skipped・既存warning2件（155.75s）。4--check、変更Python25ファイルのruff、台帳--check-artifacts、tracked releaseを検査。

## 範囲と次

λの実市場推定、多因子、income補正、確率的金利/numeraire比較は後続範囲。
P0/P1/P2完了、本ブランチ受入26・未評価280、P3は1/37。
次はM27 §28.2 Several State Variables。M26のmain統合・pushは別の選択。

## 独立最終レビューの結論

fresh-context gpt-6-astra（high）一名が32751a0d..7ff6649dを読み取り専用でレビュー。
Critical/Importantなし、Minor M1一件。利用者への効果で再判定して同じ区分とした。
コード修正は不要で、再レビューは行わない。レビュアー対象79テスト・4--check・台帳成果物照合はPASS。
著者の全suite3,843件と16表示状態の再実行、レビュアーの対象テスト/保存証跡検査を区別する。

### Deferred minors

- M1: 約100の価格をゼロ始まりの棒で描くため、MC差と95%誤差棒を比較しにくい。数値は正しく、将来の差分図/拡大パネルを保留。現在の表示を維持。

### Rulings I made（判断順、誤りの場合の費用）

1. 承認済みP3節受入を進め、設計/計画の再承認待ちにしない。利用者が次の実装を明示し工程が確立済み。誤りなら§28.1の選択範囲を修正する費用。
2. M26のD1依存範囲を親§6全体にする。同列見出し6.1だけでは残り5小節を含まないため。RED→GREENで確認。誤りなら§6の他の編集で余分な画像再描画が生じる費用。
3. λの実市場推定は後続研究に残す。今回の利用者は既知のμ/r/sの恒等式と合成実験を得る。誤りなら実市場のλ推定機能が不足する費用。
4. 多因子モデルは§28.2以降で扱う。今回の利用者は明示した単因子の関係を得る。誤りなら複数因子への適用で超過収益を誤計算する費用。
5. 配当/収入補正は後続範囲に残す。無配当条件をAPI/教材/台帳で明記。誤りなら収入付き証券の期待収益を誤計算する費用。
6. 確率金利のnumeraire比較は後続節で扱う。今回のMCは定数GBMとして再現可能。誤りなら確率金利への転用で不適切な価格測度を用いる費用。

初回全suiteの1失敗は件数/統合証跡をM25に固定した台帳テスト。期待値をM26へ移し、§28.1の6要求/5軸も追加し、全suiteを再実行してPASSを確認した。
