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

別担当が14c94ac2..a0831d8cをread-onlyで確認した。Criticalなし、Important1件、Minor1件。
元の判定はWith fixes。価格計算の誤りは見つからなかった。
対象9ファイル83テスト・M23統合--check・台帳--check-artifactsがPASS。
M23数値/notebook/browserの必須ハッシュ46項目を個別削除してすべて拒否した。
portal reset/limitsの1000px画像を目視。全suite・build・browser生成・全文notebook実行は作者の証跡を確認し、再生成しなかった。

### Important1：D1必須ハッシュ欠落（修正）

元のcheck_d1_payloadはsource/artifact辞書が非空かだけを見ており、残るキーだけを照合した。
§26.5のsourceから_forward_start_lesson.pyを削除し、digestをそのパスだけstale扱いにするとcheck_d1がPASS。
portal HTMLのartifact hash欠落も受理した。既存統合--checkではD1自体のhash変更を検出するが、
統合記録の再生成時には不完全なD1を再採用できた。現行証跡の破損を示すものではない。

修正では現行の依存宣言とPython import閉包を使い、D1生成側の_source_hashesで必須source集合を再構成する。
記録側のfingerprint／hash辞書から必須集合を決めない。artifactは宣言されたBook/portalの2ページを要求する。
collectorが消費するpython_sources/data_files/verifierと共通ファイルを再構成し、キー列挙のためにHTML描画は繰り返さない。
このcollector/fingerprint/record/storeの4helperも統合記録のsource hashesに加えた。
§26.5の81必須ハッシュを1件ずつ落とす2パラメータテストを追加。
2 failed（DID NOT RAISE）→修正後2 passedを確認。修正後の全hullkit+report suiteは3,524 passed・6 skipped・既存warning2件（108.43秒）。
executing-plansに従い1回の修正パスで対応し、別担当への再レビューは行わない。

### Minor1：NaNのAPI変異（P3、保留）

数値verifyのmax(errors)>toleranceはNaNを拒否しない。call/putを双方NaNを返す関数へ
メモリ内で置き換えるとverifyは例外なくNaN統計を返した。
現行APIは結果の有限値をチェックし、価格ピンテストもPASS。現行価格の不具合ではない。
実装者は影響をMinorと評価し、規約どおり今回の修正パスには入れず記録した。
将来の数値gateの有限値明示チェックとNaN変異テストを改善候補とする。

## 判断を保留した範囲と実装者の判断

1. M22の既存P3（経路図と価格例の時点）：明示された前節の保留事項として維持する。旧セルの変更を避けるが、読者の時点対応の難しさは残る。
2. 制約型の公開API・固定notional return・smile/確率的金利・変動率：承認済みの単純GBMスコープ外。図は診断であり、範囲拡大には追加の設計・実装・検証が必要。
3. 旧22節の金融モデル全体の再導出：pricingは変更していない。D1でbrowser/runtime/pytest/両保管庫と現行依存を確認する。全面的な再導出をしないため、既存モデルの未発見の問題が残る可能性はある。

追加の実装判断：M22 pytestは後続§4.13だけを除いて基点比較し、現在の全巻保存はM23が旧180セル・保存出力すべてで確認する。
除外範囲を誤るリスクはこの全巻比較で検出する。M22本文と保存出力は変更していない。
