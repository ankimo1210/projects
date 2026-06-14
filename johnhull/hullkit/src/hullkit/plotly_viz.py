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

from . import bsm, credit, hedging, payoffs, rates, risk, swaps, trees, volatility

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


def plotly_quadratic_variation(T: float = 1.0, n_paths: int = 400) -> go.Figure:
    """Quadratic variation [W]_t -> t, as a mean ±std band over many paths.

    Wraps :func:`hullkit.sde.running_quadratic_variation`. The band is the sampling
    spread of Σ(ΔW)² across paths (theory: std ∝ 1/√n); refine the mesh and the band
    collapses onto the diagonal y=t — that collapse *is* the a.s. convergence to t
    (Shreve II §3.4). A single path would just look noisy; the band shows the law.
    """
    from . import sde

    steps_list = [16, 64, 256, 1024]
    fig = go.Figure()
    for i, n in enumerate(steps_list):
        w = sde.brownian_paths(T, n, n_paths, rng=np.random.default_rng(7))
        rqv = sde.running_quadratic_variation(w)
        tg = np.linspace(0.0, T, n + 1)
        mean = rqv.mean(axis=0)
        sd = rqv.std(axis=0)
        fig.add_trace(
            go.Scatter(
                x=tg,
                y=mean + sd,
                mode="lines",
                line={"width": 0},
                showlegend=False,
                hoverinfo="skip",
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=tg,
                y=mean - sd,
                mode="lines",
                line={"width": 0},
                fill="tonexty",
                fillcolor="rgba(37,99,235,0.15)",
                name=f"±std (n={n})",
                hoverinfo="skip",
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=tg,
                y=mean,
                mode="lines",
                name=f"平均 [W]_t (n={n})",
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
    steps = []
    for i, n in enumerate(steps_list):
        vis = [False] * (3 * len(steps_list))
        vis[3 * i] = vis[3 * i + 1] = vis[3 * i + 2] = True
        steps.append(
            {
                "label": f"{n}",
                "method": "update",
                "args": [
                    {"visible": [*vis, True]},
                    {"title.text": f"二次変分 [W]_t → t — 分割数 n={n}(帯=±std, n↑ で収縮)"},
                ],
            }
        )
    fig.update_layout(
        title={"text": f"二次変分 [W]_t → t — 分割数 n={steps_list[0]}(帯=±std, n↑ で収縮)"},
        xaxis_title="時間 t",
        yaxis_title="累積二次変分 Σ(ΔW)²",
        sliders=[{"active": 0, "currentvalue": {"prefix": "分割数 n: "}, "steps": steps}],
    )
    return fig


def plotly_ito_correction(T: float = 1.0, n_paths: int = 6000) -> go.Figure:
    """The Itô correction itself: (midpoint − left-point) sum of ∫W dW = ½[W]_t.

    Wraps :func:`hullkit.sde.ito_riemann_sum`. On every path the Stratonovich
    (midpoint) and Itô (left-point) sums differ by exactly ½Σ(ΔW)²; that difference
    concentrates on ½T and sharpens as the mesh refines — the correction becomes
    deterministic (Shreve II §4.3). The marginal sums stay wide (std≈0.7 for any n);
    their *difference* is the object that converges, so we plot it directly.
    """
    from . import sde

    steps_list = [8, 32, 128, 512]
    fig = go.Figure()
    for i, n in enumerate(steps_list):
        w = sde.brownian_paths(T, n, n_paths, rng=np.random.default_rng(11))
        diff = sde.ito_riemann_sum(w, alpha=0.5) - sde.ito_riemann_sum(w, alpha=0.0)
        fig.add_trace(
            go.Histogram(
                x=diff, nbinsx=60, name=f"n={n}", marker={"color": ACCENT}, visible=(i == 0)
            )
        )
    fig.add_vline(x=0.5 * T, line_color=INK, line_dash="dash", annotation_text=f"½T = {0.5 * T:g}")
    steps = [
        {
            "label": f"{n}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(steps_list))]},
                {
                    "title.text": f"伊藤の補正項 ½[W]_t = 中点和 − 左点和 — "
                    f"分割数 n={n}(n↑ で ½T={0.5 * T:g} に集中)"
                },
            ],
        }
        for i, n in enumerate(steps_list)
    ]
    fig.update_layout(
        title={
            "text": f"伊藤の補正項 ½[W]_t = 中点和 − 左点和 — "
            f"分割数 n={steps_list[0]}(n↑ で ½T={0.5 * T:g} に集中)"
        },
        xaxis_title="中点和 − 左点和 = ½Σ(ΔW)²",
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
    n_paths: int = 150000,
) -> go.Figure:
    """Girsanov in action: change the real-world drift μ, the risk-neutral law stays put.

    Wraps :func:`hullkit.sde.girsanov_weights`. Grey bars = S_T under the physical
    drift μ (slider); reweighting by dQ/dP gives the accent bars, which track the
    fixed risk-neutral lognormal (dark line) for every μ — and the self-normalized
    call price stays at the BSM value (Shreve II §5.2-5.4). More paths + the
    ratio estimator keep the high-μ reweighting (lower ESS) visually stable.
    """
    from . import mc, sde

    edges = np.linspace(20.0, 260.0, 61)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(edges[1] - edges[0])
    bsm_price = float(bsm.call_price(S0, K, r, sigma, T))
    # invariant risk-neutral density of S_T (lognormal with drift r) — the target
    m_log = np.log(S0) + (r - 0.5 * sigma**2) * T
    s_log = sigma * np.sqrt(T)
    q_pdf = np.exp(-((np.log(centers) - m_log) ** 2) / (2.0 * s_log**2)) / (
        centers * s_log * np.sqrt(2.0 * np.pi)
    )
    mus = [0.00, 0.05, 0.10, 0.15, 0.20]
    fig = go.Figure()
    q_prices = []
    for i, mu in enumerate(mus):
        s_t = mc.simulate_gbm_paths(S0, mu, sigma, T, 1, n_paths, rng=np.random.default_rng(13))[
            :, -1
        ]
        w = sde.girsanov_weights(s_t, S0, sigma, T, mu_from=mu, mu_to=r)
        # self-normalized (ratio) estimator — lower variance than the plain mean
        q_prices.append(float(np.exp(-r * T) * np.sum(w * np.maximum(s_t - K, 0.0)) / np.sum(w)))
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
                opacity=0.55,
                visible=(i == 0),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=centers,
            y=q_pdf,
            mode="lines",
            name="Q 理論密度",
            line={"color": INK, "width": 2},
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
                    {"visible": [*vis, True]},
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


# ---------------------------------------------------------------------------
# A2 — stochastic volatility & Fourier pricing (volume 14)
# ---------------------------------------------------------------------------


def plotly_heston_smile(
    S0=100.0, r=0.05, T=1.0, v0=0.04, kappa=1.5, theta=0.04, xi=0.6
) -> go.Figure:
    """Heston implied-vol smile; slider over the spot-vol correlation ρ.

    Each Heston price (COS on the characteristic function) is inverted to a BSM
    implied vol. ρ<0 tilts the smile down (the equity skew), ρ>0 up; vol-of-vol ξ
    sets the curvature (Gatheral, *The Volatility Surface* Ch.3).
    """
    from . import fourier, heston, volatility

    ks = np.linspace(82.0, 120.0, 20)
    rhos = [-0.8, -0.4, 0.0, 0.4, 0.8]
    fig = go.Figure()
    for i, rho in enumerate(rhos):

        def cf(u, rho=rho):
            return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)

        iv = [volatility.implied_vol(fourier.cos_price(cf, S0, k, r, T), S0, k, r, T) for k in ks]
        fig.add_trace(
            go.Scatter(
                x=ks,
                y=iv,
                mode="lines+markers",
                name=f"ρ={rho:+.1f}",
                line={"color": ACCENT, "width": 2.5},
                marker={"size": 5},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{rho:+.1f}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(rhos))]},
                {"title.text": f"Heston インプライドボラ smile — ρ={rho:+.1f}(ρ<0 で下方スキュー)"},
            ],
        }
        for i, rho in enumerate(rhos)
    ]
    fig.update_layout(
        title={"text": f"Heston インプライドボラ smile — ρ={rhos[0]:+.1f}(ρ<0 で下方スキュー)"},
        xaxis_title="ストライク K",
        yaxis_title="インプライド・ボラティリティ",
        sliders=[{"active": 0, "currentvalue": {"prefix": "相関 ρ: "}, "steps": steps}],
    )
    return fig


def plotly_cos_density_convergence(
    r=0.05, T=1.0, v0=0.04, kappa=1.5, theta=0.04, xi=0.6, rho=-0.7
) -> go.Figure:
    """COS-recovered density of the log-return vs the number of cosine terms N.

    A handful of terms already capture the bulk; low N shows Gibbs-type wiggles
    that vanish as N grows toward the dark reference (Fang-Oosterlee 2008).
    """
    from . import fourier, heston

    def cf(u):
        return heston.heston_cf(u, r, T, v0, kappa, theta, xi, rho)

    y_ref, f_ref = fourier.cos_density(cf, N=256, L=12.0, n_grid=400)
    ns = [4, 8, 12, 20, 40]
    fig = go.Figure()
    for i, n in enumerate(ns):
        _, f = fourier.cos_density(cf, N=n, L=12.0, n_grid=400)
        fig.add_trace(
            go.Scatter(
                x=y_ref,
                y=f,
                mode="lines",
                name=f"N={n}",
                line={"color": ACCENT, "width": 2},
                visible=(i == 0),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=y_ref, y=f_ref, mode="lines", name="N=256 (基準)", line={"color": INK, "dash": "dash"}
        )
    )
    steps = [
        {
            "label": f"{n}",
            "method": "update",
            "args": [
                {"visible": [*[j == i for j in range(len(ns))], True]},
                {"title.text": f"COS 法で復元した密度 — 項数 N={n}(N↑ で基準へ収束)"},
            ],
        }
        for i, n in enumerate(ns)
    ]
    fig.update_layout(
        title={"text": f"COS 法で復元した密度 — 項数 N={ns[0]}(N↑ で基準へ収束)"},
        xaxis_title="対数収益率 y = ln(S_T/S0)",
        yaxis_title="確率密度",
        sliders=[{"active": 0, "currentvalue": {"prefix": "項数 N: "}, "steps": steps}],
    )
    return fig


def plotly_sabr_smile(F=100.0, T=1.0, alpha=0.30, beta=1.0, rho=-0.30) -> go.Figure:
    """SABR (Hagan) implied-vol smile; slider over vol-of-vol ν.

    ν=0 is flat at the backbone α; larger ν deepens the curvature and ρ<0 adds a
    downward tilt — the market-standard smile parametrization (Hagan et al. 2002).
    """
    from . import sabr

    ks = np.linspace(70.0, 135.0, 27)
    nus = [0.0, 0.2, 0.4, 0.6, 0.8]
    fig = go.Figure()
    for i, nu in enumerate(nus):
        iv = [sabr.sabr_implied_vol(F, k, T, alpha, beta, rho, nu) for k in ks]
        fig.add_trace(
            go.Scatter(
                x=ks,
                y=iv,
                mode="lines",
                name=f"ν={nu:g}",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{nu:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(nus))]},
                {"title.text": f"SABR スマイル — vol-of-vol ν={nu:g}(β={beta:g}, ρ={rho:+.1f})"},
            ],
        }
        for i, nu in enumerate(nus)
    ]
    fig.update_layout(
        title={"text": f"SABR スマイル — vol-of-vol ν={nus[0]:g}(β={beta:g}, ρ={rho:+.1f})"},
        xaxis_title="ストライク K",
        yaxis_title="インプライド・ボラティリティ",
        sliders=[{"active": 0, "currentvalue": {"prefix": "vol-of-vol ν: "}, "steps": steps}],
    )
    return fig


# ---------------------------------------------------------------------------
# A3 — advanced numerical methods (volume 15)
# ---------------------------------------------------------------------------


def plotly_mc_variance_reduction(S0=100.0, K=100.0, r=0.05, sigma=0.20, T=1.0) -> go.Figure:
    """Pricing error vs sample size N for four MC schemes (log-log).

    Wraps :func:`hullkit.mc_advanced.error_vs_n`. Control variates lower the level,
    antithetic helps modestly, and Sobol QMC bends the slope from ~N^{-1/2} toward
    ~N^{-1} (Glasserman Ch.4-5).
    """
    from . import mc_advanced as mca

    out = mca.error_vs_n(S0, K, r, sigma, T, ms=range(6, 17), seed=0)
    styles = [
        ("plain", "プレーン MC", INK, "solid"),
        ("antithetic", "アンチセティック", "#7f7f7f", "dot"),
        ("control_variate", "制御変量", "#2ca02c", "dash"),
        ("qmc", "Sobol QMC", ACCENT, "solid"),
    ]
    fig = go.Figure()
    for key, label, color, dash in styles:
        y = [max(e, 1e-6) for e in out[key]]
        fig.add_trace(
            go.Scatter(
                x=out["N"],
                y=y,
                mode="lines+markers",
                name=label,
                line={"color": color, "dash": dash, "width": 2},
            )
        )
    fig.update_layout(
        title={"text": "価格誤差 vs サンプル数 N(手法別・両対数)"},
        xaxis_title="サンプル数 N",
        yaxis_title="|価格 − BSM|",
        xaxis_type="log",
        yaxis_type="log",
    )
    return fig


def plotly_qmc_vs_pseudo(n_pow=9, seed=0) -> go.Figure:
    """Pseudo-random vs Sobol points on the unit square (N = 2^n_pow).

    Pseudo-random draws clump and leave gaps; the Sobol low-discrepancy sequence
    fills space evenly — why QMC integrates smooth payoffs faster.
    """
    from plotly.subplots import make_subplots
    from scipy.stats import qmc

    ps = np.random.default_rng(seed).random((2**n_pow, 2))
    sob = qmc.Sobol(d=2, scramble=True, seed=seed).random_base2(n_pow)
    fig = make_subplots(rows=1, cols=2, subplot_titles=("擬似乱数(むら・隙間)", "Sobol 列(一様)"))
    fig.add_trace(
        go.Scatter(
            x=ps[:, 0],
            y=ps[:, 1],
            mode="markers",
            marker={"size": 3, "color": INK},
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=sob[:, 0],
            y=sob[:, 1],
            mode="markers",
            marker={"size": 3, "color": ACCENT},
            showlegend=False,
        ),
        row=1,
        col=2,
    )
    fig.update_layout(title={"text": f"低食い違い列: 擬似乱数 vs Sobol(各 {2**n_pow} 点)"})
    return fig


def plotly_american_boundary(S0=100.0, K=100.0, r=0.05, T=1.0) -> go.Figure:
    """American-put early-exercise boundary S*(τ); slider over volatility σ.

    Wraps :func:`hullkit.fd.fd_vanilla` (Crank-Nicolson, ``return_boundary``).
    Below S*(τ) it is optimal to exercise; the boundary rises to K at expiry and
    sits lower for higher σ (more value in waiting).
    """
    from . import fd

    sigmas = [0.15, 0.20, 0.30, 0.40]
    fig = go.Figure()
    for i, sig in enumerate(sigmas):
        _, taus, bnd = fd.fd_vanilla(
            S0,
            K,
            r,
            sig,
            T,
            kind="put",
            american=True,
            method="cn",
            return_boundary=True,
            n_s=300,
            n_t=300,
        )
        fig.add_trace(
            go.Scatter(
                x=taus,
                y=bnd,
                mode="lines",
                name=f"σ={sig:g}",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    fig.add_hline(y=K, line_dash="dash", line_color=INK, annotation_text="K（行使価格）")
    steps = [
        {
            "label": f"{sig:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(sigmas))]},
                {"title.text": f"アメリカンプットの早期行使境界 S*(τ) — σ={sig:g}"},
            ],
        }
        for i, sig in enumerate(sigmas)
    ]
    fig.update_layout(
        title={"text": f"アメリカンプットの早期行使境界 S*(τ) — σ={sigmas[0]:g}"},
        xaxis_title="残存期間 τ",
        yaxis_title="行使境界 S*(τ)",
        sliders=[{"active": 0, "currentvalue": {"prefix": "ボラティリティ σ: "}, "steps": steps}],
    )
    return fig


# ---------------------------------------------------------------------------
# A4 — XVA & counterparty credit (volume 16)
# ---------------------------------------------------------------------------


def plotly_exposure_profile(S0=100.0, r=0.05, K=None, T=1.0) -> go.Figure:
    """Expected exposure (EE) and potential future exposure (PFE) of a forward.

    Wraps :func:`hullkit.xva.forward_exposure`. EE drives CVA; PFE (a high quantile)
    sizes credit limits. Slider over σ shows both profiles widen with volatility.
    """
    from . import xva

    if K is None:
        K = S0 * np.exp(r * T)
    sigmas = [0.15, 0.20, 0.30, 0.40]
    fig = go.Figure()
    for i, sig in enumerate(sigmas):
        t, mtm = xva.forward_exposure(
            S0, r, sig, K, T, n_steps=50, n_paths=40_000, rng=np.random.default_rng(0)
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=xva.pfe(mtm, 0.975),
                mode="lines",
                name="PFE 97.5%",
                line={"color": INK, "dash": "dot"},
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t,
                y=xva.expected_exposure(mtm),
                mode="lines",
                name="EE",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    steps = []
    for i, sig in enumerate(sigmas):
        vis = [False] * (2 * len(sigmas))
        vis[2 * i] = vis[2 * i + 1] = True
        steps.append(
            {
                "label": f"{sig:g}",
                "method": "update",
                "args": [
                    {"visible": vis},
                    {"title.text": f"フォワードのエクスポージャ EE / PFE — σ={sig:g}"},
                ],
            }
        )
    fig.update_layout(
        title={"text": f"フォワードのエクスポージャ EE / PFE — σ={sigmas[0]:g}"},
        xaxis_title="時間 t",
        yaxis_title="エクスポージャ",
        sliders=[{"active": 0, "currentvalue": {"prefix": "ボラティリティ σ: "}, "steps": steps}],
    )
    return fig


def plotly_portfolio_loss_correlation(pd=0.05, n_names=100) -> go.Figure:
    """Pool-loss distribution; slider over default correlation ρ (the 2008 story).

    Wraps :func:`hullkit.copula.portfolio_loss_samples`. The mean stays at the
    marginal default rate ``pd`` for every ρ, but the tail fattens dramatically as
    correlation rises — senior tranches that looked safe are not.
    """
    from . import copula

    edges = np.linspace(0.0, 0.4, 49)
    centers = 0.5 * (edges[:-1] + edges[1:])
    width = float(edges[1] - edges[0])
    rhos = [0.0, 0.1, 0.3, 0.5]
    fig = go.Figure()
    for i, rho in enumerate(rhos):
        loss = copula.portfolio_loss_samples(pd, rho, n_names, 40_000, np.random.default_rng(1))
        dens, _ = np.histogram(loss, bins=edges, density=True)
        fig.add_trace(
            go.Bar(
                x=centers,
                y=dens,
                width=width,
                name=f"ρ={rho:g}",
                marker={"color": ACCENT},
                visible=(i == 0),
            )
        )
    fig.add_vline(x=pd, line_color=INK, line_dash="dash", annotation_text=f"平均=pd={pd:g}")
    steps = [
        {
            "label": f"{rho:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(rhos))]},
                {
                    "title.text": f"ポートフォリオ損失分布 — 相関 ρ={rho:g}(平均は pd 不変・ρ↑ でテール肥大)"
                },
            ],
        }
        for i, rho in enumerate(rhos)
    ]
    fig.update_layout(
        title={
            "text": f"ポートフォリオ損失分布 — 相関 ρ={rhos[0]:g}(平均は pd 不変・ρ↑ でテール肥大)"
        },
        xaxis_title="損失割合 L",
        yaxis_title="確率密度",
        sliders=[{"active": 0, "currentvalue": {"prefix": "相関 ρ: "}, "steps": steps}],
    )
    return fig


def plotly_copula_scatter(n=3000) -> go.Figure:
    """Gaussian-copula samples (U, V); slider over ρ shows joint-default clustering.

    Wraps :func:`hullkit.copula.gaussian_copula_samples`. As ρ grows the points
    pile onto the diagonal — high U tends to come with high V (tail dependence in
    the latent factors), i.e. names default together.
    """
    from . import copula

    rhos = [0.0, 0.3, 0.6, 0.9]
    fig = go.Figure()
    for i, rho in enumerate(rhos):
        u, v = copula.gaussian_copula_samples(rho, n, np.random.default_rng(2))
        fig.add_trace(
            go.Scatter(
                x=u,
                y=v,
                mode="markers",
                name=f"ρ={rho:g}",
                marker={"size": 3, "color": ACCENT},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{rho:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(rhos))]},
                {
                    "title.text": f"ガウシアンコピュラ標本 — 相関 ρ={rho:g}(ρ↑ で同時デフォルトが集まる)"
                },
            ],
        }
        for i, rho in enumerate(rhos)
    ]
    fig.update_layout(
        title={"text": f"ガウシアンコピュラ標本 — 相関 ρ={rhos[0]:g}(ρ↑ で同時デフォルトが集まる)"},
        xaxis_title="U(名柄1の分位)",
        yaxis_title="V(名柄2の分位)",
        sliders=[{"active": 0, "currentvalue": {"prefix": "相関 ρ: "}, "steps": steps}],
    )
    return fig


# ---------------------------------------------------------------------------
# Extra coverage — Greeks, hedging, lattice, GARCH, structural credit,
# diversification, rates/swaps, exotics (all wrap existing hullkit functions).
# ---------------------------------------------------------------------------


def plotly_gamma_surface(K=100.0, r=0.05, sigma=0.20) -> go.Figure:
    """Gamma Γ(S, T) as a surface — the ridge at the strike spikes near expiry.

    Wraps :func:`hullkit.bsm.gamma` (Hull Ch.19). Explains why ATM options are
    hardest to hedge close to maturity.
    """
    s = np.linspace(60.0, 140.0, 80)
    t = np.linspace(0.05, 1.0, 60)
    gamma = bsm.gamma(s[None, :], K, r, sigma, t[:, None])
    fig = go.Figure(go.Heatmap(x=s, y=t, z=gamma, colorscale="Greys", colorbar={"title": "Γ"}))
    fig.update_layout(
        title={"text": "ガンマ曲面 Γ(S, T): ストライク近傍・満期直前で尖る"},
        xaxis_title="原資産 S",
        yaxis_title="残存 T",
    )
    return fig


def plotly_stop_loss_vs_delta_hedge(
    S0=49.0, K=50.0, r=0.05, sigma=0.20, T=20.0 / 52.0, n_paths=4000
) -> go.Figure:
    """Naive stop-loss hedging vs delta hedging; slider over rebalance frequency.

    Wraps :func:`hullkit.hedging.simulate_stop_loss_hedge` and ``simulate_delta_hedge``
    (Hull §19.2/§19.4). Stop-loss stays biased and dispersed; delta hedging tightens
    onto the BSM price.
    """
    bsm_price = float(bsm.call_price(S0, K, r, sigma, T))
    rebals = [4, 13, 52]
    fig = go.Figure()
    for i, n in enumerate(rebals):
        sl = hedging.simulate_stop_loss_hedge(
            S0, K, r, sigma, T, n, n_paths, rng=np.random.default_rng(0)
        )
        dl = hedging.simulate_delta_hedge(
            S0, K, r, sigma, T, n, n_paths, rng=np.random.default_rng(0)
        )
        fig.add_trace(
            go.Histogram(
                x=sl,
                nbinsx=60,
                name="ストップロス",
                marker={"color": INK},
                opacity=0.6,
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Histogram(
                x=dl,
                nbinsx=60,
                name="デルタヘッジ",
                marker={"color": ACCENT},
                opacity=0.6,
                visible=(i == 0),
            )
        )
    fig.add_vline(x=bsm_price, line_color="#111111", line_dash="dash", annotation_text="BSM 価格")
    steps = []
    for i, n in enumerate(rebals):
        vis = [False] * (2 * len(rebals))
        vis[2 * i] = vis[2 * i + 1] = True
        steps.append(
            {
                "label": f"{n}",
                "method": "update",
                "args": [
                    {"visible": vis},
                    {
                        "title.text": f"ストップロス vs デルタヘッジ費用 — リヘッジ {n} 回(BSM={bsm_price:.3f})"
                    },
                ],
            }
        )
    fig.update_layout(
        barmode="overlay",
        title={
            "text": f"ストップロス vs デルタヘッジ費用 — リヘッジ {rebals[0]} 回(BSM={bsm_price:.3f})"
        },
        xaxis_title="ヘッジ費用(t=0 割引)",
        yaxis_title="頻度",
        sliders=[{"active": 0, "currentvalue": {"prefix": "リヘッジ回数: "}, "steps": steps}],
    )
    return fig


def plotly_binomial_lattice(
    S0=100.0, K=100.0, r=0.05, sigma=0.20, T=1.0, n=5, kind="put"
) -> go.Figure:
    """The CRR lattice itself — nodes coloured by (American) option value.

    Wraps :func:`hullkit.trees.binomial_tree` (Hull Ch.13). Makes backward induction
    and the early-exercise region visible.
    """
    u, d = trees.crr_params(sigma, T / n)
    stock, option = trees.binomial_tree(S0, K, r, T, n, u, d, kind=kind, american=True)
    edge_x, edge_y = [], []
    for i in range(n):
        for j in range(i + 1):
            for jj in (j, j + 1):
                edge_x += [i, i + 1, None]
                edge_y += [float(stock[i][j]), float(stock[i + 1][jj]), None]
    nx, ny, nval, ntext = [], [], [], []
    for i in range(n + 1):
        for j in range(i + 1):
            nx.append(i)
            ny.append(float(stock[i][j]))
            nval.append(float(option[i][j]))
            ntext.append(f"S={stock[i][j]:.1f}<br>V={option[i][j]:.2f}")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line={"color": "#c7c7c7", "width": 1},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=nx,
            y=ny,
            mode="markers",
            text=ntext,
            hovertemplate="%{text}<extra></extra>",
            marker={
                "size": 16,
                "color": nval,
                "colorscale": "Greys",
                "colorbar": {"title": "V"},
                "line": {"color": INK, "width": 1},
            },
            showlegend=False,
        )
    )
    fig.update_layout(
        title={"text": f"二項木格子(N={n}, アメリカン{kind}): 後ろ向き帰納(色=オプション価値)"},
        xaxis_title="ステップ i",
        yaxis_title="株価 S",
    )
    return fig


def plotly_garch_volatility(n=400) -> go.Figure:
    """Volatility clustering: EWMA vs GARCH(1,1) annualized vol with the long-run line.

    Wraps :func:`hullkit.volatility.garch11_variance` / ``ewma_variance`` (Hull Ch.23).
    Both track bursts; GARCH mean-reverts to the long-run level.
    """
    omega, alpha, beta = 2e-6, 0.08, 0.90
    v_long = volatility.garch11_long_run(omega, alpha, beta)
    rng = np.random.default_rng(0)
    v = v_long
    rets = np.empty(n)
    for k in range(n):
        rets[k] = np.sqrt(v) * rng.standard_normal()
        v = omega + alpha * rets[k] ** 2 + beta * v
    ann = lambda var: np.sqrt(np.maximum(var, 0.0) * 252.0)  # noqa: E731
    x = np.arange(n)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ann(volatility.garch11_variance(rets, omega, alpha, beta)),
            mode="lines",
            name="GARCH(1,1)",
            line={"color": ACCENT, "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x,
            y=ann(volatility.ewma_variance(rets)),
            mode="lines",
            name="EWMA(λ=0.94)",
            line={"color": INK, "dash": "dot"},
        )
    )
    fig.add_hline(
        y=float(np.sqrt(v_long * 252.0)),
        line_dash="dash",
        line_color="#111111",
        annotation_text="長期ボラ",
    )
    fig.update_layout(
        title={"text": "ボラティリティ・クラスタリング: EWMA vs GARCH(年率)"},
        xaxis_title="日",
        yaxis_title="年率ボラティリティ",
    )
    return fig


def plotly_garch_term_structure(horizon=250) -> go.Figure:
    """GARCH variance forecast term structure — mean reversion to the long-run vol.

    Wraps :func:`hullkit.volatility.garch11_forecast` (Hull eq. 23.13). Whether the
    market starts calm or stressed, the forecast pulls toward the long-run level.
    """
    omega, alpha, beta = 3e-6, 0.06, 0.92
    v_long = volatility.garch11_long_run(omega, alpha, beta)
    k = np.arange(1, horizon + 1)
    series = [
        ("高ボラ start", 4.0 * v_long, ACCENT, "solid"),
        ("長期水準 start", v_long, "#7f7f7f", "dash"),
        ("低ボラ start", 0.25 * v_long, INK, "dot"),
    ]
    fig = go.Figure()
    for label, v0, color, dash in series:
        fc = np.array([volatility.garch11_forecast(v0, int(kk), omega, alpha, beta) for kk in k])
        fig.add_trace(
            go.Scatter(
                x=k,
                y=np.sqrt(fc * 252.0),
                mode="lines",
                name=label,
                line={"color": color, "dash": dash, "width": 2},
            )
        )
    fig.add_hline(
        y=float(np.sqrt(v_long * 252.0)),
        line_dash="dash",
        line_color="#111111",
        annotation_text="長期ボラ",
    )
    fig.update_layout(
        title={"text": "GARCH 予測の期間構造: 長期ボラへ平均回帰"},
        xaxis_title="予測ホライズン k(日)",
        yaxis_title="年率ボラティリティ",
    )
    return fig


def plotly_merton_structural(E0=1.0, r=0.05, T=3.0) -> go.Figure:
    """Merton structural model: risk-neutral default probability vs leverage.

    Wraps :func:`hullkit.credit.merton_default_prob` (Hull §24.6). Equity is a call
    on firm assets; more debt or more asset vol => higher default probability.
    """
    from . import credit

    debt = np.linspace(0.5, 20.0, 28)
    sigmas = [0.3, 0.4, 0.5, 0.6]
    fig = go.Figure()
    for i, s_e in enumerate(sigmas):
        q = [credit.merton_default_prob(E0, s_e, float(dx), r, T)[2] for dx in debt]
        fig.add_trace(
            go.Scatter(
                x=debt,
                y=q,
                mode="lines+markers",
                name=f"σ_E={s_e:g}",
                line={"color": ACCENT, "width": 2.5},
                marker={"size": 4},
                visible=(i == 0),
            )
        )
    steps = [
        {
            "label": f"{s_e:g}",
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(sigmas))]},
                {"title.text": f"Merton 構造模型: デフォルト確率 vs 負債 — σ_E={s_e:g}"},
            ],
        }
        for i, s_e in enumerate(sigmas)
    ]
    fig.update_layout(
        title={"text": f"Merton 構造模型: デフォルト確率 vs 負債 — σ_E={sigmas[0]:g}"},
        xaxis_title="負債 D(レバレッジ)",
        yaxis_title="リスク中立デフォルト確率 Q=N(-d₂)",
        sliders=[{"active": 0, "currentvalue": {"prefix": "株式ボラ σ_E: "}, "steps": steps}],
    )
    return fig


def plotly_portfolio_diversification(vol=0.20) -> go.Figure:
    """Portfolio volatility vs number of names, for several correlations.

    Wraps :func:`hullkit.risk.portfolio_sigma` (Hull Ch.22). Independent names
    diversify as 1/√N; correlation leaves an irreducible floor √ρ·σ.
    """
    ns = np.arange(1, 31)
    series = [(0.0, ACCENT, "solid"), (0.2, "#7f7f7f", "dash"), (0.5, INK, "dot")]
    fig = go.Figure()
    for rho, color, dash in series:
        per = []
        for nn in ns:
            corr = np.full((nn, nn), rho)
            np.fill_diagonal(corr, 1.0)
            per.append(risk.portfolio_sigma(np.ones(nn), np.full(nn, vol), corr) / nn)
        fig.add_trace(
            go.Scatter(
                x=ns,
                y=per,
                mode="lines",
                name=f"ρ={rho:g}",
                line={"color": color, "dash": dash, "width": 2},
            )
        )
    fig.update_layout(
        title={"text": "分散投資: ポートフォリオ・ボラ vs 銘柄数(相関別)"},
        xaxis_title="銘柄数 N",
        yaxis_title="1単位あたりポートフォリオ・ボラ",
    )
    return fig


def plotly_yield_curve() -> go.Figure:
    """Zero curve and the implied forward curve; slider over the curve shape.

    Wraps :func:`hullkit.rates.forward_rate` (Hull Ch.4). Forwards sit above zeros on
    an upward curve and below on an inverted one.
    """
    t = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0])
    shapes = [
        ("順イールド", 0.02 + 0.02 * (1 - np.exp(-t / 3.0))),
        ("フラット", np.full_like(t, 0.03)),
        ("逆イールド", 0.045 - 0.02 * (1 - np.exp(-t / 3.0))),
    ]
    t_mid = 0.5 * (t[:-1] + t[1:])
    fig = go.Figure()
    for i, (_label, z) in enumerate(shapes):
        fwd = [rates.forward_rate(z[j], t[j], z[j + 1], t[j + 1]) for j in range(len(t) - 1)]
        fig.add_trace(
            go.Scatter(
                x=t,
                y=z,
                mode="lines+markers",
                name="ゼロ金利",
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=t_mid,
                y=fwd,
                mode="lines",
                name="フォワード金利",
                line={"color": INK, "dash": "dot"},
                visible=(i == 0),
            )
        )
    steps = []
    for i, (label, _z) in enumerate(shapes):
        vis = [False] * (2 * len(shapes))
        vis[2 * i] = vis[2 * i + 1] = True
        steps.append(
            {
                "label": label,
                "method": "update",
                "args": [
                    {"visible": vis},
                    {"title.text": f"イールドカーブとフォワード金利 — {label}"},
                ],
            }
        )
    fig.update_layout(
        title={"text": f"イールドカーブとフォワード金利 — {shapes[0][0]}"},
        xaxis_title="年限 t",
        yaxis_title="金利",
        sliders=[{"active": 0, "currentvalue": {"prefix": "形状: "}, "steps": steps}],
    )
    return fig


def plotly_bond_convexity(coupon=5.0, maturity=10.0, y0=0.05) -> go.Figure:
    """Bond price-yield curve (convex) vs the duration (linear) approximation.

    Wraps :func:`hullkit.rates.bond_price` / ``macaulay_duration`` (Hull Ch.4). The
    true curve lies above the tangent — convexity is the curvature the tangent misses.
    """
    c_times = np.arange(0.5, maturity + 0.5, 0.5)
    c_flows = np.full(len(c_times), coupon / 2.0)
    c_flows[-1] += 100.0
    ys = np.linspace(0.01, 0.10, 60)
    px = np.array([rates.bond_price(c_times, c_flows, y) for y in ys])
    p0 = rates.bond_price(c_times, c_flows, y0)
    dur = rates.macaulay_duration(c_times, c_flows, y0)
    tangent = p0 * (1.0 - dur * (ys - y0))  # continuous comp => modified == Macaulay
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=ys, y=px, mode="lines", name="債券価格", line={"color": ACCENT, "width": 2.5})
    )
    fig.add_trace(
        go.Scatter(
            x=ys,
            y=tangent,
            mode="lines",
            name="デュレーション近似(接線)",
            line={"color": INK, "dash": "dash"},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=[y0],
            y=[p0],
            mode="markers",
            name="基準利回り",
            marker={"color": "#111111", "size": 9},
        )
    )
    fig.update_layout(
        title={"text": f"債券の価格-利回り: コンベクシティ(D={dur:.2f})"},
        xaxis_title="利回り y(連続複利)",
        yaxis_title="価格",
    )
    return fig


def plotly_swap_value() -> go.Figure:
    """Receive-fixed IRS value vs the fixed rate — zero exactly at the par swap rate.

    Wraps :func:`hullkit.swaps.irs_value_fras` / ``swap_rate`` (Hull Ch.7).
    """
    curve = (
        [0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0],
        [0.025, 0.028, 0.030, 0.032, 0.033, 0.034, 0.035, 0.036],
    )
    pay = [1.0, 2.0, 3.0, 4.0, 5.0]
    par = swaps.swap_rate(pay, curve)
    s_fixed = np.linspace(0.01, 0.06, 60)
    val = np.array(
        [swaps.irs_value_fras(100.0, float(s), pay, curve, next_float_rate=None) for s in s_fixed]
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=s_fixed,
            y=val,
            mode="lines",
            name="受取固定スワップ価値",
            line={"color": ACCENT, "width": 2.5},
        )
    )
    fig.add_hline(y=0.0, line_color="#c7c7c7")
    fig.add_vline(x=par, line_color="#111111", line_dash="dash", annotation_text=f"par={par:.2%}")
    fig.update_layout(
        title={"text": f"金利スワップの価値 vs 固定金利(par={par:.2%} で 0)"},
        xaxis_title="固定金利 s",
        yaxis_title="スワップ価値(想定元本100)",
    )
    return fig


def plotly_barrier_knockout(S0=100.0, K=100.0, r=0.05, sigma=0.20, T=1.0) -> go.Figure:
    """Knock-out barrier call price vs the barrier level; slider over barrier type.

    Wraps :func:`hullkit.exotics.barrier_call` (Hull §26.9). As the barrier approaches
    spot the option knocks out more easily and its value collapses toward zero.
    """
    from . import exotics

    vanilla = float(bsm.call_price(S0, K, r, sigma, T))
    configs = [
        ("down-and-out", np.linspace(60.0, 99.0, 40)),
        ("up-and-out", np.linspace(101.0, 160.0, 40)),
    ]
    fig = go.Figure()
    for i, (bt, hs) in enumerate(configs):
        price = [exotics.barrier_call(S0, K, float(h), r, sigma, T, barrier=bt) for h in hs]
        fig.add_trace(
            go.Scatter(
                x=hs,
                y=price,
                mode="lines",
                name=bt,
                line={"color": ACCENT, "width": 2.5},
                visible=(i == 0),
            )
        )
    fig.add_hline(
        y=vanilla, line_color=INK, line_dash="dash", annotation_text=f"バニラ={vanilla:.2f}"
    )
    steps = [
        {
            "label": bt,
            "method": "update",
            "args": [
                {"visible": [j == i for j in range(len(configs))]},
                {"title.text": f"ノックアウト・バリアコール vs バリア H — {bt}"},
            ],
        }
        for i, (bt, _hs) in enumerate(configs)
    ]
    fig.update_layout(
        title={"text": f"ノックアウト・バリアコール vs バリア H — {configs[0][0]}"},
        xaxis_title="バリア水準 H",
        yaxis_title="価格",
        sliders=[{"active": 0, "currentvalue": {"prefix": "バリア種類: "}, "steps": steps}],
    )
    return fig


def plotly_asian_vs_european(S0=100.0, r=0.05, sigma=0.20, T=1.0) -> go.Figure:
    """Asian (average-price) vs European call across strikes — averaging cuts vol.

    Wraps :func:`hullkit.exotics.asian_call_turnbull_wakeman` and BSM (Hull §26.12).
    The average is less volatile than the terminal price, so the Asian is cheaper.
    """
    from . import exotics

    ks = np.linspace(80.0, 120.0, 21)
    asian = [exotics.asian_call_turnbull_wakeman(S0, float(k), r, sigma, T) for k in ks]
    euro = [float(bsm.call_price(S0, float(k), r, sigma, T)) for k in ks]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ks, y=euro, mode="lines", name="ヨーロピアン", line={"color": INK, "dash": "dash"}
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ks,
            y=asian,
            mode="lines+markers",
            name="アジアン(平均価格)",
            line={"color": ACCENT, "width": 2.5},
            marker={"size": 4},
        )
    )
    fig.update_layout(
        title={"text": "アジアン vs ヨーロピアン・コール: 平均化でボラ低下 → 割安"},
        xaxis_title="ストライク K",
        yaxis_title="価格",
    )
    return fig
