# Grid saved-check の bounded report 修正：作者報告

## 結果

専用 17 件、関連既存 pilot 46 件、Ruff / format 2 ファイルが PASS。
実行依存の実 closure は 81 ファイル、dynamic import は 0。
旧 M6 source81 との差分は check_pilot.py だけ。残る 80 ファイルは原 byte と同一。

限定 source-unit の作者検証結果であり、独立承認・原 M6 saved-only 再計測・正式 pilot / main の金融受入は未完了。

## 変更した 2 ファイル

| ファイル | 変更 |
|---|---|
| johnhull/research/RB-F04/dynamic_hedging/check_pilot.py | grid の report_mode（full が既定、bounded を追加）。全検算後の小さい要約と原 raw 参照、cache=None の逐次消費、全節点消費数確認。正式 teacher_grid / teacher_domain_selection の 2 呼出箇所だけ bounded を明示。 |
| deep_hedge_price/tests/test_dynamic_hedging_teacher_check_report.py | 全 coarse 108 節点の小さな保存済み fixture と 17 件の検査。小 N16 / 24 step は source-unit 入力。元 M6 N1024 / 768 step と正式入力は変更していない。 |

単体 check_teacher_record の AST、返却値、引数は変更していない。
grid の既定 full 返却も維持し、成功 top status は追加していない。
replay / codec / SDE / 数学 / threshold / 公開 API / 依存は不変。

## 検算と保存境界

- 原 N 全数・全節点の saved-driver SDE replay、全 label（11 sample 配列、16 block、covariance、status 等）、全 cache の比較を従来経路で終えてから report を小さくする。
- report は原 node path、index、coords、物理 raw_binding または legacy raw_sha256 に結合する。物理 SHA は provenance 用で、再構成 float の数値一致には使わない。
- 元 raw の primitive / 全 labels / block / covariance / failure / unknown / 費用は全て残る。report は raw_status / SE / invalid・unknown 数 / SDE flag / financial scope 等の小さい要約と全 label field / shape / dtype の descriptor を持つ。
- runtime artifact_context は原/復元 root の読取にだけ使用し、report に保存しない。原 path / binding は維持する。
- declared cap の report は全原 N・未実行数と raw 参照を維持し、SDE 完了や labels 比較済みを付与しない。NaN / unknown を completed にしない。
- cache=None では raw rows をリスト化せず逐次消費する。cache consumer が途中で止まれば coverage 不一致として拒否する。

旧 prepared-v1.patch の artifact_context 保存案は採用していない。原 draft を保持し、最終 diff は今回の root 指示に従う。

## 検証

全証跡名には task-5-teacher-check-report- prefix が付く。

| 対象 | 結果 | 証跡 suffix |
|---|---|---|
| TDD RED | 既存 full の genuine 108 節点検算後、未対応 report_mode が TypeError | bounded-red-v2.log/json |
| 新専用 test | 17 PASS / pytest 55.71 秒 | bounded-green-v3.log/json |
| 関連既存 pilot | 46 PASS / 145 deselected / pytest 31.22 秒 | bounded-affected-green-v1.log/json |
| Ruff / format | 2 file PASS | bounded-ruff-check-v2.log / bounded-ruff-format-v2.log |
| AST | 既存変更は grid checker / _raw_job_check の 2 関数のみ。単体 teacher と他関数は不変 | bounded-ast-and-snapshot-v1.json |
| 実依存 | 81 source / dynamic 0。旧 source81 差分は checker のみ | bounded-source-closure-v1.json |

専用 test は、全 11 sample descriptor と original N、full/bounded の cache/要約一致、末節点の sample/block/covariance/status 改ざん、末原 path の SDE primitive 改ざん、unknown cache の変更、cap / invalid path / NaN、legacy binding、2 formal dispatch、欠落節点 / 座標改変 / 早期 cache 消費を確認する。
原 root を実際に不在にして復元先だけで成功し、report の原 path / binding / 検算要約が一致し保存復元できることも確認した。

保持検査は実 saved raw と実 replay label の弱参照で行った。
各 node 読取時、以前の再計算 sample/covariance は 0 個、以前の raw 配列は最大 2 個まで。関数終了後は全て解放された。
これは全 N65536 の peak RSS 保証ではない。

RED-v1 は PYTHONPATH 未設定による収集エラーとして原 log を保持。
GREEN-attempt-v1 / GREEN-v2 の cache test は、最初に NaN へ加算して値が変わらなかった入力、次に期待 regex と実エラー文の違いを修正した。数学/source 修正は追加していない。途中ログを保持している。

## 固定 identity と snapshot

- checker SHA: a37626ff56e6ae74e08d6841c66ca9ec5712596d491930e623620d35607bce5b
- 専用 test SHA: ce679b219491725e82da021c34326d06ca782fcf76f3d3b1285c7400854fde20
- source identity: d4a721c67c53a48bbabd7408c52d9ef5a5dfeb1770eaa2f242acaa625bf1c0db
- source snapshot: task-5-teacher-check-report-bounded-source-snapshot-v1/
- 最終小 fixture: task-5-teacher-check-report-bounded-unit-fixture-v2/teacher-report0/
- fixture: unit-grid artifact、unit-parameters.json、node0000..0107、driver。金融 qualification は unknown。v1 fixture も独立レビュー用に保持。
- 最終 fixture physical bytes: 29,977,546 B / 673 files。fixture manifest に全 byte hash を保存。

## 次

独立 reviewer の source / transport 承認後、root が別 prior budget を固定して原 M6 の全 2128 node を saved-only 再検算する。
原生成 source81、原 raw、旧 3 RSS cap と全旧費用を維持し、新 checker identity / 新再検算費用を別記録にする。
新 RNG / 再生成は使わず、saved SDE replay の全 original N は維持する。
最大 N 単体 RSS と正式 oracle / main の費用・予算は未確定。
作者は正式金融計測、全 suite、docs/Git/CAS の変更を行っていない。
