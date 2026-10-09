# Task5 protocol/artifact component

2026-10-09。担当の private 新規source・testsのみ実装。**Task5全runner・正式pilot・研究freeze・主実験・最終受入は未完了。** 本reportの成功fixtureはsynthetic receipt構造の検証であり、正式pilotの数値承認ではない。

## 変更範囲・API

- `deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py`（743行）：固定candidate、用途別SeedSequence、original fit/cell roster、source bytes registry、freeze／test開封境界、raw expenseとcharge、JSON+NPZ chunk。
- `deep_hedge_price/tests/test_dynamic_hedging_protocol.py`（539行）：52 tests。original count、namespace、未測定／flag-only拒否、digest binding、fit/candidate消去、test leakage、重複追加、計時、成果物改変／サイズ／object拒否。
- Git・既存金融source・public API・`__init__`・依存・共有docs・unknown xaaは変更していない。索引・runner接続・研究記録は親担当。

APIは `candidate_protocol()`, `main_seeds()`, `study_roster()`, `source_registry(root,relative_paths)`, `freeze_contract(candidate,source,pilot,review,selection)`, `assert_main_ready(frozen,candidate,source,selection_receipts)`, `validate_expenses(expenses,required_ids=...)`, `write_artifact(directory,metadata=...,arrays=...)`, `read_artifact(directory)`。

## 契約の所在とcaller義務

各APIのdocstringが正本。candidateはmarket／claim／universes／traded_call／hedging／training／validation／sde／teacher／test／premium／statistics／gates／pilot／limits／seedsを固定する。teacher Nとcoarse/high grid、test N、共通premiumのpilot選択のみ許可し、主12fixings・12hedges・全init・spread・precision gateは変更しない。

canonical digestは `SHA256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode())`。JSONはUTF-8、Noneはunknown。dictはinputからcanonical deep copyし、SHAにより後続改変を検出する。Python dictを物理的read-onlyにするものではない。hashはprovenance用で金融精度の保証ではない。

`source_registry`はcanonical relative POSIX path→SHA256を返す。既存file、root内、重複／path alias／symlinkなしを確認する。**金融の実import閉包の完全性はcallerが列挙する義務**であり、このhelperが自動認証しない。

seed root entropy `2026100904`、stable numeric tags 1..11を使う。train2／validation2／test3／teacher2／oracle3／bootstrap1／pilot6／premium1／refinement3／fresh3／optional_p3。NumPy global RNGを進めない。train／validationはHeston/local slots、testは3独立slotsをG間のCRNに使う。fit init11/29/47は市場seedとは別ID。

fit IDsは `fit:Heston:U1:init11` 等12件。cell IDsは `cell:Heston:U1:no_hedge`, `cell:Heston:U1:greek:Heston`, `cell:Heston:U1:band:local`, `cell:Heston:U1:nn:trainHeston:init11` 等44件。各cellはgenerator／valuation／universe／policy／training_generator／initializationを分ける。test slots0/1/2とlevels192/384/768は明示dimensionsであり、原始IID分母を9倍しない。

### freeze receipts

pilotは次を必須とする。

- `qualification="qualified"`。
- `verification={checker:<非空>,evidence_sha256:<64hex>,inputs:{candidate:<SHA>,source:<SHA>}}`。
- `original_counts={selected_states:18,initial_quotes:37,tiny_cells:44,tiny_fits:4}`。
- `measurements`：candidate.gatesの各metric（mse_difference_absolute/relativeは除く）をfinite非負で保存し、加えてbaseline_mse／mse_difference。全caseを含むworst-case reductionでgateに照合する。
- `teacher_n={Heston:<candidate N>,local:<candidate N>}` と `teacher_grid={Heston:coarse|high,local:coarse|high}`。
- `test_precision`：8192/16384/32768を順に、各original_n／worst_mean_loss_se／worst_mse_se／baseline_mse。固定SE規則を満たす最小Nを選ぶ。
- `premium={value,se,scheme_error,original_n:65536,steps_per_year:1536,seed:<reserved premium seed>}`。

reviewは同verificationにpilotのSHAもbindし、qualification qualified、`scopes={code:approved,math:approved,pilot:approved}`、`unresolved_issues=[]`を要求する。

selectionはteacher_n／teacher_grid／最小test_n／premiumと、全band_width_candidates／baseline_rule／checkpoint_ruleを同一値で保存する。

**18state／37quote／精度gateの数値再計算をhelperが行ったとは扱わない。** callerの独立saved checkerがraw arraysから元分母・失敗を含めて再計算し、evidence receiptを発行してからfreezeへ渡す。teacherの最小qualified prefix選択、support交差、finite covariance／Ctheta参照誤差、moment certificate、cutoff／bump／quadの誤差分離もcaller checkerの義務。checker名やSHAの存在は第三者の真正性認証ではない。

### main selection receipts

`assert_main_ready`はtrain/validation→test境界で使う。pre-freeze train開始許可の関数ではない。

`verification.inputs={frozen:<frozen_sha256>,candidate:<SHA>,source:<SHA>}`、`test_opened=False`、fits12、validation4を必須とする。test開封／既存frozen改変／source又はcandidate不一致は拒否。

fit各recordはid／status(completed|failed)／attempted=True／original_n8192／requested_updates512／updates／elapsed_seconds／selection_status(completed|failed)／validation_original_n2048。selectedならcheckpoint_id=`last_finite_completed`。completedはupdates512、final diagnostics含むelapsed≤300秒。failedはreasonとfailed selectionを保ち、unknown elapsedはNoneのまま。失敗fitをcompleted familyに数えない。

validation各recordは`selection:<G>:<U>` ID、generator／universe／status／original_n2048／candidates。2Greek＋両Mの全6width（計14candidate）を消さない。candidate IDは`greek:Heston`／`band:Heston:width0.01`等、status／original_n／completedならfinite MSE、failedならreasonを保持。

selected_bandsは両Mのcandidate ID又はNone、selected_baselineはfinite original-N MSEの最小candidate。tieはHeston/local、Greek→widthの固定順。Mのband全失敗はNone＋band_failures[model]、baseline全失敗はstatusfailed＋reason。失敗は選択完了と混同しない。finance／weights／全attempt historyはcallerのsaved checkerが検査する。

### expenses

各recordはid／scope／status(complete|failed|pending)／parent_id／includes_children／timing必須。timingの必須keyはwall_seconds／cpu_seconds／overrun_seconds。complete/failedは非負finite又はNone、failedはreasonも必須、pendingは全timing None。overrunはwallの内数で加算しない。

required_idsはcallerの完全phase ledger。recordから再推定して消去を見逃さない。親IDは既存で循環なし。inclusive祖先があるdescendantはraw_recordsに保持してchargedから外す。totalsにNoneが混じればNone、measured_subtotalsは別名で保存。未知時間を0にしない。外部JSONの採用／speedup／payback判断はcaller責任。

### artifacts

new directoryにmetadata.json／arrays.npz／receipt.jsonを保存し、existing directoryを拒否する。NPZはobject/pickle不可、bool／NaN／numeric raw failureは保持。expanded NPY payloadはheader込み256 MiB以下。書込途中の失敗directoryはincompleteとしてreadが拒否し、自動overwriteしない。

readはcanonical receiptとJSON／NPZの実bytes SHA、expanded size、dtype／shape／nbytesを検査して(metadata,arrays,receipt)を返す。RNG／train／networkは呼ばない。**bytes一致の後、金融semantic checkerがraw evidenceを再計算する**。CAS両コピーやstudy全load完了をこのunit testで認証しない。

## RED→GREENと検証

1. candidate／namespace tests2件：missing moduleを確認後、2 passed。
2. source／expense／artifact tests14件：missing APIsを確認後、16 passed。
3. freeze／main tests33件：freeze missingを確認。freeze実装後31 passed＋assert_main_ready missing18 failedを確認。main実装後49 passed。
4. 最終拒否反例3件：extra duplicate fit／validationとnegative failed elapsedがDID NOT RAISEでRED。件数＋失敗計時の最小修正後52 passed。
5. Ruff import1件と2file formatを修正後、fresh scoped pytest／ruff check／format checkを再実行。

実行command（WT絶対PYTHONPATH、shared .venv、root conftestをconfcutdirで切離し）：

```bash
cd /home/kazumasa/worktrees/johnhull-research-roadmap
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src:/home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/hullkit/src \
  /home/kazumasa/projects/.venv/bin/python -m pytest -q \
  --confcutdir=/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price \
  deep_hedge_price/tests/test_dynamic_hedging_protocol.py
# 52 passed in 0.22s / exit 0
/home/kazumasa/projects/.venv/bin/ruff check \
  deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py \
  deep_hedge_price/tests/test_dynamic_hedging_protocol.py
# All checks passed! / exit 0
/home/kazumasa/projects/.venv/bin/ruff format --check \
  deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py \
  deep_hedge_price/tests/test_dynamic_hedging_protocol.py
# 2 files already formatted / exit 0
PYTHONPATH=/home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src \
  /home/kazumasa/projects/.venv/bin/python -c \
  'import deep_hedge_price._dynamic_hedging_protocol as p; print(p.__file__)'
# /home/kazumasa/worktrees/johnhull-research-roadmap/deep_hedge_price/src/deep_hedge_price/_dynamic_hedging_protocol.py
```

full suite・金融実験は依頼範囲外につき実行していない。親が索引／integration／研究runner検証を行う。

## 固定指紋・未検証

source SHA256: `bbe326e8b1c31daf37a56e86a0464eb35cd8fed3e9dbf8e9f71291bf39f63700`

tests SHA256: `1286179495e115ca435afe54be67af48caf034311556af7ab90f972da3f0aa36`

レビュー開始時点でこのsource/testsを固定する。今後の変更は指摘＋新RED/GREENと新指紋を親へ通知する。

正式pilot receiptsは未生成。金融価格／Greek／P&L gateの達成、source依存閉包、全12fitの実行、44cell main、CAS復元、expenses全scope、plots／notebookは未検証。これらはrunner／independent checker／formal pilot／Tasks6–7で確認する。
