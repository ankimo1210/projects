"""Checked §28.5 multiple-factor figures and cells for Book and portal."""

import hashlib
import importlib.util
import json
import math
import sys
import uuid
from functools import lru_cache
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

_PROJECT = Path(__file__).resolve().parents[3]
_DATA = _PROJECT / "docs/validation/section-28-5/reference.json"
_RECORD = _DATA.with_name("numerical-check.json")
_SOURCES = {
    "scripts/build_multifactor_reference.py",
    "scripts/verify_multifactor_numerics.py",
    "hullkit/src/hullkit/_multi_factor_martingales.py",
}
_RESULT_KEYS = ("api_cases", "api_conditional_means", "pricing", "pricing_mc")
_KEYS = (
    "factor_ratio_ito",
    "factor_ratio_conditional",
    "factor_basis_covariance",
    "factor_measure_price",
)
_COLORS = ("#2563eb", "#0f766e", "#dc2626")


def _result_digest(record):
    return hashlib.sha256(
        json.dumps({k: record[k] for k in _RESULT_KEYS}, sort_keys=True, allow_nan=False).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def _replayed_results(reference_bytes, source_inventory):
    """Replay fixed seeds once per independently checked reference/producer.

    source_inventory is part of the cache key, after current-file SHA checks.
    The temporary package gives the verifier its relative teacher import
    without adding a scripts directory to the process-wide Python path.
    """
    name = "_hull_multifactor_replay_" + uuid.uuid4().hex
    spec = importlib.util.spec_from_file_location(
        name,
        _PROJECT / "scripts/verify_multifactor_numerics.py",
        submodule_search_locations=[str(_PROJECT / "scripts")],
    )
    verifier = importlib.util.module_from_spec(spec)
    sys.modules[name] = verifier
    try:
        spec.loader.exec_module(verifier)
        fresh = verifier.verify(verifier.build())
        return json.dumps({k: fresh[k] for k in _RESULT_KEYS}, allow_nan=False)
    finally:
        for key in tuple(sys.modules):
            if key == name or key.startswith(name + "."):
                del sys.modules[key]


def _check_numbers(actual, expected, label):
    """Keep structure/order exact, accept finite roundoff at atol/rtol 2e-12.

    Numerical truth and fixed-seed summaries are compared as numbers rather
    than cross-platform digests. The cache stores immutable JSON, and source
    file identities remain part of its key.
    """
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            raise ValueError(label + " structure differs")
        for key in expected:
            if key == "z" and "se" in expected:
                # z=(mean-reference)/se amplifies mean roundoff by 1/se, which
                # reaches 1e10 in near-singular cases; compare z*se instead.
                _check_numbers(actual[key] * actual["se"], expected[key] * expected["se"], label)
            else:
                _check_numbers(actual[key], expected[key], label)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(label + " structure differs")
        for a, b in zip(actual, expected, strict=True):
            _check_numbers(a, b, label)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if (
            isinstance(actual, bool)
            or not isinstance(actual, (int, float))
            or not math.isfinite(actual)
            or not math.isclose(actual, expected, abs_tol=2e-12, rel_tol=2e-12)
        ):
            raise ValueError(label + " numerical values differ")
    elif actual != expected:
        raise ValueError(label + " metadata differs")


def _close(actual, expected, tolerance=2e-12):
    a, b = np.asarray(actual), np.asarray(expected)
    if (
        a.dtype.kind not in "iuf"
        or a.shape != b.shape
        or not np.all(np.isfinite(a))
        or not np.allclose(a, b, atol=tolerance, rtol=0)
    ):
        raise ValueError("multifactor result differs from independent reference")


def _mc(row, truth, deterministic=False):
    for key in ("mean", "se", "z", "reference"):
        if (
            isinstance(row[key], bool)
            or not isinstance(row[key], (int, float))
            or not math.isfinite(row[key])
        ):
            raise ValueError("finite real MC result required")
    _close(row["reference"], truth, 1e-9)
    if row["se"] < 0 or row["z"] < 0 or row["z"] > 5:
        raise ValueError("invalid MC uncertainty")
    if row["se"] < 1e-14:
        if not deterministic or abs(row["mean"] - truth) > 1e-12 or row["z"] != 0:
            raise ValueError("zero MC SE without deterministic payoff")
    else:
        _close(row["z"], abs(row["mean"] - truth) / row["se"], 1e-7)


def _load_reference():
    raw = _DATA.read_bytes()
    data = json.loads(raw)
    record = json.loads(_RECORD.read_text())
    if (
        record.get("section") != "28.5"
        or record.get("status") != "PASS"
        or record.get("synthetic") is not True
    ):
        raise ValueError("passing synthetic multifactor record required")
    if hashlib.sha256(raw).hexdigest() != record.get("reference_sha256"):
        raise ValueError("multifactor reference hash mismatch")
    hashes = record.get("source_sha256", {})
    if not isinstance(hashes, dict) or not _SOURCES <= hashes.keys():
        raise ValueError("multifactor source hash missing")
    for name, want in hashes.items():
        p = (_PROJECT / name).resolve()
        if (
            not p.is_relative_to(_PROJECT)
            or not p.is_file()
            or hashlib.sha256(p.read_bytes()).hexdigest() != want
        ):
            raise ValueError("multifactor source hash mismatch")
    try:
        # Rebuild the production-independent teacher: a re-signed teacher cannot redefine truth.
        spec = importlib.util.spec_from_file_location(
            "_mf_independent_teacher", _PROJECT / "scripts/build_multifactor_reference.py"
        )
        teacher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(teacher)
        _check_numbers(data, teacher.build(), "independent multifactor teacher")
        if _result_digest(record) != record["result_sha256"]:
            raise ValueError("multifactor result hash mismatch")
        # A self-consistent mean/SE/z/digest is not evidence of a real sample.
        # Replay the producer's fixed seeds and samples before displaying it.
        expected = json.loads(_replayed_results(raw, tuple(sorted(hashes.items()))))
        _check_numbers({k: record[k] for k in _RESULT_KEYS}, expected, "fixed-seed replay")
        if (
            [len(record[k]) for k in _RESULT_KEYS] != [11, 132, 11, 11]
            or record["samples"] != 262144
            or record["source_requirement_count"] != 6
            or record["case_count"] != 11
            or record["conditional_count"] != 132
        ):
            raise ValueError("incomplete multifactor result matrix")
        if not 0 <= record["max_api_error"] <= 1e-9:
            raise ValueError("invalid API tolerance summary")
        controls = record["negative_controls"]
        if (
            len(controls) != 8
            or len({r["mutation"] for r in controls}) != 8
            or not all(r["rejected"] is True for r in controls)
        ):
            raise ValueError("negative controls missing or accepted")
        all_mc = []
        for i, (actual, want, price, mc) in enumerate(
            zip(
                record["api_cases"],
                data["cases"],
                record["pricing"],
                record["pricing_mc"],
                strict=True,
            )
        ):
            if any(r["id"] != want["id"] for r in (actual, price, mc)):
                raise ValueError("multifactor fixture ordering changed")
            for key, source in [
                ("g_drifts", "g_drifts"),
                ("ratio_q_drift", "ratio_q_drift"),
                ("ratio_g_drift", "ratio_g_drift"),
                ("ratio_variance", "relative_ratio_variance"),
            ]:
                _close(actual[key], want[source])
            for key, source in [
                ("f_variance", "f_variance"),
                ("g_variance", "g_variance"),
                ("covariance", "f_g_covariance"),
            ]:
                _close(actual[key], want["prices"][source])
            for key, source in [("price_q", "q_price"), ("price_g", "g_price")]:
                _close(price[key], want["prices"][source], 1e-9)
            deterministic = {
                "density": actual["g_variance"] == 0,
                "ratio_g": actual["ratio_variance"] == 0,
                "ratio_reweighted_q": actual["f_variance"] == 0,
                "call_q": actual["f_variance"] == 0,
                "call_g": actual["f_variance"] == actual["g_variance"] == 0,
            }
            for key, truth in [
                ("density", 1),
                ("ratio_g", 1.25),
                ("ratio_reweighted_q", 1.25),
                ("call_q", price["price_q"]),
                ("call_g", price["price_g"]),
            ]:
                _mc(mc[key], truth, deterministic[key])
                all_mc.append(mc[key])
            for state, w in zip(
                record["api_conditional_means"][12 * i : 12 * (i + 1)],
                want["conditional"],
                strict=True,
            ):
                if state["id"] != want["id"]:
                    raise ValueError("conditional market changed")
                for key in ("observed_ratio", "horizon", "g_mean", "q_mean"):
                    _close(state[key], w[key])
                _mc(state["mc"], w["g_mean"], actual["ratio_variance"] == 0 or w["horizon"] == 0)
                all_mc.append(state["mc"])
        _close(record["max_mc_se"], max(r["z"] for r in all_mc))
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError("multifactor result missing or malformed") from exc
    return data, record


def _finish(fig, key, title):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=540,
        margin=dict(l=90, r=35, t=100, b=175),
        legend=dict(orientation="h", y=-0.38),
        meta=dict(
            section="28.5",
            figure=key,
            source="Hull GE pp.679–680/footnote7; synthetic constant correlated GBM",
        ),
    )
    fig.update_xaxes(automargin=True, title_standoff=12)
    fig.update_yaxes(automargin=True, title_standoff=12)
    return fig


def _figures():
    data, record = _load_reference()
    row = record["api_cases"][1]
    ito = go.Figure()
    ito.add_bar(
        x=["μf−μg", "+sgᵀ C sg", "−sfᵀ C sg"],
        y=[row["g_drifts"][0] - row["g_drifts"][1], row["g_variance"], -row["covariance"]],
        name="g測度の比の相対drift",
        marker_color=list(_COLORS),
        meta=dict(role="ito"),
    )
    ito.update_yaxes(title_text="相対drift（1/年）")
    ito.update_xaxes(title_text="相関三因子、符号付きloading：和は0")
    states = [
        r
        for r in record["api_conditional_means"]
        if r["id"] == "correlated_3" and r["horizon"] in (0.25, 2.5)
    ]
    labels = [f"ratio={r['observed_ratio']:g}, h={r['horizon']:g}年" for r in states]
    conditional = go.Figure()
    for key, name, color in [
        ("mc", "g測度の直接MC ±95%区間", _COLORS[0]),
        ("g_mean", "g測度の独立条件付き平均", _COLORS[1]),
        ("q_mean", "Q測度の条件付き平均", _COLORS[2]),
    ]:
        args = dict(
            x=labels,
            y=[r["mc"]["mean"] if key == "mc" else r[key] for r in states],
            name=name,
            mode="markers",
            marker=dict(color=color, size=9),
            meta=dict(role=key),
        )
        if key == "mc":
            args["error_y"] = dict(
                type="data", array=[1.96 * r["mc"]["se"] for r in states], visible=True
            )
        conditional.add_scatter(**args)
    conditional.update_yaxes(title_text="将来 f/g の条件付き平均（無次元）")
    conditional.update_xaxes(title_text="現在の観測比と未来の期間；異なる初期市場を含む")
    selected = [data["cases"][i] for i in (1, 5, 6)]
    labels = [r["id"] for r in selected]
    basis = go.Figure()
    basis.add_bar(
        x=labels,
        y=[r["prices"]["f_g_covariance"] for r in selected],
        name="sfᵀ C sg",
        marker_color=_COLORS[0],
        meta=dict(role="correlated"),
    )
    basis.add_bar(
        x=labels,
        y=[
            math.fsum(
                x * y
                for x, y in zip(
                    r["independent_f_loadings"], r["independent_g_loadings"], strict=True
                )
            )
            for r in selected
        ],
        name="(sf L)・(sg L)",
        marker_color=_COLORS[1],
        meta=dict(role="independent"),
    )
    basis.update_yaxes(title_text="共分散率（1/年）")
    basis.update_xaxes(title_text="PSDのrank：3 / 1 / 1、ρ=±1もinverse不要")
    pricing = go.Figure()
    for key, name, color in [
        ("call_q", "Q: 直接MC − 独立価格", _COLORS[0]),
        ("call_g", "g: 直接MC − 独立価格", _COLORS[1]),
    ]:
        rows = record["pricing_mc"][1:4]
        pricing.add_scatter(
            x=[r["id"] for r in rows],
            y=[r[key]["mean"] - r[key]["reference"] for r in rows],
            name=name,
            mode="markers",
            error_y=dict(type="data", array=[1.96 * r[key]["se"] for r in rows], visible=True),
            marker=dict(color=color, size=9),
            meta=dict(role=key),
        )
    pricing.add_scatter(
        x=[r["id"] for r in record["pricing_mc"][1:4]],
        y=[0] * 3,
        name="同じ給付の独立価格との差0",
        mode="lines",
        line=dict(color=_COLORS[2], dash="dash"),
        meta=dict(role="reference"),
    )
    pricing.update_yaxes(title_text="MC − 独立求積価格（通貨）、±95%区間")
    pricing.update_xaxes(title_text="同じf市場・同じcall、異なるgを選択")
    return {
        key: _finish(fig, key, title)
        for key, fig, title in zip(
            _KEYS,
            [ito, conditional, basis, pricing],
            [
                "多因子の比：Itô補正とdriftの相殺",
                "現在の観測値からの条件付きmartingale",
                "相関座標から独立因子への変換",
                "同じ給付のQ/g価格：相関とnumeraire",
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
    return [
        _markdown(r"""## 6D. 複数因子への拡張（§28.5）

Hull GE pp.679–680と脚注7。元要求をMF01–06へ具体化します。本節には印刷された数値例・追加の式番号はなく、下の11市場・132条件付き状態は全て**合成**です。

### 6D.1 独立因子と期待収益（MF01）

無収入の取引資産f,gについて、独立Wiener $dz_1,\ldots,dz_n$で
$$df/f=\mu_fdt+\sum_i s_{f,i}dz_i,\qquad dg/g=\mu_gdt+\sum_i s_{g,i}dz_i.$$
Q測度では両driftは$r$、一般worldでは $\mu_f=r+\sum_i\lambda_i s_{f,i}$、$\mu_g=r+\sum_i\lambda_i s_{g,i}$。loadingは符号付きです。$\lambda_i$とloadingを同じ独立basisで表し、座標を変えたときに片方だけ据え置きません。時間は年、rate/driftは1/年、loadingと独立リスク価格は1/√年。
"""),
        _markdown(r"""### 6D.2 比のItô式：相対driftとlog drift（MF02）

$R=f/g$、独立basisでは
$$dR/R=[\mu_f-\mu_g+\|s_g\|^2-s_f\cdot s_g]dt+(s_f-s_g)\cdot dz.$$
$g$のworldは $\lambda=s_g$なので $\mu_f=r+s_f\cdot s_g$、$\mu_g=r+\|s_g\|^2$。比の**相対drift**は0になります。log driftは $-\|s_f-s_g\|^2/2$で、0と混同しません。

下の相関三因子例では独立basisへ変換後と同じ演算になり、−.06684+.06904−.00220=0（1/年）。$r_t$が確率的でも共通のr項は各時点で相殺します。後述の価格fixtureでr一定としたことは、この局所的な相殺の追加条件ではありません。
"""),
        _code(
            "from hullkit._multi_factor_lesson import _load_reference as _mf_load, _figures as _mf_figures\n_mf_data, _mf_record = _mf_load()\n_mf_plots = _mf_figures()\n_mf_plots['factor_ratio_ito'].show()\nprint('correlated g drifts:', _mf_record['api_cases'][1]['g_drifts'])"
        ),
        _markdown(r"""### 6D.3 条件付きmartingaleの意味（MF03）

現在の観測比 $R_t>0$から、g測度で $E_g[R_{t+h}\mid\mathcal F_t]=R_t$。一定係数の有限時間GBMなら、未来増分に独立な正規分布を使い、$R_{t+h}=R_t\exp(-vh/2+\sqrt{vh}Z)$、$v=\|s_f-s_g\|^2$。一次・二次モーメントは有限で真のmartingaleです。

一般のゼロdrift SDEだけから真のmartingaleとは言えず、まず局所martingale、条件付き平均には可積分性などの条件が必要です。比の分母gは正値の取引numeraireです。h=0やv=0の退化を正確に扱います。

図は現在比 .65/1.25/2、h=.25/2.5年の6状態です。違うtime0の比や決定的比の値は別の初期市場を表し、同じ市場で起きた不可能な観測とは主張しません。MCは各262144標本、区間±1.96SE、受入境界5SE。Qの比drift $s_g^T C s_g-s_f^T C s_g$は一般に0でなく、未来の平均も変わります。
"""),
        _code(
            "_mf_plots['factor_ratio_conditional'].show()\nprint('observed conditional g means:', [r['g_mean'] for r in _mf_record['api_conditional_means'][12:24]])"
        ),
        _markdown(r"""### 6D.4 相関した因子：脚注7の座標変換（MF05）

相関増分 $dW$に $dW_i dW_j=C_{ij}dt$、$C=L L^T$、$dW=Ldz$を使うと、row loadingは $s_fL,s_gL$。相関座標で
$$\mu_f^{g}=r+s_f^T C s_g,\quad \mu_g^{g}=r+s_g^T C s_g,\quad v=(s_f-s_g)^TC(s_f-s_g).$$
相関座標のrisk vectorは **C s_g** です。$s_g$を独立basisと同じように直接dotしたり、Lへ移した後にさらにCを掛けたりしません。共分散 $s_f^TCs_g=(s_fL)\cdot(s_gL)$は同じで、直交回転しても変わりません。

脚注7が述べる相関因子の独立化をPSD固有分解で実演します。Lの成分・符号自体は一意でなく、比較するのは共分散・drift・価格です。
"""),
        _code(
            "_mf_plots['factor_basis_covariance'].show()\nprint('same-payoff basis errors:', [r['basis_dot_error'] for r in _mf_data['cases']])"
        ),
        _markdown(r"""### 6D.5 同じ給付を複数のnumeraireで価格付け（MF04）

$$f_0=e^{-rh}E_Q[f_h]=g_0E_g[f_h/g_h].$$
任意の可積分な給付Hにも $V_0=e^{-rh}E_Q[H]=g_0E_g[H/g_h]$。図は同じcall $H=(f_h-105)^+$、f0=100、g0=80、r4%、h1.5年です。相関3因子のf市場を固定して、gのloadingを選び直しても同じ給付価格になります。11市場の教師に含む独立市場は別のf市場で、この3市場の価格と同じとは限りません。

Qの割引とg測度のランダムな分母を対応させます。RN密度 $g_h/(g_0e^{rh})$の方向を検査し、raw重みの平均1とQ→gの比平均を照合。自己正規化で誤りを隠しません。独立求積と閉形式、Q/gの直接MCを比較します。この価格実演は**r一定**。§28.4の確率金利では経路内の口座割引か支払日債券測度を使います。
"""),
        _code(
            "_mf_plots['factor_measure_price'].show()\nprint('Q/g independent same-payoff prices:', [[r['price_q'], r['price_g']] for r in _mf_record['pricing'][1:4]])"
        ),
        _markdown(r"""### 6D.6 退化と検証範囲（MF06）

ρ=+1/−1を含むPSD相関を扱い、逆行列は不要です。真に負の固有値・非対称・対角≠1は拒否し、丸めの負値だけを機械精度の境界で扱います。loadingの最後の軸が因子、先行軸だけbroadcast。時刻は年、h≥0、現在比>0、signedloading/負rate可。bool・文字列・複素・object・日時型・非有限値を拒否します。

11市場・132条件付き状態、n=1/2/3、ρ端・近退化・zero loading、直交回転、同一給付価格を独立に検証。直接MCは187集計、8変異を拒否。source hash・結果shape/digest・独立教師の再計算を教材消費時にも確認します。ゼロSEを退化として受け入れるのは数学的に決定的な給付の場合だけです。

多因子の測度変更は分布仮定を自動的に与えません。Black公式への応用は§28.6、交換契約は§28.7、change of numeraireは§28.8で原典要求を別々に受け入れます。
"""),
        _code(
            "assert _mf_record['status'] == 'PASS'\nassert _mf_data['source_requirements'] == [f'MF{n:02d}' for n in range(1,7)]\nassert all(r['rejected'] for r in _mf_record['negative_controls'])\nprint('§28.5: 6 source requirements, 11 markets, 132 conditional states, 187 raw MC summaries, 8 mutations PASS')"
        ),
    ]
