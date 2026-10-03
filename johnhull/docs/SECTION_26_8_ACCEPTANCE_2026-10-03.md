# §26.8 Chooser：受入記録

日付2026-10-03。Hull 11e Global Edition pp.619–620、CH01–CH06の5軸。
[原典照合・レビュー](SECTION_26_8_REVIEW_2026-10-03.md)・[M25統合記録](validation/section-26-8/m25-check.json)。
独立最終レビューのImportant I1を修正し、Minor M1を保留。全体検査を完了した。

## 実装・契約

専用 `hullkit.chooser.chooser_price(S,K,r,sigma,T1,T2,q=0)`。
同じK/T2の欧州call/putをT1で選ぶ。T1の条件付き価値max(c1,p1)とT2の給付決済を区別する。
parityからH=K exp(−(r−q)(T2−T1))、w=exp(−q(T2−T1))。
T2call一枚とT1のstrike Hのputをw枚持つ複製。S1>Hならcall、下ならput、等号なら同価値。
S,K>0、σ≥0、0≤T1≤T2、有限実数、市場broadcast、scalar float/array ndarray。
T1=0はmax(c0,p0)、T1=T2はstraddle、σ=0は決定的max、T2=0は|S−K|。
無効・表現不能な計算はValueError。正の極大rで表現可能な限界も検査。
既存API/root exports/production依存は維持。

## 原典と独立数値

原典に印刷数値例はなく、全数値は合成。
独立参照はhullkitと複製価格式を呼ばず、erfc vanillaでmax(c1,p1)をT1密度求積。
選択境界とinner vanilla遷移の±3/±10幅で分割する。極小残存期間を求積が見落とすM24の学びを引き継ぐ。
合成基準S=K=100、r5%、q2%、σ20%、T1=.5、T2=1：chooser=13.3442804480692。
選択境界H=98.5111939603063、put枚数w=0.990049833749168。
T1=.1/.5/.9/.999999の独立求積価格は10.483695744000126/13.344280448069238/15.168232237397923/15.55708234558728。
64ケースと図の全曲線で最大API差4.263256e-14通貨、複製差1.421085e-14、同次性差4.263256e-14、bounds逸脱2.842171e-14。
求積の誤差見積り最大4.867409e-11。低σ・負のr/q・T1/T2=.999999・両端点・zeroσ/満期を含む。
seed268、524288経路×4の条件付きMCは最大1.505955標準誤差で6SE以内。

95%区間は平均の標本誤差で、求積/モデル誤差を含まない。
保存price/boundary/weight/MC誤差4改変と、実APIの配当drop/選択日半減/微小bias/NaN4変異を拒否。
API変異は合法入力・有限出力でも独立価格比較で拒否することを確認。
すべてのbuild_*_reference.pyの到達可能importをAST検査し、実行時にもproduction APIを禁じて独立参照を再計算した。

## 教材・実画面

vol10 §4.15.1–6、新11セル・4共有図。基点5013f2d4の旧202セル/本文/保存出力を保持し213セル。
新セル実行と全文fresh検査、旧本文/見出し/保存図/末尾見出し4改変拒否。
M24歴史pytestは後続4.15だけを除き、M25が旧202セル全体保存を検査する。
Book/portal×1440/1000px、16状態/16画像、全trace/選択境界/複製/MC誤差棒/価格改変拒否がPASS。
Book数式983個・エラー0。portalのchoice/validationの1000px画像を目視し、切れや重なりを確認した。

## 回帰・ゲート

既受入24節のbrowser・runtime probe・個別pytest計1,868件・C:/F:両保管庫復元はPASS。23節再利用・1節再描画、追加保存505,902バイト。採用D1パスとSHA-256を固定。
参照/数値/notebook/受入の4--check、ruff、台帳--check-artifacts、全hullkit+report pytest、tracked releaseを検査する。
全hullkit+report pytestは3,757 passed・6 skipped・既存warning2件（144.27s (0:02:24)）。4--check、変更Python20ファイルのruff、台帳--check-artifacts、tracked releaseがPASS。独立最終レビューI1を修正し、M1を保留した。

## 適用範囲と統合

Simple European chooser、定数GBM・連続配当。
異なるstrike/満期のcomplex chooser、American、smile、確率的金利/変動率、離散配当、取引費用は対象外。
M1保留：空batchでは有限だが不正なK/σ/時点設定がbroadcast後に消えて空配列を返す。誤った価格の返却はない。
既存M22/M23/M24の保留は変更しない。
本ブランチで受入25・未評価281、P2 8/8完了。次はP3金利37節。main統合・pushは別の選択。
