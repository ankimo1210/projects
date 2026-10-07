# johnhull 可視化ポータル(インタラクティブ HTML)

johnhull の Hull 11e ノートで学ぶ価格付け・リスク管理を束ねる、
**オフライン自己完結のインタラクティブ静的サイト**を生成するジェネレータ。
`analytics/report` と同じ設計(jinja2 + plotly)。

- ランディング + コンセプトギャラリー + 12テーマ別ショーケース（全204図、exotics 92図）+ 統合(背骨)ページ
- 図は `hullkit.plotly_viz`、内部教材モジュール `hullkit._binary_lesson` / `hullkit._lookback_lesson` / `hullkit._shout_lesson` / `hullkit._asian_lesson` / `hullkit._exchange_lesson` / `hullkit._basket_lesson` / `hullkit._variance_swap_lesson`、またはvol 18–28のversioned reference artifactから生成。共有ソースに加え、値・操作・実画面を検査する
- **カーネル不要・ネット不要**: plotly はローカル同梱、図はブラウザ内で動く(スライダー/ホバー/ズーム)

## 生成

リポジトリ root から:

```bash
make hull-report   # -> johnhull/report/site/index.html
make hull-book     # johnhull の Jupyter Book(教科書本体)をビルド
```

または直接（Ch1ページを含めて両方を実行）:

```bash
PYTHONPATH=johnhull/hullkit/src:johnhull/report uv run --no-sync python -m report_builder.build
PYTHONPATH=johnhull/hullkit/src uv run --no-sync python johnhull/scripts/build_chapter01_portal.py
```

出力された `site/index.html` をブラウザで開くだけ(オフラインで動作)。`site/` は gitignore 済み。

通常のportalビルド `make hull-report` はCh1の10節・4共有図を `site/chapters/ch01.html` に、
受入済みのCh2–25・Ch29–37の補足教材を各 `site/chapters/chXX.html` に生成する。
`make hull-book` のvol12 Ch1から到達でき、上の両コマンドでリンク先まで再生成する。
Ch1は章別教材として追加し、既存の204図/12テーマとは別に数える。
[Ch1の受入記録](../docs/CHAPTER_01_ACCEPTANCE_2026-10-07.md) に、原典範囲と
数値・画面の再検証手順を記す。

## Ch2–9の節別補足教材

承認済みfast-v1の配布先は`site/chapters/ch02.html`〜`ch09.html`。
通常のportal生成にも含む。補足教材だけを再生成する場合は、repo rootの既存Python環境で実行する。

```bash
python johnhull/scripts/fast_acceptance.py build
```

全70節・206要件を含む補足教材で、既存Book本文は改訂していない。
数式描画はMathJax CDNを利用するためオンライン接続が必要。
[受入記録と省略した確認](../docs/CHAPTERS_02_09_ACCEPTANCE_2026-10-07.md)、
[再検証コマンド](../docs/FAST_ACCEPTANCE.md)を参照。

## Ch10–15の節別補足教材

全58節・161要件を含む補足教材を`site/chapters/ch10.html`〜`ch15.html`へ生成する。
Ch2–9の固定証跡はそのまま保持し、各便のrecipeで後続を追加する。

```bash
python johnhull/scripts/fast_acceptance_options.py build
```

数式表示はMathJax CDNを利用し、オンライン接続が必要。
[受入記録](../docs/CHAPTERS_10_15_ACCEPTANCE_2026-10-07.md)、
[省略した確認と再検証手順](../docs/FAST_ACCEPTANCE_GUIDE.md)を参照。
既存Book本文の改訂・main統合は未実施。登録後の再確認には`verify`を使い、証跡を生成し直さない。

## Ch16–21の節別補足教材

全54節・93要件を`site/chapters/ch16.html`〜`ch21.html`へ生成する。
Ch21の木/MC/差分法は節ごとに実装とtestを宣言し、前便のcoreと証跡を保持する。

```bash
python johnhull/scripts/fast_acceptance_advanced_options.py build
```

共通venvのPythonとPYTHONPATHを使う。数式表示にはオンライン接続が必要。
[受入範囲・制限・再検証](../docs/CHAPTERS_16_21_ACCEPTANCE_2026-10-07.md)を参照。
登録後は`verify`でread-only確認する。既存Book改訂/main統合は未実施。

## Ch22–25の節別補足教材

全36節・125要件を`site/chapters/ch22.html`〜`ch25.html`へ生成する。
数値105・説明20の要件と、元系列不足・印刷差・合成検証の範囲を節ごとに保持する。

```bash
python johnhull/scripts/fast_acceptance_risk_credit.py build
```

共通venv/PYTHONPATHを使用し、数式表示にはオンライン接続が必要。
[受入範囲・省略・再検証](../docs/CHAPTERS_22_25_ACCEPTANCE_2026-10-07.md)を参照。
登録後は`verify`で証跡を生成し直さず確認する。既存Book改訂/main統合は未実施。

## Ch29–37の節別補足教材

残り45節・149要件を`site/chapters/ch29.html`〜`ch37.html`へ生成する。
全306節の台帳受入を完了。§33.2/36.4はprivate計算を補完し、
caller指定条件の検証と未確定の原典価格の再現を区別する。

```bash
python johnhull/scripts/fast_acceptance_final.py build
```

共通venv/PYTHONPATHを使用し、数式表示にはオンライン接続が必要。
[受入範囲・制限・再検証](../docs/CHAPTERS_29_37_ACCEPTANCE_2026-10-08.md)を参照。
登録後は`verify`で証跡を生成し直さず確認する。既存Book改訂/main統合は別工程。

## 図を追加する

`report_builder/figures.py` の `FIGURES` に `FigureSpec` を1つ足すだけ
(`build` には `hullkit.plotly_viz` の `plotly_*` を渡す)。新テーマは `BOOKS` に `BookMeta` を1行。
A1–A4に加え、A5–A8のML・市場構造・新市場の図もここへ登録される。

## テスト

```bash
uv run --no-sync pytest johnhull/report/tests -q
```

全図ビルドの完走・registry由来の全ページ生成・`Plotly.newPlot` 数・**外部 URL ゼロ**を検証する。

§26.12 シャウトの4図は保存済み数値を共有し、ビルド時に価格探索を実行しない。
`johnhull/scripts/verify_shout_lesson_browser.cjs` はビルド済み Book/portal の実メニューを操作し、
1440/1000px の両方で13状態を独立参照値と照合する。既存 Playwright/Chromium を
`PLAYWRIGHT_MODULE` / `CHROMIUM_BIN` で指定して実行し、
`docs/validation/section-26-12/browser-m4b-check.json` に実際の検査範囲・ハッシュ・18画像を記録する。
Portal の HTTP(S) は遮断し、Book の既存 MathJax リクエストは許可して記録する。

§26.15 バスケットの4図は、厳密なモーメントと近似価格、条件付き積分参照と MC の不確実性を区別する。
`build_basket_browser_reference.py` は保存参照から独立の照合値を作り、
`verify_basket_lesson_browser.cjs` は両面・1440/1000px の全10状態、数値・軸・数式・
数値改変の拒否と復元を検査する。18画像と `section-26-15/browser-m7-check.json` を保存する。
`verify_basket_notebook.py` は §4.5 外のソースを基点 `9b7a75c7` と比較し、
新鮮な実行結果と4図の data/layout を照合する。通常ビルドは求積・MCを実行しない。

§28.4の4図は条件付きQ/T同一給付・futures/forward・支払日測度・OIS annuityを共有数値から表示。`scripts/verify_numeraire_browser.cjs`で16状態とMathJax/幅/値を検査する。

§28.5の4図は相関多因子の比drift・条件付き平均・独立basis・同一給付Q/g価格。`scripts/verify_multifactor_browser.cjs`で16状態/値/95%区間/幅/MathJaxを検査する。
