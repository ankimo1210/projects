# 正式 pilot 日付ゲートの N 契約：独立診断

## 結論

保存実入力の Asian cache は canonical key original_N=1024 を持ち、N は持たない。旧固定 run_pilot.py:2832 の asian_cache['N'] が実際の KeyError: 'N' の原因。これは consumer の key 契約違反。

## 保存証跡と連鎖

- 原 teacher:Heston:N1024:coarse:raw は executed、raw original_n=1024、cache original_N=1024。
- domain-selected teacher:Heston:N1024:coarse は executed。同じ原 N と cache schema を保持。run_teacher_domain_selection_job:3114–3128 は cache のコピーに domain metadata を付け、N 別名は付けない。
- 前に完了した selected-state:state00 も同じ native cache を保存し、run_state_job:1240 は original_N を読む。
- 原 plan の date gate 引数は domain-selected teacher の path=['cache']。保存失敗 record は raw=None、cap_evidence=None、status=unclosed_source_or_solver_defect、reason=KeyError: 'N'。
- build_asian_cache は _dynamic_hedging_surfaces.py:504 で original_N を返す。保存再評価 _dynamic_hedging_replay.py:352–363 もこの key と原 denominator を認証する。
- check_date_gate_record:1828–1830 は run_date_gate_job を再評価し、raw original_n と保存 record を比較する。producer 1行の修正でこの再評価経路も修復される。checker の schema 変更は不要。

## 最小修正と既存テストの不足

run_date_gate_job の返却 original_n を asian_cache['original_N'] にする1行修正。cache producer に N 別名を追加せず、原 N/全axes/16block/threshold/driver/financial unknown/old failure を保持する。

診断開始時点の専用 tests の date_gate 検索は teacher_candidate_gate の metadata/stage fixture に限定され、native teacher/domain cache（original_N のみ）から実 run_date_gate_job→check_date_gate_record を通す回帰がなかった。canonical schema で raw original_n と16-block saved-check の契約を通す回帰を追加する。金融教師や RNG の新規生成は不要。

旧 runtime source canonical1cc16cf7… / nativebe858ced… と旧 partial を固定保持。root が producer を修正した後の新 source 結合と実行は別判断。旧 partial70をphase accepted とせず、source error をcapへ分類しない。

詳細は task-5-formal-date-gate-N-contract-independent-results-v1.json。独立側は保存読取とAST照合だけで、新金融/RNG/SDE/solver/Popenは0件。最初の保存読取が failed raw=None をdict扱いした reviewer の失敗も結果へ費用unknownと共に残した。
