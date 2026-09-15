# SECTION_AUDIT_2026-09-14 進捗レビュー・フィードバック

再開時の入口：[包括的な引き継ぎノート（2026-09-15）](SECTION_REVIEW_HANDOFF_2026-09-15.md)。現在地、原因、修正、検証、残課題、再実行手順を整理。

## 最新追記：M3a §26.11の要求と独立検証（2026-09-15）

[ルックバックの要求と残課題](SECTION_26_11_REVIEW_2026-09-15.md)をL01–L06に整理した。
4価格関数は新規/既発を含む独立128価格と一致し、例題のcall/put、共通誤差の改変検出を合わせて132テストが成功した。
一方、教材はfloating call中心で、固定行使・put・過去履歴・観測頻度の比較と配布画面の確認が不足する。
r=q近傍の例外も未実装境界として記録した。台帳は受入済み2、不足あり1、未評価303。

今回も「価格関数がある」と「節を学べる」を分ける必要があった。
次のM3bは本文・必要図・Book/portalの確認までを対象にする。
価格・教材・描画ソースと配布物を変えていないため、既存2節の証跡は保持した。
[統合検査と独立レビュー](validation/section-26-11/m3a-check.json)を参照。

## M2b時点：§26.10受入（2026-09-15）

[§26.10受入ノート](SECTION_26_10_ACCEPTANCE_2026-09-15.md)にD01–D06の証跡をまとめた。
4給付・両複製・spread/butterfly・deltaを共有図にし、本文6小節とBook/portalへ接続。
数値・給付・図の92テスト、両ページの価格ラベル対応・境界・操作・レイアウトを確認した。
§26.9も171テスト・各8契約・5図を再確認し、古いハッシュを単に更新する方法は取っていない。
台帳は受入済み2、不足あり0、未評価304。全節へ進捗を外挿しない。

今回も数値テストだけでは、注記の欠け・凡例の重なり・put側の確率説明の誤記を検出できなかった。
これらは独立した内容レビューと実画面検査で修正した。要求ごとの説明・実装・独立検証・図・描画の5観点を維持する。
全体テストと最終統合レビューは[統合記録](validation/section-26-10/m2b-check.json)を参照。

## M2a時点の記録：§26.10（2026-09-15）

M1と§26.9の試行を`ab825e03`としてmainへpushした。
次の対象を§26.10 Binary Optionsとし、[原典要求と残課題](SECTION_26_10_REVIEW_2026-09-15.md)をD01–D06に整理した。
4種類の価格を独立積分64ケース、バニラ分解を16ケースで確認。合計を保つ誤配分等3改変も検出した。
教材にはプット側の不足、デジタルとバタフライの混同、デルタの満期極限に関する条件不足が残る。
状態は`gaps_found`。§26.9受入済み、§26.10不足あり、304項目未評価。
以下の追記はそれぞれの時点の履歴として読む。

## M1 節別台帳（2026-09-15）

[節別台帳](SECTION_LEDGER.md)と[検査CLIの更新手順](SECTION_LEDGER_GUIDE.md)を追加した。
原典outlineから299節と7付録を登録し、§26.9のB01–B09は18個の証跡へ接続した。
残る305項目は未評価であり、過去の実装件数を受入判定へ自動変換していない。
IDの欠落・重複、根拠のないaccepted、証拠の欠落・変更、生成文書の不一致を検出する。
配布物ハッシュの確認は`--check-artifacts`で明示的に行う。

検証は`pytest johnhull -q`で1,455件成功（台帳39件を含む）。実台帳への9種の改変を検出し、
空の受入要求・不正な型・出力先リンクに関する独立レビューの4点も修正、再確認済み。

[M1検証記録](validation/section-ledger-m1/validation.json)。この検査は保存証跡の整合性を確認し、数値や画面を再実行するものではない。
次の節を端から端まで確認するM2は未着手。以下の各レビューはそれぞれの実施時点の記録として読む。

## 最新追記：§26.9 の試行結果（2026-09-15）

**1節を原典の要求から完成させる試行を実施し、再確認で追加発見した2点も修正し、§26.9 の受入条件 B01–B09 を満たした。**
[受入条件と証跡](SECTION_26_9_ACCEPTANCE_2026-09-15.md) ／
[更新した教材](../volumes/10_exotics_martingales/exotics.ipynb)。

この節では、連続観測の8種類の価格式は独立した積分計算と一致した。
ただし再確認で、BGKの離散近似が契約上の厳密ゼロを壊す既存の不具合を発見・修正した。
不足が大きかったのは、全分岐の説明、観測頻度、負のベガ、Parisian、実際の配布画面の検査だった。
本文を末尾まで読むことで、従来の「数式が実装済み」という判断から漏れていた学習要求を抽出できた。

再確認では、合計価格だけを確かめる図テストが誤配分を受け入れることも再現した。
表示価格64点とブラウザ上の8種類を独立計算に照合する検査を追加し、誤配分が拒否されることを確認した。

今回追加・修正したもの：

- 8種類と全分岐の教材、経路・価格・BGK・ベガ・Parisian の5図、8種類を切り替える操作図。
- 閉形式を呼び直さない48ケースの積分検証、初期到達16ケース、負のベガ、満期観測の厳密境界24ケースの検査。
- portal の描画幅がカード幅の変更に追従せず右半分が切れる問題。
- Book の同一 Thebe 設定宣言の重複による JavaScript 例外、日本語図の欠字。
- 契約のラベルと表示内容まで照合するブラウザ検査・スクリーンショット・ソースハッシュ。

検証：**1,378 tests passed**、vol10 の新規実行と保存出力比較、ruff、Book / portal build、
通常 release gate、両画面の全8種類の操作が成功した。独立レビューの指摘も処理済み。

この結果を全節の完成へ広げない。次の節も「原典の要求 → 説明・実装 → 独立検証 → 必要な図 → 実画面」の
対応表を作り、各行を閉じる。章や巻の実装件数だけでは学習内容の完成を判定しない。

残る境界：Book の数式は MathJax CDN 依存。初回の全ページ Book build の32警告（今回の差分ビルドでは1件）の内訳と、
今回実行していない全巻検査は受入メモに明記した。コミット・push・公開は行っていない。
下記の2026-09-14レビューは当時のスナップショットで、F1–F5をこの試行で一括再判定したものではない。

---

## 2026-09-14 のレビュー記録（以下は当時の状態）

**主要な修正は進んでいる。** 当時の HEAD で hullkit＋report の **1,252 テスト**、11 巻の **118 acceptance checks**、tracked release contract が成功した。前回の CDS 入力改変の検出漏れ、D1/D2、D8 の古い出力は、今回の再現で改善を確認した。一方、文書の現在値、節別台帳、計測履歴、コアノート出力の鮮度には残課題がある。

- 更新日: 2026-09-14
- 主対象: [VALIDATION.md](../VALIDATION.md)、特に第 2 便・第 3 便の記録
- 照合先: [SECTION_AUDIT_2026-09-14.md](SECTION_AUDIT_2026-09-14.md)、実装・テスト・コミット済み成果物
- レビュー時 HEAD: `839058908f9fcb32090618278d3889c555bacfa4`
- 比較元: 初回レビュー時の `cae1cd84`。初回フィードバックは `bd278948` の Git 履歴に残る。
- 行番号は今回の HEAD に対するもの。ソースパスは `/home/kazumasa/projects/` 基準。
- 今回の変更はこのフィードバックノートのみ。`VALIDATION.md`、監査原文、実装、成果物は変更していない。

## 前回 7 項目への対応状況

| 前回の指摘 | 今回の判定 | 根拠・残り |
|---|---|---|
| 1. カバレッジの計数・分類 | **一部対応** | 監査 §1 / §10 で vol 12 の行和、code*、§7.2、§36.4 を訂正。節別台帳は未作成。第 3 便で増えた実装も含む全 306 節の最新分類は未検証 |
| 2. acceptance の保証範囲・検出漏れ | **主要な検出漏れは対応、保証の表現は要修正** | 全 11 巻に tamper テスト。CDS hazard / survival 改変は該当チェックが FAIL。GPD 標本も判定に使うようになったが、全 0 入力は例外になる。保存値依存の例外は残り、独立再計算が全面的になったわけではない |
| 3. D11 の「完全版」の限定・信用 VaR | **対応済み** | `VALIDATION.md:342–349` と `cds.py` は survival-weighted risky duration と knock-out の範囲を明記。`test_credit.py:65–75` で Ex 24.8 の 0.128 / $5.13M を固定し、テスト成功 |
| 4. CR-08 / CR-09 の既存 API の見落とし | **監査の訂正は対応済み** | 監査 §10 が binary CDS と任意 detachment 評価の存在を認定。非標準点への補間・較正規約や追加の感応度シナリオは別の open 項目 |
| 5. D2 の再現条件・符号 | **対応済み** | `first_accrual=0.5` で bonds / fras とも \(-0.291999794242\)。監査の入力・受け固定の符号も訂正済み |
| 6. vol 21 の比較除外・計測の来歴 | **文書は対応、来歴の実装は未対応** | 監査 §0 に timing 等の除外を明記。古い計測値を新しい source digest と組み合わせ得る実装は残る（下記 F3） |
| 7. 実行順序・完了条件 | **進展、一部残り** | acceptance・出力の修正を先行し、印刷値ピン、API、D9 を追加。監査 §9 に判断事項を分離。現状を示す一覧と過去の指摘表の関係はまだ整理が必要 |

D9 は今回、**出力を保存する作業は対応済み**と判断する。指定された 17 冊に出力があり、PNG 86 件、Plotly MIME 25 件を数えた。ブラウザで全ページの描画を確認したわけではなく、数値や図の鮮度を保証する範囲にも限界がある（F4）。

## 残る指摘

### F1 — VALIDATION.md の現在値と保証範囲が第 3 便に追随していない

**優先度: 中。確信度: 高。対象: `VALIDATION.md:34–39,50,284,293–297`。**

- 冒頭は tamper 契約の対象を vol 23–25 / 27 / 28 としているが、284 行とテストは vol 18–28 の全 11 巻を対象にしている。
- acceptance 表の vol 25 は **9 → 10**。現在の `evaluate_acceptance(25, ...)` は `ppa_correlation_sensitivity` を含む 10 件を返し、全件 PASS。
- 284 行の「every stored scalar a check reads must equal its recomputation」は、直後の保存値依存の例外と両立しない。`frontier_acceptance.py:136–142` の `residual_baseline` は保存した 2 つの MAE の大小比較のまま。
- 37–38 行や `CLAUDE.md` の「該当チェックだけが落ちる」には依存チェックの例外がある。`report/tests/test_frontier_acceptance_tamper.py:470–490` は複数の FAIL を許容する。

**修正案:** 冒頭の現在の契約を第 3 便に合わせて更新し、次のように限定する。

> 全 11 巻で、選定した入力改変が対象チェックと定義された依存チェックに検出されることを検証する。配列から再計算できる項目は保存値との一致も要求する。原始データや実行時情報がない項目は保存値依存として別表に列挙する。

過去の第 2 便の記録（269–271 行）は履歴として維持してよい。現在の要約と混同しないよう、第 3 便による更新先を示す。

### F2 — 監査の歴史的な「未対応」と現在の状態を分ける

**優先度: 中。確信度: 高。対象: 監査 43–50、134、714、738、755 行と §11.2。**

監査本文には「D9 以外を修正済み」「D9 は残り」「hazard を全 0 にしても 17/17 PASS」など、過去の状態が残る。§11.2 はその後の対応を記録しているが、本文や再現コードだけを読むと修正済みの問題を現在の欠陥と取り違えやすい。

**修正案:** 冒頭に「現在の状態は §11.2、§0–10 の数値・プローブは初回監査時点」と明記し、ID ごとの現状表を置く。旧コード例の `True True 17` は対象 commit を添える。現状表では、たとえば以下を区別する。

- D1/D2/D8、CDS hazard・survival の検出漏れ: 今回再現で対応を確認。
- D9: 出力の保存は対応済み。表示内容の鮮度確認には F4 の限界がある。
- 節別台帳: 未対応。関数追加後の全節集計は未検証。
- R1/R2/R3/R4/R6、BB-01、BA-08 等: 監査・negative results に残る研究／設計課題。今回それぞれを再検証したわけではない。

### F3 — vol 21 の計測値と source digest の対応は未解決

**優先度: 中。確信度: 高。対象: `johnhull/scripts/build_frontier_artifacts.py:521–570`。**

`_benchmark_contract` は現ソース全体の digest を作る一方、`_preserve_vol21_timing_reference` は `sources` を除外して前回との一致を判断し、古い timing 配列と speedup を保持する。これは初回フィードバックから変わっていない。通常の再生成で数値配列が一致しても、どの実装を測った時間かは確定できない。

**修正案:** 計測時の commit / source digest、実行環境、計測方式を timing と一緒に保持し、通常の成果物再生成の digest と分離する。計測の来歴を更新するのは実際に再計測したときにする。今回 timing 自体の再計測はしていない。

### F4 — D9 のゲートは出力の消失を検出するが、古い数値の残存は検出しない

**優先度: 中（追加の改善提案）。確信度: 高。対象: `johnhull/scripts/verify_core_notebooks.py:151–170,190–207`。**

コアの `check_committed_outputs` は出力種別と MIME キーだけを比較する。コードが `print(2)`、保存済み stdout が `1\n` の一時 notebook を作って実行したところ、戻り値は **`[]`（問題なし）**だった。

これは「出力の型を比較する」という `VALIDATION.md:288` の記載どおりの限界で、D9 の出力追加を否定するものではない。ただし、今後数値や図の内容が変わっても、型が同じなら古い結果を配布し得る。

**修正案:** stdout / text/plain の決定的な値は、frontier ゲートと同様に比較する。vol 06 の実測 LSM 時間など、非決定的な項目だけを明示的に正規化する。Plotly のデータや PNG の意味的な確認は別の検査として扱う。完了条件には「出力消去」と「同じ型で値だけ古い」の双方の検出を含める。

### F5 — GPD の超過標本ゼロは診断可能な FAIL にしたい

**優先度: 低（堅牢性・診断性）。確信度: 高。対象: `johnhull/scripts/frontier_acceptance.py:2170–2215`。**

前回は `gpd_losses[:] = 0` でも 14/14 PASS だった。現在は標本を検査に使うようになり、この入力は **`ZeroDivisionError`** になる。`n_exceedances=0` の後、EVT 再計算で `n_total / n_exceedances` を評価するため。

黙って PASS する問題は解消しているが、該当チェックを含む判定記録を返せず処理が中断する。今回の通常データでは全件 PASS で、この例外は意図的に壊したメモリ内の入力だけで発生した。

**修正案:** 超過標本数や推定パラメータの有効性を先に検証し、GPD/EVT の該当チェックを理由付き FAIL にするか、契約上の明確な入力エラーとして扱う。少なくともゼロ除算のままにはしない。なお、現在の GPD 検査は保存推定値の周辺尤度比較であり、独立した最適化の再実行と同一ではない。

## 今回の検証結果

| 確認 | 今回の結果 |
|---|---|
| hullkit＋report 全テスト | **1252 passed, 2 warnings in 37.87s**。警告は japanize_matplotlib / distutils の非推奨警告 |
| `ruff check johnhull` | PASS |
| `verify_release.py --require-tracked` | PASS |
| 現在のコミット済み reference の acceptance | 11 巻、計 118 checks、全件 PASS |
| 巻別 VALIDATION と metrics 由来の生成内容 | 11 巻すべて `validation_drift=None` |
| D1: `bootstrap_zero_curve([(1.0, 0, 97.8)])` | 例外なし。連続複利ゼロ金利 0.0222456089473 |
| D2: Ex 7.1、`first_accrual=0.5` | bonds = −0.291999794241519、fras = −0.291999794241545 |
| vol 28: bootstrap hazard を全 0 に変更 | `cds_bootstrap_round_trip` が FAIL |
| vol 28: survival を全 0 に変更 | `cds_par_spread_hull_pin` が FAIL |
| vol 27: GPD losses を全 0 に変更 | PASS にはならず ZeroDivisionError。F5 として記録 |
| D8: vol 21 / 27 の notebook を新規実行 | 両方とも `stale_output_cells=[]`。保存テキスト出力と一致 |
| D9: 出力の保存 | 17 冊に出力あり、PNG 86 件・Plotly MIME 25 件 |
| コアの古い数値の検出プローブ | 保存 stdout 1 / 新規出力 2 でも `[]`。F4 として記録 |

現在の acceptance 件数は vol 18 から順に **8 / 11 / 12 / 9 / 7 / 9 / 10 / 10 / 11 / 14 / 17**。tamper ケース数や pytest のテスト数とは別の指標である。

実行コマンド（projects root）:

```bash
cd /home/kazumasa/projects
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider \
  johnhull/hullkit/tests johnhull/report/tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m ruff check johnhull
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python johnhull/scripts/verify_release.py --require-tracked
```

CDS の再確認コード。配列はメモリ内だけで変更する:

```python
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, "johnhull/scripts")
from frontier_acceptance import evaluate_acceptance

ref = Path("johnhull/volumes/28_credit_desk/reference")
metrics = json.loads((ref / "metrics.json").read_text())["metrics"]
with np.load(ref / "credit_scenarios.npz", allow_pickle=False) as stored:
    arrays = {name: stored[name].copy() for name in stored.files}
arrays["cds_bootstrap_hazard"][:] = 0.0
record = evaluate_acceptance(28, metrics, arrays)
print([check["name"] for check in record["checks"] if not check["passed"]])
# ['cds_bootstrap_round_trip']
```

## 検証の境界と次の作業

今回は artifact の全再構築、全 19 コア notebook の再実行、book / portal の再ビルド、全ページのブラウザ描画、deep_hedge_price の 206 テストは再実行していない。これらの PASS は `VALIDATION.md` の実行記録として読み、今回独立して確認した結果とは分けて扱う。既存 build を含む tracked release の静的契約検査は上記のとおり成功している。

次は **F1/F2 の現在値・状態の整理 → F3 の計測来歴 → F4/F5 の検出・診断改善**を勧める。節別台帳を作るまでは、章・節の完了率を確定値にしない。新機能・研究課題の優先順位は、その残作業を整理した後に決める。

レビュー対象のハッシュ:

- `VALIDATION.md`: `eb272f6ab7a44c6d13b6c3c46c86e9b9229733f1a33162743815cde82860a989`
- `docs/SECTION_AUDIT_2026-09-14.md`: `d60b984bb902f63daf3b9f756ebf0cceab834744456125627fc78b70a25c5017`
