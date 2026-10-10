# M7 保存済み算術・資源の独立確認
日付: 2026-10-10

**限定判断: PASS。** 原M7の保存値・費用・来歴に、この範囲で新たな欠陥は見つからなかった。金融資格はunknown、正式budget/phase承認と全工程速度保証はfalseを維持する。今回の著者はbounded checkerを実装した担当なので、source/checker自体の独立承認は主張しない。

## 原形状と算術

- 各モデル: 原state00、N4096、13再較正query、coarse768/fine1536、seed3631740690、16chunk×256。各106,496 payoffが全有限。全query/path statusはsupported、原failure-date NaNは各106,496個を保持。開始前の同形状NaN義務も保存済み。
- 全payoffから3幅のS/Q Greeks、選択幅sample、平均/SE、16block、全共分散、scheme差分・幅差分を独自の和/中心化積で再計算した。比較34,149件・1,692,611値（alias再照合を含む）、rtol2e-9/atol2e-10、最大差7.1054e-15。
- 保存call-refinementはHeston39/local52receipt。13点の幅別座標、保存CF価格/保存local空間配列の補間算術から返却Greeks・選択幅・refinement差を照合。117保存多項式点の残差/微分も算術確認した。基礎CF/PDE精度、full-domain根の資格判定の代わりではない。
- 全8artifact/17physical packsのSHA・ZIP/NPY header/型/形状/expanded bytesを確認。256MiBはNPY header込み各chunk。81source・39input・61元observationファイルは前後bytes不変。新RNG/CF/PDE/SDE生成・全suiteは実行していない。

## 実費とcap

|原component|親wall s|原child CPU s|最大個別RSS B|今回baseline refinement s|
|---|---:|---:|---:|---:|
|Heston|13.744000597|13.725373000|853,426,176|0.040296934|
|local|90.384455612|90.308574000|853,979,136|59.122619357|

外側の原全M7は104.215731821s/child-tree CPU104.624358s。各600s/個別RSS4GiBは行政上限で、runtime予測ではない。観測cap/超過/未実行query/observer errorは0。RSS値の不明観測countも0だが、outer自分の最終receipt書込/stdout費用は原unknownのまま。

両baselineの原expense IDは independent-selected-call、scope independent_call_refinement。原wall clock: Heston35141.374109538→35141.414406472、local35154.792173605→35213.914792962。local測定の大半をこの新call refinementが占める。

各433expenses=driver16+payoff416+baseline1。driver-mapは同じexpenseへのaliasなので二重加算しない。同seed/hashでも両モデルの実生成費は両方残す。payoff実work122,683,392+driver6,291,456/model、宣言保守work163,577,856/modelを区別。旧M4/M5のreused table費用は歴史として保持し、今回へ再加算しない。native未itemize wallはH0.022805264/local0.018409608sで、0補完しない。outer費用は内側の親/expenseを包含する。

## 保持する未検証と監査履歴

native normal配列は未保存。seed/digest/chunk metadataだけを照合し、新normal生成やSDE replayは行わない。independent_path_generation / full_common_domain_call_fit、original graph controls={}との金融同等性、基礎CF/PDE精度を未検証として保持。

監査v1–v4の失敗はheader込みbyte定義、bool差分、refinement queryの別順序、報告keyの仮定による。各原script/log/failure/costは保全した。v5は全原数値/費用照合PASS。全5監査childの費用は別all-audit-costs.jsonに失敗込みで集計し、準備・読取・自己最終receiptの未計時部分はunknown。元M7の失敗/cap/unknownをPASSへ書き換えていない。

詳細: 同prefixのresults/resources/decision/before-bindings/after-bindings/all-audit-costs/manifest。
