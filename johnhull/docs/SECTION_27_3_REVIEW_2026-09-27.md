# §27.3 The IVF Model：原典照合と要求

日付：2026-09-27。原典：Hull 11e Global Edition pp.649–650、§27.3（§27.4開始前まで）。
IVF は Derman–Kani、Dupire、Rubinstein の局所ボラモデル。価格・株価は通貨、時刻は年、
金利・配当・ボラは年率小数で示す。教材は合成市場であり、市場較正の成績ではない。

## 要求契約

| 要求 | 原典上の要点 | 独立検証・教材 |
|---|---|---|
| IV01 過程と価格面 | $dS=[r(t)-q(t)]Sdt+\sigma(S,t)Sdz$。欧州バニラ価格面への適合を狙う。IV と局所ボラは異なる量。 | vol06 §9.1、3満期の逆算IV図 `ivf_smile` |
| IV02 式27.4 | $\sigma_{\rm loc}^2=(c_T+q(T)c+K[r(T)-q(T)]c_K)/(K^2c_{KK}/2)$。$r(T),q(T)$ は瞬間値。 | 中央差分の公開関数、定数BSM面と時間変化するcarryの極限、負の分母・分子を拒否。§9.2 |
| IV03 平滑な面・局所ボラ | 十分な欧州コール価格と平滑化が必要。 | 初期に15%/35%を確率0.7/0.3で選ぶ平滑な混合BSM面。密度重みの解析的局所ボラと33点比較、`ivf_local`。§9.3 |
| IV04 バニラ適合 | 局所ボラから欧州価格を再現する。 | 独立の株価方向・後退Crank–Nicolson PDEで3満期×3行使価格の9価格を再計算、`ivf_repricing`。§9.4 |
| IV05 限界分布と同時分布 | 一時点の分布は欧州価格から定まる。複合・バリアなど複数時点の価格は保証されない。 | 元の潜在ボラ混合と局所ボラを同一乱数で15万経路×200ステップ比較。各時点の上昇確率と二時点同時上昇の差を分離、`ivf_joint`。§9.5 |
| IV06 実務・配布 | 日次再較正、implicit FD または implied tree、価格微分に必要な平滑化、exotic model risk。 | §9.6、Book/portal共有4図・2幅の実画面、既受入11節の再検証 |

## 独立参照と実測

[`build_local_volatility_reference.py`](../scripts/build_local_volatility_reference.py)は`hullkit`をimportしない。
混合BSMの解析価格・満期密度・条件付き分散から局所ボラを出し、後退PDEの株価演算子に入れる。
[`reference.json`](validation/section-27-3/reference.json)は`--check`でbyte再現する。
[`verify_local_volatility_numerics.py`](../scripts/verify_local_volatility_numerics.py)が公開関数と照合し、
[`numerical-check.json`](validation/section-27-3/numerical-check.json)に実測値とソースハッシュを保存する。

| 比較 | 実測 | 基準 |
|---|---:|---:|
| 中央差分の局所ボラ vs 密度重みの解析式（33点） | 最大5.46e-7 | 2e-4 |
| 定数BSM 23%面（9点） | 最大2.50e-7 | 2e-4 |
| 時変$r(t),q(t)$の定数ボラ20%面 | 3.57e-8 | 2e-4 |
| 独立後退PDE vs 混合BSM（9価格） | 最大0.00405通貨 | 0.005 |
| 潜在/局所の単一時点 $P(S>100)$ 差 | $T=0.5$: 1.0 SE、$T=1$: 1.7 SE | 各3 paired SE以内 |
| 潜在/局所の二時点 $P(S_{0.5}>100,S_1>100)$ 差 | −0.00854（局所−潜在）、17.8 paired SE | 5 paired SE超 |

混合BSMは一つのボラを最初に選んで保持する過程である。Dupireの解析的係数は
混合成分の終値密度で重み付けした条件付き分散となり、両過程の欧州コール面が連続時間の理論上は一致する。
後退PDEには株価刻み0.5、年400ステップ、上限400を使うため価格差はゼロではない。
二時点MCの局所過程はEuler対数ステップで、双方の比較は同一乱数によるpaired SEを使う。
この数値差は選んだ閾値・満期・パラメータに対する実測であり、バリア価格の一般的な誤差上界ではない。

## 実装と配布

公開関数は`hullkit.local_volatility:dupire_local_vol`。平滑なコール価格関数と中央差分幅を要求し、
蝶型密度または局所分散が非正なら拒否する。ノイズの平滑化や裁定修復は自動で行わない。
vol06 §9.1–9.6の12セルに共有4図を入れ、Bookとportalに同一保存値を表示する。
[`verify_local_volatility_notebook.py`](../scripts/verify_local_volatility_notebook.py)は、
M11基点`ad365fee`から§9外の58セル本文・保存出力が同一（後続2見出しの番号変更のみ）であること、
§27.1–§27.3の保存Plotly値が共有図と一致すること、新規実行結果と保存値の一致、4種類の改変拒否を検査する。
ブラウザ検査はBook/portal×1440/1000pxの16状態・16画像、MathJax・外部要求・数値改変拒否を確認する。

## 限界

実市場の気配、面の平滑化・補間、日次再較正、implied tree、exoticの市場価格、ヘッジ成績は検証対象外。
式27.4の2階微分は入力ノイズを増幅し、平滑化の選択でも局所ボラが変わる。
単一時点デジタルの理論的整合は欧州コール面に基づくもので、有限格子・有限MCの厳密一致を意味しない。
