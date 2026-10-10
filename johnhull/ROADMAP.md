# johnhull Coverage Roadmap — Hull 11e + Beyond Hull

Spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

| # | Volume | Chapters | Status |
|---|--------|----------|--------|
| — | `notebooks/bsm_chapter15.ipynb` | 15 | done |
| — | `interest_rate_models/ir_models.ipynb` | 31, 32, 33 | done |
| 1 | `volumes/01_foundations` | 13, 14 | done |
| 2 | `volumes/02_options_basics` | 10, 11, 12, 17, 18 | done |
| 3 | `volumes/03_greeks` | 19 | done |
| 4 | `volumes/04_futures_forwards_rates` | 2, 3, 4, 5, 6 | done |
| 5 | `volumes/05_vol_smile_estimation` | 20, 23 | done |
| 6 | `volumes/06_numerical_methods` | 21, 27 | done（§27.1–§27.8 は節単位で受入済み） |
| 7 | `volumes/07_swaps` | 7, 34 | done |
| 8 | `volumes/08_risk_var` | 22 | done |
| 9 | `volumes/09_credit_xva` | 9, 24, 25 | done（数値例のある節は vol 28 と hullkit のテストで実装・固定。残りは `docs/SECTION_AUDIT_2026-09-14.md` §4.5） |
| 10 | `volumes/10_exotics_martingales` | 26, 28 | done（§26.1–§26.17 は節単位で受入済み） |
| 11 | `volumes/11_ir_derivatives_market` | 29, 30 | done |
| 12 | `volumes/12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | done |

Shared module: `johnhull/hullkit` (uv workspace member) — 72 public + 115 private modules in this development checkout as of 2026-10-09, including two validated RB-F04 private modules integrated into main. P3–P7 logic, accepted BGM/business models, and completed RB-F07/RB-F05 studies are retained. The catalogue is `MODEL_INDEX.md`; earlier development branches are retained.

## 現在地（2026-10-11、全306節の統合完了・研究実行中）

最新：source82の正式pilotは213jobs executed＋214番gateのKeyError: 'result'でpartial終了（約3時間37分）。元sourceの全保存検算は308.541秒で個別16GiB RSS上限を超え、行政partial停止した。原失敗・費用・82source snapshot・元3,138jobs/121cases/51義務/全4Nを保持。validationはsummary行ではなく元rollouts[id]を読む最小修正を適用し、関連220tests/Ruff/format・独立静的12確認はPASS。全件逐次検算が次の作業。金融saved数値結果・新sourceのprior結合・fresh正式pilot完走・freeze/mainは未完了、qualification unknown。 [原停止と修復](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#元source82の保存検算停止とvalidation参照修復2026-10-11)。

保存検算の準備：既存APIのinputs/parameters contextを確認し、D2監視候補の作者12件・独立66件がPASS。候補・review等の閉じた30pathsは両保管庫の標準readerで原byteを復元確認済み。全job同時展開のRAM適合はunknownで、元pilotの終了receipt・閉じたcheckpointと全byte集合を結合してから実行guardを固定する。当初の候補は未許可で保持。別の実guardによる元source82の検算は全hydrateで16GiBを超え行政partial停止。 終了後の全byte結合helper v2も、作者21検査・独立限定確認を通過。既存・差替えtempの保全と、terminal partialに残る一時fileを全byte集合へ含める契約を確認した。 [検算準備](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#正式pilot後の保存検算の準備2026-10-10)。 保存検算の外側時計v2は実wall/CPU端点を記録する最小修正を完了。作者5項目・独立41項目の限定source/mechanics確認はPASS。元source82の実saved検算は16GiB行政partial停止、数値結果・総費用・他9費用は未閉鎖。 [実時計の記録](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#保存検算の実clock端点2026-10-11)。

外部費用整理（2026-10-11）：必須10費用と7原receiptの対応台帳を作成し、独立62項目の照合は差異0。実clock端点・全金融scopeは未結合で全10費用は未閉鎖。proof/metadataのCASと金融raw全体のCASを分け、未知費用を0や完了へ置換していない。 [費用の対応と欠測](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#外部10費用と原receiptの対応整理2026-10-11)。 原snapshotを変更せず実receiptを別の派生snapshotへ結合する補助処理は、作者18件・独立9境界の限定検証がPASS。コピー時計と終了済み親への後発費用吸収を拒み、欠測は未閉鎖で保持する。実10費用の投入・閉鎖は未実施。 [派生結合の検証](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#外部費用receiptの派生結合2026-10-11)。 全子lifecycleを測るobserverは作者4/独立4、行政pendingを保持する結合v2は作者7/独立9の限定検証がPASS。全10費用・総費用は未閉鎖。

旧source81の修正版fresh正式pilotは12:34:56 UTCに終了（外側7,930.370秒、約2時間12分）。214件目のHeston/N1024/coarse stage gateで引数bindingの不一致を検出し、status=unclosed_source_or_solver_defect・qualification unknownのpartialを保存した。行政資源停止はなく、source81/入力/priorは不変。原失敗・費用・元3,138 jobs/121 cases/51義務を保持し、原因修復・再検証・原rawのsaved数値検算・freeze/mainは未完了。 [終了証跡](research/RB-F04/dynamic_hedging/implementation/pilot-execution-evidence/task-5-formal-pilot-root-terminal-readonly-summary-v1.json).

**全体：本編P0–P8は306/306節受入済み、研究v1は8テーマ完了・main統合済み。現在は動的モデル横断ヘッジのTask5（接続source/予備測定完了、精度未達の原因測定を完了、prefreeze revisionの限定設計・private source承認済み、初回prior承認・metadata lock完了、初回pilotのsourcefaultを修復・正式pilotの214件目の引数binding不一致を修復、新保存source82の限定承認済み、新prior/metadata/保存計画/実guard検算済み・別root正式pilotは213完了＋214番sourcefaultでpartial終了、元sourceのsaved検算は16GiB行政停止、validation参照修復220tests PASS、派生保存の重複145.54GBを原byte共有で削減）。その後に多曲線risk/P&L→増分XVA＋IM/資本を進める。** 8/11はテーマ件数であり、残工数の割合ではない。

追加進捗（2026-10-10）：現行v56の元全49日付call cache127,400枠（親込みH55.631秒/L7.667秒）と独立参照693/196枠（H5.468秒/L35.561秒）を生成・保存独立照合済み。教師の原始全経路/元統計を保持する圧縮・派生標本再構成を限定実装し、現在source81/dynamic0。全status付き原N65536/65閾値/16blockの合成保存復元を独立確認（外側10.928秒/peak3.467GB）。genuine原N1024四class計2,128節点の生成・保存を実測（最外側1,401.807秒）、Hcoarse検査完了・他3classは検査工程の実RSS capを保持。全N検算を維持するboundedレポート修復を限定承認し、元2,128節点の全N保存再検算を完了（774.091秒、最大kernel RSS1.490GB、実capなし）。元N4096・13query・2schemeの独立oracle部品も両modelで完了（104.216秒、全106,496 payoff枠ずつ有限）。真正最大N65536の元一節点も生成・保存し、旧4GiB検査停止を保持して全N保存検算を完了（39.414秒/peak3.722GB、生成なし）。conditional prior cap消費は限定修復・独立確認済み。旧方式の全stage実行時の既知部分外挿は606.9時間（約25日、未知費用別）となり、phase内の不変raw検算再利用v2を限定実装・独立確認し、真正原N1024/Hcoarse108節点で初回23.671秒・再利用0.222秒・別context全検算23.797秒を実測した（関連既存240tests/Ruff/format PASS）。現v3は計算に無関係なwall/work-directory引数差だけの重複検算を除き、全引数SHA・外側監査を保持。独立9境界/保存432節点とroot14tests/Ruff/format PASS。v6の全job-key件数を独立確認し、全stage時の初回40cold/840hit・別saved context40cold/768hit。旧rateの既知部分は初回139.050h・別context cold部分90.673hで、全ETAは未知。初回sourceの元3,138ジョブの資源prior・正確cap recipeを独立承認し、正式metadata lockを生成した。初回正式pilotは69件executed＋70番の日付gateでKeyError Nとなり停止（外側580.029秒、資源capなし）。native cacheのoriginal_Nを読む1行修正と実cache→日付gate→保存checkerの2回帰を追加し、関連246tests・2Python Ruff/format PASS。旧partial・原失敗・費用を保持。修正版sourceへのprior再結合・正式metadata lock・別root起動許可を完了し、fresh正式pilotを2026-10-10 10:22:45 UTCに再開した。完走・saved検算・freeze/main・研究受入は未完了。 詳細は[予算測定](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md)。

現在の実測：旧停止点の日付gateは原N1024でsaved executedとなった（数値saved検算は未完了）。修正版prior metadataは326paths/235 unique blobsを両保管庫へ保存PASS。非teacher出力の反復内包・無圧縮NPZと大きいJSONを診断し、closed NPZの原byte/receipt/pathを保つ共有を6,369 filesへ適用、旧別inodeの割当145,539,321,856 Bを削減。source81・元入力・金融費用記録は不変、実postcheck PASS。保存helperのrollback I/O失敗P2をD-only v2で修復し、12合成tests/Ruff・独立3境界PASS。新v2を2,854 filesへ実適用し、全9原journalの最新6767paths・元receipt/metadata・source81をpostcheck PASS。小合成DAG試作も原logical値/digest・mutation隔離を確認したが、production形式は未採用。両復元では別実体へ戻るため、全phase容量・金融精度の保証へは読み替えない。[保存量と対策](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#派生結果の保存量と原byte共有2026-10-10)。

| 層 | 状態 | 詳細 |
|---|---|---|
| Hull 11e 全37章 | 全306節accepted・未評価0 | [生成台帳](docs/SECTION_LEDGER.md)。原典入力不足・表示差は各節の宣言範囲と制限に保持 |
| P0–P7の計算・教材・受入 | 統合構成で完了 | 開発`9dd53804`と受入`cef7cea1`を合流。P4最新レビュー修正、private BGM/businessモデル、P8、研究v1を保持 |
| P8監査の是正 | 完了 | [P8状態](docs/P8_STATUS.md)。P8時点の33節D1・両保管庫復元・影響画面の記録を保持し、統合時に全306節native artifactsを検査 |
| 統合検証 | 全体suite・数値・台帳PASS | 全体run 6,640 passed・索引2件FAIL・6 skipped、索引修正764件と導線/render検査16件がPASS。重複を除く6,650 passed・6 skipped（hullkit + report + deep_hedge_price）。変更Python300ファイルruff/format PASS。影響4便の数値検査、Ch1の37値/40状態、最終45節のfresh画面検査PASS |
| 配布生成 | 通常`make hull-report`で全補足教材を再生成 | Ch1・Ch2–25・Ch29–37の補足教材を生成し、入口から全34章への到達を確認。Ch1の古いBookキャッシュは同一入力の受入済み出力から復元 |
| main反映 | 独立レビュー修正・main反映・root同期完了 | 実測結果・判断・反映結果は[最終統合記録](docs/FINAL_INTEGRATION_2026-10-08.md)。rootの未公開履歴・別プロジェクト変更・受入worktreeを保持 |
| Beyond Hull（vol13–28） | 完了 | A1–A4、A5–A8 G8 release、vol26/27/28 |
| 研究track #1 | RB-F07 v1完了 | [研究資料](research/RB-F07/README.md)。private単一曲線・解析Jacobian・随伴リスク、独立レビュー済み。v2/v3は別承認 |
| 研究track #2 | RB-F05 digital v1・離散バリアv1完了 | [離散研究](research/RB-F05/discrete/README.md)／[独立レビュー](research/RB-F05/discrete/REVIEW.md)。主6fits、fresh独立PDE200点・実MC116比較、32計時/会計と100loadの再検査、artifact-only3図実行/目視を完了。関連3suiteは7104 PASS/6 skip（366.24秒）。DMLは全seedでprice-only改善、強Hermiteには精度で劣るため教材保持・標準高速器不採用。main統合済み。09b8c1af統合後のrelease gateと主成果/計時・会計の再検査PASS |
| 統合研究 | quote DML v1完了・main統合済み | [結果](research/RB-F07/quote_dml/README.md)／[独立レビュー](research/RB-F07/quote_dml/REVIEW.md)。30NN＋4ridge、fresh独立再計算、310計時、288費用対照、最終23,498,066 bytesの両保管庫復元、artifact-only3図実行/目視・最終レビューを完了。`a25345e1`をmainへfast-forward統合後、関連3suiteを全再実行し6919 PASS/6 skip（334.02秒）、`verify_release.py --require-tracked` PASS。教材保持・標準器昇格不採用 |
| 研究track #3 | RB-F04 v1完了・main統合済み | [研究状態](research/RB-F04/README.md)。Fourier/支持域・固定月次の共通乱数経路・独立PDE/積分・paired集計を実装。初期8192 pathsではAsian差−0.00487、SE0.02163、失敗0。包括収束pilot・独立レビューを完了し、129×161点の面と精度予算を主実験前に固定。3seed主比較196608 paths・fresh再計算・193MBの両復元・3図を完了。Asian差0.003673/paired SE0.004387で未識別。独立レビューapproved・関連3suite7316 PASS/6 skip・ruff/format PASS。c4430dfaをmainへfast-forward統合/push。branch/mainのtracked releaseとmainの保管庫復元・原始配列checkerもPASS |
| 研究track #4 | RB-F08 GBM v1完了・main統合済み | [研究結果](research/RB-F08/README.md)／[独立レビュー](research/RB-F08/REVIEW.md)。全9levelの固定pilot・全条件/181729seedのfreeze、主3072run/18RQMCcell・105groups fresh・22MB両復元semantic・artifact-only4図を完了。3εでEuler比速度改善を支持、exact/CVが速いため標準高速器不採用。Student95%実測coverage89.1–95.7%。独立28,990比較PASS、関連3suite7616 PASS/6 skip・16Python ruff/format PASS。255f4a61をmainへfast-forward統合/pushし、mainのtracked release・保管庫復元/原始配列checkerもPASS。Heston月次Asianは未実装の専用revision |
| 研究track #5 | RB-F06 v1完了・main統合済み | [結果](research/RB-F06/README.md)／[レビュー](research/RB-F06/REVIEW.md)。条件/金融source固定後に102dataset/4398calls、全saved/fresh・両保管庫復元・3図を完了。独立最終レビューapproved・重要0。元全3suite7742 PASS/2 FAIL/6 skipのfixture2件を修正し関係56件/root索引込み777件PASS、重複なし7744 PASS/6 skip。12Python ruff/format PASS。3e919eedをmainへfast-forward統合/push。branch/main tracked release・mainの23MB復元/102dataset数値checker PASS。exact SABR・大域識別・保証被覆・joint価格包絡は未認定 |
| 研究track #6 | RB-F05短期/0DTE v1完了・main統合済み | [結果](research/RB-F05/short_maturity/RESULTS.md)／[最終受入](research/RB-F05/short_maturity/validation.json)。正式84×3 pilot・source10/N1048576固定後、640教師/6fits/336点・追加12条件180推定枠・全費用・両復元・実3図を完了。独立最終208checks PASS・Critical/Important0、関連3suite7998PASS/6skip、19Pythonruff/format・tracked release PASS。Delta-DML全3seed誤差改善、NN raw/safe全fit固定精度未達・不採用、Hermite336/336PASS。da1d1f3eをmainへfast-forward統合、mainで3配列の保管庫復元・pilot/640教師/6fits/336点/fresh180slotの数値検査・tracked release PASS。別project48変更を保持 |
| 次の研究 | 動的モデル横断ヘッジ：Tasks1–4＋Task5 helper/接続source承認済み | [現在source/測定](research/RB-F04/dynamic_hedging/implementation/TASK5_CONNECTORS.md)。study/replay/runner/checker独立レビュー未解決0。1352scoped検査は旧runner時点、最終runner27tests・独立saved replay PASS（未加算、全suite未実施）。初期37quotes/selected18・latest tiny12fits/44cells・actual教師N1024を保存。latest tiny/教師rawは各C/F復元・saved算術PASS。元36教師slotsでSE同時条件6、underresolved5/fitunknown1、全qualification unknown。[追加診断と候補revision](research/RB-F04/dynamic_hedging/PREFREEZE_REVISION.md)：state15.Hの元quote条件κ≈.808>.25、2日付108groupsでfull-ready0、固定Cartesian domain候補を確認。旧v1条件は保持し、[独立レビュー](research/RB-F04/dynamic_hedging/prefreeze-review/README.md)で別readiness/domainの限定設計を承認。[固定domain/別execution/保存再計算/入口の限定source承認](research/RB-F04/dynamic_hedging/implementation/PREFREEZE_SOURCE.md)を完了。51/101/50/39 scoped tests・1125索引/docstring、8Pythonruff/format PASS。金融precisionは未承認。追加45証跡は原byteを保持、raw両復元はbyte確認のみ。[12本の学習・検証source確認](research/RB-F04/dynamic_hedging/implementation/NN_CLOSURE_SOURCE.md)も限定承認。38tests・独立6群・索引/docstring1,129件、元件数の実12fit・分割保存/再検算PASS（合成source検査、金融precision unknown）。[主実験結果の分割保存接続](research/RB-F04/dynamic_hedging/implementation/MAIN_SINK_SOURCE.md)も限定source承認、41tests・独立writer例外probe PASS。[全phase source照合](research/RB-F04/dynamic_hedging/implementation/PHASE_SOURCE_IDENTITY.md)を限定承認、48tests・独立14件・実在80files/dynamic import0を確認。[依存cap入口](research/RB-F04/dynamic_hedging/implementation/DEPENDENCY_CAP_SOURCE.md)を限定承認（51runner tests・独立6件）。[予算測定](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md)で元18入力の実2,304再較正、Asian/16block6,912query・13再較正936query、両CAS復元/算術を確認。main expanded約70–141 GBは部品外挿。progressive教師選択・A原N/費用写像と正式全phaseは未完。[4fit空gate修復](research/RB-F04/dynamic_hedging/implementation/EMPTY_FIT_VALIDATION_SOURCE.md)を限定独立承認（65tests/19mutation、unknown保持）。[正式plan preflight](research/RB-F04/dynamic_hedging/implementation/FORMAL_PLAN_PREFLIGHT_REVIEW.md)は修復後の再確認が必要。[fresh4 source](research/RB-F04/dynamic_hedging/implementation/FRESH_SOURCE.md)を独立承認（82専用tests・改変8拒否・実saved-only検査、金融資格unknown）。[現行field/入力再照合](research/RB-F04/dynamic_hedging/implementation/CURRENT_FIELD_INPUTS.md)で旧cutoff設定の不一致を検出・修正adapterの82,497点再現、元18/24/4入力と失敗/費用保持・17MB両復元/算術PASS。[段階教師計画](research/RB-F04/dynamic_hedging/implementation/PROGRESSIVE_TEACHER_PLAN.md)は旧2,748jobsを独立metadata承認・51MB両byte復元。3,138jobsの最終mixed draftは元121/51とsignature/依存順序を確認。選択後7項目の原N/producer投影・selector自身capの修復は固定v54で131tests/Ruff PASS、独立full metadata25改変拒否。Q入力削除/worker差替えの2境界は固定v55で修復、190専用tests・独立37件/105反例拒否による限定source承認を完了。v56は動的import3件の静的化だけで191専用tests/Ruff PASS、実80files/dynamic0を確認（37独立tests/105反例拒否で限定承認）。現在はprior budget/正式lockを完了し、正式pilot実行中。旧literal保存の全最大sample下限1.44TiBを保持。現nativeの論理部分下限353.606GBは圧縮物理容量と区別し、全体storage予算は未決。[主実行器source](research/RB-F04/dynamic_hedging/implementation/MAIN_EXECUTOR_SOURCE.md)は旧199MB証跡を両byte復元。empty_claim108接続のlocal Q scalar修復後、root元N4096×両model×正常/failed4件saved/cash/resume PASS（v55依存でも再確認）。774-job draftの未対応dispatch0。Q入力結合は限定独立承認、金融精度は未承認。原N65536/all65thresholdのlabel保存復元部品はRSS2.938GB・wall5.712秒、全teacherのRSS/費用は未測定。固定v54/metadata証跡131MBを両byte復元（金融semantic未実施）。正式pilot/freeze/主実験/研究受入・main未完了（開発branchのみ） |
| 実装前の準備 | 完了 | 下調べ292/292節・65/65出典・設計/再確認9本。準備時点の件数で製品受入と区別 |

`done`・`accepted`・PASSは宣言した計算・再現性・integrationの範囲を示し、市場性能の承認ではない。
§33.2のstrike/date/MC規約、§36.4の会計/ESO条件不足による原典未再現値は保持する。
fast-v1の補足HTMLを受入対象とし、全Book本文・別幅・全節画像・両保管庫復元を統合時に再実施したとは主張しない。

追加照合（2026-10-09、F04）：本編artifact gateは基点main e803e00bでも既存の依存指紋69件がFAIL。研究worktreeの追加89件はGit管理外Book HTMLの欠如。本編source/証跡/台帳は不変で、F04の完了を全306節の新しい全面再受入PASSとは扱わない。[比較記録](research/RB-F04/validation.json)。

## 完了までの計画（2026-09-27 策定）

**更新ルール：** 節の受入、段階の着手・完了、判断事項の決定、計画の変更があったら、作業したエージェント
（Claude・Codex・Sol ほか誰でも）が**同じコミットで**この節と上の「現在地」を更新する。
件数は `docs/SECTION_LEDGER.md` の生成値に合わせ、手で数えない。規約は `AGENTS.md`／`CLAUDE.md` の「ROADMAP の更新」。

ユーザー指定（2026-10-03）：各ターンの最終応答の末尾に、P0–P8の全体ロードマップと現在の作業を表示する。

最終統合（2026-10-08）：集約開発`9dd53804`と正式受入`cef7cea1`を合流し、P4 `00d8a651`・P8 `ce801e48`・RB-F07/F05 v1と補完2モデルを保持。全306節native artifactsと統合suiteを確認。過去の受入記録を保持し、変更した入力・表示に関わる証跡だけ実測から更新した。

研究計画（2026-10-09）：[較正込みquote DMLの設計](docs/superpowers/specs/2026-10-09-calibrated-quote-dml-design.md)と[実施計画](docs/superpowers/plans/2026-10-09-calibrated-quote-dml.md)を作成後、本人の「研究ロードマップを完遂せよ」に従い実装へ移行。quote DMLを先に実施し、従来の離散バリア→F04→F08→F06と統合研究の後続候補も保持する。本編の受入件数は変えない。全研究の完了は下の研究ロードマップと成果・独立レビュー・採否の証拠で判定する。

**完了の定義：** (1) 節別台帳306項目がacceptedまたはout_of_scope、(2) P8の監査是正・判断が完了、(3) 統合構成の検証・配布生成・独立レビュー・main反映を確認。本編(1)(2)と統合検証・独立レビュー修正・main反映を完了し、反映結果を[最終統合記録](docs/FINAL_INTEGRATION_2026-10-08.md)で確認する。

### 段階

「定性」は計算対象がない節の数（`docs/SECTION_AUDIT_2026-09-14.md` §1.2 の分類）。
「未評価」は再監査していないという意味で、実装がないという判定ではない
（監査時点で計算対象 243 節のうち code 107・nb 54 節には何らかの計算がある）。

| 段階 | 範囲 | 台帳項目 | 統合構成の受入 | うち定性 | 状態・制限 |
|---|---|---:|---:|---:|---|
| P0 | §26.9–§27.4（M1–M13） | 13 | 13 | 0 | 完了 |
| P1 | §27.5–§27.8（M14–M17） | 4 | 4 | 0 | 完了 |
| P2 | §26.1–§26.8（M18–M25） | 8 | 8 | 0 | 完了 |
| P3 | 金利（Ch28–34） | 37 | 37 | 3 | 完了。§33.2 caller条件のBGM検証と、原典flexicap等の未再現を区別 |
| P4 | オプション（Ch10–21） | 112 | 112 | 19 | 完了。最新P4レビュー修正を保持し、影響数値証跡を更新 |
| P5 | リスク・信用（Ch22–25） | 36 | 36 | 4 | 完了。原系列不足・印刷差・合成入力・静的モデルの範囲を保持 |
| P6 | 基礎（Ch1–9） | 80 | 80 | 31 | 完了。Ch1 D3、Ch2–9 fast-v1。分類と原典差は[P6状態](docs/P6_STATUS.md) |
| P7 | Ch35–37 | 16 | 16 | 6 | 完了。§36.4 caller会計条件と原著未再現値、§35.4/§36.5の原典差を保持 |
| P8 | 監査の残り | — | — | — | 完了。[P8状態](docs/P8_STATUS.md) |
| **計** | | **306** | **306（100%）** | **63** | **未評価0。本編・統合・main反映完了** |

### 先に決めること

| # | 事項 | 現状と影響 | 状態 |
|---|---|---|---|
| D1 | 再検査の証跡の増え方 | 1 マイルストーンの約 13MB の大半は、受入済みの全節を撮り直した再検査画像（節自身の証跡は §27.3 で 916KB、§27.4 で 472KB）。再検査量は受入済みの節数に比例して増えた（M7 7.7MB → M13 13.0MB）。この方式のまま 306 節まで進めると、証跡は合計**約 45GB**になる（実測の傾向からの外挿）。決定：依存の変わった節を再描画し、不変の実体を保持した参照とする（[D1方針](docs/EVIDENCE_POLICY.md)） | **M15 で本運用**（下の「節単位の品質確認」） |
| D2 | 節ごとの notebook 検査の規約 | 次の節が同じ巻に入ると、前の節の検査が HEAD で FAIL していた（[レビュー F1](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。M14 で、現行 HEAD 用の `verify_accepted_vol06_notebook.py` が各節を受入 commit と照合する方式に変更 | M14 で対応済み |
| D3 | ペースと受入の軽量化 | 従来の概算は5〜10か月。現行台帳では説明とrenderedが必須で、画面検査を省略できない。[準備案](docs/prep/design/D3_LIGHT_ACCEPTANCE.md)は定性節のN/Aに理由を付け、buildと画面検査を章内で共有する。旧監査の定性63節は今回の混在分類と同一ではない | **2026-10-03本人承認済み（PR #11反映案）。2026-10-04、章末まとめ受入で運用する指示** |

### D1-preflight（M15 の前提）

[証跡方針](docs/EVIDENCE_POLICY.md) の順に、依存指紋と画像参照・保存復元器、
既存検証器の互換対応、1節での全再描画との比較、変更伝播と欠損・破損の負のテストを行う。
2コピーからの復元と既存 gate が通るまで、過去の証跡や台帳の参照を移さない。
数値・意味・release 検査と受入件数は変えず、D3 の軽量化は別判断とする。
[実装計画](docs/prep/design/D1_PREFLIGHT_PLAN.md)に依存指紋、旧形式互換、全再描画との比較、負の検査、復元の順序を具体化した。計画作成はpreflightのPASSではない。

| 段階 | 内容 | 状態 |
|---|---|---|
| 1 | 不変 blob の保存・復元器（`scripts/evidence_store.py`）と保管庫の実接続 | **完了（2026-09-28）**。C: `%USERPROFILE%\ProjectArtifacts\projects`（primary）と F: `F:\ProjectArtifacts\projects-backup`（mirror）を作成。§27.3 の画像2枚を両方に保存し、それぞれ別に復元してバイト一致。path traversal・欠損・1 byte 破損・切詰め・既存ファイル衝突・symlink 逸脱の拒否をテスト（47件） |
| 2 | 依存指紋と v2 record、台帳検査の互換対応 | **完了（2026-09-28）**。`scripts/evidence_fingerprint.py`（節スライス・Book の section・portal の図カード・ページ資産・hullkit の import 閉包・データ・検証器・環境）と `scripts/evidence_dependencies.json`（§27.3 を宣言）。§27.3 の notebook スライスの指紋は M12・M13・M14 の3 commit で同一（ファイル全体のハッシュは毎回変化）。`scripts/evidence_record.py` の schema 2 記録（redrawn / reused、再利用は redrawn の基準へ直接参照し連鎖を拒否）を `verify_section_ledger.py` が検査。schema 1 の既存記録は従来どおり（実台帳は通常・`--check-artifacts` とも PASS） |
| 3 | §27.3 で全再描画と基準再利用を比較 | **完了（2026-09-28）**。`scripts/d1_preflight_compare.py` が既存の検証器を書き換えずに（宣言した見出し番号2か所の置換のみ、`scripts/run_browser_verifier.cjs`）overlay の root で実行し、既存の証跡には書き込まない。A（全再描画）: 16 状態の数値・配置検査と pytest 14 件が PASS、画像 16 枚・413,577 B を C:/F: に保存し各コピーから復元一致。B（基準再利用）: 同じ 16 状態・同じ検査が PASS、新規保存 0 B、A の画像へ直接参照し両コピーから復元・閲覧できた。新しい撮影は 16/16 が A・M14 再検査・受入時の画像とバイト一致。実行時の Chromium 145.0.7632.6・MathJax 3.2.2・実フォント（Liberation Sans と Droid Sans Fallback。fc-match の Noto Sans とは異なる）も記録し、再利用の条件にした。記録は `docs/validation/d1-preflight/section-27-3/` |
| 4 | 変更伝播の負の対照 | **完了（2026-09-28）**。`scripts/d1_preflight_negative.py` が実際の §27.3 の入力を overlay 上でだけ書き換えて判定（プロジェクトには書き込まない）。17 件すべて期待どおり：§27.3 の前に節を足す（notebook の id・実行番号・図の UUID、Book の自動 id、portal のカード）→ 再利用可・検証器 PASS。本文1文字・portal の値・参照データ・共有 CSS・Book のテーマ JS・plotly.js・hullkit のソース・fc-match のフォント・正規化の版・未宣言の節・未構築のページ → 再描画。値と参照データの変更では既存の検証器も FAIL（例 `ivf_local values 0[0]: 32.82 != 32.32`）。実行時の Chromium・MathJax JS・実フォントの変化、C: の blob 欠損、F: の 1 byte 破損 → 再利用を拒否。途中で overlay が節ディレクトリ内の差し替えを無視するバグを負の対照が検出し、修正した |
| 5 | 小群の保管・既存 gate・統合記録 | **完了（2026-09-28）**。[実証記録](docs/validation/d1-preflight/README.md)に §27.3 の16画像・413,577 bytesの2コピー復元、再利用時の新規保存0、負の対照17件、全体 pytest 2,995 passed / 6 skipped、台帳の source / artifact 検査、release・独立数値検証の PASS を記録。Book は初回生成後の全ページ再ビルドで既存ハッシュに一致 |

保管庫は環境変数 `PROJECTS_ARTIFACT_STORE`・`PROJECTS_ARTIFACT_MIRROR` で渡す（WSL では `/mnt/c/Users/<user>/ProjectArtifacts/projects`・`/mnt/f/ProjectArtifacts/projects-backup`）。未設定・未接続・marker なしは明示的なエラーで、空のフォルダーを自動作成しない。

### 本編の外の研究・拡張（本編の完了条件に含めない）

[研究バックログ計画](docs/superpowers/plans/2026-09-27-research-backlog.md)（2026-09-27）は、
外部の[提案書](docs/RESEARCH_HANDOFF_2026-09-27.md)にある 94 件を次の4つに振り分けた：
本編に畳む（RB-F02→P1、RB-F03→P3、R11・§19.14・RB-H16→P4）、章の受入後のコラム、研究トラック（同時1本）、johnhull の外。
研究トラック #1 は RB-F07。研究の置き場は `research/<RB-ID>/`、計算は hullkit の非公開モジュールに決定した（2026-09-27 本人承認。公開 API 昇格は別承認）。
2026-10-09に[較正込み市場クオートGreeksのDML](docs/superpowers/specs/2026-10-09-calibrated-quote-dml-design.md)を推奨し、[実施計画](docs/superpowers/plans/2026-10-09-calibrated-quote-dml.md)を作成。続く完遂指示を受け、`research/RB-F07/quote_dml/` のprivate実験から着手した。既存F07/F05 v1と従来の後続研究を保持する。

### 研究ロードマップの実行（2026-10-10）

目標は「研究ロードマップを完遂せよ」。quote DMLだけを完了して全研究完了とはしない。
各研究は設計・独立参照・テスト・成果配列・artifact-only教材・独立レビュー・採否記録で完了を確認する。NNの勝利や速度向上は必須条件ではない。

| 順 | 研究 | 完了を示す主な証拠 | 現在の状態 |
|---|---|---|---|
| 既存 | RB-F07 v1 / RB-F05 digital v1 | 保存済み研究成果・再計算・レビュー・採否 | 完了。F05全体の完了とは区別 |
| 1 | F07＋F05 quote DML | 34 fits、310計時/288原価、fresh数値/改変検査、最終両復元・3図・独立最終レビュー | 完了・main統合済み。H1改善・H2優位不支持、rate-only残余改善/spot・混合悪化、全面速度優位なし。教材保持、標準器へ昇格しない。統合後6919 tests PASS/6 skip・release PASS |
| 2 | RB-F05離散バリア | 監視契約、独立離散参照、教師bias/SE、学習比較・総費用・3図・レビュー・採否 | v1完了・main統合済み。[結果](research/RB-F05/discrete/README.md)／[独立レビュー](research/RB-F05/discrete/REVIEW.md)。主6fits・fresh MC/PDE200点（最大price差1.54e-4/Delta3.12e-5）・32計時/費用/100load再検査・3図を完了。関連3suite7104 PASS/6 skip。DML全seed改善、Hermiteの精度/準備費用を理由に標準高速器は不採用。158,401,006 bytesのpilot両復元済み。0DTE/roughの完了とは区別 |
| 3 | RB-F04モデル比較 | Heston→Dupire、vanilla再価格/収束、月次12観測Asian・二時点差、paired SE・3図・レビュー | v1完了・main統合済み。[研究状態](research/RB-F04/README.md)。private面/行支持端・月次経路・独立PDE/積分・paired比集計を追加。初期8192 pathsを保存し、包括pilot/独立レビュー/条件固定は完了。主3seed/3図/採否・fresh/両復元は完了。独立最終レビューapproved・関連3suite7316 PASS/6 skip。c4430dfaをmain統合/push、branch/mainのtracked release・mainの原始配列checker/復元もPASS |
| 4 | RB-F08 MLMC / RQMC CI | GBM Euler粗細結合、bias/sampling、費用、独立scramble被覆率・4図・レビュー | GBM v1完了・main統合済み。[結果](research/RB-F08/README.md)／[レビュー](research/RB-F08/REVIEW.md)。主3072run/18×512cell・105freshgroups・22MB両復元・4図・独立28,990比較PASS。Euler比速度3/3条件支持、exact/CVが速いため標準高速器不採用。Student95%実測coverage89.1–95.7%。関連3suite7616 PASS/6 skip、16Python ruff/format PASS。255f4a61をmain統合/pushし、mainのrelease・保存数値checkerもPASS。Heston Asian次revisionの完了とは区別 |
| 5 | RB-F06識別可能性 | 固定β Hagan inverse-map、全fit・scaled J/profile・失敗/原価・3図・レビュー | v1完了・main統合済み。[結果](research/RB-F06/README.md)／[検証](research/RB-F06/validation.json)。102dataset/918 unrestricted＋3480profile。全4398独立IV/Black・918J・870slice・代表10SLSQP・32noise/12fresh・両23MB復元を完了。教材保持。弱方向と未探索gap/元分母を保持し、一般exact SABR・大域識別・保証被覆は承認しない。3e919eedをmain統合/push、branch/main release・main保存数値checker/保管庫復元PASS |
| 後続 | RB-F05短期/0DTE | 短期契約・calendar・教師分散/共通乱数・独立参照・比較・採否 | v1完了・main統合済み。[結果](research/RB-F05/short_maturity/RESULTS.md)／[最終review](research/RB-F05/short_maturity/REVIEW.json)。640教師・6fits/336点、追加12条件180推定枠・全費用・両復元・3図。最終独立208checks/重要0、3suite7998PASS/6skip、19Pythonruff/format・tracked releasePASS。DML改善は支持、NN標準採用不可、Hermite336/336PASS。Bates/PIDE/rough・実商品calendarは別範囲 |
| 後続 | 同一較正条件の動的モデル横断ヘッジ | 市場生成/評価/方策を分離、自己資金・CF・費用を持つ共通P&L実験・レビュー | [正式設計](research/RB-F04/dynamic_hedging/DESIGN.md)・[実施計画](docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md)・独立数学review完了。Tasks1–4/統計/protocol/接続sourceの独立レビュー承認。[最新source](research/RB-F04/dynamic_hedging/implementation/TASK5_CONNECTORS.md)。初期37quotes・selected18states・N32 tiny全44cells/12fits・actual教師N1024元36slotsを保存し、latest tiny/教師rawの両復元/saved算術PASS。N1024はSE同時条件6/36、underresolved5/fitunknown1。[prefreeze候補revision](research/RB-F04/dynamic_hedging/PREFREEZE_REVISION.md)は[独立設計レビュー](research/RB-F04/dynamic_hedging/prefreeze-review/README.md)で限定設計承認済み。旧閾値/unknown/全caseを保持し、日付固定domain・保存再計算・別execution-readiness・入口/CLIの[限定source承認](research/RB-F04/dynamic_hedging/implementation/PREFREEZE_SOURCE.md)を完了。旧strict v1は不変、I1/I2解消。[12本の学習・検証source](research/RB-F04/dynamic_hedging/implementation/NN_CLOSURE_SOURCE.md)を限定承認。[主実験結果の分割保存接続](research/RB-F04/dynamic_hedging/implementation/MAIN_SINK_SOURCE.md)を限定承認。[全phase source照合](research/RB-F04/dynamic_hedging/implementation/PHASE_SOURCE_IDENTITY.md)を限定承認。旧source81の修正版fresh正式pilotは214件目の引数binding不一致でpartial停止し、原失敗を保持。source82の正式pilotは213完了＋214番sourcefaultでpartial終了。元sourceの全保存数値検算は別guardで16GiB行政partial停止。validation参照を修復し関連220testsはPASS。保存検算monitorと終了後全byte結合helperの限定source確認を完了し、実検算・whole RAM/容量・金融資格は未確認。旧停止gateは原N1024でsaved executed（数値検査待ち）。派生NPZの原byte共有で別inode割当145.54GBを削減。[実測と制限](research/RB-F04/dynamic_hedging/implementation/PILOT_BUDGET_MEASUREMENTS.md#派生結果の保存量と原byte共有2026-10-10)。候補freeze・全396件の主実験・金融研究受入は未完了 |
| 後続 | 多曲線統合risk / P&L | date/fixing/曲線間依存・quote units・商品横断risk/P&L・独立比較 | [調査・候補工程](research/RB-F07/multicurve/README.md)保存・独立調査案レビュー承認。D/P3/P6・12quotes、全cross-gamma、roll/fixing/表現移行/市場の四項P&L bridge。正式設計・実装・pilot/mainは未実施 |
| 後続 | 増分XVA＋IM・資本 | 既存増分CVA再利用、担保/IM/資本規約・比較・レビュー・採否 | [調査・候補工程](research/RB-H09/incremental_xva/README.md)保存・独立調査案レビュー承認。book前後/hedge bundle、VM/MPOR/非SIMM IM・FCA/FBA/MVA/KVA、selected IRS資本subset。same-set IM便益と別set対照を分離。正式設計・実装・pilot/mainは未実施 |

F07 v2/v3、rough/inverse NN等は設計に記載された条件付き拡張として保持する。必要な具体的計画・判断を残し、未実装を完了と数えない。
execution/cross-impact、LLM、利用権未確認の実データは既存計画のjohnhull範囲外。章別コラムと外部案件はバックログRB-5/RB-6で扱い、研究完遂のために無条件で94件全てを実装するという意味にはしない。
**実装再開は、johnhull に必要な保管庫と作業分離が整った時点**とし、ワークスペース全工程の完了は待たない。
M15 は D1-preflight の完了後に実施し、2026-09-28 に受入。M16（§27.7）も同日に受入。M17（§27.8）は2026-09-29 に受入し、P1 を完了した（RB-F02 の推定経路と評価経路の分離を含む。上界の実装は拡張のまま）。M18（§26.1 Packages）で P2 に入り、M19（§26.2 永久アメリカン）も同日に受入。M20（§26.3 非標準アメリカン）は2026-09-30に受入。M21（§26.4 ギャップ）とM22（§26.5 フォワード・スタート）、M23（§26.6 Cliquet）、M24（§26.7 Compound）は2026-10-01に受入。M25（§26.8 Chooser）は2026-10-03に受入しP2を完了。M26（§28.1 市場リスクの価格）は同日受入・main統合済み。M27（§28.2 複数状態変数）も同日に受入しP3は2/37、独立最終レビューと修正後検証、main統合/push済み。M28（§28.3）は2026-10-04受入、P3 3/37。独立最終レビューI1修正済み、main統合/push済み。M29（§28.4）は受入、P3 4/37、独立レビューCritical0/Important0、Minor3記録。main統合・push済み。M30 §28.5はmain統合/push済み、P3 5/37。本人の2026-10-04指示で§28.6以降はロジック先行、章末まとめ受入。ロジック36/37をcodex/p3-logicへpush済み、§33.2は原典入力不足で保留。Ch28の§28.6–28.8をD3共通設定ツールで受入しP3 8/37、受入を保留しP4（Ch10–21）のロジックを先行する。RB-F07 v1・RB-F05 digital v1は2026-10-07に実装・独立検証・レビューを完了しmainへ反映。[準備文書](docs/prep/README.md)は292節・65出典・設計等9本を完成し、構造検査と独立レビューを終えた。出典は支持23件・部分確認42件で、性能の独立再現とは区別する。
金利編は [P3設計](docs/prep/design/P3_DESIGN.md)でHW/BKの本文範囲と独立参照の条件を整理した。R11の原典成績は利息・割引を除外する規約で再現でき、現行の資金繰り計算を誤りとみなして置換しない。

## 可視化 & 深掘り(A1–A4) — 完了 (2026-06-14)

全5巻(13–17)が build スクリプト生成・nbconvert 実行済み・book/portal 登録済み。
hullkit に 10 新モジュール(sde/heston/fourier/sabr/mc_advanced/fd_advanced/aad/xva/copula/plotly_viz)、
当時のポータル **38 図/7 テーマ**(`make hull-report`)、Jupyter Book 20 ページ(`make hull-book`)。全テスト緑。
追加可視化(深掘り外の既存 hullkit 関数): ガンマ曲面・ストップロス vs デルタ・二項木格子・GARCH(クラスタリング/期間構造)・Merton 構造模型・分散投資・イールドカーブ・債券コンベクシティ・スワップ par・バリア・アジアン。

Hull の射程の先(同じクオンツ系で Hull が浅い領域)を深掘りしつつ、既存 + 新規の全コンテンツを
インタラクティブ可視化する取り組み。すべて johnhull 内で完結。

- **可視化基盤**: `hullkit.plotly_viz`(既存の bsm/trees/hedging/risk/credit をラップする `plotly_*` ビルダー)。
- **HTML/ポータル**: `johnhull/report`(jinja2 + plotly, オフライン自己完結) → `make hull-report`。
  `johnhull/book`(全ボリュームを束ねる Jupyter Book) → `make hull-book`。

| # | Volume | テーマ(Hull の先) | Status |
|---|--------|------|--------|
| P1 | 既存全14ノートの可視化 | `plotly_viz` 6 図 + ポータル疎通(offline test 緑) | done |
| 13 | `volumes/13_stochastic_calculus` | A1 確率解析(伊藤・Girsanov・Feynman-Kac) | **done**(30セル・実行済・book登録) |
| 14 | `volumes/14_stoch_vol_fourier` | A2 確率ボラ & Fourier(Heston/SABR/COS) | **done**(35セル・実行済・book登録) |
| 15 | `volumes/15_advanced_numerics` | A3 高度な数値(分散減少/QMC/LSM/CN/AAD) | **done**(22セル・実行済・book登録) |
| 16 | `volumes/16_xva_credit` | A4 XVA/信用(EE/PFE/CVA/コピュラ) | **done**(22セル・実行済・book登録) |
| 17 | `volumes/17_capstone` | Heston×Fourier → Greeks → CVA 一気通貫 | **done**(18セル・実行済・book登録) |

## Hull の先 A5–A8 — G8 release 完了 (2026-07-18)

Design: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`

G0 decision: financial teachers and hard validation belong to torch-free `hullkit`;
the Phase 2 PyTorch engine and checkpoints belong to `deep_hedge_price`; teaching,
book, and portal integration belong to `johnhull`. Projects exchange only versioned
JSON+NPZ reference artifacts. Phase 1 and Phase 2 config/checkpoint namespaces are
separate. No production dependency was added for G0/G1 core implementation.

| Gate | # | Volume / contract | Status |
|---|---:|---|---|
| G0 | — | owner / dependency / artifact contract | done |
| G1 | 18 | `volumes/18_ml_surrogates` | done |
| G2 | 19 | `volumes/19_inverse_surfaces` | done |
| G3 | 20 | `volumes/20_surface_dynamics` | done |
| G4 | 21 | `volumes/21_spx_vix` | done |
| G4 | 22 | `volumes/22_zero_dte` | done |
| G5 | 23 | `volumes/23_rfr_post_libor` | done |
| G6 | 24 | `volumes/24_crypto_market_structure` | done |
| G7 | 25 | `volumes/25_climate_energy` | done |
| G8 | — | full integration and tracked release | **done** |

表の `done` は巻別実装、integration gate、G8 tracked release の完了を表す。
各巻に validation report、fingerprinted JSON/NPZ、artifact-only notebook、book
symlinkがあり、各巻の `integration_and_reproducibility` gate は PASS。これは
**model performance の承認ではない**。`release_manifest.json` の現行契約は portal
**204 図/12 テーマ**。監査第4便82図＋M2–M25共有4図×24節＋M26–M30共有4図×5節＋Ch28章末共有6図（2026-10-05）。
Jupyter Book は `book/_toc.yml` の root + 30 entries = 31 ページで、ページ数自体は
manifest の契約値ではなく `book_name` の掲載のみが検証される。G8 で fresh artifact/notebook/
report/book/test/lint を再検証し、最終結果と model risk を `johnhull/VALIDATION.md`
に固定した。strict tracked gate と専用 branch への remote push も完了し、その branch は
`main` へ merge 済み（release 履歴は `VALIDATION.md` の Release decision 表）。
research track は既定無効・core gate 非依存のままとする。

## Inflation-linked rates and JGBi — Phase 1–7 (2026-07-19)

Design plan: `docs/superpowers/plans/2026-07-19-johnhull-inflation-jgbi.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 26 | `volumes/26_inflation_jgbi` | inflation-linked rates and JGBi (beyond Hull ch.25) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | Shared nominal/real curve helpers | done |
| 2 | Hull–White 1F curve fit, exact transition, bond option, Jamshidian swaption | done |
| 3 | CPI lag/interpolation/rebasing, deterministic seasonality, ZCIS, YoY | done |
| 4 | JGBi tenth-day reference index, rounding, cash flow, settlement, real yield | done |
| 5 | Jarrow–Yildirim nominal/real numeraires and payment-forward measures | done |
| 6 | JGBi redemption-only deflation floor, analytic/MC value and risk | done |
| 7 | `volumes/26_inflation_jgbi` reproducible artifact-only notebook | done |

Phase 7 の `done` は synthetic-offline の integration/reproducibility gate を表し、
市場較正、production valuation、model performance の承認ではない。Portal（`rates_swaps`
テーマの `inflation_curves`・`inflation_swaps`・`jgbi_floor`・`jgbi_bei` 4 図）、
Jupyter Book 登録、full tracked release への収録はいずれも完了した。

## Advanced VaR/ES risk desk — Phase 1–6 (2026-07-20)

Design plan: `docs/superpowers/plans/2026-07-20-johnhull-27-risk-desk.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 27 | `volumes/27_risk_desk` | advanced daily VaR/ES risk desk (beyond Hull ch.22) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | VaR backtesting: Kupiec POF, Christoffersen ind/CC, quantified Basel traffic light | done |
| 2 | Filtered historical simulation and EVT/GPD peaks-over-threshold tail VaR/ES | done |
| 3 | Euler risk decomposition: marginal/component/incremental VaR and simulation ES | done |
| 4 | P&L explain: factor exposures, delta-gamma-vega attribution, limits, desk report | done |
| 5 | `volumes/27_risk_desk` reference, `_volume27` acceptance, artifact-only notebook | done |
| 6 | Portal `risk_management` page, Jupyter Book page, full tracked release | done |

Phase 5 の `done` は synthetic-offline の integration/reproducibility gate（`_volume27`
の 14 恒等式チェックと byte 再現性）を表し、市場較正・model performance の承認ではない。
恒等式チェックは当初 11 個で、2026-07-20 の review-fix 運用で
`christoffersen_pvalue_matches_recomputation` と `cross_asset_factor_mapping` を追加した。
Phase 6 の portal 図（`var_traffic_light`・`fhs_vs_hs_coverage`・`gpd_tail_fit`・
`risk_allocation_bars`）、`risk_management` book page、Jupyter Book 登録、full tracked
release はすべて完了した（commit 691877f, 63f83ce）。

FRTB IMA（liquidity-horizon ES 集約、stressed ES scaling、NMRF、P&L attribution
eligibility test、IMA/SA 資本比較）は **vol 29 候補**として scope 外に記録する。

## vol 28 — 信用デスク（Hull Ch.24–25 の節単位の完全実装、2026-09-14）

Design: `docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`

| # | Volume | 内容 | Status |
|---|--------|------|--------|
| 28 | `volumes/28_credit_desk` | 24.4 債券/CDS ブートストラップ、24.7 ネッティング・担保・式 (24.5)、24.9 CreditMetrics、25.2 CDS レッグ/MTM/バイナリ、25.4 固定クーポン、25.5 フォワード/オプション、25.6+25.10 k-th-to-default、25.10 合成 CDO と コンパウンド/ベース相関、25.11 double-t・不均質再帰 | done |

vol 09 の設計書（2026-06-08）で「md/conceptual only」とした項目のうち、Hull 本文に数値例が
あるものをすべて hullkit（`credit_curve` / `cds` / `credit_portfolio` / `credit_metrics` / `xva` 追加分）
に実装し、印刷値に固定した。KMV EDF、ランダム回収率・ファクター負荷、implied copula、
動的モデルはコードを持たず、vol 28 notebook の「本巻で実装しない節」に Hull の説明と本巻の実装との
関係を置いた。`done` は integration・恒等式・再現性・教科書ピンの PASS を表し、
市場較正の承認ではない。

## 全節監査と是正 — 第 1〜5 便完了（2026-09-14〜25）

監査: `docs/SECTION_AUDIT_2026-09-14.md`（初回監査は §0–§10、修正の経緯は §11–§11.4、ID 別の現状は §12）。
レビュー: `docs/SECTION_AUDIT_2026-09-14_FEEDBACK.md`（初回レビューは `bd278948` の履歴）。実行記録: `VALIDATION.md`。

Hull GE 版の全 306 節と vol 13–28 を棚卸しし、実物で確認した欠陥 11 件（D1–D11）から順に直した。
各便とも、全ゲート PASS を確認してから `main` へ fast-forward し、push した。

| 便 | 終点 commit | 範囲 | hullkit+report tests | Status |
|---|---|---|---:|---|
| 1 | `90e903ea` | D1–D8・D10・D11（ゼロ曲線、期中スワップ評価、vol 22 のイベント分散、vol 21 の Greek 指標、vol 23 の Hagan グリッド、vol 26 のヘッジ分解、HJM/BGM の RMSE、ノート出力の照合、Ch.13 の GE 値、vol 28 の範囲外モデル） | 917 | done |
| 2 | `8485cc29` | vol 23–25・27・28 の acceptance を配列から再計算（tamper テスト）、Hull の印刷値ピン 71 件、文書の一括修正、R5・R9・R10 | 1055 | done |
| 3 | `83905890` | vol 18–22・26 の再計算化（tamper 契約を全 11 巻へ）、§4 の関数追加（現金配当・Black 近似、BL 密度、エキゾチックの put 側、分散スワップ、利回りの凸性調整）、BB-03・07・10・17、D9（core ノートの出力をコミットし静的 book に図を出す） | 1252 | done |
| 4 | `735197a6` | 進捗レビュー F1–F5（退化入力は FAIL 記録、core ノート出力の本文照合、vol 21 計測の来歴）、vol 18–28 の図の日本語フォント（字形欠落の警告 233 件）、文書の現状整理 | 1286 | done |
| 5 | `7d04851e` | vol 26 の保存値依存 3 項目を配列からの再計算へ（改竄テスト 8 件、reference 配列 7 本追加。監査文書 §11.4） | 2630（`johnhull/tests` を含む） | done |
| 6 | P8 2026-10-07 | R1–R4・R6・R11、保存値依存5項目、監査§7判断、影響教材・証跡・リリース（[P8状態](docs/P8_STATUS.md)） | 4466 passed・6 skipped | done |

`done` は各便の integration・恒等式・再現性・印刷値ピンの PASS を表し、節単位の完全性や
model performance の承認ではない（deep_hedge_price の 206 tests も各便で PASS）。

到達点（第 4 便、2026-09-15、`735197a6`）:

- acceptance は vol 18–28 の 11 巻・118 チェックを、コミット済み配列から再計算する。
  選んだ改変が該当チェックと宣言した依存チェックだけを落とすことを tamper テストで固定。
- Jupyter Book は vol 01–16 と ir_models のコミット済み出力を表示する（ipympl は PNG、
  vol 13–16 は plotly.js 埋め込み）。コミット済み出力の本文は新規実行と照合する。
- vol 21 の timing には、計測したときの generator digest と環境が残る。

残り（`docs/SECTION_AUDIT_2026-09-14.md` §12・§7）:

| 区分 | 内容 |
|---|---|
| 保存値依存 | P8で残り5項目（vol18・19・21・22）を原始データ／実行時情報から再計算し、改変・欠損を検出。vol26の3項目は第5便で対応済み |
| 節カバレッジ | mainの[節別台帳](docs/SECTION_LEDGER.md)は33受入・273未評価。別受入branch `cef7cea1` は306/306 accepted・未評価0。最終判定は各branchの受入ノートと統合記録を参照。mainへの統合は未実施 |
| P8監査対応 | R1–R4の計算・評価接続を修正、R6の説明訂正、R11のP4対応を照合。全検証PASS。fee-aware研究・R11教材は後続へ。[P8状態](docs/P8_STATUS.md) |
| 後続の節 | P3–P7の開発ロジックと、別受入branchの補完2モデル・全306節受入を合流し、最新レビュー修正/P8との整合を検証してmainへ反映する。§33.2／§36.4の原典未再現値は保持。深掘り研究は本編外バックログ |
| 判断事項（§7） | P8で11件の採用方針を記録。既定seed／API／オフライン契約を維持、大物教材は章受入、FRTB新巻／研究・ライセンスデータ／旧ノート再編は後続。[P8状態](docs/P8_STATUS.md) |
| ゲートの限界 | core は PNG と Plotly の中身を、frontier は stderr と図を比べない（字形欠落の警告とローカルパスだけをテストで検出） |

## 節単位の品質確認 — M1–M33（2026-09-15〜2026-10-05）

[台帳](docs/SECTION_LEDGER.md) ／ [更新手順](docs/SECTION_LEDGER_GUIDE.md) ／
[実装計画](docs/superpowers/plans/2026-09-15-section-ledger-m1.md)。

M1は、原典outline由来の299節・7付録を台帳に登録し、要求・証跡・集計の整合性を検査する段階。
「未評価」は内容の再監査をしていないという状態で、実装がないという判定ではない。
M1のPASSは台帳と保存証跡の整合性を表し、数値モデルの再検証や全節の完成判定ではない
（M1と§26.9の試行は`ab825e03`、[M1記録](docs/validation/section-ledger-m1/validation.json)）。

M2–M30は節単位で、原典の要求抽出 → 独立参照 → API → 教材・共有図 →
Book/portal両面2幅の実画面 → 受入ノート、の順で受け入れた。M31以降は本人指示に従い
private計算を先行し、D3の共通設定ツールで説明とrenderedを含む5軸を章末にまとめて受け入れる。数値・レビュー指摘と対応・
既受入節の再検査記録は各受入ノートが正本で、下表は1行要約に留める。

| 段階 | 節 | 状態 |
|---|---|---|
| M1 | 全306項目のinventory、§26.9 B01–B09の要求と証跡、検査CLI、生成台帳 | 検証完了 |
| M2 | §26.10（D01–D06） | 受入。[受入ノート](docs/SECTION_26_10_ACCEPTANCE_2026-09-15.md) |
| M3 | §26.11（L01–L06） | 受入。最終ブランチレビュー承認。[受入ノート](docs/SECTION_26_11_ACCEPTANCE_2026-09-16.md) |
| M4 | §26.12（S01–S06、CRR N1024で42価格） | 受入。Task1–3独立レビュー承認。[受入ノート](docs/SECTION_26_12_ACCEPTANCE_2026-09-16.md) |
| M5 | §26.13 Asian | 受入。独立レビューP2 6件・P3 1件に対応（F1–F7）、**再レビューは利用者判断で省略**。[受入ノート](docs/SECTION_26_13_ACCEPTANCE_2026-09-16.md)・[レビュー](docs/SECTION_26_13_FEEDBACK_2026-09-16.md) |
| M6 | §26.14 Exchange options（pp.627–628） | 受入。独立24価格、早期行使は同一格子で分離。[受入ノート](docs/SECTION_26_14_ACCEPTANCE_2026-09-17.md) |
| M7 | §26.15 Basket options（pp.628–629） | 受入。独立72価格、近似誤差の範囲を明示。[受入ノート](docs/SECTION_26_15_ACCEPTANCE_2026-09-19.md) |
| M8 | §26.16 Volatility and variance swaps（pp.629–632） | 受入。Example 26.4/26.5を再現、独立レビュー2本＋再レビュー。[受入ノート](docs/SECTION_26_16_ACCEPTANCE_2026-09-25.md)・[指摘と対応](docs/SECTION_26_16_FEEDBACK_2026-09-25.md) |
| M9 | §26.17 Static options replication（pp.632–634） | 受入。Table 26.1と3/18/100点を独立再計算。[受入ノート](docs/SECTION_26_17_ACCEPTANCE_2026-09-25.md) |
| M10 | §27.1 Alternatives to BSM（pp.641–646） | 受入。CEV・Merton・VG、Table 27.1とFigure 27.1。[受入ノート](docs/SECTION_27_1_ACCEPTANCE_2026-09-25.md) |
| M11 | §27.2 Stochastic volatility models（pp.646–649） | 受入。式27.1・Hull–White混合公式・Heston COS・SABRを独立参照で照合。[受入ノート](docs/SECTION_27_2_ACCEPTANCE_2026-09-26.md) |
| M12 | §27.3 The IVF Model（pp.649–650） | 受入。式27.4を独立解析式33点・後退PDE9価格・二時点paired MCで照合。[受入ノート](docs/SECTION_27_3_ACCEPTANCE_2026-09-27.md)・[レビュー](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)（P3 2件） |
| M13 | §27.4 Convertible Bonds（pp.650–653） | 受入。Example 27.1／Figure 27.2の10節点、コール後再転換、信用・回収・利払いを照合。[受入ノート](docs/SECTION_27_4_ACCEPTANCE_2026-09-27.md)・[レビュー](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)（Example 27.1 を独立に再計算して一致） |
| M14 | §27.5 Path-Dependent Derivatives（pp.653–656） | 受入。Figure 27.3のX/Y/Z、20段・60段の欧州型/米国型4価格、独立全経路列挙を照合。[受入ノート](docs/SECTION_27_5_ACCEPTANCE_2026-09-27.md) |
| M15 | §27.6 Barrier Options（pp.656–658） | 受入。素朴な二項・三項、内側・外側バリアと補間、バリア上のノード（Figures 27.4–27.5）を解析値・PDE・前向き格子で照合。D1 の本運用初回。[受入ノート](docs/SECTION_27_6_ACCEPTANCE_2026-09-28.md)・[レビュー](docs/SECTION_27_6_REVIEW_2026-09-28.md) |
| M16 | §27.7 Options on Two Correlated Assets（pp.658–661） | 受入。変数変換・Rubinstein の非矩形ツリー・確率の調整（Tables 27.2–27.3）を Stulz・Margrabe の式、1次元に帰着した米国型、前向き格子で照合。[受入ノート](docs/SECTION_27_7_ACCEPTANCE_2026-09-28.md)・[レビュー](docs/SECTION_27_7_REVIEW_2026-09-28.md) |
| M17 | §27.8 Monte Carlo Simulation and American Options（pp.660–665） | 受入。最小二乗法と行使境界のパラメータ化（Tables 27.4–27.7）を原典の8経路で再現し、推定と評価の分離による偏りを数値積分の厳密値と比較。P1 完了。[受入ノート](docs/SECTION_27_8_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_27_8_REVIEW_2026-09-28.md) |
| M18 | §26.1 Packages（pp.614–615） | 受入。レンジ先渡しのゼロコスト条件（§17.2 の K2=1.3414・p(1.30)=0.0273）、後払いとブレークフォワード、費用ゼロでも違うリスク（買う側）を独立参照（求積・二分法・モンテカルロ）で照合。P2 の初回。[受入ノート](docs/SECTION_26_1_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_26_1_REVIEW_2026-09-29.md) |
| M19 | §26.2 Perpetual American options（pp.615–616） | 受入。コール・プットの初回到達価値、行使境界、価値一致と滑らかな接続、$q=0$ のコール極限を独立参照と有限満期CRRで照合。P2 の2節目。[受入ノート](docs/SECTION_26_2_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_26_2_REVIEW_2026-09-29.md) |
| M20 | §26.3 Nonstandard American options（p.616） | 受入。行使可能日・ロックアウト・可変行使価格・7年ワラントの契約例を独立全経路計算とCRR後退帰納で照合。原典に印刷価格はなく、価格例は合成市場。P2 の3節目。[受入ノート](docs/SECTION_26_3_ACCEPTANCE_2026-09-30.md)・[レビュー](docs/SECTION_26_3_REVIEW_2026-09-30.md) |
| M21 | §26.4 Gap options（p.617） | 受入。符号付き給付・トリガーと決済額・バニラ＋現金バイナリ分解を独立求積で照合。Example26.1の3436・1896ドル、約45%減、保険会社支出と契約者手取りを分離。P2の4節目。[受入ノート](docs/SECTION_26_4_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_4_REVIEW_2026-10-01.md) |
| M22 | §26.5 Forward start options（p.618） | 受入。ATM欧州型の二時点契約・一次同次性・配当調整、期間固定/満期固定を独立求積36例とMC3例で照合。P2の5節目。[受入ノート](docs/SECTION_26_5_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_5_REVIEW_2026-10-01.md) |
| M23 | §26.6 Cliquet options（p.618） | 受入。単純ATM call/put列と各期支払を独立求積60例・多時点MC4例で照合、制約型はMC診断。P2の6節目。[受入ノート](docs/SECTION_26_6_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_6_REVIEW_2026-10-01.md) |
| M24 | §26.7 Compound options（pp.618–619） | 受入。欧州型4契約、臨界株価と内側put根なし領域、独立条件付き求積104例・MC4例。独立レビューI1修正・M1保留、全体検査PASS。P2の7節目。[受入ノート](docs/SECTION_26_7_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_7_REVIEW_2026-10-01.md) |
| M25 | §26.8 Chooser options（pp.619–620） | 受入。配当調整複製・選択/決済時点・端点、独立求積64例・MC4例・16表示状態。独立レビューI1修正・M1保留、全体検査PASS。P2完了。[受入ノート](docs/SECTION_26_8_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_26_8_REVIEW_2026-10-03.md) |
| M26 | §28.1 The Market Price of Risk（pp.671–674） | 受入。単因子signed係数・局所portfolio・印刷値・P→Q、独立12市場/6power/4MC・16表示状態・25D1。全suiteと独立最終レビューを完了。[受入ノート](docs/SECTION_28_1_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_28_1_REVIEW_2026-10-03.md) |
| M27 | §28.2 Several State Variables（pp.674–675） | 受入/main統合済み。[受入](docs/SECTION_28_2_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_28_2_REVIEW_2026-10-03.md) |
| M28 | §28.3 Martingales（pp.675–676） | 受入。条件付き定義/signed Itô/同一給付Q・G価格、9条件付きMC/旧235保持/16状態/27D1。[受入](docs/SECTION_28_3_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_3_REVIEW_2026-10-04.md) |
| M29 | §28.4 Alternative Choices for the Numeraire（pp.676–679） | 受入。HW Q状態/同一給付Q・T/支払・annuity、63独立fixture/旧246保持/16状態/28D1。[受入](docs/SECTION_28_4_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_4_REVIEW_2026-10-04.md) |
| M30 | §28.5 Extension to Several Factors（pp.679–680） | 受入/main統合push済み。MF01–06/11市場132状態/旧257/16状態/29D1。Important1を4回帰RED→GREENで修正、Minor2保留。[受入](docs/SECTION_28_5_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_5_REVIEW_2026-10-04.md) |
| M31 | §28.6 Black’s Model Revisited（pp.680–681） | Ch28まとめで正式受入・main統合済み。独立7市場42価格・zero-hit importance検証済み |
| 以降 | Ch29–37残45節の受入 | 全306節accepted。別受入branch `cef7cea1`の成果と最新開発修正/P8を合流し、main統合・検証済み。§33.2/§36.4の補完と原典未再現値の区別は保持。[最終統合記録](docs/FINAL_INTEGRATION_2026-10-08.md) |

統合前の記録（2026-10-08）：当時のmainの正式台帳はaccepted33/unreviewed273、別受入branch `cef7cea1` はaccepted306/unreviewed0。P0–P7の台帳受入と開発側P8監査是正は完了。§33.2/§36.4は別受入branchでprivateモデルを補完し、原典未再現値は保持。受入成果・最新レビュー修正/P8の合流とmain統合・配布は未完了。研究の次はRB-F05離散バリア。
各段階で、共有ソースを変えたときは既受入節の個別テストと両画面を再検査し、台帳の現行証跡へ接続している。

受入を通じて決まった進め方と、残している制限:

- §28.1のM1保留：MC検証図がゼロ始まりの価格棒のため、微小な推定差/95%区間を比較しにくい。数値は正しい。差分図/拡大パネルは将来対応。[レビュー](docs/SECTION_28_1_REVIEW_2026-10-03.md)。
- §26.8のM1保留：空batchと不正な有限市場条件の組でValueErrorにならず空配列を返す。価格の誤返却はない。[レビュー](docs/SECTION_26_8_REVIEW_2026-10-03.md)。

- 既存のhullkit実装や説明なしのコードセルは受入の根拠にしない。NumPy/SciPyだけの独立参照を先に作り、既存実装はその誤差を測ってから教材に載せる（M5・M8）。
- 早期行使プレミアムは閉形式ではなく、同じ格子で行使判定を外した価格と比べて測る。閉形式と比べると離散化誤差が混ざる（M6）。
- 再検査のスクリーンショット差分は、文字のアンチエイリアスやmodebarツールチップと図の中身の変化を分けて判定する。前者ならコミット済み画像を戻す（M6b）。
- 適用域の制限：§26.11の価格APIは$|r-q|<10^{-8}$に未対応（教材に適用域として明示）、§26.12のlookbackは$r=q$を欠測表示、putは原典外の独立拡張。
- M5は修正後の状態を第三者が確認していない受入である。
- 固定シードの1回の実行で偶然成り立つ統計的な主張は「この実行では」と書き、理論から導ける主張（新しい経路での評価は期待値で厳密値以下など）を別に検査する。同じ経路で評価した方策どうしはペア差で比べる（M17）。
- 不等号の向きは、単調性と境界の値から導いて検査する。§26.1 の独立レビューで、$c(K_2)=p(K_1)>p(F)=c(F)$（$c$ は行使価格の減少関数なので $K_2<F$ になる向き）が本文に残っていた。正しい式があり逆向きの式がないことを本文の検査にした（M18）。
- D1 driver は `--records-dir docs/validation/d1-recheck` を必ず付ける。既定の `docs/validation/d1-preflight` に書かれると記録の置き場所が変わるので、付け忘れたら移してやり直す（M18）。
- Book の html ハッシュは build の履歴に依存する。M17 のコミットを新しい worktree で作り直した Book は、M17 の記録が持つ `06_numerical.html`・`10_exotics.html` のハッシュと一致せず、`verify_section_ledger.py --check-artifacts` は M17 の時点でも新規 build では通らなかった。M18 は §27.1–§27.8 の `notebook_check` を現行の統合記録（`section-26-1/m18-check.json`）へ付け替えて通した（原因の特定は未了）。
- 節ごとの notebook 検査は受入時点の基点との比較として保持する。現行HEADでは `verify_accepted_vol06_notebook.py --check` が§27.1–§27.7の自節セルを各受入commitと比較し、共有図と巻全体を再実行する（§27.7 はM17で追加）。M17の§27.8は直前M16基点の節外保持検査を持つ。M18の§26.1は直前M17基点`811b1792`に対する vol10 の節外125セルの保持検査を持つ（vol10 は §4.8 の追加のみ）。後続節の追加時に現行HEAD用検査の対象を増やす（[レビュー F1 対応](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。

- §28.4 Minor3保留：portal案内の状態不一致、δ≈1e−12年で金利の桁落ち、a*h=1e16でsampler X分散消失。通常教材fixtureへの影響なし。[レビュー](docs/SECTION_28_4_REVIEW_2026-10-04.md)。

- §28.5 Minor2保留：独立条件付き求積の自動判定接続、missing-RN変異の追加。現在の数値は正しい。Importantの再署名MCガードは4回帰RED→lesson20GREENで修正。[レビュー](docs/SECTION_28_5_REVIEW_2026-10-04.md)。
