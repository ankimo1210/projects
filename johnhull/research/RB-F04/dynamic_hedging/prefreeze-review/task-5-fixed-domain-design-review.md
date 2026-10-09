# B fixed-domain design independent review

2026-10-10。レビュー担当：task5_cache_domain。対象はrootのPREFREEZE_REVISION §Bと関連source・元Cartesian diagnostics。
canonical / source / Gitは変更していない。

## 判定と承認範囲

**Bのprivate実装へ進む設計を承認する。未解決のblocking設計指摘は0。**
以下のprivate interface・availability・call-root・replay/freeze契約を実装とTDDへ含めることが条件。
固定boxの具体値、selectorの実測採否、金融SE/Greeks/独立oracle、full formal pilot、sourcefreeze/readiness/mainは承認していない。
候補boxの支持を金融qualifiedと呼ばない。A schemaの全契約を独立受入したレビューではない。

対象文書SHA256：
`3728b09ab65b0960a13bc54309dee13f476c606c36c6ce9b6cbcc10281ea271b`

### 解消された重要な点：元call rootsを隠さない

§B 32行は、元common full-domainのroot・非一意・κ条件を検査した後にAsian patch支持を調べると明記した。
これは必要な修正。既存fit sourceを使う独立toyで次を再現した：

- C(state)=10+(state−.6)(state−1.2)(state−3)、Q10。
- 元domain [.25,4]：roots [.6,1.2,3]、unknown / nonunique。
- 誤ってpatch [.5,1]へfit boundsを狭めた場合：root .6だけ、status ok。

B sourceはpatchを `call["asian_state_bounds"]` へ上書きしない。
原common full bounds、raw fit roots/residual/status/κを保持し、唯一の原rootがpatch外ならAsian/risk側unknown。
study 274–277行の「原全Asian state axesとのcommon bounds」は保持できる。
新date-specific boxによる追加チェックは `evaluate_asian` 側に置けば最小の変更でこの契約を守れる。
linear branchは既にquote fitが不要な真のexact計算で、patch未支持から実行方策を救済するfallbackではない。

## 1. 最小private interface

既存関数へのkeyword-only optional config追加を推奨する：

`build_asian_cache(primitive_groups, *, model, axes, evaluation_domains=None)`

- `None` argument：現在の全Cartesian not-a-knot default。既存source / return semantics / testsを保持。
- 明示list/tuple：exact datesと同順・同数、各dateに一つのbox又は`None`。
- 各boxは半開node index範囲 `{"state":[a,b],"threshold":[c,d]}`。
  localでは `"spot":[e,f]` も必須。Hestonにspotを足さない。
- local date0のspot indicesは専用 `t0_sheet.spot_nodes` へ適用。
  t>0の全S axis indicesをt0へ流用しない。resolved sheet identityをcacheへ保存する。
- 明示config中の `None` entryは「そのdateに利用可能domainなし」でunknown。
  原全domainへ戻すfallbackとして解釈しない。
- 全axisのstart/stopが原axis内、start<stop、少なくとも4nodesを数学的に検証。
  step/skipping/disjoint indices、負indexやstop範囲外のPython silent slicingは許さない。
- 原f / block_means / primitive_groups / support_mask / full axes / original_N / shared_driver_idsは保持。
  新metadataにdomain schema・copied index ranges・resolved physical bounds・sheet・selector provenanceを追加する。
  原metadata `interpolation` がglobal支持を意味すると解釈されないよう、fixed-domain revision identityも保存する。
- callerのconfigをlater mutateしても暗黙にdomainが変わらないようsnapshotを取る。
- box選択はcallerのpilot処理。build/evaluate/replay内でfinite node探索・resize・fallback選択をしない。
- 元公開API/`__init__`/依存は変更しない。新helperはunderscore privateへ置けばよい。

これはインデックスの機械的configであり、数値precisionを表すbooleanや`qualified` flagは持たせない。

## 2. availability と元データ保存

declared boxのmean fと**全16 CV block curves（component2）**に同じindex sliceを使う。
原raw / conditioned componentsも保存するが、未使用componentの金融数値をCV価格へ混ぜない。

新明示domain modeでは以下を別理由でunknownとする：

1. no domain / query outside domain。
2. selected mean nodeにNaN/nonfinite/primitive unknown（既存buildでNaNへmasked）。
3. 必要な16 CV block nodeにNaN/nonfinite。
4. selected mean nodeがprice boundsを破る、又は補間後f/f_xが既存boundsを破る。

availabilityはMC精度qualifierとは別。readyのfinite-sample CV meanが負の場合も、原値とSEを保持しclipしない。
各blockはsigned CV estimatorなので、meanのprice boundsを各blockへ強制してN/16blocksを減らさない。
`f_x` teacher labelや別補間operatorからGreekを借りず、同じbox上のfからordinary derivativesを計算する。

独立probeで、現在のdense fixtureはmissing block evidenceでもmean価格をstatus ok、SE NaNとして返すことを確認した。
この歴史的defaultを広範に変える必要はない。
**新明示modeは必要CV blockが欠ければdomain unavailableを明示**し、finite meanだけでSE-readyを主張しない。
default/full-domain一致の検証は原全必要mean/blockがfiniteのcaseで行う。

meanと16block meanはsource identityに加え金融許容差で照合。
original_Nは全primitive/groupで既存の同一分母・16倍数・global driver-map義務を保ち、
node数×Nやfinite node数を分母にしない。原全group count / NaN count / status countも保存する。

## 3. local / exact branch / C1 scope

- local fはlogS / logell / xでinterpolate。
  `VS = D(f+f_z−x f_x)/12`、`Vell=DS f_logell/(12ell)` を保持。
  Hestonのhomogeneityを流用しない。
- t0専用near-S0 sheet / threshold / state / 16blocksへ同じdomain slice。
  片方だけ全S表を使う、N/blockをt0だけ減らす方法は禁止。
- exact linear x<=0、settled n12 branch、memory/date検証順は現在の数学的契約を保持。
  全cacheがNaN / state NaNでも既知linear/settled価格が出ることを独立probeで確認した。
- C2は固定boxの内部、C1/C2の境界検査は内側ordinary derivativeと片側FDについて行う。
  domain外はunknownなので、gap越しの全domain連続性・外挿・patch間連続性を主張しない。
- x0/m/24は仕様上のnodeをaxis生成で直接含める。teacher値や価格のround/clip修理に使わない。

## 4. source回帰テスト

source・付随replay/runnerへの最低必要なTDDセット：

1. **旧default保持**：既存20surface tests、全必要node finiteでexplicit full-domainのprice/Greeks/blocks/covarianceがdefaultと許容差で一致。
2. **固定slice参照**：nonuniform axes、analytic polynomial又は独立SciPy直接cubicを参照。
   同じsubaxesのf / fx / fs / local fzとprice chainを照合。
3. **遠方unknown**：原全arraysに遠方NaNを置き、defaultは拒否、explicit internal boxは評価。
   原NaN・full axes・countsを消していないことを確認。
4. **box内unknown**：mean又は一つの必要CV blockのNaNで明示unknown。
   shape / original_N / 元16blocksを保ち、finite-only sigmaを計算しない。
5. **bounds**：readyだが負mean node、補間overshoot / f_x bound failをraw保持してunknown。
   個別signed blocksはclip/boundsで削除しない。
6. **geometry**：各axis<4、invalid range/skip/外側indices、date数不一致を拒否。
   explicit None dateはunknownでfull-domainへ戻らない。
7. **exact date / vectorization**：dateごと異なるbox、同一batch内inside/outside queryが元row順・元Nで戻る。
8. **local t0**：full spotとt0 spotのindicesを混同しない。t0内/外、多次元block shape、fz Delta FD。
9. **exact branch**：absent/invalid-support numerical boxでも数学的に既知linear/settled branchは保持、未知stateを0へfitしない。
10. **C1**：interior knots / 内側境界のsame-price derivativeを3幅FD、unknown gapsに外側FDを要求しない。
11. **call root preservation**：上記multi-root fixture。
    patch-bound縮小で3rootsを1へ変える回帰を拒否し、unique original root outside patchはAsian unknown。
12. **saved replay / tamper**：同じdeclared domainsを保存→load→rebuild→金融再計算。
    domain indices / sheet / dates / axes / mean / blocks / N / shared IDsの改変でintegrity又は金融照合が失敗。
    原任意のdomain selectorをsaved replay内で再実行しない。
13. **無RNG**：saved checkerで生成・driver draw・trainingを禁止してもdomain arithmetic replayが完了。
14. **precision分離**：source structural okだけではfinancial qualificationがqualifiedにならない。
    underresolved/failure/原SE gate未達を元truth tableへ保持。

test対象に新private modeが増えるだけで、full suiteやformal pilotをこのdesign reviewで先にPASSとしない。
必要なsource scoped tests / ruff、docstring/index guardは実装turnで行い、独立source reviewを続ける。

## 5. saved / freeze bindings

現replay `rebuild_asian_cache` とrunner `check_bundle` はfixed domainを知らない。
source実装後は同じoptional configをreplayへ渡し、explicit metadata / raw original arraysを金融照合する。
この配線を省略するとgenerationとcheckerが異なる価格面になる。

main前freezeに最低限含める：

- 原v1 candidate digest、B revision document・code transitive closure、private domain schema/method identity。
- モデル別・全exact dates別のhalf-open node index rangesとresolved physical bounds、local t0 sheet identity。
- original full axes / date / memory_count / threshold range / every original status / N / shared IID block identity。
- full group/global driver/slice mappings、raw primitive/mean/block artifact bindings。
- selector rule、候補enumeration・tie規則、pilot-only seed/stream、選択入力のoriginal_N/grid/source、
  元候補全部の不適格理由／計算費用。採用geometryをcandidate boxから区別する。
- full-domain call roots/κ/ref uncertaintyとpost-fit Asian-domain-check rule。patchによるroot集合変更なし。
- scoped source tests、独立code/design review、saved/fresh/CAS replay境界と費用scope。
- 金融availability / qualification / readinessを別fieldsへ保持。box外元case/pathsをunknownとして数える。

実測box値は今回のreviewではfreezeしない。
pilotデータ由来のbox選択は選択不確実性も含むため、選んだoperator内のblock covarianceだけで
domain選択・interpolation bias・SDE bias・call denominator errorを包んだとしない。
別pilot streamでgeometryを決め、その後の独立source/teacher/oracle測定で採用domainを確認する。
fresh cacheに必要node欠落が出てもboxを選び直さず、元failed証跡とunknownを保持する。

cold費用は原全teacher nodes / selector / slice/coefficients / serialization / saved/fresh/CASを含む。
hot費用の短縮は独立実測があるまで未評価。遠方nodeを評価に使わなくても元費用は消さない。

## 6. evidence / 不承認の対象

- archived diagnostics：full-ready 0/108、raw late-local price-bound fails23nodes、有限ATM box候補。
  source支持の可能性を示す予備測定で、範囲・precision認定ではない。
- このreviewの独立probes：`task-5-fixed-domain-design-review-probes.py/.json/.txt`。
  full-root hiding counterexample、current block-NaN default、exact linear/settled preservation。
- fee：`task-5-fixed-domain-design-review-run.json`。source code実装は未実施。
- 前回のarchived diagnosticsを作った担当と同一だが、今回レビューするproposalはroot作成。
  rootのcanonical改変とsource実装には参加していない。

未承認：A全validator契約、box具体値、N選択の精度達成、価格/Greeks/IFT精度、独立actual Asian oracle、
正式pilot/freeze/readiness/main、NN比較、全suite、公開、main統合。
