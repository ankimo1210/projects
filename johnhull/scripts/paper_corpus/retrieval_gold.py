"""Fixed finance retrieval questions for the JohnHull paper corpus."""

from __future__ import annotations

import json
from typing import Any

from .gold import GOLD_ROOT

DEFAULT_RETRIEVAL_QUERIES_OUTPUT = GOLD_ROOT / "gold_retrieval_queries.jsonl"
DEFAULT_RETRIEVAL_METRICS_OUTPUT = GOLD_ROOT / "gold_retrieval_metrics.json"


def _query(
    query_id: str,
    category: str,
    question: str,
    expected_claim_id: str,
    *,
    equation_assertion_ids: tuple[str, ...] = (),
    language: str = "en",
) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "category": category,
        "question": question,
        "expected_claim_ids": (expected_claim_id,),
        "expected_equation_assertion_ids": equation_assertion_ids,
        "expected_table_ids": (),
        "language": language,
        "p0": True,
        "top_k": 5,
    }


RETRIEVAL_QUERIES = (
    _query(
        "hw-curve-calibration",
        "hull_white",
        "How does the Hull-White model fit the initial term structure and forward-rate volatility?",
        "1990-hull-white-interest-rate-derivative-securities:claim:curve-fit",
    ),
    _query(
        "hw-bond-loading",
        "hull_white",
        "What is the exponential zero-coupon bond loading B(t,T) in the Hull-White Vasicek model?",
        "1990-hull-white-interest-rate-derivative-securities:claim:bond-loading",
        equation_assertion_ids=("hw-p6-vasicek-b",),
    ),
    _query(
        "hw-short-rate-dynamics",
        "hull_white",
        "Which time-dependent drift, mean-reversion, and volatility coefficients define the Hull-White short-rate dynamics?",
        "1990-hull-white-interest-rate-derivative-securities:claim:short-rate-dynamics",
    ),
    _query(
        "heston-variance",
        "heston",
        "How does Heston model instantaneous variance as a correlated square-root process?",
        "1993-heston-closed-form-stochastic-volatility:claim:variance-process",
    ),
    _query(
        "heston-characteristic-function",
        "heston",
        "Where are the Heston characteristic-function quantities g and d defined for Fourier option pricing?",
        "1993-heston-closed-form-stochastic-volatility:claim:characteristic-function",
        equation_assertion_ids=("heston-p5-g", "heston-p5-d"),
    ),
    _query(
        "heston-vol-risk-premium",
        "heston",
        "Why is an assumption about the volatility risk premium required in the Heston model?",
        "1993-heston-closed-form-stochastic-volatility:claim:volatility-risk-premium",
    ),
    _query(
        "jy-fx-analogy",
        "inflation_jgbi",
        "How does Jarrow-Yildirim map nominal money, real money, and CPI to a foreign-currency economy?",
        "2003-jarrow-yildirim-inflation-hjm:claim:foreign-currency-analogy",
    ),
    _query(
        "jy-q-numeraire",
        "inflation_jgbi",
        "Which nominal and CPI-scaled real assets must be Q-martingales under the nominal money-market numeraire?",
        "2003-jarrow-yildirim-inflation-hjm:claim:q-martingales",
        equation_assertion_ids=("jy-p7-q-martingales",),
    ),
    _query(
        "jy-cpi-drift",
        "inflation_jgbi",
        "Under the risk-neutral measure, why is CPI drift the nominal short rate minus the real short rate?",
        "2003-jarrow-yildirim-inflation-hjm:claim:cpi-q-dynamics",
        equation_assertion_ids=("jy-p9-cpi-q-dynamics",),
    ),
    _query(
        "wu-zciis-payoff",
        "inflation_jgbi",
        "What fixed compounded payment is exchanged in a zero-coupon inflation-indexed swap ZCIIS?",
        "2013-wu-inflation-rate-derivatives:claim:zciis-payoff",
        equation_assertion_ids=("wu-p7-zciis-fixed-payoff",),
    ),
    _query(
        "wu-fisher-relation",
        "inflation_jgbi",
        "How does the Fisher relation split the nominal short rate into the real rate and inflation?",
        "2013-wu-inflation-rate-derivatives:claim:fisher-relation",
        equation_assertion_ids=("wu-p8-fisher-relation",),
    ),
    _query(
        "wu-forward-measure",
        "inflation_jgbi",
        "What Radon-Nikodym density and bond numeraire define the T-forward measure for inflation forwards?",
        "2013-wu-inflation-rate-derivatives:claim:forward-measure",
        equation_assertion_ids=("wu-p14-forward-measure-density",),
    ),
    _query(
        "canty-seasonality",
        "inflation_jgbi",
        "How is CPI decomposed into trend and multiplicative seasonal components for inflation-linked bonds?",
        "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:multiplicative-seasonality",
        equation_assertion_ids=("canty-p2-seasonality-decomposition",),
    ),
    _query(
        "canty-lag-interpolation",
        "inflation_jgbi",
        "How should lagged monthly CPI observations be linearly interpolated when modeling inflation-linked bond seasonality?",
        "2009-canty-seasonally-adjusted-inflation-linked-bonds:claim:lagged-interpolation",
    ),
    _query(
        "jgbi-principal-floor",
        "inflation_jgbi",
        "JGB物価連動国債の元本保証フロアにはどのようなオプション価値があるか。",
        "2024-mof-jgbi-bei-guide:claim:principal-floor",
        language="ja",
    ),
    _query(
        "jgbi-coupon-floor",
        "inflation_jgbi",
        "JGBIの元本フロアは償還元本と期中クーポンのどちらに適用されるか。",
        "2024-mof-jgbi-bei-guide:claim:floor-coupon-scope",
        language="ja",
    ),
    _query(
        "jgbi-bei-bias",
        "inflation_jgbi",
        "BEIに元本保証、流動性、リスクプレミアムが与えるバイアスは何か。",
        "2024-mof-jgbi-bei-guide:claim:bei-definition-bias",
        language="ja",
    ),
    _query(
        "jgbi-index-lag",
        "inflation_jgbi",
        "JGBIの適用指数ではコアCPIの公表ラグと日次線形補間をどう扱うか。",
        "2024-mof-jgbi-bei-guide:claim:lag-and-interpolation",
        language="ja",
    ),
    _query(
        "sabr-dynamics",
        "sabr",
        "What are the correlated forward and stochastic-volatility dynamics of SABR under the forward measure?",
        "2002-hagan-et-al-managing-smile-risk:claim:sabr-dynamics",
        equation_assertion_ids=(
            "hagan-p8-sabr-forward-dynamics",
            "hagan-p8-sabr-volatility-dynamics",
            "hagan-p8-sabr-correlation",
        ),
    ),
    _query(
        "sabr-calibration",
        "sabr",
        "Which beta, rho, vol-of-vol, alpha, and ATM volatility inputs are fitted in SABR calibration?",
        "2002-hagan-et-al-managing-smile-risk:claim:calibration",
    ),
    _query(
        "sabr-expiry-scope",
        "sabr",
        "Why does basic SABR fit a single expiry while a multi-expiry volatility surface needs dynamic SABR?",
        "2002-hagan-et-al-managing-smile-risk:claim:single-expiry-scope",
    ),
    _query(
        "rfr-risk-neutral-numeraire",
        "rfr",
        "How is a risk-free bond valued under the risk-neutral measure using the money-market numeraire?",
        "2019-lyashenko-mercurio-backward-looking-rates:claim:risk-neutral-numeraire",
        equation_assertion_ids=("lyashenko-p4-risk-neutral-bond-price",),
    ),
    _query(
        "rfr-extended-forward-measure",
        "rfr",
        "How can the T-forward measure and its bond numeraire be extended beyond bond maturity?",
        "2019-lyashenko-mercurio-backward-looking-rates:claim:extended-forward-measure",
        equation_assertion_ids=("lyashenko-p4-bond-after-maturity",),
    ),
    _query(
        "rfr-drift-adjustment",
        "rfr",
        "How is the drift adjustment between the money-market measure and rolling discrete measure quantified?",
        "2019-lyashenko-mercurio-backward-looking-rates:claim:measure-drift-adjustment",
    ),
    _query(
        "rfr-backward-analytics",
        "rfr",
        "Which martingale and analytic properties make backward-looking term rates viable IBOR replacements?",
        "2019-lyashenko-mercurio-backward-looking-rates:claim:analytics-and-implementation",
    ),
    _query(
        "var-es-two-stage",
        "var_es",
        "How are GARCH volatility filtering and extreme value theory combined for conditional VaR and expected shortfall?",
        "2000-mcneil-frey-tail-risk-evt:claim:two-stage-method",
    ),
    _query(
        "es-location-scale",
        "var_es",
        "What is the location-scale representation of conditional expected shortfall?",
        "2000-mcneil-frey-tail-risk-evt:claim:es-location-scale",
        equation_assertion_ids=("mcneil-frey-p14-es",),
    ),
    _query(
        "es-backtest",
        "var_es",
        "How should exceedance residuals be tested for independence and zero mean in an expected-shortfall backtest?",
        "2000-mcneil-frey-tail-risk-evt:claim:es-backtest",
    ),
)


def render_retrieval_queries(
    queries: tuple[dict[str, Any], ...] = RETRIEVAL_QUERIES,
) -> str:
    """Serialize fixed retrieval questions deterministically."""

    return "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for item in queries
    )
