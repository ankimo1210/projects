# B fixed-domain replay adapter independent source review

更新UTC: 2026-10-09T16:19:22.409154+00:00

## 判定

**限定 adapter code を承認。blocking findings 0。**

実際の source / dedicated tests / 旧 HEADとの差分を読んで、approved B interface に対する source integration と saved-cache comparison を独立に確認した。本レビューは自作 B surfaces source の再レビューを含まない。B は interface と dependency SHA の参照のみ。

承認対象:

- deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_replay.py
- deep_hedge_price/tests/test_dynamic_hedging_replay.py

承認から除外: 金融 SE / Greek / oracle 精度、candidate-specific bounds qualification、正式 pilot、source freeze/main readiness、本物 main/fresh/CAS、全 suite、v1.1 A schema。structural integrity PASS は qualification を unknown のまま保持する。

## Binding

approved proposal SHA:
3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b

reviewed adapter source SHA:
cb6aa06426f93705cf5613c57e8966fc7d8b0395d33e990abc95c7fe8b18a12b

reviewed dedicated tests SHA:
d811e320f449c9cd92b2894b8da38b0de2c292d4423c06a74491288f12c04781

B private surfaces dependency observed SHA:
d04ab70b83d19545e121338a54dd8daf5e9f5aef8dded3f1c764d4e14b6a83fe

rebuild_asian_cache(rows, parameters, axes, *, model, evaluation_domains=None, saved_cache=None) は per-date JSON descriptor を B builder に渡す。explicit geometry / schema / sheet mapping は厳密一致、physical bounds / prices / arrays は rtol=2e-10, atol=2e-11 の数値照合。NaN位置と shape を保存する。

## 実コード確認

- _same_cache_domains は original date count、各 None/box、全 model axis key set、整数 pair / exact index range、schema と sheet mapping を bind。float の near integer や bool の index に数値 tolerance を適用しない。
- None argument の旧 global cache は domain keys が欠落又は全 None の保存値を受入れ、explicit saved domain を拒否。explicit requested descriptor と legacy saved cache の混在も拒否。explicit per-date None は default fallback へ変えない。
- _same_asian_cache は full f / block_means / axes / dates / support_mask / original_N / driver ID / interpolation / dedicated t0_sheet を箱外まで比較。原 NaN を zero 補修した saved cache は reject。
- 元 group count、parameters、bounded label summaries、全16 CV block曲線、N/blocks/block_path_count、status/status_reasonsを照合。failure/unknownの救済や分母縮小はない。
- generation cacheの追加 N×threshold path samples と replay固有 slice_driver_id/説明 scope はこの group-summary comparison の対象外。元 primitive chunk / driver mappings が別 evidence boundary。earlier SDE/global generation は未認証のまま。この限定はdocstring/unverifiedと一致し、独立 financial/oracle認証に使えない。
- row iterator は1回だけ消費。replay_teacher は既存 primitive の式・saved local fieldの評価・labelsを再計算するが、新 teacher生成、乱数、CF/PDE solveを呼ばない。
- 元 default、market/cash/statistics replay、replay_teacher等の既存 source definitions は AST 上不変。既存 source definitionの変更は rebuild_asian_cache だけで、新2 helpers追加。
- 旧 dedicated testsの AST prefixは不変（旧82 casesを保持）、新19 casesを追加。

## 独立検証

- 専用 suite再実行: **101 passed in 0.97s**, subprocess wall 1.2476042549997146s。author報告ではなく、このreviewerの新しい実行ログを保存。
- 対象2 filesの ruff check / format --check PASS、限定 git diff --check PASS。
- 独立 scratch probe **33 cases**すべて期待結果。
  - exact metadata一致、numeric bounds/arrays +1e-12 は accept。
  - index変更/near float/bool、schema/sheet変更、4metadataの欠落、bounds誤差は reject。
  - box外 mean/16th block のNaN補修、内部16th CV block改変/削除、原threshold軸短縮、support改変は reject。
  - 原cache N/group N縮小、unknown status救済、status reasons欠落、group除去は reject。
  - local dedicated t0の全40groups、全原t0軸/16blocksを照合。t0箱外block/元spot軸/sheet mapping改変は reject。
  - explicit unavailable dateとlegacy missing/null defaultは受入、explicit/legacyの混在はreject。
  - 全 probesにsingle-use iterator guard。Heston6 rows / local40 rowsを1回消費。
  - teacher_primitives、np.random各入口、CF/quadrature入口をfail-on-callにし、**solver/RNG regeneration calls 0**。fixture setupは乱数なしの手指定finite driversを使用し、禁止guard前に組み立てた。
  - successful replayの qualification は全て unknown。

probe成功 wall 0.4598744290005925s。最初のprobe harnessで、nested list/dictのimmutability確認にnumeric _sameを誤用してTypeErrorになった。source欠陥ではない。recursive harnessへ修正し、元failed script/stdout/receiptも保存してから全33 casesを再実行した。

## 証跡と次工程

この ignored SDD に review probes.py/json/txt、失敗した初回harness、suite stdout/receipt、Ruff/AST compatibility/diff-check receipt、reviewed source/test snapshotsとSHA manifestを保存。source/Git/canonical docsへのmutationなし。金銭feesはtool outputに存在せず未計測。

rootによるB source独立レビュー、deep generation/saved replayへの正確なsource/domain binding、candidate別金融accuracy gate、pilot/cap費用、A readiness/qualification truth tableの工程を続ける。本承認を候補boundsや正式pilotの承認に転用しない。
