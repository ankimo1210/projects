# Ch16–21 軽量受入 — 2026-10-07

目的：古い章からの受入を進め、P4（Ch10–21）の残り54節を完了する。
対象54節・93要件、計算46節・説明中心8節。基点`99476dbc`、
P4計算完了時のsourceを継承したローカル`codex/johnhull-acceptance`で作業する。
開発側mainのP8や研究変更は含めない。
方針は[fast-v1](FAST_ACCEPTANCE_GUIDE.md)、判定の正本は台帳と
[統合記録](validation/fast-ch16-21/acceptance-check.json)。

## 対象と検証

原典はHull 11e Global Edition、PDF SHA-256
`8bc6e2f04fad95e4eeb40d0526219ba5f9228ee3d2ea3eaaf80870bdf7ccb482`。
下調べの全要求IDと本文を保持し、日本語の節別補足を
`report/site/chapters/ch16.html`〜`ch21.html`へ配布する。

- private8モジュール・46 testファイルを各節へ対応付ける。既存計算の独立実行は450 passed。
  受入検査25ケースを含む対象一括実行は475 passed。追加検査の欠落拒否もRED→GREENを確認した。台帳41 testsを合わせ計516 cases。
- 要求は数値78・説明15。算術を含む§16.3/5も数値要件を残す。
  説明中心は§16.1/2、§18.2、§19.3/10/14、§20.3/7の8節。
  数値verifiedは混在要件の計算部分を指す。原典Table19.5の再価格、Table20.1の実測、
  Tables21.1/2の全乱数の再生を検証済みにはしない。
- 全54節・93要件の文章/数式115個/表3つ/リンク/横はみ出しを幅1280で検査し、代表6画像を目視した。
  要件の同時欠落、本文の置換、数式/表欠損を拒否する負の対照を含む。
- 全suite、Book全build/巡回、全節2幅の画像、両保管庫復元は承認済みfast-v1で省略。
  補足HTMLのMathJax CDNにはオンライン接続が必要。既存Book本文/図の再検査は含まない。

## 原典差・制限

- §16.3 p374の「IAS 2」は実際の印字。[該当基準はIFRS 2](https://www.ifrs.org/issued-standards/list-of-standards/ifrs-2-share-based-payment/)であり、原典の誤記と推定する。
  付与日公正価値の認識と著者の毎期再評価案を分け、付与年全額費用という本文の簡略化を現行の一般則にしない。
  ESOは期待寿命BSMの近似、離職・vesting・行使を持つ木、報酬の算術を区別する。
- §17のbeta保険はCAPMの条件付き期待シナリオ。任意の実現経路を確定保証しない。
  レンジforwardの表示K2=1.3414には未丸め費用差.000012329がある。指数5183と未丸め5183.2957も分ける。
  FXのquote・国内/外国金利・notionalを揃える。
- §18では建玉と清算cash、futuresとforwardの測度、premium型とfutures-style quoteを分ける。
  原典の契約倍率は刊行時点の例。現在の契約仕様や担保cash利息の承認ではない。
- §19.4 Table19.3は精密256337.58669ドルと印刷256600ドルに262.41331ドル差。
  全21行の表示帳簿と独立資金会計は確認するが、元の非丸め入力不足を金利変更で消さない。
  Tables19.1/4の成績は無利息/無割引費用で、資金口座付きPV費用とは別。
- §19.11原典bookが不足し21セルは読取り。合成bookの2週・7×3完全再評価と独立Q求積だけを数値verifiedとする。
  §19.12のfactor4桁/未丸めの21GBP差、§19.13の88/92百万の時間近似は保持する。
  Greekの変数固定規約、1.0/1point/1bp、局所近似と大shockを分ける。
- §20.2の実測FX系列、§20.6の実測IV応答係数は不足。PとQ、合成例と実測を区別する。
  IV補間/total variance補間、無裁定診断/surface修復も別。修復は対象外。
  Table20.3 K56は印刷call1.05からIV49.885736%、未丸めから49.933602%。原典49.0%との差は価格丸めだけでは説明できない。
  密度の二階差分は価格丸めを増幅し、勝手な正規化や負値clipをしない。
- §21は格子上行使と連続停止、escrowed配当木と一般cash-jump、post-step projectionとLCPを分ける。
  Tables21.4/5の計462セルは照合するが、丸め境界の原著中間精度は未確定。
  全乱数標本不足、MCの先丸めCI、QMCの独立scramble/batch SEを明示する。
  control variate等の分散/格子改善を普遍的に保証しない。

## 検査と独立レビュー

既存計算46ファイルの独立再実行は450 passed（共通venv、8.21秒）。新しい重大数値不具合は0。
原典の重点確認はp374/425/462/488、独立DecimalでTable19.3の差を確認し、K56のIVを独立求根した。
新教材の93要求ID・本文・読み方は元draftと完全一致を独立確認した。
独立レビューでSOFR premium quoteを.05（125ドル）、Week9株式価値の増分と損益を−4.1千、
vegaの例番号をEx19.6、保険資産/floorを90/87百万、N4木の節点を各15・計30へ修正。
期間平均volと区間forward volも累積分散の積分式で区別した。
丸め確認の旧未実施表示とS=0境界の表記を修正し、guard欠落を拒否するwrapperを追加した。
新guardの独立実行は25 passed、更新画像も確認済み。
最終未解決はCritical 0 / Important 0 / Minor 0。6代表画像の切れ・重なり・数式欠落は0。
初回browserは下調べ用P8相対リンクの不備を拒否し、開発向け参照を除いて再検査PASS。
数値コードは変更していない。

## 登録と次の作業

登録はP4受入112/112、全体225/306（73.5%）、未評価81となる。
旧171受入と対象外252行の判定を基点と完全一致で保持した。件数試験の期待値を更新し、freshな台帳41 testsとnative source/artifact検査がPASS。
main統合・公開、既存Book本文の改訂は未実施。次はCh22–25の36節を同方式で進める。

## 再実行

WSLのworktree rootから共通venvのPython、設定済みPYTHONPATHを使う。
`uv`で別venvを作らず、Git/buildはLinuxパスで行う。

```bash
python johnhull/scripts/fast_acceptance_advanced_options.py build
python johnhull/scripts/fast_acceptance_advanced_options.py test
node johnhull/scripts/verify_fast_acceptance_options_browser.cjs docs/acceptance/fast-ch16-21.json
python johnhull/scripts/fast_acceptance_advanced_options.py check
python johnhull/scripts/fast_acceptance_advanced_options.py register
# commit後は日時を再生成しないread-only検査
python johnhull/scripts/fast_acceptance_advanced_options.py verify
```

新adapterは前便の固定済みcoreを別namespaceで再利用する。Ch21だけでも木/MC/FDの3モジュールがあるため、章一律ではなく節ごとに実装/testを宣言する。
前便の生成器、browser検査器、教材、数値証跡のsourceは変更しない。