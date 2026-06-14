"""Builder for notebook 13 (appendix) — Imbalanced Learning."""

from nbkit import build, code, md

cells = [
    md(r"""
# 13. 付録: 不均衡データの学習

> 各章は **直感 → 最小限の数式 → scikit-learn 実装 → 可視化 → 実験 → 演習** の順。本文は日本語、コードは英語。

## この章で分かること

- なぜ不均衡データで普通の学習が **多数派に偏る** のか
- **クラス重み (class_weight)** で損失を釣り合わせる方法
- **リサンプリング**(オーバーサンプル / アンダーサンプル / SMOTE)と、その **正しい当て方(訓練のみ)**
- 不均衡向けの **評価指標**(PR-AUC・balanced accuracy・recall@precision)
- リサンプリングが **確率の較正を壊す** こと(確率が要るなら class_weight 推奨)

> 04 章「評価」の続編。評価で問題を見たら、ここで対処する。
"""),
    code("""
import numpy as np
import matplotlib.pyplot as plt
import plotly.io as pio
import plotly.graph_objects as go
pio.renderers.default = "plotly_mimetype+notebook_connected"

from ml_textbook import datasets, plotting, metrics
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

RANDOM_SEED = 0
np.random.seed(RANDOM_SEED)

# Severe imbalance (2% positives) AND overlapping classes (class_sep=0.6), so a
# default-threshold model genuinely misses most positives.
X, y = datasets.make_imbalanced_classification_dataset(
    n=5000, weights=(0.98, 0.02), class_sep=0.6, seed=0
)
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0, stratify=y)
print(f"positives: train {ytr.mean():.3f}, test {yte.mean():.3f}")
"""),
    md(r"""
## 1. 問題 — 既定の学習は少数派を無視する

損失は件数で決まるので、98% の多数派に最適化すれば「ほぼ全部陰性」と答えるのが楽です。
accuracy は高くても **recall(陽性の取りこぼし)** が悪くなります。
"""),
    code("""
base = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xtr, ytr)
pred = base.predict(Xte)
print(f"accuracy : {metrics.accuracy(yte, pred):.3f}  (always-negative = {1 - yte.mean():.3f})")
print(f"precision: {metrics.precision(yte, pred):.3f}")
print(f"recall   : {metrics.recall(yte, pred):.3f}   <- many positives missed")
"""),
    md(r"""
## 2. クラス重み — 損失で少数派を重く扱う

`class_weight="balanced"` は、各クラスの損失を **出現頻度の逆数** で重み付けします。
データを増やさずに少数派の取りこぼしを罰せるので、まず試すべき手です。
"""),
    code("""
weighted = make_pipeline(
    StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")
).fit(Xtr, ytr)
pred_w = weighted.predict(Xte)
print("class_weight='balanced':")
print(f"  precision {metrics.precision(yte, pred_w):.3f}  recall {metrics.recall(yte, pred_w):.3f}  f1 {metrics.f1_score(yte, pred_w):.3f}")
print(f"  recall jumped from {metrics.recall(yte, pred):.3f} to {metrics.recall(yte, pred_w):.3f} (precision traded off)")
"""),
    md(r"""
## 3. リサンプリング — データ側で釣り合わせる

- **オーバーサンプリング**: 少数派を複製して増やす(情報は増えないが損失は釣り合う)
- **アンダーサンプリング**: 多数派を間引く(速いが情報を捨てる)
- **SMOTE**: 少数派の近傍を補間して合成サンプルを作る(任意依存 `imbalanced-learn`)

**最重要の鉄則: リサンプリングは訓練データだけに行う。** テストや検証に混ぜるとリーク。
交差検証では `imbalanced-learn` の `Pipeline`(fold ごとに訓練側だけ resample)を使う。
"""),
    code("""
def oversample_to_ratio(X, y, ratio, seed=0):
    \"\"\"Duplicate the minority (class 1) until minority/majority == ratio. Train only.\"\"\"
    rng = np.random.default_rng(seed)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    target = int(ratio * len(neg))
    if target <= len(pos):
        keep = rng.choice(pos, size=max(target, 1), replace=False)
        idx = np.concatenate([neg, keep])
    else:
        extra = rng.choice(pos, size=target - len(pos), replace=True)
        idx = np.concatenate([neg, pos, extra])
    rng.shuffle(idx)
    return X[idx], y[idx]

# Oversample TRAIN only to a 1:1 balance, evaluate on the untouched test set.
Xtr_bal, ytr_bal = oversample_to_ratio(Xtr, ytr, ratio=1.0, seed=0)
over = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xtr_bal, ytr_bal)
pred_o = over.predict(Xte)
print(f"train balance after oversample: {ytr_bal.mean():.2f}")
print(f"oversampled: precision {metrics.precision(yte, pred_o):.3f}  recall {metrics.recall(yte, pred_o):.3f}")
"""),
    code("""
# SMOTE if imbalanced-learn is installed; otherwise skip with a note.
try:
    from imblearn.over_sampling import SMOTE
    Xs, ys = SMOTE(random_state=0).fit_resample(Xtr, ytr)
    sm = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xs, ys)
    ps = sm.predict(Xte)
    print(f"SMOTE: precision {metrics.precision(yte, ps):.3f}  recall {metrics.recall(yte, ps):.3f}")
except Exception as e:
    print("imbalanced-learn not installed — skipping SMOTE (pip install imbalanced-learn).", type(e).__name__)
    print("Concept: SMOTE interpolates between nearby minority points to synthesize new ones.")
"""),
    md(r"""
### インタラクティブ: オーバーサンプリング比率

少数派を増やす比率(少数派/多数派)を上げると **recall が上がり precision が下がる** 典型のトレードオフが見えます
(PR-AUC は閾値非依存なのでほぼ一定 — リサンプリングは「閾値の位置」を動かしているだけ、という気づき)。静的 HTML 可。
"""),
    code("""
ratios = [ytr.mean() / (1 - ytr.mean()), 0.1, 0.25, 0.5, 1.0]
names = ["precision", "recall", "f1", "PR-AUC"]
frames = []
for r in ratios:
    Xb, yb = oversample_to_ratio(Xtr, ytr, ratio=r, seed=0)
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(Xb, yb)
    pr = m.predict(Xte); sc = m.predict_proba(Xte)[:, 1]
    vals = [metrics.precision(yte, pr), metrics.recall(yte, pr), metrics.f1_score(yte, pr), metrics.pr_auc(yte, sc)]
    frames.append(go.Frame(name=f"{r:.2f}",
                           data=[go.Bar(x=names, y=vals, marker_color=["#1f77b4", "#d62728", "#2ca02c", "#9467bd"])],
                           layout={"title": f"minority:majority = {r:.2f}"}))
fig = go.Figure(data=frames[0].data, frames=frames)
steps = [{"args": [[f.name], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}],
          "label": f.name, "method": "animate"} for f in frames]
fig.update_layout(sliders=[{"steps": steps, "currentvalue": {"prefix": "ratio = "}}],
                  title=frames[0].layout.title.text, yaxis={"range": [0, 1.05], "title": "score"},
                  width=660, height=460, margin={"l": 50, "r": 20, "t": 60, "b": 40})
fig.show()
"""),
    md(r"""
## 4. 不均衡向けの評価指標

accuracy は使わない。代わりに:

- **PR-AUC (Average Precision)**: 閾値非依存・少数派重視。手法比較の主役。
- **balanced accuracy**: クラスごとの recall の平均(=各クラスを等価に評価)。
- **recall @ precision**: 「precision を X% 以上に保ったまでの recall」など、運用要件に直結。
"""),
    code("""
from sklearn.metrics import balanced_accuracy_score

print(f"{'model':24s} {'bal_acc':>8s} {'recall':>8s} {'PR-AUC':>8s}")
for name, model in [("baseline", base), ("class_weight", weighted), ("oversample", over)]:
    p = model.predict(Xte); s = model.predict_proba(Xte)[:, 1]
    print(f"{name:24s} {balanced_accuracy_score(yte, p):8.3f} {metrics.recall(yte, p):8.3f} {metrics.pr_auc(yte, s):8.3f}")
print("\\nPR-AUC barely moves: resampling/weighting mainly shift the operating point, not the ranking.")
"""),
    md(r"""
## 5. 落とし穴 — リサンプリングは確率の較正を壊す

オーバーサンプリングで陽性割合を人工的に上げると、モデルの出力確率は **実際の陽性率より高く** 偏ります。
意思決定に **確率** を使うなら、(a) `class_weight` を使う、(b) リサンプリング後に `CalibratedClassifierCV` で再較正する、のどちらか。
"""),
    code("""
print(f"true test positive rate : {yte.mean():.3f}")
print(f"mean predicted prob — baseline   : {base.predict_proba(Xte)[:, 1].mean():.3f}")
print(f"mean predicted prob — oversampled: {over.predict_proba(Xte)[:, 1].mean():.3f}  <- inflated by resampling")
print(f"ECE baseline    : {metrics.expected_calibration_error(yte, base.predict_proba(Xte)[:, 1]):.3f}")
print(f"ECE oversampled : {metrics.expected_calibration_error(yte, over.predict_proba(Xte)[:, 1]):.3f}")
"""),
    md(r"""
## 6. まとめ

- 不均衡では accuracy を捨て、**PR-AUC / balanced accuracy / recall@precision** で測る。
- まず **`class_weight="balanced"`**(データ非破壊・確率も比較的保つ)。次に **リサンプリング**(over/under/SMOTE)。
- リサンプリングは **訓練のみ**。CV では `imbalanced-learn` の `Pipeline` で fold 内 resample(リーク防止)。
- 多くの場合、不均衡対策の本質は **閾値(動作点)の移動**。PR-AUC が動かないのはそのため(04 章の閾値調整と同じ話)。
- リサンプリングは **較正を壊す**。確率が要るなら class_weight か再較正。

## 7. Exercises

1. `weights` を (0.99, 0.01) にして、class_weight とオーバーサンプリングの recall を比べよ。
2. オーバーサンプリング比率スライダーで、PR-AUC がほぼ一定なことを確認し、何が動いているのか述べよ。
3. アンダーサンプリング版の関数を書き、オーバーサンプリングと recall/precision を比較せよ。
4. `imbalanced-learn` を入れ、SMOTE と単純オーバーサンプリングの PR-AUC を比べよ。
5. (発展)オーバーサンプリング後に `CalibratedClassifierCV` を当て、ECE が改善するか測れ。

## 8. Common Mistakes

- **accuracy で評価する。** 多数派ベースラインに勝てているか分からない。
- **リサンプリングを分割前/テストにも適用。** リーク。訓練のみ・CV では imblearn Pipeline。
- **リサンプリング後の確率をそのまま信じる。** 較正が崩れる。
- **常に 1:1 まで増やす。** 過剰だと多数派側の precision を落としすぎる。比率は検証で選ぶ。
"""),
]

if __name__ == "__main__":
    import pathlib

    out = pathlib.Path(__file__).resolve().parents[1] / "notebooks" / "13_imbalanced_learning.ipynb"
    build(cells, str(out))
