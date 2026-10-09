# Dynamic hedging prefreeze revision proposal — independent design review

2026-10-10。reviewer: /root/task5_freeze_feasibility。対象commit checkpoint: 47372fd95b3d6af599c51c4996b1993eb75a445c。

## 結論

**Critical 0 / Important 0。bounded designとして実装へ進める。**

対象はroot作成 `PREFREEZE_REVISION.md`（SHA e2a8bade84acc9b22abc119c14730521c2d89deee538db5579aedeb4cb4ef38a）の独立設計レビュー。canonical監査・domain調査・元DESIGN/数学review/候補/roster/計画/既存sourceを実読した。正式pilot、金融precision、source完成、readiness freeze、test開封、主実験、最終受入を承認したものではない。

## A. 契約の分離と元研究scope

| 要件 | 根拠・判定 |
|---|---|
| 別schema/namespace/private入口 | proposal13–15,39。旧v1のqualified guardを変更・falsequalified projectionせず、評価を実行/拒否できることだけ別に認証。妥当 |
| 旧v1厳格性 | 現candidate.jsonと _dynamic_hedging_protocol.py は47372fd95b3dとbyte同一。元κ .25/priceSE .03/hSSE .002/hQSE .005、error/Q/refinement/N/seed/rosterの変更案なし |
| 原case/原N/unknown | proposal14,16,22。原37quotes/18×2 states、invalid/unqualified1pathで対応policy/baseline/family支持unknown。finite-onlyはdescriptive。元κ拒否を数値PASSにしない |
| full pilot attempt/cap閉鎖 | proposal17–18,40。source defect、required attempt未完、identity/乱数/integrity不一致をreadiness拒否。N1024診断だけで正式pilotを閉じない。事前cap/教師・予算revisionをレビューして閉鎖 |
| research testN32768 | proposal20。smallest-qualifiedが実際に定義される場合は元選択。それ以外は元候補最大32768をtest前固定し `precision_selection=unavailable`。精度達成を認める分岐ではない |
| 全training/selection | proposal21。12fits、train8192/validation2048、512updates/300s capを維持。failed baselineはNone＋理由、width0/no-hedge/hold/safe救済禁止 |
| all main deliverables | proposal9,19,41。44cells×3seeds×192/384/768＝396元evaluation slots、全12fit attempts、premium/Q/teacher/position/P&L refinement、原始データ/全費用、saved/fresh/CAS、3図/notebook/full suites/final review/main統合を保持 |

元DESIGN §1は全rosterの実行又は理由付き失敗・unknownの保存を研究成果として許容する。したがって、上記全mainと検証を保持した別schemaの手続きrevisionは目的と整合する。**元v1数値精度契約を達成したというラベル、失敗報告だけの研究完了は不適切**でありproposalはこれを禁じている。

state15.HのCvは非ゼロ、rootは収束し、元1cent/s_v=.04に対するκだけが拒否する。これはsolver failure/数学的IFT不存在と区別されている。raw金融unknownを、sourceの正しい拒否動作の認証へ混同していない。

## B. 固定Cartesian domainのbounded review

proposal28–33と参照domain報告59–84を照合。

- 原global axes/range/全f/blocks/status/NaN/原Nを保持して、別revisionのfixed box上へ従来not-a-knot tensor cubicを構築する案は整合する。
- 全16blocksに同じ固定linear operatorを適用する。query毎stencil変更、未知tail補完、mainでのdomain再選択を禁じる。
- raw primitive `ready`、finite box、C2であることは、price bounds/Greek precisionの認証ではない。proposal33は独立oracle/SE/grid/biasを別gateに残す。
- box外/必要node不適格は元分母を保持したunknown。全domain一致や遠方失敗解決は主張しない。
- これはbounded interpolation designの承認であり、新金融source・精度gateのレビューは別に必要。

## 実装レビューへ残す具体条件

1. **原call roots/boundsを保持。** 参照報告82–84どおり、全元call rootを列挙して一意性を確認してからAsian patchへのmembershipを検査する。patchへrootをclipしたり探索boundsを狭めて元多重rootを隠さない。root二つ/patch内一つの反例をTDDに入れる。
2. **exact linear branchとgap。** x<=0の厳密linear claimはquote fit不要。boxとlinear component間のunknown gapを滑らかに埋めない。C2/C1はbox内部の性質でありgap越し全domain保証ではない。
3. **geometry選択と数値精度。** pilot streams/選択規則/選択時のデータscopeを保存して事前固定し、main/freshで都合よくpatchを変えない。fixed-box選択だけでSE/price/Greeksをqualifiedにしない。独立oracle/SE/grid/biasが必要。
4. **新readiness validator。** 完全な原counts/attempt/expense/source/raw/checker/review/拒否truth tableを実証から再計算する。flag-only approved、未完checker/source、source bug、incomplete attemptを拒否する。
5. **N unavailable分岐。** 全ordered pilot N projectionと失敗を保持し、32768とunavailableを保存する。smallest-qualifiedと表現せず、元pilot義務の代用品にしない。
6. **完了基準。** このreview、source checkpoint、expected rejection、successful subsetだけでdone/main受入にしない。全main/fresh/CAS/費用/実図/独立final reviewを完遂する。

## 検証範囲と未承認

Read-onlyの契約・source・保存資料確認と旧v1 guard/candidateのcheckpoint比較。新RNG、学習、金融実験、source修正、Git操作、full suitesは行っていない。

正式source承認・formalpilot・financial qualification・execution readiness freeze・test開封・main・speedup/risk支持・final acceptance・研究完了は**未承認**。具体入力bindingsと判定は隣接 `task-5-prefreeze-revision-review.json`。

canonical文書/source/Git変更なし。
