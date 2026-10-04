# §28.3 原典照合とレビュー

2026-10-04、Hull GE pp.675–676。脚注3の条件付き定義、式28.14のItô比とλ=sg、式28.15の同一給付価格を原典本文/頁画像と照合。[独立source note](validation/section-28-3/independent-source-note.md)参照。

同一Wienerのsigned係数、相対drift/log drift、finite-time GBMの可積分性と一般局所martingale、t=0別市場、random G_Tと測度変更を区別。
独立math参照/直接Gaussian求積/条件付きMC、保存4/API4変異を検査。教材新11/旧235保持、16表示状態と1000px目視を確認。
notebook検証器のclone由来の保存先誤りはpath assertionのRED→GREENで修正、§28.2の履歴記録はmainから復元。統合gateの必須source hashで新§28.3記録の欠落/誤参照を拒否。

## 回帰

既受入27節のbrowser・runtime probe・個別pytest計2,056件・C:/F:両保管庫復元はPASS。0節再利用・27節再描画。共有CSS変更による保守的な再描画。採用記録の再描画画像payloadは19,514,628バイトで、重複排除後の保管庫の実増加容量は未測定。採用D1パスとSHA-256を固定。

## 最終レビュー

全suiteと1名のfresh独立レビューを実行中。完了後、原文と判断をここへ保存する。

全hullkit+report 3,986 passed・6 skipped・既存warnings2件（186.50s）。変更Python20ファイルruff、4--check、台帳成果物28/278 PASS。独立最終レビュー/main統合は検証中。

## 最終レビュー対応

1名gpt-6-astra/high、範囲0aa51b13..c16964d9。Critical0/Important1/Minor1。I1の利用者影響は365daysが365yearsへ変換されNaTも有限driftになる点で、Importantのまま採用。
新private入力境界に型検査を置き、datetime/timedelta scalar/array/objectとempty batchを変換前に拒否。既存公開risk_premium helperは変更しない。
60回帰検査：RED52 failed/31 passed → GREEN83 passed（0.57s）。修正後全suite4,046 passed/6 skipped/既存warnings2（179.21s）。数値と教材4図の値は不変、fresh全文/16状態/現行hash/旧27D1・両保管庫/台帳成果物PASS。再レビューは依頼しない。
M1はdeferred：ROADMAPの旧段落に残35という記載がある。現在の受入28/278/P3 3/37と段階表は正しく、数値・証跡に影響しない。

### レビュアーの判定保留に対する判断

- 残34節の未取得原典/市場較正/実価格精度は全P3の未完了として保持（誤りなら完了範囲/検証の手戻り）。
- HW state/bond整合と公開入口への影響はM29の独立REDで先に判断（誤りなら測度価格と利用箇所に誤差が残る）。
- 全suite/16browser/27D1 producer/統合後release・pushはexecutorがfresh実行して判断（誤りなら現行配布物との不一致を見逃す）。

## 独立レビュー原文（修正前・改変なし）

# M28 §28.3 最終独立レビュー

レビュー日: 2026-10-04
対象: `/home/kazumasa/worktrees/m28`
BASE: `0aa51b134a9ddf4f4d9df0d8616fc43105b30df8`
HEAD: `c16964d99f866994e4d6571ba6fe216938f8643e`

## Assessment

**Ready to merge: With fixes.** Important 1件、Minor 1件。数式・条件付き検証・同一給付価格・証跡の主要な受入経路は整合しているが、新しいprivate APIで日時/期間型が無言で数値化されるため、I1を修正してから統合する。

今回の判定はP3の第3受入単位である§28.3に対するもの。P3全37節の完了判定ではない。既存235セル保持、新11セル、MT01–MT06、旧27節D1の範囲を確認した。

## Strengths

- `a=mu_f-mu_g+s_g*(s_g-s_f)`、`lambda=s_g`、`mu_f=r+s_g*s_f`、`mu_g=r+s_g**2`が整合。signed loadingを絶対volatilityに置換していない。原典pp.675–676の本文・脚注3と式28.14/15に照合した。
- 条件付き期待値の定義、独立将来増分、有限時間GBMのモーメント、局所/真martingaleの違いを説明している。9組の有限標本検査を一般的証明とせず、t=0の異なる状態を別初期市場と明示している。
- Q/Gの価格検査は同じcall給付を使い、G測度のdriftと確率的なG_Tを両方変更している。正負s_gの直接Gaussian求積とraw MCを独立erfc基準に照合し、自己正規化はない。
- 描画前に参照・必須source・結果digest、shape、有限性、独立解析meanとMCの統計的整合性を検査する。統合gateは保存結果を現行計算と比較し、旧235セルの本文/出力/Plotly、旧27節の依存閉包、採用D1記録と両保管庫を検査してから台帳更新を許す。
- 将来のHW/BK/LMM/M29資料は準備段階と未解決条件を明記している。公開API/root exportやproduction依存の増加はない。

## Issues

### Critical

なし。

### Important

**I1 [P2] NumPy datetime/timedelta入力を実数化して受け入れ、単位を失った値を返す。**

場所: `johnhull/hullkit/src/hullkit/_martingales.py:42`（同じ入口が`:15`、`:25`にもある）。原因は既存`risk_premium._real_inputs`のfloat変換へ、新APIの入力を型の意味を検査せず渡していること。

HEADで独立に再現:

```python
import numpy as np
from hullkit._martingales import numeraire_drifts, ratio_conditional_mean

numeraire_drifts(np.datetime64('NaT'), .3, .15)
# (-9.223372036854776e+18, -9.223372036854776e+18)

ratio_conditional_mean(1, .04, .04, .3, -.2, 1.0)
# 1.1051709180756477

ratio_conditional_mean(1, .04, .04, .3, -.2, np.timedelta64(365, 'D'))
# 7108019154642244.0
```

`timedelta64`は期間の単位を持つ。365日をfloatへcastすると365になり、このAPIは365年として指数へ渡す。さらに欠損日時`NaT`も有限の大きな負数として通過する。日付・期間配列から呼ぶ利用者が、例外も警告も受けずに無意味なdrift/条件付き平均を得る。固定教材fixtureは通常の実数なので既存56テストや4--checkはこの抜けを検出しない。

修正案: 新private APIで、float変換前にNumPyのdatetime/timedelta dtype（`M`/`m`）を拒否する。real object配列は維持し、object内に日時/期間scalarがある場合も拒否する。期間を年へ変換する規約は呼出側で明示させる。3入口、scalar/array/object、empty batchとの組合せに拒否テストを追加する。既存公開`risk_premium`の仕様まで広げる必要はなく、M28 private入口内に限定できる。

### Minor

**M1 [P3] 更新済みロードマップに旧「残り35節」が残る。**

場所: `johnhull/ROADMAP.md:312`。

M28受入3/37と次M29を同じ表へ追加した一方、直後の行が「P3金利の残り35節」のまま。現在の未受入はM29を含め34節、M29の後なら33節で、`P3_STATUS.md`と件数が一致しない。

修正案: 「M29を含む未受入34節」または「M29以降の残33節」と基準を明記して更新する。計算や受入証跡への影響はない。

## Recommendations

I1をprivate入力境界に限定してRED→GREENで修正し、仕様で要求された修正後gate・全suite・結果/source hashの更新を行う。M1は統合時の状態更新と同時に整える。新しい設計承認や公開API変更はこの指摘の解決に不要。

将来実装の優先事項として、準備資料にあるHWのQ OU状態とbond式の不整合候補をM29の独立tower検査で先に扱う。今回の§28.3計算はHWを使用していないため、その既存候補はM28の不具合として計上しない。

## 独立に実行・確認した内容

- `git diff/show`で全範囲の変更一覧、全substantive code、tests、spec/plan/execution ledger、受入文書、台帳更新経路、P3要求監査・M29/HW/BK/LMM準備資料を静的確認。
- `PYTHONDONTWRITEBYTECODE=1 python -m pytest -p no:cacheprovider`で以下8ファイル: `test_martingales.py`、`test_martingale_reference.py`、`test_martingale_numerics.py`、`test_martingale_lesson.py`、`test_martingale_notebook.py`、`test_martingale_acceptance_record.py`、`test_martingale_ledger_update.py`、`test_martingale_registry.py`。**56 passed in 15.78s**。
- `build_martingale_reference.py --check`、`verify_martingale_numerics.py --check`、`verify_martingale_notebook.py --check`、`build_martingale_acceptance_record.py --check`を再実行し、**全PASS**。最後の統合gateはcurrent filesと旧27節D1、C:/F:両保管庫のartifact検査を含む。
- 上記日時/期間の独立入力probeでI1を再現。
- 原典PDF pp.675–676を`pdftotext`で抽出し、p.676をPNGとして目視確認。
- 保存画像`book-martingale_conditional_mc-1000.png`と`portal-martingale_pricing-1000.png`を独立目視。状態ラベル、誤差棒、凡例に欠落/重なりは見当たらない。
- 終了時HEADは指定c16964d9、`git status --short`は空。checkout/index/HEAD/branchを変更していない。出力は/tmpのみ。

## 著者証跡として確認した内容（今回再実行していない）

全hullkit+report **3,986 passed / 6 skipped / 既存warning 2件、186.50s**、ruff20ファイル、台帳`--check-artifacts`、27D1の個別pytest計2,056件、16 browser states/screenshots、fresh notebook全文実行。今回の56テストおよび4--checkと区別する。browser producerは再実行せず、そのソースと保存record/hash、選択した2画像を確認した。

## Declined to judge

- §28.4–28.8/Ch29–34の残34節の実装完成度・市場較正・HW/BK/LMMの実価格精度は判定対象外。追加資料は明示的に将来準備であり、現行acceptedを水増ししていない。記載された未解決pin、外部Technical Notesの完全取得、歴史データ再現を今回完了と扱わない。
- 既存`hull_white.py`の状態/bond整合候補の修正要否と公開APIへの影響は、M29で独立REDを追加して判断すべき。今回の差分で変更も使用もしていない。
- 全16状態を新規browser操作で再観察すること、全3分suite、全旧節D1 producer再実行、主ブランチ統合後release/pushの結果は今回判定していない。指定された読み取り専用レビュー範囲と既存証跡に従い、current hash/store gateを独立再実行した。
- 上記以外に、検討した具体的な不具合候補を「仕様にない」だけで判定から外したものはない。
