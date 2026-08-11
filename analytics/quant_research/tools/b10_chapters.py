"""Deterministic cell definitions for the six B10 notebook builders."""

from __future__ import annotations

from nbkit import code, md
from stage2_nb import setup_cell

PERFORMANCE_SOURCES = """
- [Python `timeit` documentation](https://docs.python.org/3/library/timeit.html)
- [Python `multiprocessing` documentation](https://docs.python.org/3/library/multiprocessing.html)
- [NumPy CPU/SIMD optimizations](https://numpy.org/doc/stable/reference/simd/index.html)
- [IEEE 754-2019 overview](https://standards.ieee.org/ieee/754/6210/)
"""

ENGINEERING_SOURCES = """
- [Python Packaging User Guide](https://packaging.python.org/en/latest/)
- [Python logging HOWTO](https://docs.python.org/3/howto/logging.html)
- [pytest documentation](https://docs.pytest.org/)
- [Semantic Versioning 2.0.0](https://semver.org/)
"""

DATA_SOURCES = """
- [Apache Arrow columnar format specification](https://arrow.apache.org/docs/format/Columnar.html)
- [Apache Parquet format](https://parquet.apache.org/docs/file-format/)
- [DuckDB documentation](https://duckdb.org/docs/stable/)
- [SQLite window functions](https://www.sqlite.org/windowfunctions.html)
"""


def _fixture_cell():
    return code("""
fixture = qt.load_sec_teaching_fixture()
train_mask = fixture.training_mask
validation_mask = fixture.validation_mask
assert train_mask.sum() == 192
assert validation_mask.sum() == 64
assert not np.any(fixture.target_available_dates >= np.datetime64("2023-10-23"))
print("fixture rows:", fixture.targets.size)
print("inner train / validation:", int(train_mask.sum()), int(validation_mask.sum()))
print("locked outer rows present: False")
""")


def _numeric_baseline_cell():
    return code("""
numeric_preprocessor = qt.fit_numeric_preprocessor(fixture.numeric_features, train_mask)
numeric_features = numeric_preprocessor.transform(fixture.numeric_features)
numeric_model = qt.fit_sparse_ridge(
    numeric_features[train_mask], fixture.targets[train_mask], ridge=1.0
)
numeric_validation_prediction = numeric_model.predict(numeric_features[validation_mask])
numeric_metrics = qt.regression_error_table(
    fixture.targets[validation_mask],
    numeric_validation_prediction,
    np.asarray(fixture.entity_ids)[validation_mask],
)
print("numeric validation metrics:", numeric_metrics)
""")


def overview_cells():
    return [
        md(r"""
# 54. B10 — Scientific computing, data systems, and ML engineering

> 一度動くNotebookを、再現・監査・rollbackできるresearch systemへ変える。速さやtool名ではなく、correctness、lineage、information time、failure recoveryを成果物にする。

## 学習目標

- correctness testとperformance benchmarkを分離できる
- vectorization、layout、parallelism、JIT/GPUの適用境界を説明できる
- configuration、logging、type、test、dependencyをpackage contractへまとめられる
- observation/release/revision/availability/decision timeを分離してPIT joinできる
- experiment・data・model・predictionをcontent hashで結べる
- drift alert、promotion、rollbackをmodel qualityの証明と混同しない

## 前提知識

- Week 16のresearch softwareと数値契約
- B5–B9のtraining-only transform、locked test、no-model-selected規約
- SQL、Python package、NumPy/pandasの基本
"""),
        setup_cell(54),
        _fixture_cell(),
        md(r"""
## 1. B10 evidence chain

| Week | Core | B9接続 | failure injection |
|---|---|---|---|
| 37 | profiling、vectorization、layout、deterministic chunk | SEC feature matrix | result disagreement、order dependence |
| 38 | API/config/test/logging/environment | `quant_textbook` package | config hash mismatch、invalid input |
| 39 | SQLite、columnar memory、schema、bitemporal PIT | SEC availability | future revision、schema removal |
| 40 | run registry、data/model version、drift、batch inference | B9 baseline | duplicate run、wrong input hash、rollback |
| Project | reproduction manifest | development-only B9 pipeline | outer unopened、artifact mismatch |

Coreは標準library SQLite、NumPy、SciPy、pandasを使う。DuckDB/Arrow/Parquet、Numba/JIT、GPUは重要だが、新dependencyを暗黙追加せずAdvancedのinterface・memory model・migration planとして扱う。
"""),
        code("""
stage_rows = pd.DataFrame(
    {
        "stage": ["Correctness", "Performance", "Data lineage", "Experiment lineage", "Deployment"],
        "required_before_next": [1, 1, 1, 1, 0],
        "evidence_count": [4, 3, 5, 5, 3],
    }
)
fig = go.Figure()
fig.add_bar(x=stage_rows["stage"], y=stage_rows["evidence_count"], name="required evidence")
fig.update_layout(
    title="B10 evidence precedes deployment",
    xaxis_title="System layer",
    yaxis_title="Teaching evidence items",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 2. 失敗モード

- benchmarkが速いことをcorrectnessの代わりにする
- shared environmentに偶然あるundeclared dependencyを使う
- event timeとprocessing timeを同じtimestampへ潰す
- overwrite可能なmodel fileをregistryと呼ぶ
- drift thresholdをmonitoring後に調整する
- production deploymentを教材fixtureで実施したと主張する

## 3. 段階別演習

### 基礎

1. correctness/performance/reproducibilityの証拠を分類せよ。
2. B9 fixtureからouter rowが除外されているassertを書け。

### 標準

3. experiment runに必要なhashとmetadataを設計せよ。
4. availability timeを落としたPIT joinの反例を作れ。

### 研究

5. DuckDB/Arrowを追加するdependency decision recordを書け。

## 4. Exit Criteria

- [ ] 速さと正しさを別gateにした
- [ ] undeclared dependencyを使っていない
- [ ] five-time financial data contractを定義した
- [ ] run/data/model/outputをhashで結んだ
- [ ] B9 locked outerを開いていない

## 5. 出典

"""
            + PERFORMANCE_SOURCES
            + ENGINEERING_SOURCES
            + DATA_SOURCES
        ),
    ]


def week37_cells():
    return [
        md(r"""
# 55. Week 37 — Performance and deterministic numerical computing

## 学習目標

- profile前に結果一致と入力scaleを固定できる
- Python loopとvectorized kernelを同じ計算で比較できる
- memory layout、summation order、chunk planの影響を測れる
- JIT/GPU/parallelismのtransfer・compile・determinism costを説明できる

## 前提知識

- floating-point rounding、Big-O
- NumPy array、memory layout
- Week 16のbenchmark/profiling境界
"""),
        setup_cell(55),
        _fixture_cell(),
        md(r"""
## 1. Correctness before timing

同じweighted row sumをPython loopとNumPy kernelで計算する。benchmarkはwarm-up後のmedian/IQRを保存するが、共有machineで速度pass/failを置かない。
"""),
        code("""
values = np.nan_to_num(fixture.numeric_features, nan=0.0)
weights = np.linspace(0.5, 1.5, values.shape[1])


def row_score_loop():
    output = np.empty(values.shape[0])
    for row_index, row in enumerate(values):
        total = 0.0
        for value, weight in zip(row, weights, strict=True):
            total += value * weight
        output[row_index] = total
    return output


def row_score_vectorized():
    return values @ weights


loop_result = row_score_loop()
vectorized_result = row_score_vectorized()
np.testing.assert_allclose(loop_result, vectorized_result, rtol=1e-13, atol=1e-13)

loop_benchmark = qt.benchmark_function(row_score_loop, repeats=7, warmups=2)
vector_benchmark = qt.benchmark_function(row_score_vectorized, repeats=7, warmups=2)
benchmark_table = pd.DataFrame(
    [
        {"implementation": "Python loop", "median_ms": loop_benchmark.median_seconds * 1e3, "iqr_ms": loop_benchmark.interquartile_range_seconds * 1e3},
        {"implementation": "NumPy kernel", "median_ms": vector_benchmark.median_seconds * 1e3, "iqr_ms": vector_benchmark.interquartile_range_seconds * 1e3},
    ]
)
display(benchmark_table)

fig = go.Figure()
fig.add_bar(x=benchmark_table["implementation"], y=benchmark_table["median_ms"], error_y={"array": benchmark_table["iqr_ms"]})
fig.update_layout(title="Warm-up-aware timing, no universal speed gate", yaxis_title="Milliseconds", template="plotly_white")
fig.show()
"""),
        md(r"""
## 2. Summation orderとlayout

floating-point additionは結合的でない。parallel reductionはchunk/schedulingで順序が変わるため、seed固定だけではbitwise reproductionを保証しない。row chunkは入力順から決定し、merge順も固定する。
"""),
        code("""
adversarial = np.array([1e16, 1.0, -1e16] * 2000, dtype=float)
forward_sum = float(np.sum(adversarial))
reverse_sum = float(np.sum(adversarial[::-1]))
python_sum = float(sum(adversarial.tolist()))
chunk_plan = qt.deterministic_chunk_plan(values.shape[0], worker_count=7)
covered_rows = [row for start, stop in chunk_plan for row in range(start, stop)]
assert covered_rows == list(range(values.shape[0]))

c_layout = np.array(values, order="C")
f_layout = np.array(values, order="F")
np.testing.assert_allclose(c_layout @ weights, f_layout @ weights)
display(
    pd.DataFrame(
        [
            {"reduction": "numpy forward", "value": forward_sum},
            {"reduction": "numpy reversed", "value": reverse_sum},
            {"reduction": "Python left fold", "value": python_sum},
        ]
    )
)
print("chunk plan:", chunk_plan)
print("C/F contiguous:", c_layout.flags.c_contiguous, f_layout.flags.f_contiguous)
"""),
        md(
            r"""
## 3. Parallel/JIT/GPU decision table

| method | fixed cost | 向く処理 | 必須監査 |
|---|---|---|---|
| process pool | serialization、startup | coarse independent tasks | chunk/merge order、seed tree |
| threads | GILまたはnative release | I/O、native kernels | shared mutation、BLAS threads |
| JIT | compile、specialization | repeated numeric kernel | signature、warm-up、fallback |
| GPU | transfer、kernel launch | large dense parallel work | device/version、deterministic op |

NumPy kernelが既にnative codeを呼ぶ場合、Python-level parallelismを重ねるとoversubscriptionで遅くなり得る。Coreでは未宣言のNumba/GPU dependencyを使わず、追加判断に必要なevidenceを先に固定する。

## 4. 失敗モード

- timing前に値を照合しない
- 一回のwall timeをbenchmarkと呼ぶ
- compilation/transferを除外して都合のよい速度だけを出す
- BLAS thread数とhardwareを記録しない
- parallel workerへ同じRNG stateをcopyする

## 5. 段階別演習

### 基礎

1. loop/vectorized結果のscale-aware assertionを書け。
2. forward/reverse summationが異なるfixtureを説明せよ。

### 標準

3. deterministic chunk planのcoverage property testを書け。
4. C/F layoutを演算方向別にbenchmarkせよ。

### 研究

5. JIT/GPU採用のbreak-even sizeをcompile/transfer込みで設計せよ。

## 6. Exit Criteria

- [ ] 結果一致をtimingより先に確認した
- [ ] warm-up、median、IQRを保存した
- [ ] chunkとmerge順を固定した
- [ ] JIT/GPUの固定costを含めた
- [ ] performanceを共有machineの普遍gateにしていない

## 7. 出典
"""
            + PERFORMANCE_SOURCES
        ),
    ]


def week38_cells():
    return [
        md(r"""
# 56. Week 38 — Software engineering for research

## 学習目標

- exploratory cellからpure APIとI/O adapterを分離できる
- configuration、type、error、logのcontractを書ける
- example/unit/property/integration testを役割別に設計できる
- content-addressed experiment runを再生成できる

## 前提知識

- Python package、dataclass、exception
- Week 16のresearch software
- B9 feature/model API
"""),
        setup_cell(56),
        _fixture_cell(),
        _numeric_baseline_cell(),
        md(r"""
## 1. Package boundary

`quant_textbook`はpure numerical/data contractを`src/`へ置き、Notebookは設定・可視化・解釈を担当する。raw SEC network/cache adapter、feature transform、model、metric、artifact hashを一つのfunctionへ混ぜない。

| layer | input | output | failure |
|---|---|---|---|
| data adapter | path/manifest | validated records | missing/hash/schema error |
| features | records + training mask | transform + matrix | leakage/shape/nonfinite |
| model | matrix + config | immutable parameters | rank/convergence/budget |
| evaluation | target/pred/entity | metric table | mismatch/nonfinite |
| registry | run metadata/hash | append-only state | duplicate/tamper |
"""),
        code("""
import hashlib

fixture_digest = "6487c20568fbbbb18326bcde49d985b42ddd5072f321e33e4b2b8154a7293295"
prediction_digest = hashlib.sha256(
    numeric_validation_prediction.astype("<f8", copy=False).tobytes()
).hexdigest()
config = {
    "family": "numeric_ridge",
    "ridge": 1.0,
    "training_rows": int(train_mask.sum()),
    "validation_rows": int(validation_mask.sum()),
    "outer_access": "unopened",
}
run = qt.build_experiment_run(
    experiment_name="b10-teaching-reproduction",
    candidate_name="numeric-ridge",
    stage="development",
    config=config,
    data_sha256=fixture_digest,
    code_revision="notebook-56-generated-source",
    metrics=numeric_metrics,
    artifact_sha256={"validation_prediction": prediction_digest},
)
repeated = qt.build_experiment_run(
    experiment_name="b10-teaching-reproduction",
    candidate_name="numeric-ridge",
    stage="development",
    config=config,
    data_sha256=fixture_digest,
    code_revision="notebook-56-generated-source",
    metrics=numeric_metrics,
    artifact_sha256={"validation_prediction": prediction_digest},
)
assert run == repeated
display(pd.DataFrame([{"run_id": run.run_id, "config_sha256": run.config_sha256, "data_sha256": run.data_sha256, "prediction_sha256": prediction_digest}]))
"""),
        md(r"""
## 2. Test portfolioとfailure semantics

unit testは局所契約、property-style testは多入力のinvariant、integration testはlayer間契約、Notebook executionはreader-facing evidenceを検査する。例が一つ通っただけでpropertyを証明しない。invalid inputをwarningだけで続行せず、例外type/messageをcontractにする。
"""),
        code("""
test_portfolio = pd.DataFrame(
    [
        {"test_type": "known-answer unit", "examples": 14, "target": "gradient/hash/metric"},
        {"test_type": "edge case", "examples": 12, "target": "empty/nonfinite/schema/time"},
        {"test_type": "property-style", "examples": 8, "target": "determinism/invariance/coverage"},
        {"test_type": "integration", "examples": 6, "target": "builder/notebook/book"},
    ]
)
fig = go.Figure()
fig.add_bar(x=test_portfolio["test_type"], y=test_portfolio["examples"])
fig.update_layout(title="Test roles are complementary", yaxis_title="Illustrative checks", template="plotly_white")
fig.show()

try:
    qt.fit_sparse_ridge(np.ones((2, 1)), np.array([1.0, np.nan]), ridge=1.0)
except ValueError as error:
    failure_message = str(error)
else:
    raise AssertionError("invalid target must fail closed")
print("expected failure:", failure_message)
"""),
        md(
            r"""
## 3. Logging、configuration、environment

logはhuman proseでなくevent name、run ID、stage、input/output hash、duration、statusをstructured fieldにする。secret、contact、raw filing本文をlogへ入れない。configurationはversioned schemaとして保存し、environment lockはdependencyを宣言するが、共有`.venv`に偶然あるpackageを依存contractにはしない。

## 4. 失敗モード

- Notebook global stateをlibrary APIが読む
- broad `except Exception`でpartial artifactをsuccessにする
- configurationを後から上書きして同じrun IDを使う
- test数だけをquality metricにする
- logへsecret/raw documentを出す

## 5. 段階別演習

### 基礎

1. data/features/model/evaluationのinterfaceを書け。
2. invalid targetがfail-closedになるtestを書け。

### 標準

3. config一項変更でrun IDが変わるpropertyを確認せよ。
4. clean processで同じprediction hashを再生成せよ。

### 研究

5. CI matrixにPython/OS/BLAS差を入れる費用と価値を評価せよ。

## 6. Exit Criteria

- [ ] package layerとNotebook責務を分離した
- [ ] config/data/code/output hashをrunへ結んだ
- [ ] unit/property/integration testを区別した
- [ ] invalid inputをfail-closedにした
- [ ] undeclared dependencyとsecretをartifactへ入れていない

## 7. 出典
"""
            + ENGINEERING_SOURCES
        ),
    ]


def week39_cells():
    return [
        md(r"""
# 57. Week 39 — Data systems, bitemporal records, and PIT joins

## 学習目標

- observation/release/revision/availability/decision timeを分離できる
- future revisionを除外するPIT joinをpandasとSQLで実装できる
- row/column storage、partition、predicate pushdownのcostを説明できる
- additive schema evolutionとbreaking changeを監査できる

## 前提知識

- SQL join/window function
- timezone-aware timestamp
- SEC M6 availability contract
"""),
        setup_cell(57),
        md(r"""
## 1. Five-time contract

| time | 意味 | 例 |
|---|---|---|
| observation | 経済量が対応する時点 | quarter end |
| release | sourceが公表した時点 | filing acceptance |
| revision | 値のversionが作られた時点 | amendment |
| availability | 保守的にpipelineで使用可能 | next business day |
| decision | modelがfeatureを読む時点 | forecast origin |

PIT joinのeligible条件は少なくとも (availability\le decision) であり、同じobservationのfuture revisionを選ばない。
"""),
        code("""
import pandas as pd


def utc(value):
    return pd.Timestamp(value, tz="UTC")


records = (
    qt.TemporalRecord("issuer-a", "assets", 100.0, utc("2020-03-31"), utc("2020-05-01"), utc("2020-05-01"), utc("2020-05-04")),
    qt.TemporalRecord("issuer-a", "assets", 110.0, utc("2020-06-30"), utc("2020-08-01"), utc("2020-08-01"), utc("2020-08-03")),
    qt.TemporalRecord("issuer-a", "assets", 112.0, utc("2020-06-30"), utc("2020-08-01"), utc("2020-09-10"), utc("2020-09-11")),
    qt.TemporalRecord("issuer-a", "liabilities", 70.0, utc("2020-06-30"), utc("2020-08-01"), utc("2020-08-01"), utc("2020-08-03")),
)
decisions = pd.DataFrame(
    {
        "decision_id": ["early", "late"],
        "entity_id": ["issuer-a", "issuer-a"],
        "decision_time": [utc("2020-08-10"), utc("2020-09-20")],
    }
)
pandas_snapshot = qt.point_in_time_snapshot(records, decisions)
sqlite_snapshot = qt.point_in_time_snapshot_sqlite(records, decisions)
pd.testing.assert_frame_equal(pandas_snapshot, sqlite_snapshot, check_dtype=False)
assert pandas_snapshot.loc[(pandas_snapshot["decision_id"] == "early") & (pandas_snapshot["field"] == "assets"), "value"].item() == 110.0
assert pandas_snapshot.loc[(pandas_snapshot["decision_id"] == "late") & (pandas_snapshot["field"] == "assets"), "value"].item() == 112.0
display(pandas_snapshot)
"""),
        code("""
timeline = pd.DataFrame(
    [
        {"label": "initial value available", "time": utc("2020-08-03"), "value": 110.0},
        {"label": "early decision", "time": utc("2020-08-10"), "value": 110.0},
        {"label": "revision available", "time": utc("2020-09-11"), "value": 112.0},
        {"label": "late decision", "time": utc("2020-09-20"), "value": 112.0},
    ]
)
fig = go.Figure()
fig.add_scatter(x=timeline["time"], y=timeline["value"], mode="lines+markers+text", text=timeline["label"], textposition="top center")
fig.update_layout(title="Availability-time join excludes the future revision", yaxis_title="Assets value", template="plotly_white")
fig.show()
"""),
        _fixture_cell(),
        md(r"""
## 2. Columnar memory、partition、schema

Arrowはin-memory columnar layout、Parquetはcolumnar file format、DuckDBはanalytical SQL engineであり同義ではない。Coreは依存追加なしでpandas column memoryとPython row representationを比較し、SQLite window queryでSQL semanticsを検証する。production-scale Parquet/DuckDB adapterはAdvancedで、schema/hash/predicate benchmarkを伴って追加する。
"""),
        code("""
fixture_frame = pd.DataFrame(fixture.numeric_features, columns=fixture.numeric_feature_names)
fixture_frame["partition"] = fixture.partitions
memory_audit = qt.audit_columnar_memory(fixture_frame)
schema_ok = qt.audit_schema_evolution(
    {"entity_id": "string", "value": "float64"},
    {"entity_id": "string", "value": "float64", "availability": "timestamp[UTC]"},
)
schema_bad = qt.audit_schema_evolution(
    {"entity_id": "string", "value": "float64"},
    {"entity_id": "int64"},
)
assert schema_ok.compatible
assert not schema_bad.compatible
display(pd.DataFrame([{"representation": "pandas columns", "bytes": memory_audit.total_columnar_bytes}, {"representation": "Python row dictionaries", "bytes": memory_audit.row_dictionary_bytes}]))
print("partition counts:", fixture_frame["partition"].value_counts().to_dict())
print("additive fields:", schema_ok.added_fields)
print("breaking changes:", schema_bad.removed_fields, schema_bad.changed_types)
"""),
        md(
            r"""
`row_dictionary_bytes`はkey/valueをUTF-8文字列化した教材用下限推定で、Python object headerやallocator overheadを完全には測らない。Arrow/Parquetの実memory/file size比較へ読み替えない。

## 3. 失敗モード

- period endをavailability timeとして使う
- future revisionをlatest valueとして過去decisionへbackfillする
- Arrow/Parquet/DuckDBを同じstorage layerと呼ぶ
- schema field removalをsilent nullへ変える
- partition keyをquery patternなしで増やす

## 4. 段階別演習

### 基礎

1. five-time contractをSEC Assets factへ対応付けよ。
2. early decisionが110を選ぶSQL predicateを説明せよ。

### 標準

3. pandas/SQLite結果のindependent agreement testを書け。
4. additive/breaking schema transitionを各1件作れ。

### 研究

5. DuckDB+Parquet adapterのdependency、schema、partition、benchmark ADRを書け。

## 5. Exit Criteria

- [ ] five timestampsを分離した
- [ ] future revisionを除外した
- [ ] pandasとSQL PIT joinを照合した
- [ ] Arrow/Parquet/DuckDBの責務を区別した
- [ ] breaking schema changeをfail-closedにした

## 6. 出典
"""
            + DATA_SOURCES
        ),
    ]


def week40_cells():
    return [
        md(r"""
# 58. Week 40 — Experiment infrastructure, registry, drift, and rollback

## 学習目標

- config/data/code/metric/artifactをcontent-addressed runへ固定できる
- append-only run evidenceとproduction pointerを分離できる
- reference-fixed drift diagnosticを計算できる
- batch inferenceのmodel/input/output lineageを保存できる
- alert、promotion、rollbackの事前規則を書ける

## 前提知識

- Week 38のpackage/config contract
- Week 39のavailabilityとschema
- B9 model selection gate
"""),
        setup_cell(58),
        _fixture_cell(),
        _numeric_baseline_cell(),
        md(r"""
## 1. Content-addressed runとregistry

run IDはhuman labelでなくcanonical config、data hash、code revision、metric、artifact hashから作る。registryはevidenceを上書きせずappendし、promotion/rollbackはpointerを動かす。教材fixtureのrunをproductionへpromoteしない。
"""),
        code("""
import hashlib

data_digest = "6487c20568fbbbb18326bcde49d985b42ddd5072f321e33e4b2b8154a7293295"
prediction_digest = hashlib.sha256(numeric_validation_prediction.astype("<f8").tobytes()).hexdigest()
development_run = qt.build_experiment_run(
    experiment_name="b10-infrastructure-lab",
    candidate_name="numeric-ridge",
    stage="development",
    config={"ridge": 1.0, "outer_access": "unopened"},
    data_sha256=data_digest,
    code_revision="notebook-58-generated-source",
    metrics=numeric_metrics,
    artifact_sha256={"validation_prediction": prediction_digest},
)
registry = qt.register_run(qt.ModelRegistry(), development_run)
assert registry.production_run_id is None
print("registered run:", development_run.run_id)
print("production pointer:", registry.production_run_id)
"""),
        md(r"""
## 2. Drift is a diagnostic, not a model verdict

reference training quantileを固定してPSIを計算し、KS statisticを併記する。p値はsample size依存であり、PSI 0.1/0.25等の慣用値も普遍定数ではない。threshold、action、minimum sample、seasonal exclusionをmonitoring前に固定する。
"""),
        code("""
feature_index = fixture.numeric_feature_names.index("log_previous_assets")
reference = fixture.numeric_features[train_mask, feature_index]
current = fixture.numeric_features[validation_mask, feature_index]
drift = qt.numeric_drift_report(reference, current, bins=8)

fig = go.Figure()
labels = [f"bin {index}" for index in range(drift.reference_proportions.size)]
fig.add_bar(x=labels, y=drift.reference_proportions, name="inner train")
fig.add_bar(x=labels, y=drift.current_proportions, name="inner validation")
fig.update_layout(title="Reference-fixed feature drift bins", yaxis_title="Proportion", barmode="group", template="plotly_white")
fig.show()
print("PSI:", drift.population_stability_index)
print("KS statistic / p-value:", drift.ks_statistic, drift.ks_pvalue)
"""),
        code("""
feature_input_digest = hashlib.sha256(numeric_features[validation_mask].astype("<f8").tobytes()).hexdigest()
batch_result = qt.batch_inference(
    numeric_model.predict,
    numeric_features[validation_mask],
    model_run_id=development_run.run_id,
    input_sha256=feature_input_digest,
)
np.testing.assert_array_equal(batch_result.predictions, numeric_validation_prediction)
display(pd.DataFrame([{"model_run_id": batch_result.model_run_id, "input_sha256": batch_result.input_sha256, "output_sha256": batch_result.output_sha256, "rows": batch_result.row_count}]))
"""),
        md(
            r"""
## 3. Batch/online/rollback boundary

batch inferenceはimmutable input snapshotへ同じmodelを適用しやすい。online inferenceはfeature freshness、concurrency、latency、partial failure、serving/training skewを追加する。rollbackは旧run artifactとschemaが利用可能であることを事前testし、model pointerだけでなくfeature/data compatibilityも確認する。

## 4. 失敗モード

- mutable file pathをmodel versionと呼ぶ
- config変更後も同じrun IDを使う
- drift alert後にthresholdを変更する
- validation driftだけでproduction rollbackする
- online endpointを作っただけでreproducibleと呼ぶ

## 5. 段階別演習

### 基礎

1. run IDに結ぶ5種類のlineageを書け。
2. batch input/output hashを再計算せよ。

### 標準

3. candidate run 2件のpromotion/rollback testを書け。
4. drift thresholdとaction matrixを事前登録せよ。

### 研究

5. training-serving skewを検知するshadow inference計画を書け。

## 6. Exit Criteria

- [ ] run evidenceをappend-onlyにした
- [ ] production pointerとartifactを分離した
- [ ] reference binをcurrent dataで再fitしていない
- [ ] batch model/input/output hashを保存した
- [ ] 教材runをproductionへpromoteしていない

## 7. 出典
"""
            + ENGINEERING_SOURCES
        ),
    ]


def project_cells():
    return [
        md(r"""
# 59. B10 Project — Reproducible B9 research package

> B9 development pipelineを、入力hashからprediction hashまでclean processで追跡できるpackage artifactへ変換する。locked outer evaluationやproduction deploymentは行わない。

## 学習目標

- data/features/model/evaluation/registryの責務を分離できる
- numeric/TF–IDF baselineを同じfixtureから再生成できる
- config/data/code/prediction hashをrunへ固定できる
- failure injectionでhash・schema・PIT gateを検証できる
- one-command reproductionの範囲と未実装範囲を説明できる

## 前提知識

- Week 37–40のbenchmark、package、PIT、registry
- B9 development-only fixtureとouter gate
"""),
        setup_cell(59),
        _fixture_cell(),
        md(r"""
## 1. Reproduction configuration

| layer | implementation | artifact |
|---|---|---|
| data | bundled SEC-derived fixture loader | fixture + manifest SHA |
| features | training-only numeric/hashed TF–IDF | transform parameters |
| models | sparse ridge baselines | coefficients/config |
| evaluation | row + company metric | validation prediction hash |
| registry | immutable development runs | run IDs |
| report | executed Notebook/Jupyter Book | HTML |

Docker/container、DuckDB/Parquet adapter、scheduler、online servingはAdvanced deployment workで、Coreの再現packageと同一視しない。
"""),
        code("""
import hashlib
from scipy import sparse

preprocessor = qt.fit_numeric_preprocessor(fixture.numeric_features, train_mask)
numeric = preprocessor.transform(fixture.numeric_features)
tfidf_model = qt.fit_hashed_tfidf(fixture.token_hashes, train_mask, maximum_features=256, minimum_document_frequency=2)
tfidf = tfidf_model.transform(fixture.token_hashes)

models = {
    "numeric-ridge": (
        qt.fit_sparse_ridge(numeric[train_mask], fixture.targets[train_mask], ridge=1.0),
        numeric[validation_mask],
        {"family": "numeric_ridge", "ridge": 1.0},
    ),
    "tfidf-ridge": (
        qt.fit_sparse_ridge(tfidf[train_mask], fixture.targets[train_mask], ridge=1.0),
        tfidf[validation_mask],
        {"family": "hashed_tfidf_ridge", "ridge": 1.0, "maximum_features": 256, "minimum_document_frequency": 2},
    ),
}
data_digest = "6487c20568fbbbb18326bcde49d985b42ddd5072f321e33e4b2b8154a7293295"
registry = qt.ModelRegistry()
metric_rows = []
run_rows = []
for candidate_name, (model, validation_features, config) in models.items():
    prediction = model.predict(validation_features)
    metrics = qt.regression_error_table(fixture.targets[validation_mask], prediction, np.asarray(fixture.entity_ids)[validation_mask])
    prediction_digest = hashlib.sha256(prediction.astype("<f8").tobytes()).hexdigest()
    run = qt.build_experiment_run(
        experiment_name="b10-b9-reproduction",
        candidate_name=candidate_name,
        stage="development",
        config={**config, "outer_access": "unopened"},
        data_sha256=data_digest,
        code_revision="notebook-59-generated-source",
        metrics=metrics,
        artifact_sha256={"validation_prediction": prediction_digest},
    )
    registry = qt.register_run(registry, run)
    metric_rows.append({"model": candidate_name, **metrics})
    run_rows.append({"model": candidate_name, "run_id": run.run_id, "config_sha256": run.config_sha256, "prediction_sha256": prediction_digest})

metric_table = pd.DataFrame(metric_rows).sort_values("mae")
display(metric_table)
display(pd.DataFrame(run_rows))
assert registry.production_run_id is None
"""),
        md(r"""
## 2. Failure injection and evidence graph

config、input、code、predictionのどれかが変わればrun evidenceも変わる。run ID一致だけでsource document integrityを再検査したことにはならないため、各layerの検証責務を残す。
"""),
        code("""
base_run = registry.runs[0]
changed_run = qt.build_experiment_run(
    experiment_name=base_run.experiment_name,
    candidate_name=base_run.candidate_name,
    stage="development",
    config={**base_run.config, "ridge": 10.0},
    data_sha256=base_run.data_sha256,
    code_revision=base_run.code_revision,
    metrics=base_run.metrics,
    artifact_sha256=base_run.artifact_sha256,
)
assert changed_run.config_sha256 != base_run.config_sha256
assert changed_run.run_id != base_run.run_id

evidence = pd.DataFrame(
    [
        {"node": "SEC source gate", "status": "passed"},
        {"node": "teaching fixture", "status": "passed"},
        {"node": "feature transforms", "status": "passed"},
        {"node": "development runs", "status": "registered"},
        {"node": "nominee manifest", "status": "not frozen"},
        {"node": "locked outer", "status": "unopened"},
        {"node": "production", "status": "not applicable"},
    ]
)
display(evidence)

fig = go.Figure()
fig.add_bar(x=metric_table["model"], y=metric_table["mae"], name="MAE")
fig.add_bar(x=metric_table["model"], y=metric_table["company_macro_mae"], name="company macro MAE")
fig.update_layout(title="Reproduced development-only baselines", yaxis_title="Absolute log-change error", barmode="group", template="plotly_white")
fig.show()
"""),
        md(
            r"""
## 3. One-command contract

repository rootからの再現順序は次である。

```bash
uv sync --package quant-research-textbook
uv run --no-sync pytest analytics/quant_research/tests
uv run --no-sync python analytics/quant_research/tools/build_notebooks.py --check
uv run --no-sync jupyter-book build analytics/quant_research/book -W --keep-going --all
```

raw SEC取得はcontact-bearing User-Agentと外部cacheを必要とし、このoffline教材再現commandへ含めない。source gateを再取得する場合は別の明示手順・rate limit・manifestを使う。

## 4. 失敗モード

- `latest.pkl`をmodel registryと呼ぶ
- environmentに偶然あるdependencyを利用する
- external raw cacheなしでsource retrievalを再現したと主張する
- development baselineをproductionへpromoteする
- B9 outerをB10 engineering確認のために開く

## 5. 段階別演習

### 基礎

1. run IDを変えるinputを5種類挙げよ。
2. config変更failure injectionを再実行せよ。

### 標準

3. clean processで同じprediction hashを得よ。
4. artifact DAGをmachine-readable JSONへ変換せよ。

### 研究

5. container/remote registry追加のthreat modelとrollback drillを書け。

## 6. Exit Criteria

- [ ] package layerを分離した
- [ ] numeric/TF–IDF baselineを再生成した
- [ ] data/config/code/prediction hashをrunへ結んだ
- [ ] config mutationでrun IDが変わることをtestした
- [ ] outer/production未実装範囲を隠していない

## 7. 出典
"""
            + PERFORMANCE_SOURCES
            + ENGINEERING_SOURCES
            + DATA_SOURCES
        ),
    ]


__all__ = [
    "overview_cells",
    "project_cells",
    "week37_cells",
    "week38_cells",
    "week39_cells",
    "week40_cells",
]
