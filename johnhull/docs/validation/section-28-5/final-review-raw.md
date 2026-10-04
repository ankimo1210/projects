# M30 §28.5 最終コードレビュー

レビュー日: 2026-10-04。対象: `codex/m30-multifactor-martingales`、BASE `7ac2f470b9e3f25a81fb8ed611a5ded8fa97b3c7` → HEAD `4c2ce9ff617f8bc6ef1c4d5dd3a808059de2c4ee`。1名によるfreshレビュー。checkout/index/HEAD/branchは変更していない。再現用ファイルとpytest一時ファイルは `/tmp` のみ。

**結論: Critical 0 / Important 1 / Minor 2。Ready to merge: With fixes。** 因子計算・同一給付価格・D1受入ゲートは整合している。教材の直接生成時に、平均とSEを同時改変した保存MCを受容する穴を修正する必要がある。

## Strengths

- 原典PDF pp.679–680／脚注7、spec／plan、private API、独立教師、数値verifier、教材、notebook/browser verifier、受入gate/updater、関連testsと差分を照合した。`C=L Lᵀ`、row loading `s L`、相関座標のrisk vector `C s_g`、比の相対Itô driftの交差項とlog driftの区別は正しい。PSD退化でinverseやjitterを必要としない。
- 160個の独立ランダム市場（因子数1/2/3/5、rank 1/full、signed loading、負を含むrate）をmath.fsumの直接bilinear式と照合。回転前後のdriftと条件付き平均を含む最大絶対差は `2.6645352591003757e-15`。主要な数値式の不具合は見つからなかった。
- 同じf市場でgのloadingを正・負・ゼロに変えた3市場のQ価格は `9.038314313908826`、g価格も最終桁まで一致する。raw RN方向、ランダムなg分母、一般local martingaleと有限定数GBMのtrue martingaleの区別、M29確率金利教材を置き換えない説明は妥当。
- 入力をfloatへ変換する前の型／非有限検査、empty batchより前のvalue/horizon domain検査、final factor axis、相関entryの先行上限検査は適切。混合boolの回帰もある。
- 独立教師はproduction APIをimportせず、math.fsumの直接共分散とGaussian求積を持つ。今回独立に保存値を照合したところ、132状態の一次・二次モーメント求積誤差はともに最大 `8.881784197001252e-16`、最大打切りtail boundは `1.9661911028715037e-25`。
- freshの88対象testsと4つの `--check` がすべてPASS。統合gateは29既受入節について現行producer inventoryから必須hashを導出し、現行ファイルと両保管庫の実体を検証する。updaterはgate成功後に全変更をメモリで構築し、最後に台帳を書く。
- 旧257セルの本文・保存出力・Plotly保持と新11セル、16 browser statesを現行gateで照合した。4枚の保存画像を目視し、今回見た図にはラベル衝突・判読を妨げる欠けを認めなかった。M31以降の準備を正式受入に数えていない。

## Issues

### Critical (Must Fix)

なし。

### Important (Should Fix)

**I1. 保存MCのSEが自己申告のままなので、平均とSEを同時に変えると教材消費時の検査を通る。**

- 場所: `johnhull/hullkit/src/hullkit/_multi_factor_lesson.py:47–62`、呼び出し `:150–168`、結果digest検査 `:97`。
- `_mc()` はtruthの照合後、保存した `z = abs(mean-truth)/se` の内部整合と5SEだけを確認する。`mean` と `se` が固定seed・262144 samplesから実際に得られた値であることは確認しない。`_result_digest` は改変後に再計算できるので、この不足を補えない。非負call payoffのMC平均が負であるという不可能な保存値さえ受容する。
- 現行正常値: `pricing_mc[1].call_g = {mean: 9.05207105830452, se: 0.030065377563162417, z: 0.45756100573797426, reference: 9.038314313908828}`。
- 独立再現: 同じrowを `mean=-100.0, se=100.0, z=1.0903831431390882` に変更し、全rowから `max_mc_se` を再計算、`result_sha256` も再計算した。source/reference hash・samples・seed・他の数値は正常のまま。`_figures()` は例外を投げず、call_gの価格差 `-109.03831431390883`、区間半幅 `196.0` を描いた。別の正値改変 `mean += 100; se=100` も受容し、差 `100.01375674439569 ±196` を描いた。単なる非負性検査の追加だけでは後者を防げない。
- 利用者への影響: report registryとnotebookはこのconsumerを直接使うため、保存結果の破損や誤った結果更新があると「独立検証済み」の図に誤った平均／不確実性を表示する。とくに本変更は再署名した保存結果を消費時にも拒否する契約を掲げているため、消費時ガードの欠落としてImportant。
- 影響範囲の限定: `build_multifactor_acceptance_record.py:284,315–318` はfresh MC結果と保存recordを完全比較するので、同じ改変は正式統合gateでは拒否される。現行committed MC値が誤っているという指摘でも、正式gateを回避できるという指摘でもない。
- 修正案: 消費時に固定seed／samplesのMC集計を再生成してmean/se/seed等を照合するか、生成済み結果とは独立した同等の検証を行う。source/referenceが変わらない場合の再利用は、検証済みの内容をキーにしてよい。平均・SE・z・summary・digestを同時に整合改変する回帰testを追加し、正値の大幅偏りと不可能な負平均の両方を拒否する。

再現コード（環境は `source /tmp/m30-env.sh; export PYTHONDONTWRITEBYTECODE=1`、checkoutで実行、出力は/tmpのみ）:

```python
import json
from pathlib import Path
from hullkit import _multi_factor_lesson as m

record = json.loads(m._RECORD.read_text())
row = record["pricing_mc"][1]["call_g"]
row.update(mean=-100.0, se=100.0)
row["z"] = abs(row["mean"] - row["reference"]) / row["se"]
all_mc = [
    v for r in record["pricing_mc"] for v in r.values()
    if isinstance(v, dict)
] + [r["mc"] for r in record["api_conditional_means"]]
record["max_mc_se"] = max(r["z"] for r in all_mc)
record["result_sha256"] = m._result_digest(record)
p = Path("/tmp/m30-review-negative-call.json")
p.write_text(json.dumps(record))
m._RECORD = p
fig = m._figures()["factor_measure_price"]
print(fig.data[1].y[0], fig.data[1].error_y.array[0])
# -109.03831431390883 196.0 — 本来は拒否が必要
```

### Minor (Nice to Have)

**M1. 条件付き一次・二次モーメントの独立求積を計算するが、合否判定に接続していない。**

- 場所: `johnhull/scripts/build_multifactor_reference.py:188–218,273–276`、`johnhull/scripts/verify_multifactor_numerics.py:153–170`。
- 教師は `g_mean_quadrature`、`g_second_moment_quadrature` とtail boundを保存する。しかしbuild末尾のassertやverifierでは、これらを解析モーメントと比較しない。verifierが比較するのはAPI平均と解析 `g_mean/q_mean`、MC平均である。
- 現行132状態の求積値は上記のとおり正しいため、価格や教材の現在の誤りではない。将来、独立求積の一方が壊れても「独立求積PASS」の記録が成立し得る検証ギャップ。
- 改善案: 一次・二次求積と解析値、およびtail boundを固定許容値で判定し、求積だけを壊す変異を拒否する。

**M2. specで明示したmissing-RN変異がnegative_controlsに存在しない。**

- 場所: `johnhull/scripts/verify_multifactor_numerics.py:205–214,256–263`、spec `Independent acceptance`。
- 8 controlsは `saved_drift/omit_correlation/wrong_cross_sign/double_C/initial_ratio/log_drift/jitter_PSD/missing_path_numeraire`。最後はランダムg分母を落とした価格であり、Q→gのRN重みを落とす／逆向きにする変異ではない。
- 正常経路の `:141–148` ではraw RNを正しく計算し、平均1と再重み付け平均を照合している。そのため現在の数値誤りではなく、specが約束した負例の不足としてMinor。
- 改善案: 同一のQ標本に対しdensityを省略、または逆転した対照を実際に走らせて拒否し、記録するcontrol一覧と件数を実際のものへ合わせる。

## Recommendations

I1を一回のRED→GREENで修正し、教材consumerの複数フィールド同時改変testを含めて検証する。変更後は既存の証跡更新手順で関連source hash／notebook・browser・D1・台帳を整合させ、計画の全suiteとrelease gateを実行する。M1/M2はMinorとして後続へ記録してよい。別レビュアーや再レビューは実施していない。

## Declined to judge

- 一般状態依存SDEについてtrue martingaleを保証する機能: 実装は有限時間・一定GBMに明示限定し、一般local/trueの区別を教材に記載しているため、この変更の欠落としない。
- 確率金利下の新しい多因子価格エンジン: 今回の価格例は一定rであると明示され、M29教材は保持検査済み。点ごとのr相殺の説明と矛盾しないため、新規実装を要求しない。
- 極端なfloat領域の中間exp overflow／subnormal精度: `value=1e-300, drift=710, h=1` は最終値が約 `2.233994766e8` でも中間expでValueError、`value=1e308, drift=-745` は約 `2.82235e-16` に対し `4.940656e-16` を返すことを確認した。全実数域の浮動小数精度を保証しない制約、通常教材の入力規模から大きく外れる条件、既存方針との一貫性から、今回のmerge阻害にはしない。将来全float域を契約にするならlog-domain計算が必要。
- 任意巨大因子数でのメモリ／固有分解コスト: 小規模因子のprivate教材であり、通常ケースで実害を観測していない。新たな疎行列・大規模APIの設計は要求しない。
- 毎回のconsumer読み込みで独立教師のMCも再生成するコスト: ローカル再現の `_figures()` は約0.51秒で、実害としての性能退行を立証していない。正しさ検査の代償として今回の欠陥に数えない。
- 将来M31以降／Ch29–34の準備文書内のすべての数値導出・scratch再現性: diffには含まれるが、いずれも準備／未受入の表示があり、台帳上も未受入を保持している。正式教材品質の承認は行わず、各節受入時に原典とscratchを再検証する必要がある。
- 既存の `johnhull/AGENTS.md -> CLAUDE.md` とCLAUDE本文の `@AGENTS.md` 参照の循環: BASEでも同じで、このdiffが導入した問題ではない。今回のレビューは与えられたworkspace指示とspecを採用し、ファイル修正はしない。
- main FF／push／remote一致: まだ計画上の将来工程であり、未実行を実装欠陥や完了済みとして扱わない。

## Actual checks run

- `python -m pytest -p no:cacheprovider --basetemp=/tmp/m30-review-pytest` + 新API/numerics/lesson、multifactor notebook/registry/acceptance_record/ledger_updateの7 test files: **88 passed in 31.74s**。
- `build_multifactor_reference.py --check`、`verify_multifactor_numerics.py --check`、`verify_multifactor_notebook.py --check`、`build_multifactor_acceptance_record.py --check`: **すべてPASS**。最後は29D1の現行hash・成果物・両保管庫の検証を含む。
- 独立ランダム160ケース、132求積モーメント／tail bound、同じfの3価格照合: 上記誤差内。
- I1の正値偏り／負call平均という2改変: **両方ともconsumerが誤って受容することを再現**。
- 原典PDF pp.679–680の該当本文を直接抽出して照合。保存画像 `portal-factor_measure_price-1000.png`、`book-factor_ratio_conditional-1000.png`、`portal-factor_basis_covariance-1000.png`、`book-factor_ratio_ito-1440.png` を直接目視。
- 全suiteは本レビューでは再実行していない。executorの保存ログ `full-suite-before-review.txt` の **4219 passed / 6 skipped / 2 warnings / 272.81s** を確認し、fresh対象testsとは区別した。browserの全16状態を新たに操作／撮影したとは主張しない。
- 開始・終了時とも `git status --short` は空、HEADは指定SHAのまま。

## Assessment

**Ready to merge? With fixes**

数式、PSD・基底変換、同じ給付の価格、入力契約、および正式受入gateは確認した範囲で堅実である。ただし教材の直接利用時に、再署名した保存MCの誤った平均とSEを受容するI1は、今回明示した消費時検証契約と実際の図の信頼性を損なうため、merge前に修正する必要がある。
