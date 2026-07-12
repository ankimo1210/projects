"""Report-only prior-literature registry and section renderer.

The prior-literature section is not part of the shared 26-section
report/notebook registry in :mod:`rough_volatility.notebook`. It is inserted
into the standalone HTML report only, and only for locales whose catalog
provides literature prose (currently Japanese; the English catalog keeps the
keys empty until the English edition is written, which disables the section).

Language-neutral bibliographic data lives here; all prose (approach, problem,
proposal, findings, open problems, one-line summary) lives in the locale
catalogs under ``literature.<key>.<field>`` so the English edition can be added
later without touching this module.
"""

from __future__ import annotations

import html
from dataclasses import dataclass

from rough_volatility.i18n import Translator

LITERATURE_ANCHOR = "prior-literature"
# The report section is inserted immediately after this shared-registry anchor.
LITERATURE_AFTER_ANCHOR = "conceptual-map"

_CARD_FIELDS = ("problem", "proposal", "findings", "future")
_TABLE_COLUMNS = ("work", "approach", "summary")


@dataclass(frozen=True)
class PriorWork:
    """One prior-literature entry; the prose lives in the locale catalogs."""

    key: str
    short: str
    citation: str


PRIOR_WORKS: tuple[PriorWork, ...] = (
    PriorWork(
        "comte-renault-1998",
        "Comte & Renault (1998)",
        "F. Comte & E. Renault (1998): Long memory in continuous-time stochastic "
        "volatility models. Mathematical Finance.",
    ),
    PriorWork(
        "alos-leon-vives-2007",
        "Alòs, León & Vives (2007)",
        "E. Alòs, J. A. León & J. Vives (2007): On the short-time behavior of the "
        "implied volatility for jump-diffusion models with stochastic volatility. "
        "Finance and Stochastics.",
    ),
    PriorWork(
        "fukasawa-2011",
        "Fukasawa (2011)",
        "M. Fukasawa (2011): Asymptotic analysis for stochastic volatility: "
        "martingale expansion. Finance and Stochastics.",
    ),
    PriorWork(
        "gatheral-jaisson-rosenbaum-2018",
        "Gatheral, Jaisson & Rosenbaum (2018)",
        "J. Gatheral, T. Jaisson & M. Rosenbaum (2018): Volatility is rough. "
        "Quantitative Finance (first draft 2014).",
    ),
    PriorWork(
        "bayer-friz-gatheral-2016",
        "Bayer, Friz & Gatheral (2016)",
        "C. Bayer, P. K. Friz & J. Gatheral (2016): Pricing under rough volatility. "
        "Quantitative Finance.",
    ),
    PriorWork(
        "bennedsen-lunde-pakkanen-2017",
        "Bennedsen, Lunde & Pakkanen (2017)",
        "M. Bennedsen, A. Lunde & M. S. Pakkanen (2017): Hybrid scheme for Brownian "
        "semistationary processes. Finance and Stochastics.",
    ),
    PriorWork(
        "mccrickerd-pakkanen-2018",
        "McCrickerd & Pakkanen (2018)",
        "R. McCrickerd & M. S. Pakkanen (2018): Turbocharging Monte Carlo pricing "
        "for the rough Bergomi model. Quantitative Finance.",
    ),
    PriorWork(
        "el-euch-rosenbaum-2019",
        "El Euch & Rosenbaum (2019)",
        "O. El Euch & M. Rosenbaum (2019): The characteristic function of rough "
        "Heston models. Mathematical Finance.",
    ),
    PriorWork(
        "jaisson-rosenbaum-2016",
        "Jaisson & Rosenbaum (2016)",
        "T. Jaisson & M. Rosenbaum (2016): Rough fractional diffusions as scaling "
        "limits of nearly unstable heavy-tailed Hawkes processes. Annals of Applied "
        "Probability.",
    ),
    PriorWork(
        "el-euch-fukasawa-rosenbaum-2018",
        "El Euch, Fukasawa & Rosenbaum (2018)",
        "O. El Euch, M. Fukasawa & M. Rosenbaum (2018): The microstructural "
        "foundations of leverage effect and rough volatility. Finance and "
        "Stochastics.",
    ),
    PriorWork(
        "abi-jaber-el-euch-2019",
        "Abi Jaber & El Euch (2019)",
        "E. Abi Jaber & O. El Euch (2019): Multifactor approximation of rough "
        "volatility models. SIAM Journal on Financial Mathematics.",
    ),
    PriorWork(
        "horvath-muguruza-tomas-2021",
        "Horvath, Muguruza & Tomas (2021)",
        "B. Horvath, A. Muguruza & M. Tomas (2021): Deep learning volatility. "
        "Quantitative Finance.",
    ),
    PriorWork(
        "fukasawa-takabatake-westphal-2022",
        "Fukasawa, Takabatake & Westphal (2022)",
        "M. Fukasawa, T. Takabatake & R. Westphal (2022): Consistent estimation for "
        "fractional stochastic volatility model under high-frequency asymptotics. "
        "Mathematical Finance (2019 preprint title: Is volatility rough?).",
    ),
    PriorWork(
        "cont-das-2022",
        "Cont & Das (2022)",
        "R. Cont & P. Das (2022): Rough volatility: fact or artefact? (preprint; "
        "later published).",
    ),
    PriorWork(
        "guyon-lekeufack-2023",
        "Guyon & Lekeufack (2023)",
        "J. Guyon & J. Lekeufack (2023): Volatility is (mostly) path-dependent. "
        "Quantitative Finance.",
    ),
)


def render_literature_section(t: Translator) -> str | None:
    """Inner HTML for the report-only prior-literature section.

    Returns ``None`` when the locale has no literature content yet, which is
    signalled by an empty ``callout.prior-literature`` catalog value; the
    caller then omits the section entirely.
    """
    overview = t(f"callout.{LITERATURE_ANCHOR}")
    if not overview:
        return None
    header = "".join(f"<th>{t(f'literature.col.{column}')}</th>" for column in _TABLE_COLUMNS)
    rows = "".join(
        f"<tr><th>{html.escape(work.short)}</th>"
        f"<td>{t(f'literature.{work.key}.approach')}</td>"
        f"<td>{t(f'literature.{work.key}.summary')}</td></tr>"
        for work in PRIOR_WORKS
    )
    cards = "".join(
        f'<article class="lit-card"><h3>{html.escape(work.citation)}</h3><dl>'
        + "".join(
            f"<dt>{t(f'literature.label.{field}')}</dt>"
            f"<dd>{t(f'literature.{work.key}.{field}')}</dd>"
            for field in _CARD_FIELDS
        )
        + "</dl></article>"
        for work in PRIOR_WORKS
    )
    return (
        overview
        + f'<table class="definition-table lit-table"><thead><tr>{header}</tr></thead>'
        + f"<tbody>{rows}</tbody></table>"
        + f'<div class="lit-cards">{cards}</div>'
    )
