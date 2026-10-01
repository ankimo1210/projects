# §26.6 Cliquet：受入記録

**判定：accepted。** 日付：2026-10-01。Hull 11e Global Edition p.618のCQ01–CQ06を照合した。
[原典照合とレビュー](SECTION_26_6_REVIEW_2026-10-01.md)、[M23統合記録](validation/section-26-6/m23-check.json)を参照。独立最終レビューはこれから実施する。

## 実装と原典

通常のATM vanilla 1本とn−1本のforward-startを足す単純型call／putを専用APIに実装した。
最初のstrikeはS0、以後は各期開始の株価にresetし、正の株価差を各期末に通貨で支払う。
各成分はS0 exp(−q start)×単位ATM BSM。callは既存forward_start_call、putはnormalized putを使う。
全給付の満期一括割引と固定notional returnは別契約。既存pricing・hullkit.__init__・production依存は変更しない。
APIは市場broadcast、非空1D・正・厳密増加の共通支払日、S>0・σ≥0・有限実数を要求し、無効／overflowをValueErrorで拒否する。

## 独立数値

原典に印刷例はなく、全数値は合成。hullkit／正規CDF公式を使わない二増分密度求積60ケースで
API差最大9.9476e-14通貨、求積誤差見積り最大3.28948e-10。
合成市場S=100,r=5%,q=3%,σ=20%、支払日.5/1/1.5/2年は
call=23.58483577816892、put=19.75071882528578。
各期成分和、spot同次性、call−put cashflow差を照合した。
単純型はcall／put×等間隔／非等間隔の4例・各524,288経路。制約比較の単純型を含む求積との差は
最大1.415254標準誤差で6SE以内。
参照price/reset/discount/capの4改変と、実APIを固定strike／満期一括割引／固定notionalに変えた3変異を拒否した。

## 教材と実画面

vol10 §4.13.1–4.13.6の11セル・共有4図を追加。M22基点14c94ac2の旧180セルと保存出力を保持（計191セル）。
resetと給付、各期PV、満期固定の回数比較、複雑条項のMC診断を示す。
制約図だけS=100,r=q=0,σ=20%、4支払日。総額floor 5/cap 20、各期cap 5、95–105で当期支払後に終了を比較する。
r=0で精算時点の割引差がないと明記。95%区間は平均の標本誤差で、求積・モデル誤差ではない。
notebook4改変を拒否、fresh全文実行を照合。Book/portal×1440/1000pxの16状態・16画像、
全trace・給付customdata・MC誤差棒・価格改変拒否がPASS。Book数式919個・エラー0。
1000pxのportal reset／制約図を目視した。

## 回帰とゲート

既受入22節のbrowser・runtime probe・個別pytest計1,728件・C:/F:復元はPASS。21節再利用・1節再描画、追加保存481,959バイト。採用D1パスとSHA-256を固定した。
参照・数値・notebook・統合の4照合、ruff、全hullkit+report pytest、台帳の成果物照合、releaseを実行する。
全hullkit+report pytestは3,522 passed・6 skipped（既存warning2件）。その他の全ゲートもPASS。独立最終レビューの確定結果は最終更新で記載する。

## 適用範囲

公開APIは定数GBM・株価差の単純ATM call／put列。global/local制約と終了は教材用MC診断で公開APIには含めない。
固定notional return、実市場smile、確率的金利・変動率、取引費用は対象外。
M22のP3（図の時点と価格例の時点の本文対応）は前節の保留事項として維持する。
