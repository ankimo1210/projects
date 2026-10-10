# 元fullmixedの次の事前予算・config（限定整理、2026-10-10）

**結論：rootのconfig更新でジョブ予算・出所・受入cap選択を具体化できる。全phaseのディスク上界と、外側停止を既存の受入capへ変換する契約は未確定。現時点で正式lock／金融精度／phaseは承認しない。**

元v3の3,138 jobs／28 operations、121 cases／51 obligations、20 teacher／10 driver、全N・threshold・seed・unknown・failed義務を保持する。source81のcanonical identityは408f2bc271a3379fb5aa8a1c96be0839f090cd3b2452bcd8b8a94c4af7bb7652。旧draftの原controlsと最新実測の変更点を区別して結合する。

## rootが次のprior/configへ記入する場所

| 場所 | 具体的な更新と未確定 |
|---|---|
| controls／原arguments | M2/M3の49日付・原state axes、M4/M5の全7 spots・3CF/4PDE levels、原field257×321を維持。独立call controlsの原{}と測定で使ったupper250／log_half_width1.8／2401 space／1920 time等の差は、明示したroot controls deltaとして保存し、原入力を同一扱いしない。 |
| reviewed_budgets[全3,138 job IDs] | 全件budget欠落。各jobにplanned_before_attempt=true、独立review SHA、正のwall_secondsを記入。predictionのexpanded_bytesは全件None、rate_sourceも全件未設定。measured_prior_jobまたはindependently_reviewed_estimateへ出所付きで更新し、28種全operationを覆う。 |
| predictionの粒度 | 元path_steps／total_path_steps／financial_child_count／child_boundaryを保持。256MiBはchunkの展開上限、1e9は原job/child境界のpath-step上限。full保存量・aggregate RAM・total workをこの小上限で代替しない。4件の追加date教師のby_original_n全4枝も元Nに対応したbyte/rateを記入し、branch identityを再固定する。 |
| lock_job_graphの引数 | source=現81件closure、inputsの実値由来SHA、全reviewed_budgets、原失敗・既往費用history、required_external_expense_idsを設定。既存validate_locked_planを通す段階はrootの次の作業。今回再compile／実行はしていない。 |
| execution_projection | cases121／attempts51すべてcap_options=[]／parent_expense_id=None。元case/attemptを変えず、実wall cap親job・正確なlimit・事前budget decision digest・expense aliasを候補ごとに固定する。v3のcap_scopeはselector/adapterを含む真の祖先unionを保ち、実消費した親だけ投影する。未実行子のNとunknownを保持し、scope宣言だけを拡大して通さない。 |
| 外部10 expense | cold_imports、source_registry、code_review、math_review、pilot_review、serialization、saved_check、CAS_primary、CAS_mirror、domain_selection。原実時計・parent・covered_job_ids・出所を結合。実測親のinclusive aliasは再課金せず、レビュー／CAS／最終checkpoint後の費用はactual receiptが必要。過去の部品費用を新phase実費にコピーしない。 |

operationごとの埋め方：①field／premium／quotes／source／call_cache／call_tableはM2–M5・既存入力準備に結合。②teacher_driver／teacher_grid／teacher_domain_selection／teacher_candidate_gate／teacher_selection／teacher_selected_inputs／date_gate／stateはM6の原geometryと保存再検算に結合。③oracleはM7の元state00・N4096・13queriesに結合。④market_pair／quote_risk／bump_risk／Q／empty_claim／teacher_diagnostic／frequency_cache／precision、⑤validation／cell_pair／stream_receipts／tiny_fits／rosterは既存scoped source証拠＋未測定を明記した独立推計を使う。部品測定で未評価の領域は数値資格unknownのまま。

## 実測と容量をどこまで使えるか

M2/M3外側wallは55.631／7.667秒、M4/M5は5.468／35.561秒。旧M6生成＋検査は1,401.807秒・3実RSS capsを含み、新bounded保存再検算774.091秒は別scope。M7は104.216秒（Heston13.744／local90.384、現N4096）。この比率を全state・最大N・全28operationの保証にしない。M7はroot原測定の読取で、今回独立金融レビューしていない。最大Nのgenuine source準備は進行中の作業を待ち、追加実測案を増やさない。

静的353,606,441,728 Bは論理配列の部分量。node/nativeの限定名目355,868,451,168 B、driver/grid/report込み364,185,768,816 Bも全物理upperではない。metadata、standalone full diagnostic、他job、旧失敗、staging／restore／複写／両vaultを別枠にする。過去観測の空きC314.778GB／F185.711GB／WSL595.310GBは実行直前に再確認し、C/Fを合算しない。合成やN1024の圧縮比を全量へ保証しない。

## sourceを変えずに使える外側資源監視の境界

Dのroot enclosing wrapperに、対象volumeごとの実空き／使用byte／安全reserve、監視頻度、全phase wall／RSS行政上限、graceful停止猶予と保存tail容量、実start/stop/CPU/returncode、停止理由・観測欠落を事前固定できる。原root/work/pack・未実行義務と実費を残し、同時発生exceptionの順序不明もunknownとして残す。これは資源を制限した実行試行には使えるが、全corpus完了の容量保証にはならない。

現run_pilotは一部workerへwall_cap_secondsを渡し、返却後の実elapsedをjob capに結合する。checkerのcheck_job_envelopeはwall_secondsだけを認証する。phase時計は最終checkpoint直前までのinclusive実費で、全phase wall/RSS/storage capによる中断を全caseのgenuine capへ変換する実装はない。外側killは原partialの資源停止として保持し、未完row／checkpointやsource・solver欠陥をfailed_at_declared_capに書き換えない。完成済み行は元plan/sourceでresume認証できるが、中断された全phaseの正式受入は別に未閉鎖となる。現sourceを保つなら、この未閉鎖を許す行政試行と、元契約のwall cap optionsで閉じる判断を分離する。

## 出典・今回の範囲

full-progressive draft-source-unit-v3、producer-v3／formal-pilot-plan-producer、run_pilot.py:3845/3976/4198/4299、check_pilot.py:746/1098/1637/4009、whole-phase-capacity-static-v1-report、M2–M7の原enclosing receipts、M6-saved-recheck-independent-v1を参照。詳細counts・SHA・読取費用は同prefixのresults.json／manifest.json。production/source/docs/tests/Git/CASは変更せず、Dだけに保存した。
