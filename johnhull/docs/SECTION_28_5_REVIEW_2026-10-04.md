# §28.5 M30 最終レビューと修正

更新2026-10-04。[raw report](validation/section-28-5/final-review-raw.md) は変更せず保存。対象 `7ac2f470..4c2ce9ff`。sole fresh gpt-6-astra/high、Critical0／Important1／Minor2、With fixes。fresh88 tests／4 --check／独立160 random市場／132求積モーメント／4画像を確認。

## I1修正

保存MCのmean・SE・z・summary・digestを整合改変すると、教材単体で不可能な負call平均や大幅な正値偏りを受容した。正式受入gateは拒否していたが、消費時の契約違反としてImportantを維持。

負call平均、正call平均、密度平均、条件付き平均の4回帰を先に実行し、全4件がDID NOT RAISEでRED。固定seed／262144 samplesからproducer結果を再生成し、表示前に結果digestを完全照合する修正後はlesson全20 tests GREEN。reference／現行source inventoryをキーに、検証済みreplayのimmutable digestだけを1件cacheする。scriptsの相対importは一時private packageで解決し、Python pathを変更しない。

notebook全268／旧257、独立teacher／数値／統合、fresh browser16/16、ruff19を確認。Book／portal HTMLの値は変更していない。既受入29D1の現行必須source／artifact／両保管庫は統合gateで再検証してPASS。既存D1の対象producerは今回のprivate consumer変更で変わらない。証跡を手動再署名していない。

I1の1回のfix passは4回帰RED→lesson20GREEN、修正後全suite4223 passed／6 skipped／従来warnings2（293.49s）で完了。Critical0／未解消Important0、Minor2保留。4 --check、ruff19、16表示、29D1現行hash／両保管庫／台帳成果物／tracked release PASS。main統合はこれから。 再レビューは行わない。

## Deferred minors

- M1：条件付き一次・二次求積とtail boundは現在正しいが、将来の求積単独破損を自動合否判定に接続していない。reviewerは132状態を独立確認した。
- M2：specのmissing-RN変異は実際の8 controlsに含まれない。正常raw RN・価格は正しい。省略／逆転の明示対照は後続。

## 判定を置いた範囲

raw reportのDeclined to judge全8項目は [executor ledger](validation/section-28-5/execution-ledger.md) にroot判断と誤りの費用を記録。一般SDEのtrue保証、確率金利engine、極端float精度、大規模因子、replay費用、将来prep、既存AGENTS循環、main統合を区別する。

極端入力の観測限界：value=1e-300／drift710／h1は中間expで拒否。value1e308／drift−745は数学上約2.82235e−16に対して4.940656e−16を返す。通常教材のfixtureに影響しないが、全float域精度を保証しない。
