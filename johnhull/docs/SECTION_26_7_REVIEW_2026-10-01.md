# §26.7 Compound：原典照合とレビュー

日付2026-10-01。Hull 11e Global Edition pp.618–619。基点cb3665fd。

## 原典と独立照合

4契約・二つのstrike/行使日、T1での内側価値、aにS*・bにK2、4式の符号/相関を原典と照合した。
call-on-callとcall-on-putは異なる臨界株価を用いる。内側putの上限以上のK1では根なしでも価格を与える。
原典に印刷例がなく、合成基準価格/2根と104条件付き密度求積・4 MCを固定した。
独立参照はhullkitと二変量CDFを呼ばない。求積と公式の最大差5.57e-12、根残差7.82e-13、MC差1.737656SE。
strike入替、相関0、根変更、NaNの実装変異を拒否する。

## 表示・保存

旧191セルと保存出力を保持し新11セルを追加。全202セルfresh出力と共有図のdata/layoutを確認した。
16状態/16画像、全数値trace・臨界点・MC95%区間・価格改変拒否がPASS、Book数式971個・エラー0。
portalの閾値/検証図1000pxを目視した。
既受入23節のbrowser・runtime probe・個別pytest計1,803件・C:/F:復元はPASS。22節再利用・1節再描画、追加保存373,236バイト。採用D1パスとSHA-256を固定した。

## 実装者の判断

- 既存m18 worktreeを新M24 branchで再利用する。build/gateを新たに検証し、古い生成物を採用するリスクを抑える。
- 正の極大rateが表現可能なcall限界を持つので、恣意的に拒否せず限界値を検査する。異常なrateの一般的数値解析を網羅した意味ではない。
- M23歴史pytestは後続4.14だけを除き、M22の既存除外は4.13/4.14を含む。除外を誤るリスクはM24の旧191セル全体比較で検出する。
- 計画のregistry属性例は既存FigureSpec.idに訂正した。実際のテストは当初からidを使う。属性の判断を誤ると登録検査が失敗するが、公開APIの変更は不要。

## 独立最終レビュー

未実施。別担当の一度のwhole-branch reviewを行い、Important/CriticalはRED→GREENと全suiteで修正、Minorは保留記録にする。結果と判断範囲はこの節を置き換えて確定する。

二変量正規CDFの定義と符号恒等式は[Hull Technical Note 5](https://www-2.rotman.utoronto.ca/~hull/TechnicalNotes/TechnicalNote5.pdf)を参照。本文の4桁近似を転記せず、相関角度積分を独立条件付き求積と照合した。
