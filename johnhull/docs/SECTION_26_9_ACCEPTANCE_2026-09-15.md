# §26.9 バリア・オプション：受入条件と検証証跡

> **M2b後の再確認：** §26.10追加後に関連171テスト、vol10出力型・MIME・正規化テキストの別実行比較（PNG/Plotly値は別検査）、Book/portal各8契約・静的5図・数式93箇所を再検査した。§3以降の本文・コードは保持。[新しい回帰記録](validation/section-26-9/m2b-recheck.json)と更新したbrowser記録が現在の証跡で、以下の初回検証記録・double-checkは当時の履歴。

**判定：再確認で見つけた2点を修正し、B01–B09 を満たした。** 全巻の節別完成を意味しない。

日付：2026-09-15（JST）\
開始コミット：`735197a66d9793e880961d6d9974dd40e941642f`。結果はその上の未コミット作業ツリー。\
原典：Hull, *Options, Futures, and Other Derivatives*, 11e **Global Edition**、§26.9、**pp.620–622**。
ローカル PDF の物理ページ番号も620–622。本文を節末まで確認し、価格式だけでなく負のベガ・Parisian まで受入条件に含めた。

教材：[vol10 notebook](../volumes/10_exotics_martingales/exotics.ipynb) の §3.1–3.6\
閲覧：[Book の §26.9](../book/_build/html/notebooks/10_exotics.html#ge-pp-620622) ／ [portal](../report/site/exotics.html#fig-barrier_knockout)\
計画：[実施チェックリスト](superpowers/plans/2026-09-15-section-26-9-pilot.md)

## 要求と証拠の対応

| ID | 学習者が説明・確認できること | 開始時点の不足 | 完了の証拠 |
|---|---|---|---|
| B01 | 同じ終値でも到達履歴で payoff が変わる。等号・時点0の扱い | 定義と価格の図だけ | §3.1、[経路と payoff](validation/section-26-9/book-path.png)、初期到達16テスト |
| B02 | down/up × in/out × call/put の8種類、pathwise な in+out=vanilla | 実装は8種類、教材は主に down call | §3.1–3.2、8種類×3ストライクの表、[8種類の図](validation/section-26-9/book-eight.png) |
| B03 | GBM・定数 r/q/σ・欧州型・リベート0・連続観測という適用条件と全分岐 H≶K | 公式・分岐の説明不足 | §3.2、[全分岐の数式](validation/section-26-9/book-formulas.png)、独立積分48ケース |
| B04 | H=K、初期到達、価格範囲、縮退を payoff から説明できる | parity 中心で独立 oracle が不足 | §3.1–3.2、test_barrier_reference.py。縮退を「到達確率1」とする旧コメントも修正 |
| B05 | BGK の向き・観測頻度・連続極限・近似の限界 | ライブラリとテストに留まる | §3.3、[観測頻度と週次MC](validation/section-26-9/book-bgk.png)、下の数値 |
| B06 | up-and-out call の vega が負になりうる理由 | 説明・図なし | §3.4、[負のベガとバニラ](validation/section-26-9/book-vega.png)、独立した符号テスト |
| B07 | Parisian の連続滞在と累積滞在、通常バリアとの違い | taxonomy の名前だけ | §3.5、[30+20日と連続50日](validation/section-26-9/book-parisian.png)、実行時の滞在日数・payoff 検算 |
| B08 | Book の静的図・数式を読め、Book / portal の8種類を操作できる | 主に2種類の knockout call。実際の画面は未検査 | [ブラウザ証跡](validation/section-26-9/browser-check.json)。両ページ各8回の選択、5画像、数式93箇所、JSエラー0 |
| B09 | 実装式を複製しない数値検証、出力の鮮度、画面検査が揃う | 各証拠の対応なし | [独立積分の全48結果](validation/section-26-9/numerical-check.json)、vol10 fresh run、全体1,378テスト、下の実施記録 |

## 数値検証

独立 oracle は、GBM の終端正規密度と Brownian bridge の条件付き到達確率を数値積分する。
ライブラリのバリア閉形式・BGK・in/out の価格差引きを参照しない。
8種類 × H/K の3関係 × 2組の市場パラメータ（配当と負の金利を含む）で48ケース。
最大絶対誤差は **1.7764×10⁻¹⁴**、合格許容値は **2×10⁻⁸**（原資産と同じ通貨単位）。
この有限のパラメータ集合での結果であり、全入力での精度保証ではない。

さらに時点0で H=S0 の16ケース（8種類 × 連続/週次）と負のベガ1ケースを追加した。
再確認では満期観測の厳密な境界24ケースと、図の独立価格照合2ケース（計64点）を追加した。
このファイルの数値検査は計91件。図の契約選択・境界検査と既存関連テストを合わせて171件。

教材の数値例はすべて合成条件で、Hull の印刷済み価格例ではない。

| 計算 | 結果 |
|---|---:|
| 週次 up-and-in put：S0=K=100, H=120, r=5%, q=0, σ=30%, T=1 |  |
| MC（200,000経路、seed=2026） | 0.97597 |
| MC 標準誤差 | 0.00939 |
| BGK 近似 | 0.96768 |
| 連続観測の価格 | 1.35555 |
| up-and-out call：S0=99,K=90,H=100,r=5%,q=0,T=1、σ=20%→21% の価格変化 | −0.001999 |
| Parisian A（30日+20日）：通常 / 連続50日 / 累積50日 out の payoff | 0 / 10 / 0 |
| Parisian B（連続50日）：同上 | 0 / 0 / 0 |

MC の ±3 SE は標本誤差の範囲であり、BGK の近似誤差保証ではない。
Parisian は区分一定の合成経路で滞在条件と payoff を確認した。
Parisian の価格エンジンは追加していない。原典が参照する数値手法 §27.5–27.6 への接続を教材に明記した。

## 実施した検査

| 検査 | 最終結果 |
|---|---|
| hullkit + report の全 pytest | **1,378 passed**、44.04秒。既存ライブラリの deprecation warning 2件 |
| 対象の独立積分・既存 exotics・図 | **171 passed** |
| vol10 の実行済み出力の生成 | PASS、45 cells |
| vol10 の別 fresh run と保存出力の比較 | PASS |
| ruff / git diff --check | PASS |
| make hull-report | PASS、82図 |
| make hull-book | PASS、警告の内訳は下記 |
| make hull-release-check | PASS（未コミットを許す通常モード） |
| Chromium / Playwright、1440×1000 の実ブラウザ | PASS、portal は外部通信を遮断して動作 |
| Book / portal の全8種類 | 選択契約名、call/put、表示3曲線、価格恒等式、H軸、実描画幅を検査 |
| 目視 | Book の5図・全分岐の式・両ページの初期表示と put/up/in 表示を確認 |
| 独立レビュー | 初回 Minor 2件に加え、再確認のBGK境界条件も修正・再レビュー済み。未解決指摘なし |

実ブラウザ検査は [verify_barrier_pilot_browser.cjs](../scripts/verify_barrier_pilot_browser.cjs)。
ブラウザ結果 JSON にはソース・notebook・生成HTML・配布JS/CSSの SHA-256 とブラウザ版を保存した。
PNG が存在するだけでは通過せず、DOM上の画像読込・操作後の曲線・数式の組版・JS例外・描画幅を検査する。

## 画面検査で見つけて修正した点

1. Matplotlib の下付き文字「₀」が IPAexGothic で欠け、警告にローカルパスが出力された。図を S0 表記に修正して出力を再生成。警告を抑制する対応は取っていない。
2. portal のカード幅は約445pxなのに Plotly は約952pxで描画し、右側が切れていた。カード追加後の CSS auto-fit による幅変更を ResizeObserver で追従するよう共通 renderer を修正。
3. Book の生成HTMLで同じ Thebe 設定の定数宣言が二重になり、SyntaxError が発生。クリーンビルドでも再現した。同一の設定本文の重複だけを除くローカル拡張を追加し、順序・別の設定・外部スクリプトは維持した。
4. 操作図の注記の下端を収め、BGK と負のベガの見出し・図の順序を整理。契約切替テストがラベルと表示価格の対応まで確認するよう強化した。

[portal 初期表示](validation/section-26-9/portal-initial.png) ／
[portal put/up/in](validation/section-26-9/portal-put-up-in.png) ／
[Book 操作図](validation/section-26-9/book-explorer-put-up-in.png)

## 検証範囲と残る制約

- **portal はオフラインで確認。Book の数式は MathJax の CDN とフォントに依存する。**
  Book を完全オフラインとする判定はしていない。外部要求は browser-check.json に記録。
- 初回の全ページ Book build は32警告（vol10の未対応 Plotly MIME 1件、他巻の MIME / 見出し31件）。
  再確認の差分ビルドは vol10 の MIME 警告1件。
  vol10 は同時保存した HTML 表現で描画され、実ブラウザで操作を確認済み。警告ゼロの全巻ビルドを達成したという意味ではない。
- 画面検査は上記デスクトップ幅の Chromium。別ブラウザ・モバイル・他巻の全画面・live Jupyter の全 widget は未検査。
- 全19コア notebook や beyond-Hull の全artifact再構築は再実行していない。今回の fresh notebook 検査は vol10 に限定。
- コミット・push・公開は行っていない。strict tracked release の最終判定はこの未コミット作業には適用していない。

## 再実行

projects root で実行する。Python は共有 uv 環境を使用する。

```bash
.venv/bin/python -m pytest -q johnhull/hullkit/tests johnhull/report/tests
.venv/bin/python -m ruff check johnhull
make hull-report
make hull-book
make hull-release-check
```

vol10 だけの出力検査：

```python
import sys
from pathlib import Path
sys.path.insert(0, "johnhull/scripts")
from verify_core_notebooks import check_committed_outputs
assert not check_committed_outputs(
    Path("johnhull/volumes/10_exotics_martingales/exotics.ipynb")
)
```

ブラウザ検査は既存の Playwright / Chromium のパスを指定する（新しい依存関係は追加していない）。

```bash
PLAYWRIGHT_MODULE=/path/to/playwright \
CHROMIUM_BIN=/path/to/chrome \
node johnhull/scripts/verify_barrier_pilot_browser.cjs
```

## 再確認での追加修正（2026-09-15）

初回の受入判定後、追加の独立レビューと検査への入力改変で2点を発見した。

### 1. BGK が契約上の厳密なゼロ条件を壊していた

満期を観測する up-and-out call の $H\le K$、down-and-out put の $H\ge K$ は、
正の満期 payoff と生存が両立しないため厳密に価格0になる。
既存の実装は BGK で置換した $H$ に対して分岐し、補正によって $K$ をまたぐと正価格を返していた。

| 条件（S0=100,r=5%,q=0,σ=30%,T=1） | 修正前 | 修正後 |
|---|---:|---:|
| up-out call、H=K=110、年52回 | 0.0008192177 | 0 |
| up-out call、H=K=110、年4回 | 0.0531802973 | 0 |
| down-out put、H=K=90、年52回 | 0.0006991612 | 0 |
| down-out put、H=K=90、年4回 | 0.0423471897 | 0 |

元の契約バリアを保持してこの条件を適用するよう修正した。
初期到達判定と BGK の入力検証順は維持した。
H=K とその近傍、in/out、連続・4回・52回の24ケースを追加。
修正前は **16 fail / 8 pass**、修正後は24ケースが通過した。対応する in はバニラ価格に一致する。
教材 §3.3 に条件と実行時の検算を追加した。

### 2. 曲線の合計が正しければ通る検査だった

out を全て0、in を全てバニラに置き換えても、in+out=vanilla、価格範囲、ラベルの検査は通ってしまった。
図の構造や恒等式だけでは、選択された商品の価格そのものを検証できていなかった。

既定入力・別のスポット/ストライク/市場パラメータの2ケースで、表示曲線の計64点を
独立した Brownian bridge 積分と比較する検査を追加。
ブラウザにも8種類の途中のHに対する独立価格を追加し、実際に表示される値を照合するようにした。
意図的に誤配分した図は Python 検査とブラウザ検査の両方が拒否した。

今回のブラウザ記録には、ソースに加えて生成HTMLと配布JS/CSSのハッシュ、ブラウザの版も保存した。
数式の表示領域の幅超過も失敗条件に加えた。

最終結果：**1,378 tests passed**（44.04秒）、関連171件、vol10 fresh run、Book/portal build、
通常 release gate、ruff、実ブラウザ検査が通過。表示数式は93箇所。
[再確認の機械可読記録](validation/section-26-9/double-check.json)。

今回の見落としは、連続式の検証を離散近似の境界条件へ広げていなかったことと、
価格の恒等式を価格そのものの正しさと取り違えた検査設計にあった。
「近似の前後で維持すべき厳密条件」と「各表示値の独立根拠」を、他の節の受入条件にも含める。

## 他の節へ展開する基準

連続式は独立計算と一致した。一方、教材の説明・配布画面に加え、離散近似の厳密な境界条件にも不足が見つかった。
以後は節ごとに原典の末尾まで読み、学習要求を先に列挙する。
各要求へ説明・実装または扱わない理由・独立検証・必要な図・実画面の証拠を結び、
未検証の行が残っていればその節を完了扱いにしない。
