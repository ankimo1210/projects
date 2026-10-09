# Task 6 optional evaluation sink 独立限定レビュー

2026-10-10。Task6 本体作者による root-owned 変更の読取専用レビュー。

**限定 source 承認。未解決0。金融source・pilot・freeze・主実験の承認ではない。**

対象 SHA:

- `run_reference.py`: `7a8f4a3e3d0289a06ca2d1732fe8287a3a87a1ca10a2585a4e3fab400ae22110`
- `test_dynamic_hedging_runner.py`: `88474feec57cb9b6fff64be2251b2a237b43be164885304338355766658726e7`

確認した境界:

1. `run_execution_main` の任意 `evaluation_sink=None` のみ追加。旧 strict v1 `run_main` と sink 未指定の戻り値は維持。
2. source identity、元12 fit、raw 4×14 validation、A readiness の後に loader が呼ばれ、その後36個の G/seed/level/U ごとに実 `study.test_roster` の11 cells が sink へ渡る。元396 cells の実行を減らす入口ではない。
3. sink の返す参照のみをリストに保存し、`row/result` を各反復末に解放。weakref テストは次の評価前と終了時に先行配列が残らないことを検査する。呼出し側が参照へ配列を入れた場合の保持までは禁止しない。
4. 独立 writer 例外 probe は最初の sink の `RuntimeError` をそのまま伝播させ、retry/fallback・結果の捏造なし。sink 自身の保存と復元の金融検算は呼出し側の責務。

独立検証:

- runner41 + 当時の Task6 main15 = **56 PASS、30.96秒**。両者の合計を root 作者41件へ重複加算しない。
- 別 probe **PASS**。合成 source registry と小さい評価stubだけを供給し、実 A/raw gate を置換していない。正式 originalN の金融経路・main/PDE/教師を実行した証拠ではない。
- 実 stdout は `task-6-main-sink-review-test.log`、`task-6-main-sink-review-probe.log`。probe source は同名 `.py`。

本体は lazy metadata enumeration と immutable artifact sink を使う。このフックだけでは all costs/Q/refinement/saved checker の受入を成立させない。
