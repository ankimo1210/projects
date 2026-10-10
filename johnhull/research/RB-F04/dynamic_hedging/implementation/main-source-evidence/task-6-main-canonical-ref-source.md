# Task6 canonical producer参照 — 最終source checkpoint

2026-10-10。限定source承認済み。正式DAG/freeze/金融精度/全費用/研究完了は未承認。

正式DAG dryrunで、事前guardの `$job` と実resolverの `{job[,path]}` が接続しないことを確認した。親の指示によりactual schemaへ最小修復した。全3 distinct producer IDs、whole raw、declared paired operation、producerとmarketの原N4096、market_pair→元ordered reserved seedsを事前に照合する。inlineはrecord自体も原N4096/paired_pnlで必須とし、shared_marketのNだけで代用しない。未解決 `$job` は許さない。

元参照の依存列挙→actual resolver→prior guardを接続し、金融/RNGは遮断した。4 genuine RED（canonical接続2、未解決legacy/inline N64のDID NOT RAISE2）からGREEN。既存fixtureもactual schemaへ更新した。事前metadata照合は保存金融算術と正式raw gateを代替しない。

| 対象 | SHA-256 |
|---|---|
| `johnhull/research/RB-F04/dynamic_hedging/run_main.py` | `4956903ea0b6f25a2a556fc1e0745b2d98d253ff3d26731e6cf55e5fc253cbc4` |
| `johnhull/research/RB-F04/dynamic_hedging/check_main.py` | `ada38ad09270ce4468f33840dba48b83ad74f1922a388103f65ec76b4d3a8134` |
| `deep_hedge_price/tests/test_dynamic_hedging_main.py` | `f24564687cbfd54501dbba7e2318b52b96c3808e3461a8e9e57bcde42e06faad` |

著者80scoped PASS31.26秒、Ruff check/format3PASS。独立14scoped PASS1.34秒、18自己整合receipt反例全拒否、Ruff3PASS、限定approved。独立判定は `task-6-main-independent-final-review-canonical.md/-decision.json/-manifest.json`。件数を著者80へ重複加算しない。

原始source/log/diffのSHA・byte数は `task-6-main-canonical-ref-snapshot.json`。旧4517f766 sourceを逆patchから再構成し旧SHA完全一致を確認した `task-6-main-canonical-ref-previous-run-main.py.txt` と最新copy・unified diffを保存した。新旧ASTで変更は `_prior_three_stream_records` と呼出し側の2functionsだけ。finance/cost/resume/stat本体とcheck_mainはbyte不変。

全体の実装・元396scope・resume costs・actual policy full/view同値と容量測定は前段 `task-6-main-source.md` を参照する。前段4517 snapshot/72testsとactual probeは元bytesの履歴として保存する。このcanonical修復の最新SHAはこの文書が示す。正式source固定へ旧probeを流用しない。

正式main planは `task-6-main-plan-draft.md` のTODO条件を解消するまでlock不可。原full-runの連続wall時間は未実測。
