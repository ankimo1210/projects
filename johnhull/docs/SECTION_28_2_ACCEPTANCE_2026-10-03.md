# §28.2 複数状態変数：受入記録

日付2026-10-03。Hull 11e GE pp.674–675、FR01–FR06の5軸。
[原典照合・レビュー](SECTION_28_2_REVIEW_2026-10-03.md)・[M27統合記録](validation/section-28-2/m27-check.json)。

## 実装と原典

専用hullkit.factor_riskのfactor_contributions(risk_prices,loadings)、factor_excess_return(risk_prices,loadings)、factor_required_return(r,risk_prices,loadings)。
μ−r=Σλᵢsᵢ。同一リスク基底、λ,sは年^(-1/2)、積/μ/rは年^(-1)。signed係数を絶対値にしない。最後の因子軸は同じ正整数で先行batchのみbroadcast、rは減らしたbatch軸へbroadcast。
正負/ゼロのλ・係数・金利、空batchは有効。scalar因子/空因子/因子数不一致/非実数・非有限・不整合・overflowはValueError。実数object可、object内NumPy complexも拒否。単市場の合計はfloat、その他はndarray。
既存one-factor API/root exports/production依存は不変。

## 印刷値と独立数値

Example28.3: λ=(.2,−.1,.4),s=(.05,.1,.15)、寄与(.01,−.01,.06)、**超過収益6%/年**。総収益はr+6%で、教材追加のr=4%なら10%。
無価格の追加因子を加えても6%で、追加価格.3/係数.8なら30%に変わる。原典の条件を省略しない。
APIを呼ばないmath.fsum参照12市場。APIとの差最大6.9388939e-18、SVD局所hedge差2.77555756e-17、4直交回転差2.77555756e-17、許容1e−12。
独立2因子3証券の係数(.2,0),(0,.2),(−.1,−.1)、λ=(.3,−.2)、金額weights(.25,.25,.5)、r=.04。両因子寄与合計0、収益合計.04をSVD零空間から解き直す。
株数はw_i/f_iで局所・瞬間の自己金融hedge。固定株数が満期まで無リスクとはしない。
両係数vectorを同じ直交Qで回転すると内積とvolatility normは不変。相関を内積へ二重に掛けない。
保存4改変/API4変異（絶対値化・最終因子省略・全batch合計・金利二重加算）を拒否。全reference builderの到達importをASTで独立性検査。

## CAPM・APT・範囲

CAPMは式28.13の特殊例。**CAPMが成立するなら**市場と無相関なnonsystematic riskの価格はゼロ。一般のAPTの結論へ拡張しない。
独立な市場/固有因子の合成CAPM例ではλ=(.3,0),s=(.2ρ,.2√(1−ρ²))、超過収益.06ρ。ρ=0でもvolatility.2は残る。
実市場の推定、一般の相関行列の白色化、多因子測度変更、配当/収入補正、確率金利は対象外。関連する後続§28.5以降を参照。

## 教材と実画面

vol10親§6A全体、6A.1–6A.6、新11セル・4共有図。main基点010a2bc3の旧224セル本文/出力/Plotlyを保持し計235。fresh全文出力一致、notebook4改変拒否。
過去のpytestから新6Aだけを除き、M27が旧224セル全体を検査。M26の元の基点固定scriptは歴史受入用のまま。
Book/portal×1440/1000、16状態/16画像、全trace/基準r線/6%と10%/MathJax/数値改変拒否がPASS。
1000pxのBook寄与/portal hedge・validationを目視。portal4図をfull rowへ拡大、両幅で図の幅700px以上をbrowser検査。
Book136warnings（M26時132に新4Plotly MIME警告）。HTML全4図を実表示確認。

## 回帰・ゲート

既受入26節のbrowser・runtime probe・個別pytest計1,995件・C:/F:両保管庫復元はPASS。0節再利用・26節再描画。共有CSS変更による保守的な再描画。採用記録の再描画画像payloadは19,126,473バイトで、重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。
参照/数値/notebook/統合の4--check、ruff、全hullkit+report suite、独立レビュー、台帳--check-artifacts、tracked releaseは最終実行で結果を固定する。

## 範囲と次

P0/P1/P2完了、M27受入でaccepted27/unreviewed279（8.8%）、P3は2/37。次はM28 §28.3 Martingales（GE pp.675–676）。
本人のmainへのpush指示に従い、独立最終レビューと統合後ゲートを完了して統合・pushする。
