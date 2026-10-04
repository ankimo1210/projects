# §28.3 Martingales — M28受入

日付2026-10-04、原典Hull 11e GE pp.675–676、main基点0aa51b13。

## 完了条件と範囲

MT01–MT06の5軸で条件付き定義/式28.14/式28.15を照合。正値・無収入のnumeraire、可積分性は数学的追加条件として原典本文と区別。一般のzero driftは局所martingaleに留まり、数値実演は有限時間の定数GBM。全数値はsyntheticで印刷pinなし。

- signed same-Wiener比のrelative driftとlog drift、λ=sgのdrift相殺/別測度の非零drift、finite第二モーメント。
- 6市場、9時刻/状態の解析mean、262144×9直接条件付きMC。t=0の異なる比は別初期市場。
- 同じH=(S_T−100)+をQ/G測度で評価。S0=100,G0=80,r=.04,T=1.5,sf=.3,sg=±.15。独立価格17.24948327902953、確率的G_Tの分母とmeasure driftを保持。H/G≤S/Gで可積分性を確認。
- API最大誤差7.105427357601002e−15、求積4.4007170449362294e−11、MC最大1.9903212092033933SE。許容1e−12/1e−9/5SE、図の95%区間と5SEを区別。保存4改変/API4変異拒否。
- 新6B.1–6B.6の11セル/計246、旧235本文/出力/Plotly保持とfresh全文一致。notebook4変異拒否。
- 4共有図、Book/portal×1440/1000の16状態/16画像、全trace/誤差棒/MathJax/幅700px/表示改変拒否。1000pxのconditional MC/pricing、Book Itôを目視。
- portal190図/12テーマ（exotics78）、public72/private29。Book140 warningsは既存136+新Plotly4。

## 既受入節の回帰

既受入27節のbrowser・runtime probe・個別pytest計2,056件・C:/F:両保管庫復元はPASS。0節再利用・27節再描画。共有CSS変更による保守的な再描画。採用記録の再描画画像payloadは19,514,628バイトで、重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。
clean39f47b32からD1を実行。§28.2は初回redraw、旧26節は直接redrawn基点へのreuse要求から共有CSS変更によりredrawへ移行。過去記録/画像は保持。

## 台帳・検証

受入28/未評価278、P3 3/37。統合記録は[ m28-check](validation/section-28-3/m28-check.json)、台帳成果物PASS。全suite/独立最終レビュー/main統合は検証中。

全hullkit+report 3,986 passed・6 skipped・既存warnings2件（186.50s）。変更Python20ファイルruff、4--check、台帳成果物28/278 PASS。独立最終レビュー/main統合は検証中。
