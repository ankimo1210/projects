# monitor v2: root launch用チェックリスト

D限定の読取整理。新schema・mandatory gate・承認は作成しない。金融/RNG/SDE/solver/Popenは0。
対象: `task-5-full-pilot-root-operational-monitor-v2.py` SHA `1c8e0c375cfff3d347326b63b1f324177e29bb4216810490c9d468cabbb6181c`。
元false候補・v1/v2 manifest・失敗履歴は不変。

## 1. rootが既存false guardへ埋める値

元候補: `task-5-full-pilot-root-operational-monitor-v2-guard-candidate.json`。
schema `rb-f04-root-full-pilot-operational-prior-v1` のまま。

|既存field|実入力／制約|
|---|---|
|root_preapproved / prior_role|実root承認後だけ true / root_fixed_operational_prior|
|formal_financial_launch_authorized|全priorレビューとmetadata materialize後の別root金融launch承認。source限定／行政prior承認だけではtrueにしない|
|full_budget_and_cap_recipe_review|実全3138レビューの絶対path・file SHA・status approved。schema rb-f04-independent-fullmixed-prior-budget-review-v1 / role independent static prior resource reviewer / decision approved|
|approved_budget_bindings|同実decisionのapproved_bindings全18項目をそのままコピー。候補raw digestで代替しない|
|phase_wall_limit_seconds|root選択の行政allowance。30日なら2592000秒。runtime予測／金融capではない|
|child_rss_limit_bytes / parent_rss_limit_bytes|root選択の各process RSS。16GiBなら各17179869184。既存validatorは16–24GiB。tree合計／RLIMIT_ASではない|
|poll_seconds|root選択1秒。既存loopは正値かつ60秒以下|
|plan / typed_inputs|実immutable artifact directory絶対path、全files map、tree_sha256、root receipt_sha256（次節算式）|
|native_output_path|新規絶対path。実run_pilot出力。開始前に存在しない|
|receipt_directory|D内の別新規絶対path。nativeと同一／親子ではなく、開始前に存在しない|
|python_executable|monitorのsys.executableと完全一致。現候補 /home/kazumasa/projects/.venv/bin/python|
|volume_probes|順序WSL/C/F、path / /mnt/c /mnt/f、各reserve_bytes10737418240。実st_devが3種類必要|

固定項目は現source81 inventory／canonical1cc16cf7…／nativebe858ced…、source8a000b…限定decision、rebind evidence1e83ebae…、v6 b1e395…／manifest a47743…、monitor SHA、121cases／51attempts／3138jobs／4N、administrative_guard_only=true、financial_A_cap_projection_approved=false、financial_qualification=unknown、formal_phase_completion_claimed=false。

effective normalized／recipeは最終実全budgetdecisionのapproved_bindingsを使う。reviewer通知の02da310d…／e8fda1ec…を実decisionなしに承認扱いしない。raw fb42604f…／d5f29fbf…は歴史bindingとして別欄のまま。

## 2. plan / typed_inputs treeの算式

materializer保存planは `<実materialization出力>/locked-prior-metadata/`。
typed_inputsは同planの `_locked_bindings` が確認した既存prepared artifact。実コピー／復元rootを使う場合は、その全物理bytesを結合する。金融合否をSHAで判定しない。

- `files[relative_path] = SHA256(file.read_bytes())`。root以下の**全file**（root/packのreceipt、metadata、arrays、その他）を含む。file symlinkは禁止。
- `tree_sha256 = SHA256(json.dumps(files, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())`。monitor.digestそのまま。
- `receipt_sha256 = files["receipt.json"]`。receipt **file bytesのSHA**であり、JSON内の `artifact_sha256` ではない。
- plan／typed_inputsを独立に作成。`path` は実root絶対path。payload planSHA／input bindingsをtree SHAへ読み替えない。

root用read-only算式例（ここでは未実行）:

```python
from pathlib import Path
import hashlib, json
root = Path("/ABS/IMMUTABLE/ARTIFACT")
files = {}
for p in sorted(root.rglob("*")):
    if p.is_file():
        if p.is_symlink():
            raise ValueError("file symlink prohibited")
        files[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
spec = {
    "path": str(root), "files": files,
    "tree_sha256": hashlib.sha256(json.dumps(
        files, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()).hexdigest(),
    "receipt_sha256": files["receipt.json"],
}
print(json.dumps(spec, indent=2, sort_keys=True))
```

guard自身の実file SHAはbefore-bindings／終了receiptへ保存される。既存guard schemaに自分自身のSHA fieldはない。rootの別prior／外側時計へ実SHAを結合する。

## 3. 容量の直前read-onlyコマンド

root launch直前に実取得する資料。今回未実計測。C/Fを合算して単一volume空きに比較しない。

```bash
df -B1 / /mnt/c /mnt/f
stat -c '%d %n' / /mnt/c /mnt/f
rg 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo
```

10GiB reserveより空いていても全phase保存量を保証しない。各free<=reserveなら行政停止する。poll間の増加、kill/wait、終了binding検算／receipt尾部は上限を超え得る。RSSはVmRSS×1024、kernel peakはgetrusage ru_maxrss×1024。帰属／値が不明ならunknown保持。

## 4. 実launch argv（root承認後のみ）

```bash
/home/kazumasa/projects/.venv/bin/python \
  /home/kazumasa/worktrees/johnhull-research-roadmap/.superpowers/sdd/2026-10-09-dynamic-cross-model-hedging/task-5-full-pilot-root-operational-monitor-v2.py \
  --guard /ABS/ROOT-FIXED-LAUNCH-GUARD.json
```

monitorがそのまま起動するchild:
```text
[python_executable,
 /home/kazumasa/worktrees/johnhull-research-roadmap/johnhull/research/RB-F04/dynamic_hedging/run_pilot.py,
 --plan, plan.path, --inputs, typed_inputs.path, --output, native_output_path]
```
cwdはWT。PYTHONPATHはWTの dynamic_hedging / hullkit/src / deep_hedge_price/src をこの順で結合。Windows Pythonを混ぜない。v2はfresh出力CLIであり `--resume` は渡さない。再開をこのguardへ追加しない。

## 5. 保存資料の観察点・終了解釈

**monitor側**
- `prior-root-fixed.json`／`before-bindings-and-command.json`: 実prior・source81・plan/input全tree・argv・clock・初期free・元obligations。
- `stdout.log`／`stderr.log`: 原child出力。run_pilotは最終printまで無出力でも進行し得る。
- `observations.jsonl`: flush済みpollごとのclock／elapsed／childとparent RSS／3volume free。PIDは最終receipt。
- `after-bindings.json`／`parent-cost-and-status.json`: 原binding不変／code／wall・CPU・RSS・overrun／停止理由・unknown。

**native側**（必要な保存metadataだけを読取）
- `<native>/plan/`: child保存の元locked plan。
- `<native>/jobs/<original job.id>/`: 元3138rosterのIDで特定。途中のdirectory／3file数をcompletedへ数えない。成功、declaredcap、dependencycap、sourcefault、unusedを原statusで区別。
- teachergridは原typed `work_directory/nodeNNNN/` に原rawを保存する。node countは観察であり、全N／labels／SDE／cache検算完了ではない。
- root metadataの原tree／全shape／dtype／partsと `packNNNN/{metadata.json,arrays.npz,receipt.json}`。writer128MiB配列partとprotocol **NPY header込み256MiB expanded cap**を区別。teacher圧縮の物理bytesとexpanded bytesも区別。receiptは金融精度を認定しない。
- `<native>/checkpointNNNN/` は**phase終了時**（freshはcheckpoint0000）。jobごとのprogress checkpointではない。原raw参照・費用・teacher proof eventsは後のsaved checkerで検証する。

child exit0でも `child_terminal_needs_saved_check`。非zeroをresourcecapへ改名しない。行政signalはpartial/unclosed、binding差／observer error／stoprace／unknown／NaN／failure／未保存rawを保持。monitor inclusive費用へnative phase/job/driver/history内訳を二重加算しない。monitor最終receipt作成／stdout尾部はunknown、root外側時計で別測定。

既存実source参照: monitor v2 tree_binding88–109/load_guard199–269/run337–621、run_pilot write1812–1869/run4061–4459/main4461–4480、protocol write645–695/read698–746。これは既存callerの使用材料であり、追加mandatory pipelineではない。
