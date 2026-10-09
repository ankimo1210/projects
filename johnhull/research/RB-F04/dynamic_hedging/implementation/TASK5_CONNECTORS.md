# Task5 接続・saved checker・予備測定のチェックポイント

2026-10-10。**study/replay/runnerと金融checkerのソース実装・独立レビュー完了。開発branchのみ。Task5全体・正式pilot/freeze/main・研究受入は未完了。**

## 実装・検査・独立レビュー

| 部分 | 内容 | 対象検査 |
|---|---|---:|
| 条件付き教師 | optional uint8 status辞書。原N・失敗・標本値を保持 | 30 |
| call価格面 | local calendar PDE空間格子601→1201、独立Black反例で修正 | 20 |
| study | S/Q/月次記憶、観測値からのfit、IFT/band/Greek/NN、12fit/44cell | 59 |
| replay | 保存CE/control/cache、市場/CF、独立cash/gain、保存統計 | 82 |
| 初期quote checker | 元37quotes・8PDE attempts・7refinementの再算出 | 11 |
| selected call checker | 元18states・before/refined price/fitの保存算術 | 5 |
| runner | test開封前のsource/checkpoint/validation固定、immutable tiny/check | 27 |

[compact](task-5-compact-status-review.json)・[study](task-5-study-rereview.json)・[replay](task-5-replay-rereview.json)・[call/checker](task-5-initial-call-rereview.json)・[runner](task-5-runner-review.json)の独立レビューは各宣言範囲で未解決0。元レビュー・RED/GREEN・修正前source/probeを保持。[正確な原証跡対応](checkpoint-evidence-files.json)。

[変更範囲＋両索引/docstring](task-5-checkpoint-3-final-tests.txt)は1352 passed（36.71秒、whole subprocess39.22秒）・14Python ruff/format PASS。その後runnerのloader alias/dict保存順を修正し、最終source `f96d768f` / tests `4af2f331` に対して27 tests・ruff/format、独立18probesと26操作禁止saved replayがPASS。1352件は旧runner `c7347038` に結び、最新版へ読み替えない。重複件数を足さない。[現在source/レビュー/run照合](connectors-source-validation.json)。関連3suite・tracked releaseは最終phase gateで実行予定、今回は未実施。

## 主な修正

- study：exact-linear claimを不要なquote rootで失敗させない。G/U/seed/N/checkpoint同一性を検査。local共分散は現在時刻の係数を使い、midpoint proxyと区別。
- replay：宣言Nを元array軸と照合し、同global driver IDの異なるstep数を拒否。未取引callのunknown寄与はexact zero、非ゼロ保有/売却はunknownを保持。
- runner：test重みが閉じたcheckpointを置換できたRUN1、validation等の可変参照を変更できたRUN2、JSON辞書順でpayload digestが変わったRUN3を解消。全pretest入力をdetached snapshotへ固定。
- 初期checker：元PDE stageの消去を拒否。全7refinementを元price配列から再算出。

## 実測の進捗

| 測定 | 結果 | 範囲・残り |
|---|---|---|
| [初期37quotes](../pilot/initial-quotes/README.md) | CF差/quad error最大3.96e−10、local最大price差1.04e−4 | 全attempt保持。conditional Greeks/Asian/P&L/Qは未認定 |
| [selected18 call](../pilot/selected-calls/README.md) | local価格差1.45e−3→2.91e−4、Heston7.92e−6 | Heston識別不良1件を保持。全倍率/Greek精度は未測定 |
| [latest tiny](../pilot/tiny/README.md) | 原N32、12fit/12weights、56validation、44cells、実CLI6.52秒 | constant-vol、小格子/1update。全44cell unknown、正式OOSではない |
| [actual N1024 teacher](../pilot/teacher-n1024/README.md) | 元36slots/35実行、175calls、82,247,680pathsteps、whole45.12秒 | priceSE18・hS10・hQ9・同時6/36。underresolved5、fitunknown1、全qualification unknown |

初期/selected solver計測は起動/import/最終保存を含まない。N1024は全子processを含む。全費用scopeと未測定値を保持し、0へ置換しない。N65536×768のstatusメモリは式で12.9GB→50.3MB（最大配置自体は未実行）。

latest tiny/教師rawは各C/F CASから別々に復元してsaved算術PASS。旧c734 tinyはexact bytesを両保存し、旧source時点のchecker実行を歴史的証跡として保持。金融比較は許容差/SE、SHAは同定のみ。保存境界再計算は先行SDE/CF/PDE solve・training/scalerの真正性や金融精度の認定ではない。

## 次に満たすこと

1. 教師SE・underresolved tail・call識別不良を原36slotsと既存閾値を保持して検討。独立Asian/position/分母/格子/SDE/Q/P&L誤差を実測。
2. 正式pilot・独立reviewを完成しsource/候補/全条件を固定。現時点でformal freeze/主test開封をしない。
3. 実train/validation生成、12fit・全幅選択、主3seeds×3levels×44cells、原始分母/全費用/失敗を保存。
4. saved/fresh/両CAS、独立envelope、3artifact-only図、最終suite・レビュー・採否・main統合。

[実施計画](../../../../docs/superpowers/plans/2026-10-09-dynamic-cross-model-hedging.md)のTask5残り/Tasks6–7は維持。NN優越は完了条件ではない。
