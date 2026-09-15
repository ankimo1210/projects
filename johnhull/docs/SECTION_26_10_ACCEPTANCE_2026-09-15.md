# §26.10 Binary Options：受入条件と検証証跡

**判定：D01–D06を満たした。** §26.9と合わせて2節を受入済みとし、残る304項目は未評価。
この判定はCh.26全体や全巻の完成を意味しない。

日付：2026-09-15（JST）。開始コミット：ad3b9ab5e501654acdbe61b331b89104b41502c6。\
原典：Hull 11e **Global Edition** §26.10、印刷・物理pp.622–623。本文を節末まで再照合した。\
教材：[vol10 notebook](../volumes/10_exotics_martingales/exotics.ipynb) §2.1–2.6 ／
[portal](../report/site/exotics.html#fig-binary_payoffs)。\
計画：[M2b](superpowers/plans/2026-09-15-section-26-10-m2b.md) ／
[M2a時点の要求と不足](SECTION_26_10_REVIEW_2026-09-15.md)。

## 要求と証拠

| ID | 満たした学習要求 | 本文・実装・検査 |
|---|---|---|
| D01 | cash/asset × call/putの4給付、単位、等号規約、実際の決済と片側極限 | §2.1、[4給付の図](validation/section-26-10/book-binary_payoffs-1440.png)、個別給付・境界のsemantic tests |
| D02 | GBMの前提、4価格、r/q、N(d₂)と資産重み付けN(d₁)の区別 | §2.2、[式と価格表](validation/section-26-10/book-binary-prices-1000.png)、独立密度積分64ケースと各契約の表示価格照合 |
| D03 | call/put両方の満期給付・現在価値の分解。複製時の現金給付額はK | §2.3、[put複製](validation/section-26-10/book-binary_replication-1440.png)、価格分解16ケース、両選択状態の各leg・合計を検査 |
| D04 | 不連続給付と薄い市場での決済リスク | §2.4、4給付図のジャンプ。参照価格・時刻・丸め等の規約を説明。定性的要求なので追加の価格エンジン・数値oracleは対象外 |
| D05 | 正規化spreadとbutterfly、価格密度と満期給付、有限Tのdeltaと満期極限を区別 | §2.5–2.6、[spread/butterfly](validation/section-26-10/book-binary_spreads-1440.png)・[delta](validation/section-26-10/book-binary_delta-1440.png)、幅ごとの給付と独立積分価格の数値微分 |
| D06 | Book/portalの4図、call/put操作、式・軸・凡例・表示値を読める | [ブラウザ記録](validation/section-26-10/browser-check.json)、[検査スクリプト](../scripts/verify_binary_lesson_browser.cjs)、両面・2幅の画像18枚 |

D05は元の補助説明の誤りの是正、D06は配布物の確認であり、原典に存在しない小節を追加したという主張ではない。

## 計算条件と独立検証

欧州型・満期決済、リスク中立GBM、定数$r,q,\sigma$、$S_0,K,T,\sigma>0$。
通貨・年・連続複利年率・年率ボラティリティを用いる。
満期給付はcallで$S_T\ge K$、putで$S_T<K$を採用する。この契約規約は、正の$T,\sigma$の
連続分布モデルでは時点0価格を変えない。図の実際の決済点と片側極限は別トレースで管理する。

既定の合成条件は$S_0=K=100,r=5\%,q=2\%,\sigma=20\%,T=1,Q=100$。

| 契約 | 時点0価格（通貨、小数6桁） |
|---|---:|
| cash call | 49.458109 |
| cash put | 45.664833 |
| asset call | 58.685115 |
| asset put | 39.334753 |

[M2aの独立価格64ケース・分解16ケース](validation/section-26-10/numerical-check.json)を再実行し、
新たな給付・図・deltaの12テストと合わせて**92件成功**。M2aの記録自体は当時の検証範囲を保つ。
deltaの基準値は、閉形式を使わず終端密度を積分した価格の差分から得た。
ブラウザは契約名と小数6桁の価格を行ごとに照合し、給付の境界点・各leg・spread幅・3満期のdeltaも検査する。
合計を保ったままcash legに+1、asset legに−1を加える一時改変は、両ページで拒否された。
恒等式だけを価格・図の独立検証の代わりにしない。

## 生成・画面・回帰検証

[統合記録](validation/section-26-10/m2b-check.json)と[VALIDATION](../VALIDATION.md)に実行結果を保存した。

- vol10は**55セル**。出力型・MIMEキー・正規化された決定的テキストが別実行と一致。計時セルは型のみで、PNG・Plotly payloadの値はこの比較の対象外。図の値は別のsemantic testsとブラウザ検査で確認する。§3以降のbuilder本文・notebook sourceは開始コミットと完全一致。
- portalは**12テーマ・86図**、exoticsは6図。4つのbinaryカードだけを全幅にし、既存カード構成を維持。
- Book全31ページを再構築。ビルダーは36警告を報告した。明示された警告はPlotly MIME30件・見出し5件で、新4図のMIME警告を含む。HTML出力での描画を実ブラウザで検証した。
- Chromium、viewport幅1440/1000で両面の4図と両複製状態を確認。図枠外の文字、軸と凡例、凡例と注記の重複を検査。
- §26.10の数式52箇所が組版され、数式エラー・式の横溢れ・JavaScript例外は0。
- portalは外部通信遮断下で外部要求0。Bookは既存のMathJax CDNを利用。
- §26.9は関連**171テスト**、Book/portal各8契約、静的5図、数式93箇所を再検査。
  [新しい回帰記録](validation/section-26-9/m2b-recheck.json)を台帳へ結び、古いdouble-check記録は履歴として保持した。

## レビューで修正した点

共有図の注記の横欠け、凡例と注記の重なり、軸タイトルと凡例の重なりを修正し、860px幅で独立再検査した。
本文ではbutterflyの$h^2$正規化を明示し、$N(-d_1)$の資産重み付け事象をput側の$S_T<K$として書き分けた。
独立したTask1/Task2レビューと[最終統合レビュー](validation/section-26-10/final-review.md)は承認済み。重大・中程度の未解決指摘はない。最終レビューでは新4図の保存Plotly data/layoutを現行builderの生成値と全件比較し、別途一致を確認した。
スクリーンショットはレイアウト安定後に対象を固定ヘッダーの下へ置いて撮影する。

## 受入の限界

既存の公開価格API・価格ロジック・本番依存関係は変更していない。
$T=0,\sigma=0$、不正入力、点質量を持つ終端分布、全入力域の安定性は今回の検証範囲外。
Bookは完全オフラインではない。モバイル・他ブラウザ・全巻の目視確認は未実施。
本節の受入は、合成条件での教材・計算・配布物に対する判定であり、市場性能の承認ではない。
