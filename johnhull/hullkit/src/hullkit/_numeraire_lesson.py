"""Checked §28.4 figures and teaching cells shared by Book and portal."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-4/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_numeraire_reference.py",
    "scripts/verify_numeraire_numerics.py",
    "hullkit/src/hullkit/_numeraire_choices.py",
    "hullkit/src/hullkit/hull_white.py",
    "hullkit/src/hullkit/rates.py",
}
_RESULT_KEYS = ("api_joint", "api_stock", "api_rates", "api_annuity", "pricing_mc")
_KEYS = (
    "martingale_numeraire_pricing",
    "martingale_numeraire_forward",
    "martingale_numeraire_payment",
    "martingale_numeraire_annuity",
)
_COLORS = ("#2563eb", "#0f766e", "#dc2626")


def _result_digest(record):
    return hashlib.sha256(
        json.dumps({k: record[k] for k in _RESULT_KEYS}, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


def _close(actual, expected, tolerance=2e-12):
    a, b = np.asarray(actual), np.asarray(expected)
    if (
        a.dtype.kind not in "iuf"
        or a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, atol=tolerance, rtol=0)
    ):
        raise ValueError("numeraire result differs from independent reference")


def _mc(row, want):
    for n in ("mean", "se", "z", "reference"):
        if (
            isinstance(row[n], bool)
            or not isinstance(row[n], (float, int))
            or not math.isfinite(row[n])
        ):
            raise ValueError("MC requires finite real results")
    _close(row["reference"], want, 1e-9)
    if row["se"] <= 0 or row["z"] > 5:
        raise ValueError("invalid MC interval")
    _close(row["z"], abs(row["mean"] - want) / row["se"])


def _load_reference():
    raw = _DATA.read_bytes()
    data = json.loads(raw)
    record = json.loads(_RECORD.read_text())
    if (
        record.get("section") != "28.4"
        or record.get("status") != "PASS"
        or not record.get("synthetic")
    ):
        raise ValueError("passing synthetic numeraire record required")
    if hashlib.sha256(raw).hexdigest() != record.get("artifact_sha256"):
        raise ValueError("numeraire reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not isinstance(hashes, dict) or not _SOURCES <= hashes.keys():
        raise ValueError("numeraire source hash missing")
    for name, want in hashes.items():
        path = (_PROJECT / name).resolve()
        if (
            not path.is_relative_to(_PROJECT)
            or hashlib.sha256(path.read_bytes()).hexdigest() != want
        ):
            raise ValueError("numeraire source hash mismatch")
    try:
        if _result_digest(record) != record["result_sha256"]:
            raise ValueError("numeraire result hash mismatch")
        if (
            data["source_requirements"] != [f"N{n:02d}" for n in range(1, 13)]
            or data["printed_pins"] != []
        ):
            raise ValueError("source requirements incomplete")
        if [len(record[k]) for k in _RESULT_KEYS] != [6, 18, 21, 12, 10]:
            raise ValueError("numeraire result matrix incomplete")
        for actual, want in zip(record["api_joint"], data["joint"], strict=True):
            _close(actual["mean"], want["mean_X_I_W"])
            _close(actual["covariance"], want["covariance_X_I_W"])
            _close(actual["bond"], want["bond"])
            loading = -math.expm1(-want["a"] * 0.5) / want["a"]
            _close(
                actual["tilted_mean"],
                np.asarray(want["mean_X_I_W"])
                - np.asarray(want["covariance_X_I_W"]) @ np.array([loading, 1, 0]),
            )
        for actual, want in zip(record["api_stock"], data["stock"], strict=True):
            for name, source in [
                ("price_q", "call_Q_quad"),
                ("price_payment", "call_T_quad"),
                ("price_wrong_q_outer_discount", "wrong_external_Q_discount"),
                ("futures", "futures_Q"),
                ("forward", "forward_T"),
            ]:
                _close(actual[name], want[source], 1e-9)
        for actual, want in zip(record["api_rates"], data["rates"], strict=True):
            for name, source in [
                ("forward", "forward"),
                ("term_q", "term_E_Q"),
                ("term_payment", "term_E_pay"),
                ("term_wrong_fix", "term_E_wrong_fix"),
                ("overnight_q", "overnight_E_Q"),
                ("overnight_payment", "overnight_E_pay"),
                ("overnight_wrong_fix", "overnight_E_wrong_fix"),
            ]:
                _close(actual[name], want[source])
        source_rows = [r for r in data["annuity"] if r["basis_mode"] != "multiplicative"]
        for actual, want in zip(record["api_annuity"], source_rows, strict=True):
            for name, source in [
                ("annuity", "A_t"),
                ("value", "V_t"),
                ("rate", "swap_rate_t"),
                ("weights", "mixture_weights"),
                ("component_means", "mixture_means_x_T"),
                ("state_variance", "variance_x_T"),
                ("mean_a_rate", "mean_A_swap_rate"),
                ("price_a", "payer_A_quad"),
                ("price_q", "payer_Q_quad"),
            ]:
                _close(actual[name], want[source], 1e-9 if name.startswith("price") else 2e-12)
        expected = [(i, m) for i in (0, 1, 2, 3, 6) for m in ("Q", "T")]
        for actual, (i, measure) in zip(record["pricing_mc"], expected, strict=True):
            if actual["fixture_index"] != i or actual["measure"] != measure:
                raise ValueError("MC fixture ordering changed")
            _mc(actual, data["stock"][i]["call_Q_quad"])
            if measure == "Q":
                _mc(actual["raw_rn"], 1.0)
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("numeraire result missing or malformed") from exc
    return data, record


def _finish(fig, key, title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=85, r=35, t=100, b=175),
        legend=dict(orientation="h", y=-0.38),
        meta=dict(
            section="28.4",
            figure=key,
            source="Hull GE pp.676–679; synthetic flat HW, additive rate basis",
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _figures():
    data, record = _load_reference()
    mc = record["pricing_mc"][:6]
    labels = [
        f"{r['measure']}, σS={data['stock'][r['fixture_index']]['stock_loading']:+.2f}" for r in mc
    ]
    pricing = go.Figure()
    pricing.add_scatter(
        x=labels,
        y=[r["mean"] - r["reference"] for r in mc],
        mode="markers",
        name="直接MC差 ±95%区間",
        error_y=dict(type="data", array=[1.96 * r["se"] for r in mc], visible=True),
        marker=dict(color=_COLORS[0], size=9),
        meta=dict(role="mc"),
    )
    pricing.add_scatter(
        x=labels,
        y=[0.0] * 6,
        mode="lines",
        name="独立求積価格との差0",
        line=dict(color=_COLORS[1], dash="dash"),
        meta=dict(role="reference"),
    )
    pricing.add_scatter(
        x=labels,
        y=[
            record["api_stock"][r["fixture_index"]]["price_wrong_q_outer_discount"] - r["reference"]
            for r in mc
        ],
        mode="markers",
        name="誤ったQ外側割引の差",
        marker=dict(color=_COLORS[2], symbol="x", size=9),
        meta=dict(role="wrong"),
    )
    pricing.update_xaxes(title_text="同一call給付、Qの経路割引 / Tの外側債券割引")
    pricing.update_yaxes(title_text="MC又は誤った価格 − 独立価格（通貨）")
    rows = record["api_stock"][:3]
    labels = ["σS=+.25", "σS=−.25", "σS=0"]
    forward = go.Figure()
    for name, key, color in [
        ("futures: E_Q S", "futures", _COLORS[0]),
        ("forward: E_T S", "forward", _COLORS[1]),
    ]:
        forward.add_bar(
            x=labels, y=[r[key] for r in rows], name=name, marker_color=color, meta=dict(role=key)
        )
    forward.update_xaxes(title_text="同じ金利乱数に対するstockの符号付きloading")
    forward.update_yaxes(title_text="受渡価格（通貨）；T=2年、S0=100", range=[106, 110])
    rates = record["api_rates"][:3]
    labels = [f"fix {r['fixing']:g} → pay {r['payment']:g}" for r in rates]
    payment = go.Figure()
    for key, name, color in [
        ("term_payment", "term / 支払U測度", _COLORS[0]),
        ("overnight_payment", "overnight / 支払U測度", _COLORS[1]),
        ("term_wrong_fix", "誤った固定T測度", _COLORS[2]),
    ]:
        payment.add_bar(
            x=labels,
            y=[1e4 * (r[key] - r["forward"]) for r in rates],
            name=name,
            marker_color=color,
            meta=dict(role=key),
        )
    payment.update_xaxes(title_text="金利の固定・実現日と支払日（年）、δ=.25/.5")
    payment.update_yaxes(title_text="期待金利 − 現在forward（bp）")
    actual = record["api_annuity"][:6]
    wanted = [r for r in data["annuity"] if r["basis_mode"] != "multiplicative"][:6]
    labels = [f"t={r['t']}, x={r['x_t']:+.3f}<br>{r['basis_mode']}" for r in wanted]
    annuity = go.Figure()
    annuity.add_bar(
        x=labels,
        y=[1e4 * (r["mean_a_rate"] - r["rate"]) for r in actual],
        name="E_A s(T)−s(t)",
        marker_color=_COLORS[1],
        meta=dict(role="annuity"),
    )
    annuity.add_bar(
        x=labels,
        y=[1e4 * (w["mean_Q_swap_rate"] - r["rate"]) for w, r in zip(wanted, actual, strict=True)],
        name="誤ったE_Q s(T)−s(t)",
        marker_color=_COLORS[2],
        meta=dict(role="wrong"),
    )
    annuity.update_xaxes(title_text="条件付き時刻・OU状態、単一curve / 合成projection basis")
    annuity.update_yaxes(title_text="平均swap rate − 現在swap rate（bp）")
    return {
        key: _finish(fig, key, title)
        for key, fig, title in zip(
            _KEYS,
            [pricing, forward, payment, annuity],
            [
                "同じ給付：Q/Tの価格と割引の位置",
                "futuresとforwardは異なる測度の平均",
                "term・overnight金利は支払日測度",
                "annuity測度：条件付きswap rateの保存",
            ],
            strict=True,
        )
    }


def _markdown(source):
    return dict(cell_type="markdown", metadata={}, source=source.splitlines(True))


def _code(source):
    return dict(
        cell_type="code",
        metadata={},
        source=source.splitlines(True),
        execution_count=None,
        outputs=[],
    )


def _cells():
    """N01–N12 and equations 28.16–25, including footnotes5/6."""
    return [
        _markdown(r"""## 6C. ニュメレールの選択（§28.4）

Hull GE pp.676–679、式28.16–28.25。§28.3の比のmartingaleを、口座・支払日債券・annuityに適用します。下の市場入力は全て**合成**で、原典に印刷された価格の再現例ではありません。原典には本節の印刷価格pinはありません。

### 6C.1 口座の測度：確率割引を各経路の内側へ（N01–N03, N05）

短期口座は $M_0=1$、$dM_t=r_tM_t\,dt$（28.16）で、
$M_T=\exp(\int_0^T r_u\,du)$。瞬間拡散は0でも、$r_t$が確率的なら口座の将来値は確率的です。ゼロ拡散を決定的口座と読み替えません。

$$f_0=M_0\widehat E[f_T/M_T]
=E_Q[\exp(-\int_0^T r_u\,du)f_T]
=E_Q[e^{-\bar rT}f_T]. \tag{28.17–19}$$

給付と**同じ経路**の平均短期金利 $\bar r=T^{-1}\int_0^T r_u\,du$で割引します。原典脚注5：短期間の投資・再投資を連続化した口座です。別通貨の口座にも同じ構成を使えますが、この教材は同一通貨に固定します。
"""),
        _markdown(r"""### 6C.2 支払日債券の測度：同じ給付を違う期待値で（N04, N06）

$r$一定なら $f_0=e^{-rT}E_Q[f_T]$。確率金利で外側へ出すことはできません。一方、$P(t,T)$はTに元本1を払う無リスク債券、$P(T,T)=1$なので

$$f_0=P(0,T)E_T[f_T]. \tag{28.20}$$

$Q$と$T$の平均を区別します。下は同じcall $H=(S_T-105)^+$、$S_0=100$、$T=2$年。$Q$では経路割引、$T$では外側の既知DFです。1因子HW金利・stockの符号付きloading $+.25,-.25,0$を使います。独立求積価格は順に約16.371619、14.457904、3.262097。

棒・点は検証済み数値から生成します。MCの表示区間は±1.96SE、受入条件は5SE。raw RN重みは自己正規化せず平均1を検査し、金利vol=0の定数金利極限も照合しています。
"""),
        _code(
            "from hullkit._numeraire_lesson import _load_reference as _nc_load, _figures as _nc_figures\n_nc_data, _nc_record = _nc_load()\n_nc_plots = _nc_figures()\n_nc_plots['martingale_numeraire_pricing'].show()\nprint('synthetic same-payoff prices:', [r['price_q'] for r in _nc_record['api_stock'][:3]])"
        ),
        _markdown(r"""### 6C.3 一般forwardとfutures：期待値の測度（N07–N08）

任意の変数 $\theta$について、Tのforward給付を $\theta_T-K$と定義すると、
$f_0=P(0,T)(E_T[\theta_T]-K)$。ゼロ価値となる受渡価格は

$$F=E_T[\theta_T]. \tag{28.21}$$

原典脚注6・§18.6のfuturesは $E_Q[\theta_T]$、forwardは $E_T[\theta_T]$です。確率金利では異なり得ます。stock実演は無収入で $dS/S=r_tdt+\sigma_SdW$、金利と同じWです。loadingの符号で差が反転し、金利vol=0では差は消えます。金利FRAは支払規約が違うため、この一般変数の式を金利へ機械的に当てはめません。
"""),
        _code(
            "_nc_plots['martingale_numeraire_forward'].show()\nprint('futures Q:', [r['futures'] for r in _nc_record['api_stock'][:3]])\nprint('forward T:', [r['forward'] for r in _nc_record['api_stock'][:3]])"
        ),
        _markdown(r"""### 6C.4 金利：固定・実現・支払の時点を分ける（N09–N10）

金利の対象期間は $[T,T^*]$、$\delta=T^*-T$。$F(t)$と$R$は同じ複利頻度の年率金利です。半期 $\delta=.5$、四半期 $.25$。原典の $F-R$をT*で払うゼロ価値FRAに、教材では元本L・期間を明示して $L\delta(F-R)$を使います。

$$E^{T^*}[R\mid\mathcal F_t]=F(t). \tag{28.22}$$

numeraireは**支払日T***の $P(t,T^*)$です。合成term金利 $R_T=(1/P(T,T^*)-1)/\delta$はTで既知。overnight金利 $R_{on}=(\exp(\int_T^{T^*}r_u du)-1)/\delta$はT*まで未知です。どちらも支払測度で同じforward平均になる一方、誤った固定日T測度は一致しません。$t=.25,.75$、複数状態、負金利、金利vol=0も保存した21ケースで検査します。連続複利zero rateとこのsimple年率金利を混同しません。
"""),
        _code(
            "_nc_plots['martingale_numeraire_payment'].show()\nprint('term / overnight / forward:', [[r[k] for k in ('term_payment','overnight_payment','forward')] for r in _nc_record['api_rates'][:3]])"
        ),
        _markdown(r"""### 6C.5 年金係数：割引curveとprojectionを分ける（N11–N12）

swap開始T、$T_0=T$、支払 $T_i$、$t\leq T$、元本1。期間と年率をそろえて

$$A(t)=\sum_{i=0}^{N-1}(T_{i+1}-T_i)P_d(t,T_{i+1})>0,\qquad s(t)=V(t)/A(t). \tag{28.23}$$

固定側は $sA$、浮動側はV。Aはrisk-free/OIS割引curve、Vのクーポンは任意のprojection yield curveから構成できる（原典はLIBOR/OISの例）。Aへprojection curveを入れません。annuity測度では

$$E_A[s(T)\mid\mathcal F_t]=s(t),\qquad V(0)=A(0)E_A[V(T)/A(T)]. \tag{28.24–25}$$

この実演は初期discount zero4%、projection zero5%を、simple rateの**決定的加算basis** $b_i=F_{p,i}(0)-F_{d,i}(0)$で結びます。
$V(t)=P_d(t,T)-P_d(t,U_N)+\sum_i\delta_i b_iP_d(t,U_i)$、Aはdiscount側のままです。現在のLIBOR市場データではなく、初期projection curveを一致させた合成モデルです。独立に二つのcurveを確率発展させる一般モデルとは主張しません。

正確なA測度は支払日Gaussianの有限混合、重み $w_i(t)=\delta_iP_d(t,U_i)/A(t)$。複数時刻・状態の平均と同じpayer給付 $\max(V-KA,0)$のQ/A価格も検査します。単一Gaussianやlognormal swap rateを仮定しません。Ch29のBlack公式には追加の分布仮定が必要です。
"""),
        _code(
            "_nc_plots['martingale_numeraire_annuity'].show()\nprint('conditional A means:', [r['mean_a_rate'] for r in _nc_record['api_annuity'][:6]])\nprint('OIS annuity unchanged by projection basis:', _nc_record['api_annuity'][0]['annuity'] == _nc_record['api_annuity'][1]['annuity'])"
        ),
        _markdown(r"""### 6C.6 モデルの境界と検証（全N01–N12の補足）

本節の定理はモデル一般の内容です。数値実演は $dx=-axdt+\eta dW$、$r=x+\phi$、$\phi=r_0+\eta^2B(0,t)^2/2$、flat初期curveだけです。Qのzero-mean OU状態xに対するbondには $-B(t,U)c(t)$を含め、条件付き短期金利積分と割引towerで独立検証しました。既存Jamshidianは根の座標が移るためtime0価格は数学的に不変です。

$(x_T,\int_t^T r, W_T-W_t)$は同じ未来増分から作るrank 2 Gaussianです。端点だけを生成して台形積分をexactと呼びません。小さいahの級数、退化Gaussian、負金利、条件付き状態を扱い、時間は年、rateは年率小数、Aは年×単位元本価格。V/sが負でもよく、正値が必要なのはnumeraireです。

独立kernel求積・Q条件付き割引・T直接密度・annuity混合、63 fixtureと10直接MC、8種類の改変拒否、source/result hashを使っています。別のmultiplicative basis教師は初期par率が同じでもoption価格が違うため、教材のadditive basisへ混ぜません。多因子導出は§28.5、市場モデルは§28.6–28.8/Ch29以降で進めます。
"""),
        _code(
            "assert _nc_record['status'] == 'PASS'\nassert _nc_data['source_requirements'] == [f'N{n:02d}' for n in range(1,13)]\nassert _nc_record['max_mc_se'] <= 5\nassert all(r['rejected'] for r in _nc_record['negative_controls'])\nprint('§28.4: 12 source requirements, 6 joint/18 stock/21 rate/12 additive-annuity and6 contrasting fixtures, 10 iid MCs and8 mutations PASS')"
        ),
    ]
