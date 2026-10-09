# Task 5 fixed-domain saved replay adapter

## 結果

owned replay source/tests 2ファイルのみ実装。`evaluation_domains=None`と`saved_cache=None`をprivate keywordとして追加。金融qualificationはunknownのまま。

- B生成cacheと同じcanonical/detached per-date descriptorを渡し、選択・finite node探索・RNGを行わない。
- 保存cache指定時は4domain keys（geometry/schema/bounds/sheets）と元full axes/f/16blocks/support/t0、original N、retained group statuses/means/blocks/source parametersを照合。
- integer domain rangesはexact、物理座標・金融値は既存rtol2e-10/atol2e-11、NaNとshapeを保持する。
- default/legacy cacheのdomain keys欠落/Noneは互換。explicit unavailable dateはfull-domain fallbackへ戻さない。
- 生成側full-label cache（N×threshold samplesを含む）とも比較するが、replay cacheにそれらの全標本を追加保持しない。共通の元summary/status/countを照合。
- local t0専用6spot sheetとmain4spotを混同せず、原40groups/N32/16blocks/fullarraysを保持。
- selected box外の未知node/原全arrayも照合対象。金融精度やbox selectorの採用を主張しない。

## 検証

- corrected RED：isolated child processで記録済みbaseline replayを実行し19failed/82passed。source差戻し/Git操作なし。
- GREEN：101passed (1.01s)。
- Ruff check PASS、Ruff format実行後format --check PASS（対象2filesのみ）。
- AST照合：旧test/fixtureの変更0。旧sourceで変更された関数はrebuild_asian_cacheのみ、追加private比較helper2本。
- canonical B dependency sourceとdesign review、owned source/testSHAは同名JSONに保存。

当初のREDには新testのsurface引数抜けが1件あり、fixtureを訂正後にbaseline全反例を再実行した。local fixtureのdeep-ITM thresholdがunknownとなる事実も保持し、全4必要nodesがreadyな検証用calendar/threshold fixtureへ変更した。金融sourceのunknown判定は変えていない。

## 次

rootのrunner配線と別担当による独立sourceレビューが残る。全suite/正式pilot/freeze/mainは今回未実行。元review/測定証跡は変更なし。
