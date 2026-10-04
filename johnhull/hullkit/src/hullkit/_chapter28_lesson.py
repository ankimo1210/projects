"""Private chapter-28 closing lessons, shared by the notebook and portal."""

from functools import lru_cache

import numpy as np
import plotly.graph_objects as go

from ._exchange_measure import exchange_measure_price, exchange_ratio_statistics
from ._forward_black import forward_black_price, gaussian_forward_statistics
from ._numeraire_change import numeraire_drift_change

FIGURES = {
    "martingale_black_forward_market": (
        "28.6",
        "forwardとfuturesの期待値",
        "stockと金利の相関 ρ",
        "価格 (USD)",
    ),
    "martingale_black_forward_prices": (
        "28.6",
        "T測度のBlackと確率金利の給付",
        "行使価格 K (USD)",
        "call価格 (USD)",
    ),
    "martingale_exchange_ratio_means": (
        "28.7",
        "配当を含む比の条件付き平均",
        "残存期間 (年)",
        "比 V/U (無次元)",
    ),
    "martingale_exchange_measure_prices": (
        "28.7",
        "渡す資産を基準に交換callを評価",
        "資産間の相関 ρ",
        "交換call価格 (USD)",
    ),
    "martingale_numeraire_drift_shift": (
        "28.8",
        "新/旧の向きと相関drift補正",
        "因子間の相関 ρ",
        "相対drift (1/年)",
    ),
    "martingale_numeraire_absolute_shift": (
        "28.8",
        "非取引変数の絶対drift",
        "現在の状態 (状態単位)",
        "絶対drift (状態単位/年)",
    ),
}


@lru_cache(maxsize=1)
def _series():
    """Small declared synthetic markets; no printed prices exist in these sections."""
    rows = {}
    correlations = [-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]
    stats = [gaussian_forward_statistics(100, 0.04, 0.03, 0.25, rho, 2) for rho in correlations]
    rows["martingale_black_forward_market"] = [
        dict(role=key, name=name, x=correlations, y=[r[key] for r in stats])
        for key, name in [("forward", "T測度: forward"), ("futures", "Q測度: futures")]
    ]
    s = gaussian_forward_statistics(100, 0.04, 0.03, 0.25, 0.75, 2)
    strikes = [70, 80, 90, 100, 105, 110, 120, 130, 140]
    prices = [
        forward_black_price(s["discount"], s["forward"], k, s["forward_sigma"], 2) for k in strikes
    ]
    naive = [
        forward_black_price(s["discount"], s["futures"], k, s["forward_sigma"], 2) for k in strikes
    ]
    rows["martingale_black_forward_prices"] = [
        dict(role="black_T", name="T測度 Black", x=strikes, y=prices),
        dict(role="outer_Q", name="誤用: P(0,T)×Qの給付期待値", x=strikes, y=naive),
    ]
    times = [0, 0.25, 0.5, 1, 1.5, 2]
    ratios = [exchange_ratio_statistics(1.1, 0.2, 0.3, 0.4, t, 0.06, 0.02) for t in times]
    rows["martingale_exchange_ratio_means"] = [
        dict(role=key, name=name, x=times, y=[r[key] for r in ratios])
        for key, name in [("mean_given", "U測度: 配当差4%"), ("mean_Q", "Q測度: drift5.6%")]
    ] + [dict(role="no_income", name="U測度: 両資産の配当なし", x=times, y=[1.1] * len(times))]
    rhos = [-1, -0.5, 0, 0.4, 0.5, 1]
    rows["martingale_exchange_measure_prices"] = [
        dict(
            role="income",
            name="qU=6%, qV=2%",
            x=rhos,
            y=[exchange_measure_price(100, 110, 0.25, 0.3, r, 1.5, 0.06, 0.02) for r in rhos],
        ),
        dict(
            role="no_income",
            name="qU=qV=0",
            x=rhos,
            y=[exchange_measure_price(100, 110, 0.25, 0.3, r, 1.5) for r in rhos],
        ),
    ]
    rhos = [-1, -0.5, 0, 0.45, 1]
    new = [
        numeraire_drift_change(0.08, [0.2, -0.1], [0.12, 0.08], [-0.09, 0.17], [[1, r], [r, 1]])
        for r in rhos
    ]
    restored = [
        numeraire_drift_change(v, [0.2, -0.1], [-0.09, 0.17], [0.12, 0.08], [[1, r], [r, 1]])
        for r, v in zip(rhos, new, strict=True)
    ]
    rows["martingale_numeraire_drift_shift"] = [
        dict(role="old", name="旧測度", x=rhos, y=[0.08] * len(rhos)),
        dict(role="new", name="新測度: h/g", x=rhos, y=new),
        dict(role="restored", name="逆変換: g/h", x=rhos, y=restored),
    ]
    states = [-20, 0, 50]
    C = [[1, 0.45, -0.3], [0.45, 1, 0.2], [-0.3, 0.2, 1]]
    old = [0.7 - 0.08 * x for x in states]
    new = [
        numeraire_drift_change(
            mu,
            np.array([3.0, -1.0, 2.0]) + x * np.array([0.005, 0.002, -0.001]),
            [0.12, 0.08, -0.18],
            [-0.09, 0.17, 0.04],
            C,
        )
        for x, mu in zip(states, old, strict=True)
    ]
    rows["martingale_numeraire_absolute_shift"] = [
        dict(role="old", name="旧測度: 絶対drift", x=states, y=old),
        dict(role="new", name="新測度: 絶対loadingで補正", x=states, y=new),
    ]
    return rows


def _figures():
    result = {}
    colors = ("#2563eb", "#d97706", "#0f766e")
    for key, (section, title, xaxis, yaxis) in FIGURES.items():
        fig = go.Figure()
        for i, trace in enumerate(_series()[key]):
            fig.add_scatter(
                x=trace["x"],
                y=trace["y"],
                mode="lines+markers",
                name=trace["name"],
                meta=dict(role=trace["role"]),
                line=dict(color=colors[i], dash="dash" if i == 1 else "solid"),
            )
        fig.update_layout(
            template="plotly_white",
            title=title,
            height=510,
            xaxis_title=xaxis,
            yaxis_title=yaxis,
            margin=dict(l=85, r=25, t=70, b=150),
            legend=dict(orientation="h", y=-0.30),
            meta=dict(
                section=section,
                figure=key,
                synthetic=True,
                source_pages="Hull GE pp.680–684",
                units=yaxis,
            ),
        )
        result[key] = fig
    return result


def _md(source):
    return dict(cell_type="markdown", metadata={}, source=source.splitlines(True))


def _code(source):
    return dict(
        cell_type="code",
        metadata={},
        source=source.splitlines(True),
        outputs=[],
        execution_count=None,
    )


def _cells():
    return [
        _md(r"""## 6E. Blackのモデルを測度から再訪（§28.6）

### 6E.1 確率金利でも成立する仮定（GE pp.680–681、式28.26–28.29）
満期$T$の債券を基準にすると、同じ$T$に決済されるforward $F$について
$$c_0=P(0,T)E^T[(F_T-K)^+].$$
$T$測度で$F_T$が対数正規、$\log F_T$の分散が$\sigma_F^2T$なら
$$c_0=P(0,T)[F_0N(d_1)-KN(d_2)],\quad
 d_1=\frac{\log(F_0/K)+\sigma_F^2T/2}{\sigma_F\sqrt T},\quad d_2=d_1-\sigma_F\sqrt T.$$
putは$P(0,T)[KN(-d_2)-F_0N(-d_1)]$。満期一致と該当測度での分布が必要です。
$\sigma_F$はforwardの実効変動率で、spotの変動率をそのまま代入しません。
$T=0$・$\sigma_F=0$は割引intrinsic、負のforwardにはこのlognormal式を使いません。

### 6E.2 forwardとfuturesは異なる期待値
$F_0=E^T[S_T]$、連続決済のfuturesは$E^Q[S_T]$。
確率金利では$E^Q[e^{-\int_0^T r_sds}(S_T-K)^+]$を、
$P(0,T)E^Q[(S_T-K)^+]$へ分離できません。金利が確定的なら両者は一致します。
以下は**合成例**で、印刷例ではありません。$S_0=100,r_0=.04,\eta=.03,\sigma_S=.25,T=2$、
$dr=\eta dW_r$、$dS/S=r\,dt+\sigma_SdW_S$、相関$\rho$。
$$P(0,T)=e^{-r_0T+\eta^2T^3/6},\quad
\sigma_F^2=\sigma_S^2+\rho\eta\sigma_ST+\eta^2T^2/3.$$
このGaussianモデルは本文の一般命題を説明する一例で、一般の確率金利で対数正規性を保証しません。"""),
        _code(
            'from hullkit._chapter28_lesson import _figures\nchapter28_plots = _figures()\nchapter28_plots["martingale_black_forward_market"].show()'
        ),
        _md(r"""### 6E.3 同じ給付を二つの測度で検証
$\rho=.75$を固定して行使価格を変えます。図の誤用線はQの期待値を外側の平均割引で掛けた結果です。
独立参照はhullkitを使わない正規密度のQ/T求積。7市場42のcall/put、parity、外生forward、
低確率給付$7.1683521394\times10^{-8}$も照合し、固定seed MCは標準誤差で判定します。
ゼロhitのMCを価格ゼロの根拠にせず、非正規化importance samplingも使用します。
時刻は年、価格はUSD、変動率は年率。モデルの値と標本誤差・近似誤差を区別します。

**理解の確認:** spot volatilityとforward volatilityが一致するのはどの条件ですか。
Qの割引と給付を別々に平均すると何を失いますか。"""),
        _code('chapter28_plots["martingale_black_forward_prices"].show()'),
        _md(r"""## 6F. 一つの資産を別の資産と交換（§28.7）

### 6F.1 渡す資産Uを基準にする（GE pp.681–682、式28.30–28.32）
満期に$U_T$を渡して$V_T$を受け取る給付は$(V_T-U_T)^+$。
無配当なら$U$測度で$R=V/U$のdriftはゼロ、$E^U[R_T]=V_0/U_0$。
比の分散率は$\widehat\sigma^2=\sigma_U^2+\sigma_V^2-2\rho\sigma_U\sigma_V$。
$\log R$のdriftは$-\widehat\sigma^2/2$で、比自身のdriftゼロと区別します。
資産への変動率と相関を保ち、strike 1のcallとして評価します。

### 6F.2 配当を再投資したnumeraire
連続配当率$q_U,q_V$では基準は$e^{q_Ut}U_t$で、配当落ちspotだけを基準にしません。
$$E^U[R_T]=\frac{V_0}{U_0}e^{(q_U-q_V)T},\quad
V_0^{\mathrm{option}}=U_0e^{-q_UT}E^U[(R_T-1)^+].$$
したがって$V_0e^{-q_VT}N(d_1)-U_0e^{-q_UT}N(d_2)$となり、§26.14の交換式を再導出します。
図は**合成例**$V_0/U_0=1.1,\sigma_U=.2,\sigma_V=.3,\rho=.4,q_U=.06,q_V=.02$。
Qでの比のdriftは$q_U-q_V+\sigma_U^2-\rho\sigma_U\sigma_V=.056$、Uでは$.04$。
両配当ゼロの別市場ならU測度の平均は1.1を保存します。"""),
        _code('chapter28_plots["martingale_exchange_ratio_means"].show()'),
        _md(r"""### 6F.3 相関・退化・確率金利
価格図は$U_0=100,V_0=110,\sigma_U=.25,\sigma_V=.3,T=1.5$。
独立求積33市場と確率金利のraw Q MCを比較します。raw密度は
$$L_T=e^{q_UT-\int_0^T r_sds}U_T/U_0,$$
標本平均で自己正規化しません。同じ経路の金利因子は割引給付で相殺され、価格は$r$に依存しません。
これは共通通貨・同じ金利口座・連続配当・定数loadingのモデルでの結果です。
$\rho=\pm1$、比の分散ゼロ、満期ゼロも扱います。本文に印刷数値はありません。

**理解の確認:** qUとqVの向きを逆にすると平均比はどう変わりますか。
比の相対driftとlog driftが同じではないのはなぜですか。"""),
        _code('chapter28_plots["martingale_exchange_measure_prices"].show()'),
        _md(r"""## 6G. ニュメレール変更の共分散補正（§28.8）

### 6G.1 比は新/旧（GE pp.682–684、式28.33–28.35）
旧numeraireを$g$、新を$h$、$w=h/g$と置きます。独立因子のsigned loadingなら
$$\mu_v^h=\mu_v^g+\sum_i s_{v,i}(s_{h,i}-s_{g,i})
=\mu_v^g+\rho_{vw}\sigma_v\sigma_w.$$
相関座標$C$では補正$b_v^TC(s_h-s_g)$。同じbasisで係数をそろえ、$C$を二重に掛けません。
$$dW^h=dW^g-C(s_h-s_g)dt.$$
Brownianの補正はdrift補正と逆符号です。$h\to g$で元のdriftへ戻り、途中のnumeraireを挟んでも補正は加算されます。
図は合成2因子、旧drift$.08$、$b_v=(.2,-.1),s_g=(.12,.08),s_h=(-.09,.17)$。
相関端点の退化PSDでも逆行列を使わず計算します。"""),
        _code('chapter28_plots["martingale_numeraire_drift_shift"].show()'),
        _md(r"""### 6G.2 PからQと非取引変数
物理測度からQでは$\mu_v^Q=\mu_v^P-b_v^TC\lambda$。独立3因子で
$\mu_P=.08,b=(.2,-.1,.15),\lambda=(.4,-.25,.18)$なら$\mu_Q=-.052$。
非取引変数のQ driftを金利$r$に置き換えません。相対drift/loadingは$1/年$・$1/\sqrt{年}$、
絶対drift/loadingは状態単位/年・状態単位/$\sqrt{年}$で、両方の規約を混ぜません。
図の状態は$-20,0,50$、旧絶対drift$.7-.08x$、
$b(x)=(3,-1,2)+x(.005,.002,-.001)$。ゼロ状態でも絶対係数を使えます。
局所状態依存係数を与えただけで、有限時間分布が対数正規になるとは主張しません。

### 6G.3 独立検証と真のmartingale条件
9相関条件の共分散・逆変換、TN20のchain rule、Gaussian密度傾斜の独立求積と固定seed MCを確認。
有限時間の定数loadingならraw密度は
$$L_T=\exp((s_h-s_g)^TW_T^g-\tfrac12(s_h-s_g)^TC(s_h-s_g)T).$$
一般の予測可能loadingには確率積分と可積分性が必要です。局所係数の恒等式から真のmartingaleを断定しません。
本文の印刷例はありません。図と数値は明示した合成例です。

**理解の確認:** h/gをg/hへ替えると符号はどう変わりますか。
状態がゼロのとき、絶対loadingを相対loadingへ割り算できますか。"""),
        _code(
            'from hullkit._numeraire_change import physical_to_q_drift\nprint("非取引変数のQ drift:", physical_to_q_drift(.08, [.2, -.1, .15], [.4, -.25, .18]))\nchapter28_plots["martingale_numeraire_absolute_shift"].show()'
        ),
    ]
