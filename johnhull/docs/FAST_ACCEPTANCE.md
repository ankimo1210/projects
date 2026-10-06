# 受入の軽量化（fast-v1）

承認・適用開始：2026-10-07。ユーザーの「どんどん行こう、受け入れ作業時間かかりすぎるから条件を緩和してもいいよ」に基づく。

目的は古い章から受入を進めること。今回の範囲はCh2–9の70節。
既存の節別台帳schemaと5観点は維持する。D3の全節2面2幅の証跡とは区別する。

- 原典本文の全要件、単位・符号・前提・表示精度は減らさない。
- 計算49節は既存の原典値固定と別方法の独立参照をfresh実行する。
  原典入力のない価格を合成値で埋めない。式のみの節は合成例と明記する。
- 日本語の節別補足教材を原典順に配布HTMLへ生成し、全70節の見出し、全要件、
  表、数式、リンク、横方向のはみ出しを幅1280で自動確認する。
  各章の代表1節だけ撮影・目視する。全節の目視・別幅・Book側の再巡回は省略する。
- 追加グラフは文章・受払/単位付き表で学習上の関係を説明できる要求では省略し、
  台帳に理由を残す。既存巻のグラフを今回の画面検査済みとして数えない。
- 関連計算テスト、受入検証器、台帳検査を一括実行する。6千件の全suiteと
  全巻notebook再実行・Book全体再buildを各章で繰り返さない。
- 原典、教材、計算、試験、ブラウザ検査器、実行結果、配布HTMLのSHA-256を保存する。
  代表画像はローカル保存。二重保管庫への全件保存・復元は今回の必須条件から外す。
- 原典不足・不一致は要求ごとに残す。失敗した節をacceptedにしない。
  main統合、公開、現行制度の調査、章末問題は別工程。

## 実行計画

1. Ch2–9の原典下調べを、内部の作業予定を除いた説明・要点・数値・前提へ整理する。
2. 49計算節とテストの対応を固定し、109件の原典値/独立参照を一括実行する。
3. 補足HTMLを生成し、全節/全要求を巡回、代表8画像を確認する。
4. 独立レビューの重要指摘を解決する。台帳とP6状態を更新する。
5. 件数固定試験の期待値だけ更新し、台帳41ケースを再検査する。
   Ch1の以前の全suite結果は保持し、この件数変更による証跡更新を明示する。
6. 成果をローカルコミットに保存。次はCh10から同方式で進める。

既存教材を変更しないため、補足教材の受入と既存Book本文の改訂を区別する。
古い受入33節の判定・証跡は保持。Ch1の10節も判定・教材・40画面は保持し、
台帳件数の変更に伴う試験metadataだけ再検査して参照を更新する。

## 再実行

リポジトリrootで既存Python環境を使用し、PYTHONPATHに当該checkoutの
`johnhull/hullkit/src`、`johnhull/report`、rootを指定する。

```
python johnhull/scripts/fast_acceptance.py build
python johnhull/scripts/fast_acceptance.py test
node johnhull/scripts/verify_fast_acceptance_browser.cjs
python johnhull/scripts/fast_acceptance.py check
python johnhull/scripts/fast_acceptance.py register
python johnhull/scripts/verify_section_ledger.py --write-summary
python johnhull/scripts/verify_section_ledger.py --check-artifacts
```

画像二重保管と全体suiteは省略を明記した追加確認であり、上記PASSへ混ぜない。
