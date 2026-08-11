"""Deterministic cell definitions for the six B9 notebook builders."""

from __future__ import annotations

from nbkit import code, md
from stage2_nb import setup_cell

DEEP_SOURCES = """
- [Goodfellow, Bengio, and Courville, *Deep Learning*](https://www.deeplearningbook.org/)
- [Glorot and Bengio (2010), Understanding the difficulty of training deep feedforward neural networks](https://proceedings.mlr.press/v9/glorot10a.html)
- [Kingma and Ba (2015), Adam](https://arxiv.org/abs/1412.6980)
"""

SEQUENCE_SOURCES = """
- [Hochreiter and Schmidhuber (1997), Long Short-Term Memory](https://www.bioinf.jku.at/publications/older/2604.pdf)
- [Bai, Kolter, and Koltun (2018), An Empirical Evaluation of Generic Convolutional and Recurrent Networks](https://arxiv.org/abs/1803.01271)
- [Vaswani et al. (2017), Attention Is All You Need](https://arxiv.org/abs/1706.03762)
"""

SEC_SOURCES = """
- [SEC EDGAR application programming interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC Developer Resources](https://www.sec.gov/about/developer-resources)
- [Manning, Raghavan, and Schütze, *Introduction to Information Retrieval*](https://nlp.stanford.edu/IR-book/)
"""


def _fixture_cell():
    return code("""
fixture = qt.load_sec_teaching_fixture()
train_mask = fixture.training_mask
validation_mask = fixture.validation_mask

assert train_mask.sum() == 192
assert validation_mask.sum() == 64
assert not np.any(fixture.target_available_dates >= np.datetime64("2023-10-23"))
assert set(fixture.partitions) == {"inner_train", "inner_validation"}

print("fixture rows:", fixture.targets.size)
print("inner train / validation:", int(train_mask.sum()), int(validation_mask.sum()))
print("numeric / sequence shape:", fixture.numeric_features.shape, fixture.token_hashes.shape)
print("locked outer rows present: False")
print("fixture hash lineage:", fixture.provenance)
""")


def _numeric_cell():
    return code("""
numeric_preprocessor = qt.fit_numeric_preprocessor(fixture.numeric_features, train_mask)
numeric_features = numeric_preprocessor.transform(fixture.numeric_features)
numeric_train = numeric_features[train_mask]
numeric_validation = numeric_features[validation_mask]
target_train = fixture.targets[train_mask]
target_validation = fixture.targets[validation_mask]
entity_validation = np.asarray(fixture.entity_ids)[validation_mask]

assert np.all(np.isfinite(numeric_features))
print("processed numeric shape:", numeric_features.shape)
""")


def overview_cells():
    return [
        md(r"""
# 48. B9 — Deep learning and SEC filing representations

> B9の目的はneural architectureを使うことではない。同じ情報集合・split・計算予算で、線形probeを超える表現価値があるかを反証可能に調べることである。

## 学習目標

- computational graphからreverse-mode backpropagationを導出できる
- MLP、LSTM、TCN、self-attentionのinductive biasを比較できる
- vocabulary、imputation、scalingをactive training partitionだけでfitできる
- TF–IDF＋ridgeをdeep modelより前に固定できる
- data scale、duplicate、timestamp、budgetの差をarchitecture効果と混同しない

## 前提知識

- B4のgradient auditとoptimization trace
- B5–B6のregularization、validation、shift診断
- M6のSEC point-in-time panelとB9 pre-analysis contract
"""),
        setup_cell(48),
        _fixture_cell(),
        md(r"""
## 1. Evidence chainと範囲

| Week | Core implementation | 実データlab | 主な反証 |
|---|---|---|---|
| 33 | MLP forward/backprop/Adam | numeric feature MLP | gradient不一致、linear優位 |
| 34 | LSTM/causal TCN forward | 同じhashed token sequence | unequal budget、短いeffective context |
| 35 | scaled dot-product attention | small attention probe | mask漏れ、data不足 |
| 36 | train-only TF–IDF/ridge、ablation | previous SEC filing | target text、duplicate、coverage |
| Project | frozen contract audit | SEC Assets log-change | `no_model_selected`を許す |

教材fixtureは実SEC filingとfundamentalsから作ったが、inner train 192行・inner validation 64行だけの縮約版である。raw text、CIK、accession、locked outer 413行を含まない。したがってarchitectureの仕組みと漏洩監査には使えるが、pre-registered tournamentのnominee選定には使わない。
"""),
        code("""
target_frame = pd.DataFrame(
    {
        "partition": fixture.partitions,
        "target": fixture.targets,
        "date": fixture.target_available_dates,
    }
)
summary = target_frame.groupby("partition")["target"].agg(["count", "mean", "std", "median"])
display(summary)

fig = go.Figure()
for partition in ["inner_train", "inner_validation"]:
    values = target_frame.loc[target_frame["partition"] == partition, "target"]
    fig.add_histogram(x=values, name=partition, opacity=0.6, histnorm="probability density")
fig.update_layout(
    title="Real SEC-derived teaching fixture: target shift",
    xaxis_title="Next-quarter log Assets change",
    barmode="overlay",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 2. Claim boundary

estimandはfixed-anchor feasibility cohortにおける

$$
E\!\left[\log(A_{i,t}/A_{i,t-1})\mid\mathcal I_{i,t-1}\right]
$$

の予測である。filing languageの因果効果、abnormal return、取引収益、全米issuerへの代表性は主張しない。fixtureは本文でなくmany-to-one token bucketだけを保持するが、dictionary attackに対するprivacy保証ではない。正式candidateの512-token chunk契約も置き換えない。

## 3. 失敗モード

- target accessionの文書をfeatureへ入れる
- outer結果を見てarchitecture、seed、thresholdを変更する
- vocabularyやstandardizationをvalidation込みでfitする
- parameter数、epoch、run数が違うmodelを「同じ予算」と呼ぶ
- pretrained modelの一般知識を無料の情報とみなす
- deep modelを採用しない結論を失敗扱いする

## 4. 段階別演習

### 基礎

1. fixtureとfull pre-analysis datasetの違いを5項目書け。
2. `known_at`より後に利用可能なtarget historyを使えない理由を説明せよ。

### 標準

3. data、information set、parameter budget、metricを揃えたcomparison tableを作れ。
4. text-only / numeric-only / joint ablationが回答する問いを分けよ。

### 研究

5. pretrained encoderをAdvancedへ追加する際のdependency、license、compute、leakage監査を書け。

## 5. Exit Criteria

- [ ] 教材fixtureをcandidate tournamentと呼んでいない
- [ ] outer testを一度も読んでいない
- [ ] linear baselineをneural modelより先に置いた
- [ ] architecture効果とdata/budget差を分離した
- [ ] `no_model_selected`を有効な結論にした

## 6. 出典

"""
            + DEEP_SOURCES
            + SEQUENCE_SOURCES
            + SEC_SOURCES
        ),
    ]


def week33_cells():
    return [
        md(r"""
# 49. Week 33 — MLP, backpropagation, initialization, and Adam

## 学習目標

- affine–tanh–affine graphのforward passを式とcodeで対応付ける
- chain ruleから全parameter gradientを導出する
- centered finite differenceでbackpropを監査する
- initialization、regularization、early stoppingを比較する

## 前提知識

- multivariable calculus、matrix multiplication
- B4のfinite-difference audit
- B9のdevelopment-only fixture contract
"""),
        setup_cell(49),
        _fixture_cell(),
        _numeric_cell(),
        md(r"""
## 1. Computational graph

one-hidden-layer regressorを

$$
Z=XW_1+b_1,\qquad H=\tanh Z,\qquad \hat y=Hw_2+b_2,
$$

$$
L=\frac{1}{2n}\lVert\hat y-y\rVert_2^2
$$

とする。reverse modeでは出力からadjointを逆伝播する。

$$
\bar{\hat y}=\frac{\hat y-y}{n},\quad
\bar w_2=H^\top\bar{\hat y},\quad
\bar Z=(\bar{\hat y}w_2^\top)\odot(1-H^2),\quad
\bar W_1=X^\top\bar Z.
$$
"""),
        code("""
audit_rng = task_rng(1)
audit_features = numeric_train[:6, :3]
audit_target = target_train[:6]
audit_parameters = qt.initialize_mlp(3, 4, rng=audit_rng)
gradient_audit = qt.check_mlp_gradients(
    audit_parameters, audit_features, audit_target, step=1e-6, tolerance=2e-5
)
assert gradient_audit.passed
print("maximum relative gradient error:", gradient_audit.maximum_relative_error)

fig = go.Figure()
fig.add_scatter(
    x=gradient_audit.numerical,
    y=gradient_audit.analytic,
    mode="markers",
    name="parameters",
)
low = float(min(gradient_audit.numerical.min(), gradient_audit.analytic.min()))
high = float(max(gradient_audit.numerical.max(), gradient_audit.analytic.max()))
fig.add_scatter(x=[low, high], y=[low, high], mode="lines", name="identity")
fig.update_layout(
    title="Backpropagation audit",
    xaxis_title="Centered finite difference",
    yaxis_title="Analytic gradient",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Initializationとtraining trace

Xavier scaleはfan-in/fan-outに応じてactivation varianceの崩壊・爆発を抑える。Adamはgradientの一次・二次momentを追跡するが、optimizer名だけで収束や一般化は保証しない。validationはparameter更新に使わずearly-stopping epochの選択だけに使う。
"""),
        code("""
mlp_result = qt.train_mlp(
    numeric_train,
    target_train,
    numeric_validation,
    target_validation,
    hidden_width=16,
    learning_rate=0.003,
    epochs=200,
    patience=20,
    l2=1e-4,
    rng=task_rng(2),
)
mlp_validation = qt.mlp_predict(mlp_result.parameters, numeric_validation)
zero_validation = np.zeros_like(target_validation)
metrics = pd.DataFrame(
    [
        {"model": "zero", **qt.regression_error_table(target_validation, zero_validation, entity_validation)},
        {"model": "numeric_mlp", **qt.regression_error_table(target_validation, mlp_validation, entity_validation)},
    ]
)
display(metrics)

fig = go.Figure()
fig.add_scatter(y=mlp_result.training_losses, mode="lines", name="training loss")
fig.add_scatter(y=mlp_result.validation_losses, mode="lines", name="validation loss")
fig.add_vline(x=mlp_result.best_epoch, line_dash="dash")
fig.update_layout(
    title="Full-batch Adam trace",
    xaxis_title="Epoch",
    yaxis_title="Half MSE",
    yaxis_type="log",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 3. 失敗モード

- gradient checkを1 parameterだけで済ませる
- objective scaleが小さいだけでconvergedと判定する
- validationをgradient updateへ混ぜる
- best epochをouter testから選ぶ
- initialization seedを変えた1回の改善をarchitecture効果と呼ぶ

## 4. 段階別演習

### 基礎

1. output biasのgradientを導出せよ。
2. tanh derivativeをcodeと式で照合せよ。

### 標準

3. ReLUへ変更しdead-unit割合を記録せよ。
4. hidden width 16/32、seed 3本を同じ200 epoch上限で比較せよ。

### 研究

5. Adamとfull-batch gradient descentをruntime、best epoch、validation MAEで比較せよ。

## 5. Exit Criteria

- [ ] forward graphとreverse graphを対応付けた
- [ ] 全parameterのcentered finite-difference auditを通した
- [ ] initialization、seed、regularizationを記録した
- [ ] trainingとvalidation traceを分けた
- [ ] fixture結果をcandidate nominationに使っていない

## 6. 出典

"""
            + DEEP_SOURCES
        ),
    ]


def week34_cells():
    return [
        md(r"""
# 50. Week 34 — Sequence models: LSTM and causal TCN

## 学習目標

- recurrent stateとcausal convolutionの情報経路を比較できる
- LSTMのfour gatesとcell updateを書ける
- TCNのreceptive fieldをkernel/dilationから計算できる
- 同じtoken sequence・width・linear probeでrepresentationを比較できる

## 前提知識

- Week 33のcomputational graph
- convolutionとrecurrenceの基本
- previous-filing-only text contract
"""),
        setup_cell(50),
        _fixture_cell(),
        md(r"""
## 1. LSTMとTCN

LSTM cellは

$$
f_t=\sigma(W_fx_t+U_fh_{t-1}+b_f),\quad
i_t=\sigma(W_ix_t+U_ih_{t-1}+b_i),
$$

$$
c_t=f_t\odot c_{t-1}+i_t\odot\tanh(W_cx_t+U_ch_{t-1}+b_c),
\quad h_t=o_t\odot\tanh c_t.
$$

TCNはcausal paddingにより時点 (t) の出力が (x_{1:t}) だけに依存する。kernel幅 (k)、layer数 (L)、dilation (d_l) ならreceptive fieldは (1+(k-1)\sum_l d_l) である。
"""),
        code("""
bptt_rng = task_rng(1)
bptt_embeddings = bptt_rng.normal(size=(3, 4, 2))
bptt_target = bptt_rng.normal(size=3)
bptt_parameters = qt.initialize_lstm(2, 2, rng=bptt_rng)
bptt_audit = qt.check_lstm_gradients(
    bptt_parameters,
    bptt_embeddings,
    bptt_target,
    step=1e-6,
    tolerance=5e-5,
)
assert bptt_audit.passed
print("BPTT maximum relative gradient error:", bptt_audit.maximum_relative_error)
"""),
        code("""
embedding_width = 8
representation_width = 12
embeddings = qt.token_embedding(fixture.token_hashes, embedding_width, seed=20260811)
architecture_rng = task_rng(2)

lstm_input = architecture_rng.normal(
    scale=1.0 / np.sqrt(embedding_width), size=(embedding_width, 4 * representation_width)
)
lstm_recurrent = architecture_rng.normal(
    scale=1.0 / np.sqrt(representation_width),
    size=(representation_width, 4 * representation_width),
)
lstm_bias = np.zeros(4 * representation_width)
lstm_representation = qt.lstm_encode(embeddings, lstm_input, lstm_recurrent, lstm_bias)

tcn_kernels = architecture_rng.normal(
    scale=1.0 / np.sqrt(3 * embedding_width),
    size=(3, embedding_width, representation_width),
)
tcn_representation = qt.temporal_convolution_encode(
    embeddings, tcn_kernels, np.zeros(representation_width)
)
mean_representation = embeddings.mean(axis=1)

assert lstm_representation.shape == (fixture.targets.size, representation_width)
assert tcn_representation.shape == (fixture.targets.size, representation_width)
print("effective sequence length:", fixture.token_hashes.shape[1])
print("single-layer TCN receptive field:", 3)
"""),
        md(r"""
## 2. Frozen representation probe

ここではBPTT candidateを学習したと主張しない。forward recurrence/convolutionを透明に確認した後、同じridge probeを各固定representationへ当て、data scaleに対してarchitecture差を判断する準備をする。正式candidateはpre-registered run/epoch/parameter budgetでend-to-end学習する。
"""),
        code("""
representations = {
    "mean_embedding": mean_representation,
    "random_lstm": lstm_representation,
    "random_tcn": tcn_representation,
}
probe_rows = []
probe_predictions = {}
for name, representation in representations.items():
    probe = qt.fit_sparse_ridge(
        representation[train_mask], fixture.targets[train_mask], ridge=1.0
    )
    prediction = probe.predict(representation[validation_mask])
    probe_predictions[name] = prediction
    probe_rows.append(
        {
            "representation": name,
            "width": representation.shape[1],
            **qt.regression_error_table(
                fixture.targets[validation_mask],
                prediction,
                np.asarray(fixture.entity_ids)[validation_mask],
            ),
        }
    )
probe_table = pd.DataFrame(probe_rows)
display(probe_table)

fig = go.Figure()
for name, prediction in probe_predictions.items():
    fig.add_scatter(
        x=fixture.targets[validation_mask],
        y=prediction,
        mode="markers",
        name=name,
    )
fig.update_layout(
    title="Same-data frozen representation probes",
    xaxis_title="Observed target",
    yaxis_title="Probe prediction",
    template="plotly_white",
)
fig.show()
"""),
        md(
            r"""
## 3. 失敗モード

- bidirectional contextやtarget filingをprevious-filing featureへ混ぜる
- causal paddingなしのconvolutionをforecast modelと呼ぶ
- LSTM/TCNでtokenization、sequence length、probeを変える
- frozen random featureの結果をtrained architectureの結果と呼ぶ
- BPTTのtruncation lengthを隠す

## 4. 段階別演習

### 基礎

1. forget gateが1、input gateが0のcell updateを説明せよ。
2. kernel 5、dilation 1/2/4のreceptive fieldを求めよ。

### 標準

3. sequence後半だけを変え、causal TCNの過去出力が不変なtestを書け。
4. 同じparameter budgetでLSTM widthとTCN channel widthを決めよ。

### 研究

5. chunk平均がdocument順序情報をどこで失うか監査せよ。

## 5. Exit Criteria

- [ ] LSTM four gatesを実装した
- [ ] TCNのcausal contractをtestした
- [ ] sequence、width、probe budgetを揃えた
- [ ] frozen probeとend-to-end candidateを区別した
- [ ] effective contextとdocument lengthを報告した

## 6. 出典

"""
            + SEQUENCE_SOURCES
        ),
    ]


def week35_cells():
    return [
        md(r"""
# 51. Week 35 — Self-attention, masks, and transformer boundaries

## 学習目標

- scaled dot-product attentionを行列で実装できる
- row-stochastic weightとcausal maskを監査できる
- positional informationが必要な理由を反例で示せる
- pretrained/fine-tuned modelをCoreのsmall attentionと区別できる

## 前提知識

- matrix calculus、softmax
- Week 34のsequence representation
- training-only vocabulary contract
"""),
        setup_cell(51),
        _fixture_cell(),
        md(r"""
## 1. Scaled dot-product attention

$$
Q=XW_Q,\qquad K=XW_K,\qquad V=XW_V,
$$

$$
\operatorname{Attention}(X)=
\operatorname{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}+M\right)V.
$$

mask (M) は許可しない位置へ (-\infty) を置く。softmaxは各query rowで和1にならなければならない。SEC previous filingのdocument-level regressionでは必ずしもcausal maskが必要ではないが、autoregressive説明と混同しないため両方を実装する。
"""),
        code("""
toy_embeddings = np.array(
    [
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ]
    ]
)
identity = np.eye(4)
toy_output, toy_weights = qt.self_attention(
    toy_embeddings, identity, identity, identity, causal=True
)
assert np.allclose(toy_weights.sum(axis=-1), 1.0)
assert np.allclose(np.triu(toy_weights[0], k=1), 0.0)

fig = go.Figure(
    data=go.Heatmap(z=toy_weights[0], colorscale="Blues", zmin=0.0, zmax=1.0)
)
fig.update_layout(
    title="Causal attention audit",
    xaxis_title="Key position",
    yaxis_title="Query position",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Positionとsmall attention probe

self-attention単体はtoken permutationに対してequivariantである。位置を識別するにはpositional encodingを加える。ここでは幅8の固定embeddingにsin/cos positionを加え、single-head forward representationを平均poolしてridge probeへ渡す。これはpretrained transformerでも正式candidateでもない。
"""),
        code("""
width = 8
embedded = qt.token_embedding(fixture.token_hashes, width, seed=20260811)
positions = np.arange(embedded.shape[1])[:, None]
frequencies = np.exp(-np.arange(0, width, 2) * np.log(10000.0) / width)
position_encoding = np.zeros((embedded.shape[1], width))
position_encoding[:, 0::2] = np.sin(positions * frequencies)
position_encoding[:, 1::2] = np.cos(positions * frequencies)
positioned = embedded + position_encoding[None, :, :]

attention_rng = task_rng(1)
query_weights = attention_rng.normal(scale=1.0 / np.sqrt(width), size=(width, width))
key_weights = attention_rng.normal(scale=1.0 / np.sqrt(width), size=(width, width))
value_weights = attention_rng.normal(scale=1.0 / np.sqrt(width), size=(width, width))
attention_output, attention_weights = qt.self_attention(
    positioned, query_weights, key_weights, value_weights, causal=False
)
attention_representation = attention_output.mean(axis=1)
attention_probe = qt.fit_sparse_ridge(
    attention_representation[train_mask], fixture.targets[train_mask], ridge=1.0
)
attention_prediction = attention_probe.predict(attention_representation[validation_mask])
attention_metrics = qt.regression_error_table(
    fixture.targets[validation_mask],
    attention_prediction,
    np.asarray(fixture.entity_ids)[validation_mask],
)
display(pd.DataFrame([{"model": "random_small_attention_probe", **attention_metrics}]))

mean_entropy = -np.mean(
    np.sum(attention_weights * np.log(np.maximum(attention_weights, 1e-15)), axis=-1)
)
print("mean attention entropy:", mean_entropy)
print("trainable parameters in this frozen probe: 0")
"""),
        md(
            r"""
## 3. Transformerとfoundation modelの境界

multi-head attentionはheadごとに異なるprojection subspaceを持つ。transformer blockはattentionだけでなくresidual connection、normalization、position-wise feed-forward networkを含む。pretraining、tokenizer、retrieval corpus、fine-tuningを省いたsingle-head NumPy実装を「foundation model」と呼ばない。

## 4. 失敗モード

- (1/\sqrt{d_k}) scalingを省きsoftmaxを飽和させる
- mask後にfuture weightがexact zeroか検査しない
- positionなしでtoken順序を学習したと主張する
- attention weightを因果的説明・feature importanceと呼ぶ
- pretrained modelのtraining corpus leakageを監査しない

## 5. 段階別演習

### 基礎

1. 各attention rowの和が1になる理由を説明せよ。
2. causal maskの上三角がzeroになるtestを書け。

### 標準

3. 2-head attentionを実装しparameter数を数えよ。
4. position encodingの有無でpermutation反例を作れ。

### 研究

5. pretrained encoder追加時のcorpus cutoff、license、carbon/compute budgetをmanifest化せよ。

## 6. Exit Criteria

- [ ] scaled dot-product attentionを実装した
- [ ] row sumとmaskをassertした
- [ ] positionの必要性を説明した
- [ ] attention weightを因果説明と呼んでいない
- [ ] small attentionとfoundation modelを区別した

## 7. 出典

"""
            + SEQUENCE_SOURCES
        ),
    ]


def week36_cells():
    return [
        md(r"""
# 52. Week 36 — Financial NLP, TF–IDF, and modality ablation

## 学習目標

- previous accessionだけを使うtext information setを監査できる
- training-only vocabulary/IDFでTF–IDFを作れる
- numeric-only、text-only、jointを同じvalidationで比較できる
- duplicate、coverage、document length、regime shiftをmetricと分けて報告できる

## 前提知識

- B5のridgeとvalidation
- Week 33–35のrepresentation
- SEC filing retrieval gate
"""),
        setup_cell(52),
        _fixture_cell(),
        _numeric_cell(),
        md(r"""
## 1. TF–IDF baseline

term (j)、document (i) についてsublinear TFとsmoothed IDFを

$$
\operatorname{tf}_{ij}=1+\log c_{ij},\qquad
\operatorname{idf}_{j}=\log\frac{1+n_{\mathrm{train}}}{1+\operatorname{df}_{j}}+1
$$

とし、document rowをL2 normalizeする。vocabulary rankingと (\operatorname{df}) はinner trainだけでfitする。fixtureのmany-to-one token bucketは本文を含まないがprivacy mechanismではなく、正式candidateの5,000/10,000語TF–IDFも代替しない。
"""),
        code("""
tfidf_model = qt.fit_hashed_tfidf(
    fixture.token_hashes,
    train_mask,
    maximum_features=256,
    minimum_document_frequency=2,
)
tfidf = tfidf_model.transform(fixture.token_hashes)
assert tfidf.shape[0] == fixture.targets.size
assert np.all(np.isfinite(tfidf.data))

from scipy import sparse

numeric_ridge = qt.fit_sparse_ridge(numeric_train, target_train, ridge=1.0)
text_ridge = qt.fit_sparse_ridge(tfidf[train_mask], target_train, ridge=1.0)
joint_train = sparse.hstack([numeric_train, tfidf[train_mask]], format="csr")
joint_validation = sparse.hstack(
    [numeric_validation, tfidf[validation_mask]], format="csr"
)
joint_ridge = qt.fit_sparse_ridge(joint_train, target_train, ridge=1.0)

predictions = {
    "zero": np.zeros_like(target_validation),
    "numeric_ridge": numeric_ridge.predict(numeric_validation),
    "hashed_tfidf_ridge": text_ridge.predict(tfidf[validation_mask]),
    "joint_ridge": joint_ridge.predict(joint_validation),
}
metric_rows = [
    {"model": name, **qt.regression_error_table(target_validation, prediction, entity_validation)}
    for name, prediction in predictions.items()
]
metric_table = pd.DataFrame(metric_rows).sort_values("mae")
display(metric_table)

fig = go.Figure()
fig.add_bar(x=metric_table["model"], y=metric_table["mae"], name="row MAE")
fig.add_bar(
    x=metric_table["model"], y=metric_table["company_macro_mae"], name="company macro MAE"
)
fig.update_layout(
    title="Development-only modality ablation",
    yaxis_title="Absolute log-change error",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 2. Data-quality auditとmultimodal boundary

full retrieval gateは4,631 / 4,631 previous documents、empty 0、exact duplicate family 0、target accession leakage 0で通過した。教材fixtureは256 document hashがuniqueで、outer rowを含まない。raw/normalized SEC textとcontact-bearing User-Agentはrepository外に置く。

multimodal joint modelの改善がtext情報によるとは限らない。numeric scaling、text vocabulary、model capacity、regularization、company/date compositionを固定し、text-only / numeric-only / jointを同じrowで比較する。
"""),
        code("""
quality_rows = pd.DataFrame(
    [
        {"check": "fixture row ids unique", "value": len(set(fixture.row_ids)), "expected": 256},
        {"check": "document hashes unique", "value": len(set(fixture.document_sha256)), "expected": 256},
        {"check": "outer rows", "value": int(np.sum(fixture.target_available_dates >= np.datetime64("2023-10-23"))), "expected": 0},
        {"check": "TF-IDF vocabulary", "value": tfidf_model.vocabulary.size, "expected": "train fitted"},
    ]
)
display(quality_rows)
assert quality_rows.loc[0, "value"] == quality_rows.loc[0, "expected"]
assert quality_rows.loc[1, "value"] == quality_rows.loc[1, "expected"]
assert quality_rows.loc[2, "value"] == 0
"""),
        md(
            r"""
## 3. 失敗モード

- full corpusでvocabulary/IDFをfitする
- target accessionまたはamended future filingをfeatureへ混ぜる
- exact duplicateをcompany/time splitの両側へ置く
- missing documentをzero vectorへ黙って変換する
- TF–IDF baselineより悪いdeep modelをarchitecture名だけで採用する
- calibration intervalを同じvalidationで何度も調整する

## 4. 段階別演習

### 基礎

1. validation-only tokenがvocabularyに入らないtestを書け。
2. text coverageの分母をpanel rowで定義せよ。

### 標準

3. numeric/text/jointのparameter数とmatrix bytesを報告せよ。
4. company-macro MAEがrow MAEと異なる例を作れ。

### 研究

5. near-duplicate familyをMinHash等で監査するpre-fit protocolを書け。

## 5. Exit Criteria

- [ ] vocabulary/IDFをtrainingだけでfitした
- [ ] numeric/text/jointを同じrowで比較した
- [ ] row MAEとcompany-macro MAEを併記した
- [ ] duplicate、coverage、timestampをmodel metricから分けた
- [ ] raw textとcontact情報をrepositoryへ入れていない

## 6. 出典

"""
            + SEC_SOURCES
        ),
    ]


def project_cells():
    return [
        md(r"""
# 53. B9 Project — SEC Filing Text & Fundamentals Forecast

> 最終成果物は「deep model」ではなく、data gate、feature lineage、baseline ladder、gradient audit、budget、nomination ruleを一つの再実行可能なevidence chainにしたもの。

## 学習目標

- pre-analysis contractをcode assertionへ変換できる
- linear baselineとNumPy MLPをdevelopment-only dataで再現できる
- point metricとcompany aggregationを分離できる
- outer access前にnominee manifestへ固定すべき項目を列挙できる
- evidence不足なら`no_model_selected`で停止できる

## 前提知識

- Week 33–36のbackprop、sequence、attention、TF–IDF
- M6 SEC data gate
- B5–B6のmodel selectionとuncertainty gate
"""),
        setup_cell(53),
        _fixture_cell(),
        _numeric_cell(),
        md(r"""
## 1. Frozen Project contract

| 項目 | 固定値 |
|---|---|
| target | next-quarter log Assets change |
| prediction time | previous filing availability (`known_at`) |
| inner train / validation | date cutoff 2021-01-01、company rule維持 |
| locked outer | 2023-10-23以降かつ`cik % 3 == 0` |
| primary / secondary | MAE / median absolute error |
| fixed baseline ladder | zero、pooled drift、seasonal、company mean |
| primary comparator | inner-validation MAE最小baselineを固定tie-breakで選び、outer前にfreeze |
| neural comparator | TF–IDF ridge |
| budget | 12 runs/family、200 epochs/run、100k parameters以下 |
| failure result | `no_model_selected` |

このNotebookは256行教材fixtureだけを使う。candidate教材実装はcompact inner train 192行でfitする一方、fixed baseline predictionは正式規約どおりfull 1,504-row inner training partitionだけから事前計算している。したがって同じ64-row validation上のbaseline ladder規約は検証できるが、candidateとの順位は公平なfull-data tournamentではない。full 2,195-row development search、nominee manifest、company-cluster bootstrapが未実行なのでouterは開かない。
"""),
        code("""
tfidf_model = qt.fit_hashed_tfidf(
    fixture.token_hashes, train_mask, maximum_features=256, minimum_document_frequency=2
)
tfidf = tfidf_model.transform(fixture.token_hashes)
numeric_ridge = qt.fit_sparse_ridge(numeric_train, target_train, ridge=1.0)
text_ridge = qt.fit_sparse_ridge(tfidf[train_mask], target_train, ridge=1.0)
mlp = qt.train_mlp(
    numeric_train,
    target_train,
    numeric_validation,
    target_validation,
    hidden_width=16,
    learning_rate=0.003,
    epochs=200,
    patience=20,
    l2=1e-4,
    rng=task_rng(1),
)

fixed_baseline_names = ["zero", "pooled_drift", "seasonal", "company_mean"]
project_predictions = {
    name: fixture.baseline_predictions[name][validation_mask]
    for name in fixed_baseline_names
}
project_predictions.update({
    "numeric_ridge": numeric_ridge.predict(numeric_validation),
    "hashed_tfidf_ridge": text_ridge.predict(tfidf[validation_mask]),
    "numeric_mlp": qt.mlp_predict(mlp.parameters, numeric_validation),
})
project_metrics = pd.DataFrame(
    [
        {"model": name, **qt.regression_error_table(target_validation, prediction, entity_validation)}
        for name, prediction in project_predictions.items()
    ]
).sort_values(["mae", "median_absolute_error"])
display(project_metrics)

baseline_metrics = (
    project_metrics.set_index("model").loc[fixed_baseline_names].reset_index()
)
tie_break = {name: index for index, name in enumerate(fixed_baseline_names)}
primary_baseline = min(
    fixed_baseline_names,
    key=lambda name: (
        float(baseline_metrics.loc[baseline_metrics["model"] == name, "mae"].iloc[0]),
        tie_break[name],
    ),
)
baseline_minima = {
    metric: float(baseline_metrics[metric].min())
    for metric in ("mae", "median_absolute_error", "company_macro_mae")
}
print("teaching-fixture primary baseline:", primary_baseline)
print("metric-wise fixed-baseline minima:", baseline_minima)
assert set(baseline_metrics["model"]) == set(fixed_baseline_names)
"""),
        md(r"""
## 2. Evidence gate

教材fixtureでもfixed baseline 4本を省略しない。ただし64-row validationの順位を正式nominee選定へ転用しない。full inner validationでは、MAEをfixed baseline中の最小値から1%以上改善し、medAEとcompany-macro MAEも各metricのbaseline最小値を悪化させないことを要求する。MAE最小baselineは固定tie-breakで選び、nominee manifestと一緒にouter前にfreezeする。outerのpaired intervalはそのfrozen baselineだけを比較対象とし、outer outcomeから再選択しない。neural valueの追加主張にはTF–IDF ridgeに対する同じpoint/uncertainty gateも必要である。

この規約はteaching fixtureでzeroがpooled driftより強いと確認した後、full candidate search・nominee freeze・outer accessより前にamendmentとして記録した。元のcontract hash、観測済み情報、変更理由をcontractの \`amendments\` へ残しており、事前登録を黙って書き換えてはいない。
"""),
        code("""
gate = pd.DataFrame(
    [
        {"artifact": "M6 panel integrity", "status": "passed"},
        {"artifact": "filing retrieval and text gate", "status": "passed"},
        {"artifact": "development-only teaching fixture", "status": "passed"},
        {"artifact": "full 2,195-row candidate search", "status": "not run"},
        {"artifact": "company-cluster paired bootstrap", "status": "not run"},
        {"artifact": "nominee manifest", "status": "not frozen"},
        {"artifact": "locked outer evaluation", "status": "unopened"},
    ]
)
modeling_decision = "no_model_selected"
assert modeling_decision == "no_model_selected"
assert gate.loc[gate["artifact"] == "locked outer evaluation", "status"].item() == "unopened"
display(gate)
print("current decision:", modeling_decision)

fig = go.Figure()
fig.add_bar(x=project_metrics["model"], y=project_metrics["mae"], name="MAE")
fig.add_bar(
    x=project_metrics["model"],
    y=project_metrics["company_macro_mae"],
    name="company macro MAE",
)
fig.update_layout(
    title="Teaching-fixture diagnostics, not nominee selection",
    yaxis_title="Absolute log-change error",
    barmode="group",
    template="plotly_white",
)
fig.show()
"""),
        md(r"""
## 3. Deliverable checklist

正式nominee manifestには少なくとも次を固定する。

- source panel / filing sidecar / raw / normalized manifest SHA
- feature code commit、vocabulary/IDF hash、numeric scaler/imputer
- family、hyperparameters、root seedとseed offset
- parameter count、epochs、early-stopping rule、runtime environment
- inner-validation prediction hashとmetric table
- overall nominee / neural nomineeまたは`no_model_selected`
- outer access timestampと「一度だけ」の監査記録

## 4. 失敗モード

- 教材fixtureの64-row validationでnomineeを決める
- outerを見てfeature/modelを追加する
- best seedだけを報告する
- parameter budgetを超えたmodelを同じtournamentへ入れる
- row MAEだけでcompany concentrationを隠す
- neural gainが不明でもdeep-learning成功と書く

## 5. 段階別演習

### 基礎

1. Project gateの未完了artifactを列挙せよ。
2. `no_model_selected`が妥当な結論になる条件を書け。

### 標準

3. nominee manifest JSON schemaを設計せよ。
4. company-cluster paired bootstrapのresampling unitを実装せよ。

### 研究

5. outer一回評価後に許される分析と禁止するretuningをpre-commitせよ。

## 6. Exit Criteria

- [ ] SEC data/text integrity gateを通した
- [ ] full development searchと教材fixtureを区別した
- [ ] numeric/TF–IDF baselineを先に固定した
- [ ] gradient、budget、runtime、prediction hashを監査した
- [ ] outer前にnomineeまたは`no_model_selected`を凍結した
- [ ] causal/trading/representative claimをしていない

## 7. 出典

"""),
        md(DEEP_SOURCES + SEQUENCE_SOURCES + SEC_SOURCES),
    ]


__all__ = [
    "overview_cells",
    "project_cells",
    "week33_cells",
    "week34_cells",
    "week35_cells",
    "week36_cells",
]
