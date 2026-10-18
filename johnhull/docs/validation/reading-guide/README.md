# 読むガイド：T0–T2 の検証資料

計画：[2026-10-18 の計画](../../READING_GUIDE_PLAN_2026-10-18.md)。
進捗・検査結果・時間・使用量・停止条件は [READING_GUIDE_STATUS.md](../../READING_GUIDE_STATUS.md) を正本とする。
このディレクトリは検証の対応表と再実行の方法を残す。節の受入台帳を置き換えるものではない。

## 原典との照合範囲

以下は**実装者による照合**。初稿e491b454と修正8e3cbe9dはClaudeが独立検証済み。T2の追加・改訂差分はClaudeの独立検証待ち。
対象は Hull 第11版 Global Edition。今回の範囲では PDF の物理頁と印刷頁が一致する。
抽出本文と PDF の描画画像は公開ファイルに含めず、外部データ領域に保持する。

| ガイド | 原典の印刷頁 | 確認した論点・注意 |
|---|---|---|
| Ch13 §13.1 | 288–292 | 株式と売りオプションの確定終価、金利4%、一般式の複製、現在価格を所与とする意味 |
| §13.2 | 291–294 | 原典の1期間は満期T。多段でΔtへ置換。P/Qの重みと割引率の組、現実の確率p*、脚注の55.96%が当該契約の年率であること |
| §13.3 | 294–297 | 再結合する中間状態の二経路と後退帰納 |
| §13.4 | 297–298 | p=0.6282を使う印刷値と未丸めの価格の区別。Figure 13.7は p.298 の描画でも確認 |
| §13.5 | 298–299 | 行使12と継続価値、根では待つ判断。負のK−Sを負の権利行使価値としない |
| §13.6 | 299–300 | 節点ごとのヘッジ量と、有限の木でのスポット再評価による微分との違い |
| §13.7 | 300–302 | 平均・分散の二式と一次の近似からCRRの枝幅を導く。有限刻みの厳密一致ではない。P/Qで変わる成長率と偶然の変動幅の区別 |
| §13.8 | 302–303 | σ指定の木と固定u,dの木は違う入力。Figure 13.10 の出現頁にも注意 |
| §13.9 | 302–303 | 段数と枝幅の同時変更、再結合と経路依存、欧州価格の収束 |
| §13.10 | 303–304 | 段数比較と行使方式比較を分け、DerivaGem自体のUI動作を検証済みとしない |
| §13.11 | 304–308 | 配当・外国金利・先物の成長倍率と国内金利での割引、指数ポイント・為替の単位 |
| Ch13付録 | 312–315 | U1は確率そのものではない。境界はギリシャ文字αで、成長倍率aとは別記号。p*の再利用、j>αの境界、二つの正規極限 |
| Ch8 §8.1 | 201–205 | 元本配分、受取と損失の逆順、二段目の分母、89.75%と10.25%の意味。p.205も描画で確認 |
| §8.2 | 205–209 | subprime・ARM・teaser rate、LTV・審査の誘因・negative equity、非遡及の範囲、ABX/TABXの損失とLIBOR–OIS/TEDの歴史的観測値 |
| §8.3 | 209–211 | 相関上昇を相関1としない。PDと期待損失、損失5〜6%を負う薄い層、規制裁定とagency costs |
| §8.4 | 211–212 | 刊行時点の対応を信用・流動性・誘因へ結び付ける。将来予定を現在の施行としない |

Ch13の一般的なストーリーは GE pp.288, 308、Ch8は GE pp.208–209, 212に基づく。
Ch8の現在側の補足は、2026-10-18に確認した [BCBS憲章](https://www.bis.org/committees/bcbs/charter)と
[市中協議文書（2019年4月）](https://www.bis.org/publications/201904-consultation-consolidated-basel-framework)の法的地位に限定する。
個別国の現在の適用や施行日程は調査していない。

## 数値の再検査

`numerics.json` は、原典の入力・印刷値・未丸め値・単位・台帳の要求ID・既存テストを章別に対応付ける。
式の定義の0/1、章節頁番号、確認日、文献の刊行年は、新しい数値実験とは区別している。
ガイドのための新しい pricing API や原典外の数値実験は加えていない。

実行コマンドと採用結果は状態文書および検証JSONに記録する。既存テストの出力は、原典照合そのものの代わりにはしない。

## 文字数の数え方

修正版は3通りで数える。①従来方式はソースのUnicode U+3040–30FF / U+3400–9FFF（漢字・かなと同範囲の記号）。
②和文＋約物は、生成HTMLのarticle本文からinline・displayの数式と見出しのリンク記号を除き、同範囲の文字とUnicodeカテゴリーPの約物を数える。
③数式を除く可視文字は、②と同じ本文の空白以外すべて（英数字・記号を含む）を数える。
②③は見出し・頁参照・リンクの表示文を含み、MyST/HTML記法・URL・CSSで付くリスト番号は含めない。
値・対象ソースとHTMLのSHA-256・再計数スクリプトのSHA-256は、T1が `revision-2026-10-18.json`、T2が [t2-2026-10-19.json](t2-2026-10-19.json) にある。

## 環境と再実行

すべて worktree のルート `/home/kazumasa/worktrees/reading-guide` で実行する。
検査用の `uv` ラッパーは、make のレシピが相対 `PYTHONPATH` を代入しても、worktree の hullkit/src と report の絶対パスを先頭へ置く。
この環境ファイルとラッパーは今回のworktree専用。別checkoutで再検査する場合は、両方の絶対パスを検査するcheckoutへ合わせ、下記のimport先表示を確認してから実行する。

```bash
source /home/kazumasa/projects/_data/johnhull/reading-guide/env.sh
cd /home/kazumasa/worktrees/reading-guide
uv run --no-sync python -c 'import hullkit; print(hullkit.__file__)'
make hull-book
node johnhull/scripts/check_book_math.cjs johnhull/book/_build/html
# 既存の証跡を上書きしない新しい出力先を、実行ごとに指定する。
export READING_GUIDE_OUTPUT_DIR=/home/kazumasa/projects/_data/johnhull/reading-guide/new-review-output
node johnhull/scripts/check_reading_guides.cjs
make hull-release-check
uv run --no-sync --package hullkit python johnhull/scripts/verify_section_ledger.py --check-artifacts
make lint
make test
```

ブラウザは Playwright **1.56.0**、Chromium **145.0.7632.6**。新しい2ページは1280pxと390pxで、MathJax・ローカルリンク・外部通信・ページエラー・横幅を追加確認する。
既存の `check_book_math.cjs` は `notebooks/` 直下だけを走査するため、サブディレクトリの新ページは別に確認する必要がある。
`check_reading_guides.cjs` は `READING_GUIDE_OUTPUT_DIR` が未指定・空白だけなら、描画や出力の前に停止する。
数式の内側のはみ出し検査はdisplay数式（`div.math` と `mjx-container[display="true"]`）を対象とし、inline数式の内側は対象外。
ページ全体の横幅検査は行うが、inlineを含む数式の欠けは狭い幅での目視も併用する。

生成物の実体は `/home/kazumasa/projects/_data/johnhull/reading-guide/` に置く。
台帳検証器は外部symlinkを拒否するため、Bookの `_build` と portalの `site` はその実体の **bind mount** とする。
F: の保管庫は既存 `/mnt/f` の接続不良を避け、別の読取専用マウントで参照する。研究RB-F04の既存参照ファイルも main から読取専用で参照し、再計算・コピーはしない。
pytest自体が管理する一時ファイルは、保存先がGit内でないことを確かめる既存テストに合わせ、通常の一時領域を使う。ガイドの成果・ログ・画像・抽出本文は上記データ領域に置く。

worktreeを撤去する際には、通常のignoredファイル・容量・参照先の確認に加えて、これらのマウントを先に解除する。
外部の生成物や原典抽出を削除せず、読後判断と独立検証が終わるまでworktreeと検証データを残す。

## T1 独立レビュー後の修正（履歴）

Claudeの指示書はmain `6c2daf2c` の `johnhull/docs/READING_GUIDE_REVIEW_2026-10-18.md`。
このbranchへmainの変更は取り込まず、指定されたパスから全文を読んで§2を修正した。
初稿の `t0.json`・`verification.json` と過去の出力は保持し、今回の検査・文字数・計測は
`revision-2026-10-18.json` と外部データrootの `revision-20261018-n1-n20/` に別記録する。
新たな歴史的な数値は `numerics.json` の `non_example_numbers`、89.75%と薄いBBB層の計算は同ファイルの各例へ対応付けた。
Bookは `--path-output` で新しい出力rootへ全ビルドし、worktreeの `_build` のbind mountをその生成物へ切り替えた。
以前の `/home/kazumasa/projects/_data/johnhull/reading-guide/build/` は保持している。

N18は次回の共有runtime更新時の要件として保持する。T2などで `shared_runtime.py --write` を行う際は、
各検査に対象commitと実行時刻を記録する。今回 `shared-runtime.json`・`_toc.yml` は変更しない。
`--require-tracked` はoverviewがHEADと一致していることを要求するため、最終commit後に実行する。
この記録の締切り後の結果は、今回の出力rootの `post-commit-checks.json` と最終報告に残す。

## T2 の追加と検査（2026-10-19）

main a115b2cbまでを `codex/reading-guide` へ取り込み、merge commit d040c960でROADMAPの両側の内容を保持した。T2は用語集・モデル地図・overviewの章間地図・Ch8/Ch13の改訂。既存notebook・補足教材・台帳・過去の検証JSON・受入検証器は変更していない。T3は [影響見積もり](t3-impact-2026-10-19.md) だけで、実装していない。

- 正本：`book/notebooks/guide/model_map.json`。索引§1–14・P3/P4の実測178行を135カードへ対応。27本の関係に式の条件と出典、12行の問いの早見表を付けた。インフラ§15とRB-F*研究は除く。
- 生成物：`models.md`、`model_map/figure.json`、`figure.html`、`runtime.html`。生成器の `--check` は書込みせずbyteの鮮度を検査する。Bookの節アンカー・portalの検査を完全に行うには、そのHTMLを先に生成しておく。
- plotly.py 6.9.0 / Plotly.js 3.7.0。JS全文はgzip（mtime=0）＋base64でページ内に同梱し、既存依存のまま追加インストールはしない。DecompressionStreamが必要な図と、JSなしでも読める本文を併置した。ライセンスは `model_map/LICENSE.plotly`。生成HTMLは **2,294,253 bytes**（図のJS込み、Book共通ファイルは別）。追加ファイルは各2 MB未満。
- 新規鮮度テスト20件：索引行の網羅、図とカードの一致、生成byte、無効な関係・空の説明・切れた参照の拒否を確認する。数値の44既存テストと、§13.7の有理係数による展開の独立検算も別に行う。
- 新規ブラウザ検査：6系統、拡大、実際のクリック/タップによるカード移動、選択欄、MathJax・ローカル参照・通信・エラー・幅、JSなしの135カードを1280/390pxで確認する。既存31ページの数式検査とパイロット2章の検査も保持する。本文・数式は390pxの画像でも点検する。
- 数値・頁・記号はGE PDFと照合。カードの読む場所は130節の抽出本文を位置確認に使い、式の記号・特殊化の条件は22頁のページ画像も読んだ。PDF画像・抽出本文はGitに含めない。原典の連続した訳文や図表の再掲は行わない。Hull以外の9出典と確認日はT2の検証JSONに記録する。

新しい出力rootは `/home/kazumasa/projects/_data/johnhull/reading-guide/t2-20261019/`。Bookの `_build` はその `book/_build` へのbind mountへ切り替え、T0/T1/Claudeの過去の出力を保持した。各検査の生ログ、UTC開始/終了・実際のcheckout commit・未コミット差分を含むソース指紋は同rootの `*-check.json` にある。
読むときの入口はworktree側の `johnhull/book/_build/html/notebooks/guide/models.html`（用語集は `glossary.html`）。このパスから開くと、同じcheckoutの `MODEL_INDEX.md` と `report/site` への相対リンクも、ブラウザ検査時と同じ配置で使える。

```bash
source /home/kazumasa/projects/_data/johnhull/reading-guide/env.sh
cd /home/kazumasa/worktrees/reading-guide
uv run --no-sync --package hullkit python johnhull/scripts/build_model_map.py --check
uv run --no-sync --package hullkit pytest -q johnhull/report/tests/test_model_map.py
export MODEL_MAP_OUTPUT_DIR=/home/kazumasa/projects/_data/johnhull/reading-guide/new-map-review-output
node johnhull/scripts/check_model_map.cjs
```

編集時は `model_map.json` を直し、生成器を `--write` で回してからBookを生成し、上の検査を行う。出力先は実行ごとに新しくする。章ガイドを足したら、モデルカードの読む場所とoverviewの両方向のつながりを更新する。

TOC追加に伴う共有runtime更新では、Book全生成・全数式・releaseの各検査に対象commit・UTC時刻・ソース指紋を記録した（N18）。manifest自身の不一致でreleaseが停止する循環は、完了済みBook/数式検査だけを記したseed manifestで一度検査し、その成功結果を最終manifestへ記録する順序で処理した。各検査は最終commit前の実際のcheckoutを示し、未コミット状態を隠していない。

strict gateは今回も158エラー（HTML89・旧指紋69）、受入306件のまま。既存のbsm15のERROR表示1件と153 WARNINGも保持した。これらを修復した、あるいは全受入証跡が最新になったとは扱わない。T2の主張と読みやすさについての独立レビューはClaudeへ引き継ぐ。
