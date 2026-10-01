# §26.7 Compound：受入記録

**判定：accepted。** 日付2026-10-01。Hull 11e Global Edition pp.618–619のCO01–CO06を照合。
[原典照合・レビュー](SECTION_26_7_REVIEW_2026-10-01.md)、[M24統合記録](validation/section-26-7/m24-check.json)を参照。独立最終レビューは未実施で、重要指摘対応と最終検査後にこのノートを確定する。

## 実装・契約

専用module hullkit.compoundのcompound_priceでcall-on-call、put-on-call、call-on-put、put-on-putを評価する。
T1で内側vanilla価値V1とK1を比較し、外側callはmax(V1−K1,0)、putは逆の正部分。
内側のstrikeはK2、満期T2。外側給付はT1から割り引く。
臨界株価は内側価値=K1の根。aにはS*、bにはK2、相関は契約別に±sqrt(T1/T2)。Hullの4公式を直接実装する。
二変量正規CDFは相関角度の一次元積分で再現可能に評価する。

S,K2>0,K1≥0,σ≥0,0<T1<T2、有限実数・broadcast。scalar float/array ndarray。
K1=0は内側vanilla/0、σ=0は決定的T1給付。
内側putの上限K2 exp(−r(T2−T1))以上のK1では有限根がなく、call-on-put=0、put-on-put=K1PV−p0。
既存pricing・root exports・production依存は維持する。

## 独立数値

原典に印刷例はなく、すべて合成。基準S100/K1=10/K2=100/r5%/q2%/σ20%/T1=.5/T2=1の独立求積価格：
call-on-call3.25682701977442、put-on-call3.78292063190369、call-on-put1.29980310015750、put-on-put4.72282159289091。
根はcall105.772962280276、put90.7302199250643。

hullkit/二変量CDFを使わないerfc vanillaとT1密度求積104例でAPI差最大5.570655e-12通貨、求積誤差見積り最大9.639635e-11。
根残差7.815970e-13、compound parity2.842171e-14、全通貨量同次性3.552714e-14。
近接日付T1/T2=.9999、K1=0、σ=0、put上限ちょうど/直下/以上を含む。
MCは共通seed267、T1 spot samplingと内側条件付きvanilla価値、524288経路×4契約。
求積との差最大1.737656標準誤差で6SE以内。95%区間は平均の標本誤差で、求積/モデル誤差ではない。
保存price/critical/strike/MC誤差の4改変、実APIのstrike入替/相関0/根変更/NaNの4変異を拒否した。

## 教材・実画面

vol10 §4.14.1–6に11セル・4共有図。M23基点cb3665fdの旧191セル/保存出力を保持し計202セル。
新11セルと全文fresh実行を照合。旧本文/新見出し/保存図/末尾見出しの4改変を拒否。
検査記録の保存先のテストで前節パスの残存を検出しRED→GREEN。前節記録は元の全バイトへ復元し、M24記録だけを作った。
Book/portal×1440/1000pxの16状態/16画像で全trace、根、MC誤差棒、価格改変拒否、文字切れを確認。
Book数式971個・エラー0。portal閾値/MC図の1000px画像を目視した。

## 回帰・ゲート

既受入23節のbrowser・runtime probe・個別pytest計1,803件・C:/F:復元はPASS。22節再利用・1節再描画、追加保存373,236バイト。採用D1パスとSHA-256を固定した。
参照/数値/notebook/統合の4--check、ruff、台帳--check-artifacts、releaseと全hullkit+report pytestを検証する。
全hullkit+report pytestは3,601 passed・6 skipped・既存warning2件。4ゲートとその他の検査もPASS。独立最終レビューの確定結果は最終追記する。

## 適用範囲・判断

欧州型・定数GBM。American exercise、smile、確率的金利/変動率、取引費用は対象外。
M23のNaN gate保留とM22の時点説明P3は旧節の保留として保持し、M24では有限値拒否を検査する。
歴史M23 pytestは後続4.14だけを除いて基点比較。M22既存検査は後続4.13/4.14を除き、M24が旧191セル全体の保存を担う。
正の極大r=10000は割引項が0となる表現可能な限界で、call-on-call=S exp(−qT2)を検査。
負の極大r/負の極大qなど表現不能な計算はValueError。恣意的なrate上限を追加しない。
