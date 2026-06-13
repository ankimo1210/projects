"""Interactive Plotly builders for the johnhull volumes (existing content).

Peer to :mod:`hullkit.nbplot` (which serves matplotlib/ipympl widgets *inside*
notebooks). These builders return self-contained ``plotly`` figures used by the
offline johnhull portal (``johnhull/report``) and embedded in the Jupyter Book,
so the same pricing logic powers the notebooks and the interactive site.

Design rules (mirrors ``analytics/report``):
- every builder is **deterministic** (fixed seed) and does no I/O, so the portal
  renders with no network and no notebook kernel;
- "the answer" line is drawn in ``ACCENT`` (red ``#d62728``); the portal theme
  remaps that single hue to its accent and greys everything else.

Each ``plotly_*`` wraps an existing :mod:`hullkit` pricing/risk function, so the
visualization can never drift from the maths the books teach.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from . import bsm, credit, hedging, payoffs, risk, trees

SEED = 0
ACCENT = "#d62728"  # remapped to the portal accent; "the important line"
INK = "#1f77b4"  # remapped to ink/grey by the theme


# ---------------------------------------------------------------------------
# Options core: payoffs, Greeks, hedging
# ---------------------------------------------------------------------------


def plotly_strategy_payoffs(S0: float = 100.0) -> go.Figure:
    """Terminal payoff of common option strategies; dropdown switches strategy.

    Wraps :func:`hullkit.payoffs.strategy_payoff` and the ``STRATEGIES`` registry
    (Hull Ch.12). Beginners can *see* how legs combine into bull spreads,
    straddles, butterflies, ...
    """
    s = np.linspace(0.5 * S0, 1.5 * S0, 241)
    specs = [
        ("強気コールスプレッド", payoffs.STRATEGIES["bull_call_spread"](95, 110)),
        ("ストラドル", payoffs.STRATEGIES["straddle"](100)),
        ("バタフライ", payoffs.STRATEGIES["butterfly"](90, 100, 110)),
        ("ストラングル", payoffs.STRATEGIES["strangle"](95, 105)),
        ("プロテクティブプット", payoffs.STRATEGIES["protective_put"](95)),
        ("カバードコール", payoffs.STRATEGIES["covered_call"](110)),
    ]
    fig = go.Figure()
    for i, (label, legs) in enumerate(specs):
        fig.add_trace(
            go.Scatter(
                x=s,
                y=payoffs.strategy_payoff(s, legs),
                mode="lines",
                name=label,
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    buttons = [
        {
            "label": label,
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(specs))]},
                {"title.text": f"満期ペイオフ — {label}"},
            ],
        }
        for i, (label, _legs) in enumerate(specs)
    ]
    fig.add_hline(y=0.0, line_width=1, line_color="gray")
    fig.update_layout(
        title={"text": f"満期ペイオフ — {specs[0][0]}"},
        xaxis_title="満期の原資産価格 S_T",
        yaxis_title="ペイオフ(プレミアム前)",
        updatemenus=[
            {
                "buttons": buttons,
                "direction": "down",
                "x": 1.0,
                "xanchor": "right",
                "y": 1.16,
                "yanchor": "top",
            }
        ],
    )
    return fig


def plotly_delta_vs_spot(K: float = 100.0, r: float = 0.05, sigma: float = 0.20) -> go.Figure:
    """Call delta vs spot, with a slider over time-to-maturity T.

    Wraps :func:`hullkit.bsm.call_delta`. As T -> 0 the smooth S-curve sharpens
    toward a step at the strike — the reason gamma explodes near expiry.
    """
    s = np.linspace(0.5 * K, 1.5 * K, 241)
    maturities = [1.0, 0.5, 0.25, 0.1, 0.02]
    fig = go.Figure()
    for i, t in enumerate(maturities):
        fig.add_trace(
            go.Scatter(
                x=s,
                y=bsm.call_delta(s, K, r, sigma, t),
                mode="lines",
                name=f"T={t:g}",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{t:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(maturities))]},
                {"title.text": f"コールデルタ Δ=e<sup>-qT</sup>N(d₁) vs 原資産 — 残存 T={t:g} 年"},
            ],
        }
        for i, t in enumerate(maturities)
    ]
    fig.update_layout(
        title={"text": f"コールデルタ Δ vs 原資産 — 残存 T={maturities[0]:g} 年"},
        xaxis_title="原資産価格 S",
        yaxis_title="デルタ Δ",
        sliders=[{"active": 0, "currentvalue": {"prefix": "残存年数 T: "}, "steps": steps}],
    )
    return fig


def plotly_delta_hedge_cost(
    S0: float = 49.0,
    K: float = 50.0,
    r: float = 0.05,
    sigma: float = 0.20,
    T: float = 20.0 / 52.0,
    n_paths: int = 4000,
) -> go.Figure:
    """Distribution of delta-hedging cost; slider over rebalance frequency.

    Wraps :func:`hullkit.hedging.simulate_delta_hedge` (Hull §19.4). The dashed
    accent line is the BSM price: as rebalancing gets finer the cost distribution
    tightens around it, independent of the real-world drift.
    """
    bsm_price = float(bsm.call_price(S0, K, r, sigma, T))
    rebals = [1, 4, 13, 52]
    fig = go.Figure()
    for i, n in enumerate(rebals):
        rng = np.random.default_rng(SEED)
        cost = hedging.simulate_delta_hedge(S0, K, r, sigma, T, n, n_paths, rng=rng)
        fig.add_trace(
            go.Histogram(
                x=cost,
                nbinsx=70,
                name=f"{n} 回",
                marker={"color": INK},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{n}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(rebals))]},
                {
                    "title.text": f"デルタヘッジ費用の分布 — リヘッジ {n} 回 "
                    f"(BSM 価格 = {bsm_price:.3f})"
                },
            ],
        }
        for i, n in enumerate(rebals)
    ]
    fig.add_vline(
        x=bsm_price,
        line_color=ACCENT,
        line_width=2,
        line_dash="dash",
        annotation_text="BSM 価格",
        annotation_position="top",
    )
    fig.update_layout(
        title={
            "text": f"デルタヘッジ費用の分布 — リヘッジ {rebals[0]} 回 (BSM 価格 = {bsm_price:.3f})"
        },
        xaxis_title="ヘッジ費用(t=0 割引・1株あたり)",
        yaxis_title="頻度",
        bargap=0.02,
        sliders=[{"active": 0, "currentvalue": {"prefix": "リヘッジ回数: "}, "steps": steps}],
    )
    return fig


# ---------------------------------------------------------------------------
# Numerical methods
# ---------------------------------------------------------------------------


def plotly_tree_convergence(
    S0: float = 100.0,
    K: float = 100.0,
    r: float = 0.05,
    sigma: float = 0.20,
    T: float = 1.0,
    n_max: int = 80,
) -> go.Figure:
    """CRR binomial price vs steps N, converging (with oscillation) to BSM.

    Wraps :func:`hullkit.trees.crr_price` and :func:`hullkit.bsm.call_price`
    (Hull Ch.13). The classic odd/even sawtooth that damps toward the closed form.
    """
    ns = np.arange(1, n_max + 1)
    prices = np.array([trees.crr_price(S0, K, r, sigma, T, int(n)) for n in ns])
    bsm_p = float(bsm.call_price(S0, K, r, sigma, T))
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ns,
            y=prices,
            mode="lines+markers",
            name="二項木 (CRR)",
            line={"color": INK},
            marker={"size": 4},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ns,
            y=np.full(ns.shape, bsm_p),
            mode="lines",
            name="BSM 閉形式",
            line={"color": ACCENT, "width": 2, "dash": "dash"},
        )
    )
    fig.update_layout(
        title={"text": f"二項木 → BSM 収束 (BSM = {bsm_p:.4f})"},
        xaxis_title="ステップ数 N",
        yaxis_title="ヨーロピアンコール価格",
    )
    return fig


# ---------------------------------------------------------------------------
# Risk and credit
# ---------------------------------------------------------------------------


def plotly_var_es(n: int = 2500) -> go.Figure:
    """Historical-simulation VaR & ES on a stylized P&L; slider over confidence.

    Wraps :func:`hullkit.risk.historical_var_es` (Hull Ch.22). A small jump
    component fattens the left tail; raising the confidence pushes VaR (and ES,
    further out) deeper into the loss tail.
    """
    rng = np.random.default_rng(SEED)
    base = rng.standard_normal(n)
    jump = 3.0 * rng.standard_normal(n) * (rng.random(n) < 0.05)
    pnl = base + jump  # daily P&L, gains positive (arbitrary $mm units)

    counts, edges = np.histogram(pnl, bins=70)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(edges[1] - edges[0])
    ymax = float(counts.max())

    fig = go.Figure()
    fig.add_trace(
        go.Bar(x=centers, y=counts, width=width, name="日次 P&L", marker={"color": "#c7c7c7"})
    )
    confs = [0.90, 0.95, 0.975, 0.99]
    for i, c in enumerate(confs):
        var, es = risk.historical_var_es(pnl, alpha=c)
        fig.add_trace(
            go.Scatter(
                x=[-var, -var],
                y=[0, ymax],
                mode="lines",
                name=f"VaR {int(c * 100)}%",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[-es, -es],
                y=[0, ymax],
                mode="lines",
                name=f"ES {int(c * 100)}%",
                line={"color": INK, "width": 2, "dash": "dot"},
                visible=(i == 0),
            )
        )
    steps = []
    for i, c in enumerate(confs):
        vis = [True] + [False] * (2 * len(confs))
        vis[1 + 2 * i] = True
        vis[2 + 2 * i] = True
        steps.append(
            {
                "label": f"{int(c * 100)}%",
                "method": "update",
                "args": [
                    {"visible": vis},
                    {"title.text": f"ヒストリカル VaR / ES — 信頼水準 {int(c * 100)}%"},
                ],
            }
        )
    fig.update_layout(
        title={"text": "ヒストリカル VaR / ES — 信頼水準 90%"},
        xaxis_title="日次 P&L(損失は左)",
        yaxis_title="シナリオ数",
        sliders=[{"active": 0, "currentvalue": {"prefix": "信頼水準: "}, "steps": steps}],
    )
    return fig


def plotly_credit_survival(
    t_max: float = 10.0, recovery: float = 0.4, r: float = 0.03
) -> go.Figure:
    """Survival curve S(t)=e^{-λt}; slider over the hazard λ, title shows 5Y CDS.

    Wraps :func:`hullkit.credit.survival_prob` / :func:`hullkit.credit.cds_spread`
    (Hull Ch.24-25). Higher hazard => faster-decaying survival and a wider par
    CDS spread.
    """
    t = np.linspace(0.0, t_max, 121)
    hazards = [0.005, 0.01, 0.02, 0.04, 0.08]
    fig = go.Figure()
    spreads_bps = []
    for i, h in enumerate(hazards):
        spread = credit.cds_spread(h, recovery, r, 5.0) * 1e4
        spreads_bps.append(spread)
        fig.add_trace(
            go.Scatter(
                x=t,
                y=np.exp(-h * t),
                mode="lines",
                name=f"λ={h:g}",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{h:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(hazards))]},
                {
                    "title.text": f"生存確率 S(t)=e<sup>-λt</sup> — λ={h:g} "
                    f"(5Y CDS ≈ {spreads_bps[i]:.0f} bps)"
                },
            ],
        }
        for i, h in enumerate(hazards)
    ]
    fig.update_layout(
        title={
            "text": f"生存確率 S(t)=e<sup>-λt</sup> — λ={hazards[0]:g} "
            f"(5Y CDS ≈ {spreads_bps[0]:.0f} bps)"
        },
        xaxis_title="年数 t",
        yaxis_title="生存確率 S(t)",
        yaxis_range=[0, 1.02],
        sliders=[{"active": 0, "currentvalue": {"prefix": "ハザード率 λ: "}, "steps": steps}],
    )
    return fig


# ---------------------------------------------------------------------------
# A1 — stochastic calculus (volume 13)
# ---------------------------------------------------------------------------


def plotly_quadratic_variation(T: float = 1.0) -> go.Figure:
    """Running quadratic variation [W]_t of a Brownian path -> the line y=t.

    Wraps :func:`hullkit.sde.running_quadratic_variation`. Slider refines the
    mesh; the staircase Σ(ΔW)² hugs the diagonal ever more tightly (Shreve II §3.4).
    """
    from . import sde

    steps_list = [16, 64, 256, 1024]
    fig = go.Figure()
    for i, n in enumerate(steps_list):
        w = sde.brownian_paths(T, n, 1, rng=np.random.default_rng(7))
        rqv = sde.running_quadratic_variation(w)[0]
        fig.add_trace(
            go.Scatter(
                x=np.linspace(0.0, T, n + 1),
                y=rqv,
                mode="lines",
                name=f"n={n}",
                line={"color": ACCENT, "width": 2},
                visible=(i == 0),
            )
        )
    t_ref = np.linspace(0.0, T, 200)
    fig.add_trace(
        go.Scatter(
            x=t_ref, y=t_ref, mode="lines", name="y = t", line={"color": INK, "dash": "dash"}
        )
    )
    steps = [
        {
            "label": f"{n}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(steps_list))] + [True]},
                {"title.text": f"二次変分 [W]_t → t — 分割数 n={n}"},
            ],
        }
        for i, n in enumerate(steps_list)
    ]
    fig.update_layout(
        title={"text": f"二次変分 [W]_t → t — 分割数 n={steps_list[0]}"},
        xaxis_title="時間 t",
        yaxis_title="累積二次変分 Σ(ΔW)²",
        sliders=[{"active": 0, "currentvalue": {"prefix": "分割数 n: "}, "steps": steps}],
    )
    return fig


def plotly_ito_correction(T: float = 1.0, n_paths: int = 6000) -> go.Figure:
    """Itô vs Stratonovich Riemann sums of ∫ W dW; the gap is the ½[W]_T correction.

    Wraps :func:`hullkit.sde.ito_riemann_sum`. Left-point (Itô) sums cluster at
    ½(W_T²−[W]_T) (mean 0), midpoint (Stratonovich) at ½W_T² (mean ½T); the
    constant ½T gap is the Itô correction, stable as the mesh refines (Shreve II §4.3).
    """
    from . import sde

    steps_list = [8, 32, 128, 512]
    fig = go.Figure()
    for i, n in enumerate(steps_list):
        w = sde.brownian_paths(T, n, n_paths, rng=np.random.default_rng(11))
        left = sde.ito_riemann_sum(w, alpha=0.0)
        mid = sde.ito_riemann_sum(w, alpha=0.5)
        fig.add_trace(
            go.Histogram(
                x=left,
                nbinsx=55,
                name="左点(伊藤)",
                marker={"color": INK},
                opacity=0.6,
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Histogram(
                x=mid,
                nbinsx=55,
                name="中点(Stratonovich)",
                marker={"color": ACCENT},
                opacity=0.6,
                visible=(i == 0),
            )
        )
    fig.add_vline(x=0.0, line_color=INK, line_dash="dot", annotation_text="伊藤 平均 0")
    fig.add_vline(
        x=0.5 * T, line_color=ACCENT, line_dash="dot", annotation_text="Stratonovich 平均 ½T"
    )
    steps = []
    for i, n in enumerate(steps_list):
        vis = [False] * (2 * len(steps_list))
        vis[2 * i] = True
        vis[2 * i + 1] = True
        steps.append(
            {
                "label": f"{n}",
                "method": "update",
                "args": [
                    {"visible": vis},
                    {"title.text": f"伊藤 vs Stratonovich — 分割数 n={n}(差 = ½[W]_T → ½T)"},
                ],
            }
        )
    fig.update_layout(
        barmode="overlay",
        title={"text": f"伊藤 vs Stratonovich — 分割数 n={steps_list[0]}(差 = ½[W]_T → ½T)"},
        xaxis_title="∫₀ᵀ W dW の近似値",
        yaxis_title="頻度",
        sliders=[{"active": 0, "currentvalue": {"prefix": "分割数 n: "}, "steps": steps}],
    )
    return fig


def plotly_girsanov(
    S0: float = 100.0,
    K: float = 100.0,
    r: float = 0.05,
    sigma: float = 0.20,
    T: float = 1.0,
    n_paths: int = 80000,
) -> go.Figure:
    """Girsanov in action: change the real-world drift μ, the risk-neutral law stays put.

    Wraps :func:`hullkit.sde.girsanov_weights`. The grey density is S_T under the
    physical drift μ (slider); reweighting by dQ/dP gives the accent density, which
    does NOT move with μ — and the implied call price stays at the BSM value
    (Shreve II §5.2-5.4; the measure change Hull's pricing assumes).
    """
    from . import mc, sde

    edges = np.linspace(20.0, 260.0, 61)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(edges[1] - edges[0])
    bsm_price = float(bsm.call_price(S0, K, r, sigma, T))
    mus = [0.00, 0.05, 0.10, 0.15, 0.20]
    fig = go.Figure()
    q_prices = []
    for i, mu in enumerate(mus):
        s_t = mc.simulate_gbm_paths(S0, mu, sigma, T, 1, n_paths, rng=np.random.default_rng(13))[
            :, -1
        ]
        w = sde.girsanov_weights(s_t, S0, sigma, T, mu_from=mu, mu_to=r)
        q_prices.append(float(np.mean(w * np.exp(-r * T) * np.maximum(s_t - K, 0.0))))
        dens_p, _ = np.histogram(s_t, bins=edges, density=True)
        dens_q, _ = np.histogram(s_t, bins=edges, weights=w, density=True)
        fig.add_trace(
            go.Bar(
                x=centers,
                y=dens_p,
                width=width,
                name="P (実世界 μ)",
                marker={"color": "#c7c7c7"},
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Bar(
                x=centers,
                y=dens_q,
                width=width,
                name="Q (リスク中立 r)",
                marker={"color": ACCENT},
                opacity=0.65,
                visible=(i == 0),
            )
        )
    steps = []
    for i, mu in enumerate(mus):
        vis = [False] * (2 * len(mus))
        vis[2 * i] = True
        vis[2 * i + 1] = True
        steps.append(
            {
                "label": f"{mu:.2f}",
                "method": "update",
                "args": [
                    {"visible": vis},
                    {
                        "title.text": f"Girsanov: μ={mu:.0%} でも Q は不変 — "
                        f"Q コール価格 ≈ {q_prices[i]:.2f}(BSM={bsm_price:.2f})"
                    },
                ],
            }
        )
    fig.update_layout(
        barmode="overlay",
        title={
            "text": f"Girsanov: μ={mus[0]:.0%} でも Q は不変 — "
            f"Q コール価格 ≈ {q_prices[0]:.2f}(BSM={bsm_price:.2f})"
        },
        xaxis_title="満期株価 S_T",
        yaxis_title="確率密度",
        sliders=[{"active": 0, "currentvalue": {"prefix": "実世界ドリフト μ: "}, "steps": steps}],
    )
    return fig
