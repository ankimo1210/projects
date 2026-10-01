# M24 Compound Options — §26.7

日付2026-10-01。ユーザーの「1 and go next」でM23のmainへのローカル統合とM24の実装を承認。P2の継続として既存の節受入フローを使い、定数GBMの欧州型4契約を実装・説明・数値・実画面・回帰の5軸で受け入れる。原典Hull 11e Global Edition pp.618–619、準備資料docs/prep/sections/ch26.md。原典に印刷数値例はない。

## 契約・インターフェース

外側の行使時点T1で、残存期間T2−T1・行使価格K2の内側vanilla option価値V1を受け取る権利。外側callの給付はmax(V1−K1,0)、putはmax(K1−V1,0)。このT1価値を現在へ割り引く。内側optionはT2に欧州行使される。

公開専用module hullkit.compoundのcompound_price(S,K1,K2,r,sigma,T1,T2,q=0,*,kind="call_on_call")。kindはcall_on_call/put_on_call/call_on_put/put_on_put。市場と二つのstrike/時点はbroadcastし、scalarはfloat、配列はndarray。S,K2>0、K1≥0、sigma≥0、0<T1<T2、全入力有限実数。無効shape/非実数/非有限/表現範囲外計算はValueError。q,rは定数連続複利率。既存公開API/root exports/pricingとproduction依存は維持する。

## 要求

- CO01：4契約・K1/K2・T1/T2・T1での外側給付を説明し、4給付を閾値図で示す。
- CO02：内側vanilla(S*,K2,T2−T1)=K1の臨界株価を求める。内側callではS>S*、内側putではS<S*で外側callを行使する。putの上限K2 exp(−r(T2−T1))以上のK1では有限根がない。call-on-put=0、put-on-put=K1 exp(−rT1)−vanilla_put(0)とし、探索失敗扱いにしない。
- CO03：Hull p.619の4公式を直接実装。aの閾値はS*、bの閾値はK2、相関の符号は契約別、絶対値sqrt(T1/T2)。Mは決定的な二変量正規積分（相関角度の一次元求積）で評価し、ランダムCDFを使わない。
- CO04：K1=0では外側call=内側vanilla現在価値、外側put=0。sigma=0では決定的なT1給付。根残差・4価格・二つのcompound put-call parity・全通貨量の一次同次性を確認する。T1/T2が近い合成ケースも含む。
- CO05：hullkit/二変量CDFを使わないT1対数正規密度についての独立条件付き求積104ケース。内側vanillaは独自erfc実装。MCは固定seedの524288経路×4契約（T1 spotをsamplingし内側vanilla条件付き期待値を用いる）。MC95%区間は平均の標本誤差で、求積やモデル誤差ではない。価格差1e−8、恒等式1e−8、根残差1e−9、MC6SEを要求。非有限API結果も拒否する。strike入替・相関0・誤った臨界株価・NaNへのAPI変異を検出する。
- CO06：vol10 §4.14.1–6の11セル・4共有図。基点cb3665fdの旧191セル/保存出力を保持。Book/portal×1440/1000pxの16状態/16画像・数式・trace・MC誤差棒・価格改変拒否を照合。既受入23節をD1で再検査し両保管庫から復元する。台帳accepted24/unreviewed282、P2は7/8。

## 図と適用範囲

compound_threshold：T1株価に対する内側価値・外側4給付、K1とS*。compound_strikes：外側K1を0から内側put上限以上まで変えた4価格。compound_timing：T2=1年固定でT1を0.01〜0.9999年とした4価格。compound_validation：4契約の独立求積と条件付きMC95%区間。

図はS=100,K1=10,K2=100,r=5%,q=2%,sigma=20%,T1=.5,T2=1を共通基準とし、変更する軸だけを明記。独立価格はcall-on-call=3.25682701977442、put-on-call=3.78292063190369、call-on-put=1.29980310015750、put-on-put=4.72282159289091。根は105.772962280276/90.7302199250643。すべて合成。欧州型・定数GBMに限定し、American exercise、smile、確率的金利/変動率、取引費用は扱わない。

M23のNaN gate保留とM22の時点説明P3は旧節の保留として保持する。M24では最初から有限値拒否を設ける。D1必須hash集合は記録の自己申告ではなく現行依存宣言とPython閉包から再構成する。

作業は既存worktree /home/kazumasa/worktrees/m18、branch codex/m24-compound-options、基点main=cb3665fd。M23はmainへローカル統合済み。mainのmarket-research変更と他担当worktreeは保持。Git/buildはWSL、共有venv /home/kazumasa/projects/.venv。受入後のM24統合/pushは別選択を待つ。

本人が継続承認したinline方式を使う。実装計画、TDD、全hullkit+report pytest、ruff、4本--check、台帳成果物/コミット後tracked release、一度の独立最終レビューと重要指摘のRED→GREEN修正を行う。

二変量CDFの定義・符号恒等式は[Hull Technical Note 5](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/TechnicalNote5.pdf)を参照。本実装はそこにある4桁近似を転記せず、相関角度積分と独立conditional quadratureで精度を検証する。
