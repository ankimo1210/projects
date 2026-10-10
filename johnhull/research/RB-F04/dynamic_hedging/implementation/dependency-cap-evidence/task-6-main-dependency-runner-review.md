# Task 6 runner dependency cap 独立限定レビュー

2026-10-10。Task6 main 作者の読取専用レビュー。**限定 source approved、未解決 0。金融精度、正式 freeze、主実験の承認ではない。**

- `run_reference.py` SHA: `cc7183df08f8d4b7942929ccc44cbcc5899be5df74128016c7c6521bac2909b9`
- runner tests SHA: `f44c0bd50b5ddec76aa9f2dca7e7363d72a355156817984bb9977a2e96032f54`
- 独立実行: `task-6-main-dependency-runner-review.log`、6 PASS / 79 deselected、4.08 秒。

実 source/raw selection/12 fit/readiness guard の順序は保持され、loader は guard 後だけである。指定 `execution_status=unexecuted_dependency_cap` の場合だけ static helper を呼ぶ。元 N は frozen selection と一致を要求し、dataset/risk/政策を読まない。helper 例外は最初の sink 前に伝播する。strict v1 は typed cap を拒否し、正常 case の金融経路と任意 sink 解放は保持する。source identity は今回追加された bare `run_main` を全 phase 境界へ含む。

runner 3 tests の bounded helper は合成 stub なので、その実行だけを金融証拠とはしない。実 helper 合同 test は `deep_hedge_price/tests/test_dynamic_hedging_main.py::test_parent_actual_guard_and_actual_cap_helper_retain_all_396_original_slots`。actual market worker の宣言 cap、immutable 親 raw/receipt/source/input 検査、actual helper を使い、18 cases × 2 U × 11 cells = 396 unique 枠、元 N=32768 を保存する。source registry だけは限定合成 fixture で、reserved RNG と政策は呼ばれていない。したがって正式 396 cells の金融実行・収束を示さない。

cap branch が根拠不明 case を承認する処理はない。actual parent receipt を検査する helper と producer/checker の閉鎖は main source レビューで別に確認する。
