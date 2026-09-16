# セクション品質レビュー：引き継ぎノート

> **最新追記（M3b、2026-09-16）：** [§26.11受入ノート](SECTION_26_11_ACCEPTANCE_2026-09-16.md)にL01–L06の本文6小節・共有4図・独立検証・Book/portal両面2幅の証跡を集約。影響範囲407テストと全体1,695テスト（79.36秒、既存警告2件）が成功し、§26.9・§26.10の画面も再検証した。Task 2独立レビューは承認済み、最終ブランチレビューも承認済み。[統合記録](validation/section-26-11/m3b-check.json)で最終判定を確認する。台帳は3受入・0不足・303未評価。abs(r-q)<1e-8の新しい価格実装は対象外で、未対応境界を教材へ明記した。以下は各段階の履歴。

> **M3a時点：** [§26.11のL01–L06と独立128価格](SECTION_26_11_REVIEW_2026-09-15.md)を記録。132テスト成功。既存4価格は合成条件で一致したが、教材・図・実画面は未完了なのでgaps_found。当時は受入済み2、不足あり1、未評価303。次の作業をM3b（本文・必要図・配布画面の検証）とした。[統合記録](validation/section-26-11/m3a-check.json)。

> **M2b時点：** [§26.10のD01–D06を受入](SECTION_26_10_ACCEPTANCE_2026-09-15.md)。本文6小節、4共有図、独立検証、Book/portalの実画面まで確認した。§26.9も共有成果物の変更後に再検証。当時は受入済み2、不足あり0、未評価304。[統合記録](validation/section-26-10/m2b-check.json)は当時の証跡。

> **M2a時点：** M1と§26.9の試行は`ab825e03`としてmainへpush済み。次の対象は§26.10 Binary Options。[要求と次の作業](SECTION_26_10_REVIEW_2026-09-15.md)をD01–D06へ整理し、独立価格64ケースと分解16ケースを検証した。教材・図・実画面の確認が残るため、状態は`gaps_found`。当時の台帳は受入済み1、不足あり1、未評価304項目。以下の記述は各段階のスナップショット。

> **追記（2026-09-15、M1実装後）：** §9の最初の段階を実装した。[節別台帳](SECTION_LEDGER.md)に306項目を登録し、§26.9だけを受入済み、残り305項目を未評価とした。[更新手順と検査CLI](SECTION_LEDGER_GUIDE.md)・[M1検証記録](validation/section-ledger-m1/validation.json)を参照。以下はM1開始前の引き継ぎスナップショットで、台帳の「未作成」は当時の状態。M2は未着手。

**§26.9 バリア・オプションの試行と再確認は終了。B01–B09 を満たし、再確認で見つけた2点も修正済み。全節の完成判定は未実施。**

記録日：2026-09-15（JST）。ユーザーの「comprehensive note for now」に基づく区切りの記録。\
作業場所：`/home/kazumasa/projects/johnhull`（WSL Ubuntu）。Git のルートは `/home/kazumasa/projects`。\
ブランチ：`main`。開始・記録時 HEAD：`735197a66d9793e880961d6d9974dd40e941642f`。\
今回の試行・再確認の変更はこの HEAD 上の**未コミット作業ツリー**にある。コミット・push・公開は未実施。

このノートは既存の検証記録をまとめたもの。ノート作成時にはソース10ファイル・配布物4ファイルの
SHA-256 が再確認時の証跡と一致することを照合した。下記のテスト件数は直前の再確認の実行結果で、
ノート作成のために pytest や全巻ビルドを再実行したものではない。

## 1. 再開時に読む順序

| 文書・成果物 | 用途 |
|---|---|
| このノート | 現在地、問題の原因、残課題、次の作業順 |
| [§26.9 受入条件と証跡](SECTION_26_9_ACCEPTANCE_2026-09-15.md) | B01–B09、数値、図、再確認での修正の詳細 |
| [進捗フィードバック](SECTION_AUDIT_2026-09-14_FEEDBACK.md) | 9月15日の試行結果と、9月14日時点のレビュー履歴 |
| [検証記録](../VALIDATION.md) | 実行したコマンド・範囲・過去のリリースとの区別 |
| [監査原文](SECTION_AUDIT_2026-09-14.md) | §12 が第4便終了後の ID 別状態。§0–§10 は主に監査当時の記述 |
| [実施計画](superpowers/plans/2026-09-15-section-26-9-pilot.md) | 完了した試行のチェックリスト |
| [vol10 教材](../volumes/10_exotics_martingales/exotics.ipynb) | §3.1–3.6 が今回の対象 |
| [Book](../book/_build/html/notebooks/10_exotics.html#ge-pp-620622) / [portal](../report/site/exotics.html#fig-barrier_knockout) | 実際の配布画面。ローカル生成物のため別環境では再構築が必要 |

過去の「対応済み」は、その修正と当時の検査に対する状態である。
機能の存在、印刷値の再現、節としての学習内容、図の正しさ、配布画面の正常動作は個別に判断する。

## 2. なぜ計画後も抜けが残ったのか

ユーザーの問題意識は、各節にロジック・コンテンツ・可視化の欠落が目立つことだった。
これに対して、1節を原典から読み直し、要求と証拠を対応させる試行を選んだ。

今回確認できた事実と、そこからの工程上の解釈は次のとおり。
**全306節で同じ原因が成立することまで調べたわけではない。**

| 観測した事実 | 工程上の解釈・次回の対策 |
|---|---|
| 8種類の連続観測価格は実装されていたが、教材は主に down call に偏り、負のベガ・Parisian 等が不足 | 実装シンボルの存在を学習内容の充足と結び付けすぎていた。節末まで読んで学習要求を先に固定する |
| 連続観測の閉形式は独立積分と一致したが、BGK の補正後に厳密なゼロ条件が壊れた | 中核式だけの検査では近似・分岐を取りこぼす。近似の前後で維持すべき契約条件を別に検査する |
| out=0、in=vanilla という誤った曲線でも parity・上下限・ラベル検査が通った | 恒等式は必要条件であり、個別価格の独立根拠を置き換えられない |
| build が成功していても、portal の右側切れ、Book の JS 例外、図の欠字があった | 保存出力・ビルド成功と、読めて操作できる画面の間に検査の空白があった |
| 監査・フィードバックの古い未対応表と、その後の修正記録が併存している | 時点を見ずに読むと対応済みを再作業したり、未検証を完了扱いしたりする。現在の判定に証拠・日付を付ける |

今回の試行から得た結論は、計画の項目数を増やすことよりも、
**学習要求ごとに、説明・実装または対象外理由・独立検証・必要な図・実画面の証拠を結ぶこと**が必要という点である。
コード行数、関数数、テスト件数だけで節の完成を判定しない。

## 3. §26.9 で完成させた範囲

原典は Hull 11e **Global Edition** §26.9、pp.620–622。
価格式だけでなく、本文末尾の負のベガ・Parisian まで確認した。

| 項目 | 到達点 |
|---|---|
| 定義と payoff | 同じ終値でも到達履歴で変わること、等号、時点0での到達、pathwise な in/out 分解 |
| 全契約 | down/up × in/out × call/put の8種類、8種類×3ストライクの表、全価格分岐 |
| 仮定 | GBM、定数金利・配当利回り・ボラティリティ、欧州型、リベート0、観測時点の規約 |
| 観測頻度 | 連続観測と離散観測、BGK の方向・頻度・連続極限・近似の限界 |
| 感応度 | up-and-out call のベガが負になりうる理由と数値例 |
| Parisian | 通常バリア、連続滞在、累積滞在の違い。30日+20日と連続50日の経路比較 |
| 静的な可視化 | 経路/payoff、全8種類、BGK/週次MC、ベガ、Parisian の5図 |
| 操作図 | Book / portal 共通の8契約選択。選択契約・補完契約・vanilla の3曲線 |
| 保存出力 | vol10 notebook 45 cells を再生成し、別の実行と比較 |

Parisian は契約条件と payoff の教材で、価格エンジンを追加していない。
数値解法は原典の §27.5–27.6 へ接続する。
教材の市場条件はすべて合成例で、Hull の印刷済み価格例や実市場の性能評価ではない。

## 4. 再確認で見つけた2点

### DC01：BGK が厳密なゼロ条件を壊していた

満期も観測する契約では、up-and-out call の $H\le K$、
down-and-out put の $H\ge K$ は、正の payoff と生存が両立せず価格0となる。
対応する in 契約は vanilla に等しい。

補正前の契約バリアで判断すべき条件を、BGK で移動したバリアで判断していたため、
補正がストライクをまたぐと正価格を返した。

| 条件：$S_0=100,r=5\%,q=0,\sigma=30\%,T=1$、観測52回 | 修正前 | 修正後 |
|---|---:|---:|
| up-and-out call、$H=K=110$ | 0.0008192177 | 0 |
| down-and-out put、$H=K=90$ | 0.0006991612 | 0 |

元の契約バリアを保持して判断するよう修正した。初期到達の判定と入力検証の順序は維持した。
等号・近傍、in/out、連続/4回/52回の24ケースを追加し、
修正前の16 fail / 8 pass が、修正後は24 pass となった。教材にも条件と検算を加えた。

### DC02：誤った個別曲線でも合計が正しければ通った

一時的に out を0、in をvanillaへ置き換えたところ、従来の構造・parity検査は受け入れた。

対策として、通常入力と別の市場条件で、図の各契約の計64点を独立積分と照合した。
実ブラウザでも各8種類に独立価格の基準点を置いた。
誤った図は Python 検査・ブラウザ検査の両方で拒否された。
この改変実験はメモリ内とブラウザ DOM だけで行い、正規の成果物は保持した。

追加で、数式の表示幅超過を失敗条件にし、生成HTML・配布JS/CSSのハッシュとブラウザ版も証跡へ保存した。

## 5. 変更ファイルと役割

以下は今回の試行・再確認で変更した範囲。個別の変更は Git diff と受入メモを併読する。

| ファイル | 内容 |
|---|---|
| [exotics.py](../hullkit/src/hullkit/exotics.py) | BGK 適用時の元の契約バリア保持、厳密ゼロ条件、説明の修正 |
| [plotly_viz.py](../hullkit/src/hullkit/plotly_viz.py) | 既存関数を8種類の操作図へ拡張、軸・ラベル・注記 |
| [test_barrier_reference.py](../hullkit/tests/test_barrier_reference.py) | 独立積分、初期到達、負のベガ、満期の境界、図の価格照合 |
| [test_plotly_viz.py](../hullkit/tests/test_plotly_viz.py) | 契約選択、表示内容、価格範囲と境界の確認 |
| [教材 builder](../volumes/10_exotics_martingales/build_exotics_notebook.py) / [notebook](../volumes/10_exotics_martingales/exotics.ipynb) | 説明・数式・5図・操作図と実行済み出力 |
| [figures.py](../report/report_builder/figures.py) | portal の図の説明・接続 |
| [render.py](../report/report_builder/render.py) | カード幅が変わった際の Plotly 描画幅を ResizeObserver で更新 |
| [Book 設定](../book/_config.yml) / [book_runtime.py](../book/_ext/book_runtime.py) | 同一内容の Thebe 設定宣言の重複による JS 例外を修正 |
| [ブラウザ検査](../scripts/verify_barrier_pilot_browser.cjs) | 画面操作、価格・数式・画像・JSエラー・描画幅の検査と証跡保存 |
| [MODEL_INDEX](../MODEL_INDEX.md) / [vol10 PROGRESS](../volumes/10_exotics_martingales/PROGRESS.md) | 実装・教材と検証範囲の記録 |
| [VALIDATION](../VALIDATION.md) / [feedback](SECTION_AUDIT_2026-09-14_FEEDBACK.md) / [受入メモ](SECTION_26_9_ACCEPTANCE_2026-09-15.md) / [計画](superpowers/plans/2026-09-15-section-26-9-pilot.md) | 実施記録・完了条件とその証拠 |
| [証跡ディレクトリ](validation/section-26-9/) | JSON 3件とスクリーンショット10枚 |

公開関数の引数と portal の図ID `barrier_knockout` は維持した。portal の図数は82。
新しい production 依存関係は追加していない。

共通 renderer と Book 拡張にも変更があるため、次回そこを編集するときは、
§26.9以外の代表画面も確認する。今回すべての画面を目視したわけではない。

## 6. 検証記録の読み方

| 検証 | 直前の再確認で得た結果 |
|---|---|
| hullkit + report の全 pytest | **1,378 passed**、44.04秒、既存 deprecation warning 2件 |
| 今回の関連テスト | **171 passed** |
| 新規の独立検証ファイル | 91ケース：積分48、初期到達16、負のベガ1、満期境界24、図の価格照合2 |
| 連続価格の独立積分 | 48ケース、最大絶対誤差 $1.7764\times10^{-14}$、許容 $2\times10^{-8}$ |
| 図の個別価格 | Python 2ケースで64点、ブラウザは8種類×2ページで16基準点 |
| vol10 の保存出力 | 45 cells、出力再生成後に別の実行と比較して PASS |
| lint / 差分 | ruff と git diff --check が PASS |
| portal / Book | build 成功。portal は82図 |
| release contract | 通常モード PASS。未コミットを禁止する strict tracked 判定は未実施 |
| 実ブラウザ | Chromium 151.0.7922.34、1440×1000、Book / portal 各8選択 |
| 画像・数式 | Book 5図を読込、数式93箇所を組版、数式エラー・幅超過なし |
| JavaScript | 両対象ページで例外0 |
| 改変実験 | 誤配分した個別価格を Python / ブラウザ検査が拒否 |
| 独立レビュー | 指摘を修正して再レビュー済み。§26.9の今回の範囲で未解決指摘なし |

171件・91件は1,378件に含まれる。64点・16基準点は価格の照合点数で、pytest件数ではない。
過去の1,252・1,286・初回試行時の1,352は、その時点の記録として扱い、最新結果へ混ぜない。

証拠：

- [numerical-check.json](validation/section-26-9/numerical-check.json)：48ケースの入力・計算値・誤差と、独立参照のハッシュ。
- [browser-check.json](validation/section-26-9/browser-check.json)：選択ごとの曲線・基準価格・画面状態・外部要求・ハッシュ・ブラウザ版。
- [double-check.json](validation/section-26-9/double-check.json)：2指摘の修正前後、改変検出、テスト結果、ソース10件・配布物4件のハッシュ。
- [経路](validation/section-26-9/book-path.png)、[8種類](validation/section-26-9/book-eight.png)、[BGK](validation/section-26-9/book-bgk.png)、[ベガ](validation/section-26-9/book-vega.png)、[Parisian](validation/section-26-9/book-parisian.png)。
- [数式](validation/section-26-9/book-formulas.png)、[Book操作図](validation/section-26-9/book-explorer-put-up-in.png)、[portal操作図](validation/section-26-9/portal-put-up-in.png)。

JSON の日時は UTC 表記で9月14日になっているが、JSTでは9月15日の実行。
ハッシュは、保存した証拠とファイルの対応を確認するためのもの。内容の正しさ自体を証明する検査ではない。

## 7. 全体の監査について引き継ぐ状態

この節は [監査 §11.3–§12](SECTION_AUDIT_2026-09-14.md) と
[VALIDATION 第4便](../VALIDATION.md) の記録に基づく。今回全項目を再検証していない。

| 項目 | 引き継ぐ状態 |
|---|---|
| F1 / F2：文書の現在値・履歴 | 第4便で対応記録あり。9月14日の feedback 下段を現在の未対応一覧として使わない |
| F3：vol21 timing の来歴 | 計測時の digest・環境を保持する修正と再計測の記録あり |
| F4：保存出力の古い値 | core のテキスト出力比較を追加済み。PNG / Plotly 本体の一般的な比較は依然対象外 |
| F5：退化入力で検査が例外終了 | FAIL 記録へ変える修正と回帰検査の記録あり |
| 全306節の台帳 | 未作成。更新後の分類・学習要件を全節で再確認していない。完了率の確定値を出さない |
| 保存値に依存する acceptance | 原データの裏付けがない例外が残る。vol18・19・21・22・26の対象は VALIDATION 第3便末尾を参照 |
| R1 / R2 / R3 / R4 / R6 / R11 | 監査 §12 では未対応・未再確認。研究・設計課題を含み、今回の試行では再判定していない |
| その他の節・印刷値・API項目 | §12 の「一部」「未対応」を引き継ぐ。§26.9の完了を理由に状態を変更しない |

過去の118 acceptance checksの成功は、定義した統合・数値・再現性検査の記録。
教材の全論点の網羅、市場性能、production readiness の承認ではない。

## 8. 残る制約と未実施範囲

- **Book の数式は MathJax CDN とフォントに依存する。** portal は外部通信遮断下で確認したが、Book の完全オフライン表示は確認していない。
- 初回の全ページ Book build は32警告：vol10の Plotly MIME 1件、他巻の MIME / 見出し31件。再確認の差分ビルドは1件。vol10は保存済みHTML表現で正常に描画した。
- デスクトップ幅の Chromium が対象。モバイル、他ブラウザ、全巻の全画面、live Jupyter の全widgetは未検査。
- 全19コア notebook、beyond-Hull の全artifact再構築、deep_hedge_price の個別スイートは今回再実行していない。fresh notebook比較はvol10に限定。
- 独立積分の一致は検査したパラメータ集合での結果。全入力に対する数値安定性の証明ではない。
- 週次MCの標準誤差はサンプリング誤差であり、BGK近似の誤差上限ではない。
- Parisian価格エンジン、他のエキゾチック節の受入、全巻の図の意味検査は今回の到達点に含まれない。
- 未コミット・未追跡の新規ファイルがある。別checkoutで再開する際には、ソースだけでなくnotebook・テスト・Book拡張・証跡も必要。

## 9. 再開するときの推奨順序

ここからは**次回の提案**。次の対象節は未決定で、追加実装や全306節の監査は開始していない。

1. **現在の作業ツリーと証跡を照合する。** このノートのHEADと現在のHEAD・diffを確認し、以後の変更を区別する。
2. **節別台帳の書式を決め、§26.9を最初の記入例にする。** 親行に節の状態、子行に学習要求と証拠を置く。未読の節をファイル名や関数の有無だけで完了へ分類しない。
3. **次の1節を選び、同じ工程をもう一度適用する。** 原典の末尾まで要求抽出 → 既存実装との照合 → 独立検証 → 必要な説明・図 → notebook出力 → 配布画面 → 再確認。
4. **2節目で工程の不足を直してから対象を広げる。** 親子の台帳から分類を集計できるようにし、要件の判断自体は原典と証拠に基づける。
5. **共通の検査を必要な範囲で一般化する。** 表示価格の独立根拠、近似前後の厳密条件、操作後の状態、数式と図の欠けを検出対象にする。
6. **研究・設計課題は別に判断する。** R1等のモデル変更、乱数や規約の変更、他プロジェクトへの作業拡張を、教材の不足の補完に混ぜて自動的に進めない。

台帳に最低限必要な項目：

| 列 | 記載内容 |
|---|---|
| 節ID・版・ページ | Global Editionの位置。跨ぐ節や原典の参照先も明示 |
| 学習要求 | 学習者が何を説明・計算・比較できる必要があるか |
| 前提・単位・適用範囲 | 変数、観測規約、厳密式/近似/概念説明の区別 |
| 説明・実装の根拠 | notebookの見出し、関数、または実装を置かない理由 |
| 独立検証 | 基準値の出所、許容幅、境界、元の不具合を検出する負例 |
| 必要な可視化 | 図が示す問いと結論。不要ならその理由 |
| 配布画面 | 静的表示、操作、選択と表示値の対応、数式・軸・凡例の読める証拠 |
| 判定・残り | 未評価 / 不足あり / 検証待ち / 受入済み / 対象外（理由必須） |
| 日付・ファイル対応 | 検証日、ソース・成果物のハッシュ、証跡パス |

未検証の要求が残る節は受入済みにしない。実装しない項目でも、なぜ対象外か・どこまで説明するかを記録する。
コードや図を変更したら、影響する証拠の鮮度を更新する。

## 10. 再実行の手順

以下はすべて **WSL上の projects root** で行う。共有の `.venv` を使用する。
新規環境の依存追加や全巻の再生成を、このメモを読むだけで開始する必要はない。

現在地の確認：

```bash
cd /home/kazumasa/projects
git status --short -- johnhull
git rev-parse HEAD
```

対象変更後のテスト・lint：

```bash
.venv/bin/python -m pytest -q johnhull/hullkit/tests johnhull/report/tests
.venv/bin/python -m ruff check johnhull
git diff --check -- johnhull
```

保存済みvol10出力の独立した再実行比較：

```bash
.venv/bin/python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "johnhull/scripts")
from verify_core_notebooks import check_committed_outputs

source = Path("johnhull/volumes/10_exotics_martingales/exotics.ipynb")
findings = check_committed_outputs(source)
if findings:
    raise SystemExit("\n".join(findings))
print("PASS: vol10 saved outputs match a fresh run")
PY
```

builderを変更した場合は、builderの実行後に出力が空になるため、上記比較の前にvol10の出力を再生成する。
全巻を書き換えず、この1冊に限定できる：

```bash
.venv/bin/python johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py
.venv/bin/python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "johnhull/scripts")
from verify_core_notebooks import write_outputs

source = Path("johnhull/volumes/10_exotics_martingales/exotics.ipynb")
findings = write_outputs(source)
if findings:
    raise SystemExit("\n".join(findings))
print("PASS: vol10 outputs regenerated")
PY
```

配布物の構築と契約検査：

```bash
make hull-report
make hull-book
make hull-release-check
```

ブラウザ検査。下記は記録時に存在した既存インストールのパスであり、環境が変わった場合は調べ直す：

```bash
PLAYWRIGHT_MODULE=/home/kazumasa/.npm/_npx/e78b33305587cb7c/node_modules/playwright \
CHROMIUM_BIN=/home/kazumasa/.cache/ms-playwright/chromium-1234/chrome-linux64/chrome \
/usr/bin/node johnhull/scripts/verify_barrier_pilot_browser.cjs
```

このスクリプトは `browser-check.json` とスクリーンショットを更新する。
`double-check.json` と `numerical-check.json` はその実行だけでは更新されない。
新しい検査の日時と結果を追記し、古い再確認記録を新しい実行結果のように読み替えない。

全巻リリースを検証する次回作業では、上記に加えて `make hull-core-notebooks-check`、
`make hull-notebooks-check`、`make hull-artifacts-check` 等、変更に応じた全体検査を行う。
strict tracked check は、別途コミットした後の作業。
今回の未コミット作業に、過去の strict check の成功を適用しない。

## 11. この記録を残した時点での区切り

§26.9の試行・再確認と、その証拠の整理までを完了範囲とする。
このノートを残すターンでは文書だけを変更し、証跡とファイルの対応・参照リンク・差分を検査する。
次の節の実装、全節台帳の作成、コミット・公開はここからの別の作業となる。
