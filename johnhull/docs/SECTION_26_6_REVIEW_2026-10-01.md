# §26.6 Cliquet：原典照合とレビュー

日付：2026-10-01。Hull 11e Global Edition p.618。統合基点14c94ac2。

## 原典と実装

call／putの列、最初のATM vanilla、以後のATM forward-start、各期の支払を原典と照合した。
株価差を通貨で支払う単純型を実装し、総額上限・下限と範囲終了では単純和が使えずMCが適するという説明を教材に反映した。
各期cap 5は総額capとの違いを示す合成比較例で、原典の印刷契約・価格ではない。
制約診断はr=q=0に分離し、支払後の終了と総額へのfloor/cap適用を明示した。

## 独立計算と表示

二つのGBM増分の密度求積を各期ごとに行い、支払日t_iから割り引く。
60ケースと曲線でAPI差9.9476e-14、多時点MC各524288経路×4例、最大1.415254SE。
call−put差・同次性・成分和、価格・reset・割引・cap改変と実API3変異を検査。
旧180セルの本文・保存出力・Plotly値を保持し、全文fresh実行で一致。
両画面16状態のtrace数値、customdata、MC95%平均区間と文字切れを確認。既受入22節のbrowser・runtime probe・個別pytest計1,728件・C:/F:復元はPASS。21節再利用・1節再描画、追加保存481,959バイト。採用D1パスとSHA-256を固定した。

## 独立最終レビュー

これから別担当がブランチ全体をread-onlyでレビューする。結果・指摘・判定留保を記録し、
Critical/ImportantはRED→GREENと全suiteで修正、Minorはexecuting-plans規約に従い保留する。
