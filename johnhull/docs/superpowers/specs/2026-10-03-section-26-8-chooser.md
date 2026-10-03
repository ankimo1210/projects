# M25 §26.8 Chooser Options

日付2026-10-03。main基点5013f2d4。承認済みの節受入工程を継続する。

## 契約と範囲

Hull 11e GE pp.619–620。T1で、同じ行使価格K・満期T2の欧州call/putのどちらを保有するか選ぶ。T1での価値はmax(c1,p1)、給付の決済はT2。定数r,q,σのGBMを仮定する。原典に印刷数値例はなく、教材例は合成と明記する。異なるstrike/満期のcomplex chooser、American、smile、確率的金利は対象外。

複製はT2のcall一枚と、行使価格H=K exp(−(r−q)(T2−T1))、満期T1のputをw=exp(−q(T2−T1))枚。callを選ぶ境界はS1≥H（同価値ならどちらでもよい）。T1=0はmax(c0,p0)、T1=T2はstraddle、σ=0は決定的なmax(c0,p0)、T2=0は|S−K|。

## インターフェース

専用 `hullkit.chooser.chooser_price(S,K,r,sigma,T1,T2,q=0)`。有限実数S,K>0、σ≥0、0≤T1≤T2。全市場入力broadcast、scalar float/ndarray。無効入力・表現不能な計算はValueError。既存API・root exports・production依存は維持。

独立 `build_chooser_reference.py` はhullkitを呼ばずerfc vanillaとT1の対数正規密度からmax(c1,p1)を求積。境界およびinner vanilla遷移±3/±10幅で分割し近接満期も検査。64市場ケース、524288経路×4条件付きMC、合成価格ピンを保存。API差/同次性/複製恒等式は1e−8通貨、MCは6標準誤差。保存参照・実APIの誤りと非有限を負の対照で拒否。

## 教材・受入

vol10 §4.15.1–6に11セル、chooser_choice/chooser_package/chooser_timing/chooser_validationの4共有図。旧202セル・本文・保存出力を完全保持し213セル。Book/portal×1440/1000pxの16状態/16画像で全trace、境界、複製、価格、誤差棒、数式・配置を確認。

台帳CH01–CH06の説明・式・コード・数値・実画面の5軸を検証。既受入24節をD1で検査し、現在依存の必須hash、採用記録、C:/F:両保管庫復元を照合する。受入25・未評価281、P2 8/8へ更新する。全hullkit+report pytest、ruff、参照/数値/notebook/受入--check、台帳--check-artifacts、release--require-trackedが必須。独立最終レビュー一度、重要指摘はRED→GREENと全suiteで解消する。M25のmain統合・pushは最後の選択を待つ。
