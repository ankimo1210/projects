"""JohnHull-specific source pages and verified regression assertions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .baseline import REFERENCES_ROOT, read_json
from .schema import P0_PAPER_IDS

GOLD_ROOT = REFERENCES_ROOT / "gold"
DEFAULT_MANIFEST_OUTPUT = GOLD_ROOT / "gold_manifest.json"
DEFAULT_ASSERTIONS_OUTPUT = GOLD_ROOT / "gold_assertions.jsonl"

GOLD_PAGE_SELECTIONS = {
    "1900-bachelier-theorie-de-la-speculation": (1, 6, 11, 16, 23, 67),
    "1973-black-scholes-options-corporate-liabilities": (1, 2, 4, 5, 8, 19),
    "1990-hull-white-interest-rate-derivative-securities": (1, 4, 5, 6, 7, 14, 17, 18, 20),
    "1993-heston-closed-form-stochastic-volatility": (1, 2, 3, 5, 6, 8, 16, 17),
    "2000-mcneil-frey-tail-risk-evt": (1, 5, 8, 14, 15, 24, 29),
    "2001-longstaff-schwartz-american-options-lsm": (1, 5, 10, 20, 30, 36),
    "2002-hagan-et-al-managing-smile-risk": (1, 4, 8, 9, 15, 25, 41),
    "2003-jarrow-yildirim-inflation-hjm": (1, 3, 5, 7, 8, 9, 20, 21, 22),
    "2009-canty-seasonally-adjusted-inflation-linked-bonds": (1, 2, 3, 4, 5),
    "2008-fang-oosterlee-cos-method": (1, 3, 5, 10, 15, 16, 17, 18, 23),
    "2013-wu-inflation-rate-derivatives": (2, 3, 7, 8, 9, 13, 14, 15, 16, 17),
    "2019-lyashenko-mercurio-backward-looking-rates": (1, 4, 8, 12, 20, 25),
    "2020-huge-savine-differential-machine-learning": (1, 5, 10, 20, 35, 51),
    "2021-mof-jgbi-indexation-notice": (1, 2, 3, 4, 5, 6),
    "2024-mof-jgbi-bei-guide": (1, 2, 5, 7, 8, 9),
}

VERIFIED_ASSERTIONS = (
    {
        "assertion_id": "hw-p4-short-rate-dynamics",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 4,
        "kind": "display_formula",
        "equation_number": "2",
        "expected_latex": (r"dr=\{\theta(t)+a(t)(b-r)\}dt+\sigma(t)r^\beta dz"),
        "expected_text": None,
        "source_bbox_normalized": [262, 446, 725, 466],
        "source_asset_name": "e547a4de6b170c3592d042f0498af663e262f5859f78e2e2eb3ee3ce21ecd115.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p6-vasicek-b",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 6,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": r"B(t,T)=\frac{1-e^{-a(T-t)}}{a}",
        "expected_text": None,
        "source_bbox_normalized": [156, 190, 838, 261],
        "source_asset_name": "958dbd9b1387f764e95241003396aa1ab876121d0968662d9b0309acdcdb9529.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p6-mean-reversion",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 6,
        "kind": "display_formula",
        "equation_number": "15",
        "expected_latex": (
            r"a(t)=-\frac{\partial^2 B(0,t)/\partial t^2}{\partial B(0,t)/\partial t}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [258, 863, 537, 905],
        "source_asset_name": "b09a4e119fac6b3aaa081a82979e5b15932c7b83853b9a15aaf12a1a08329ab0.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p7-zcb-call",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 7,
        "kind": "display_formula",
        "equation_number": "17",
        "expected_latex": (r"C=P(r,t,s)N(b)-XP(r,t,T)N(b-\sigma_P)"),
        "expected_text": None,
        "source_bbox_normalized": [267, 540, 753, 560],
        "source_asset_name": "02ae7f9962f2507f52ccae84d756581035cd48b318843bba12f6fa596717597f.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p7-zcb-call-d1",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 7,
        "kind": "display_formula",
        "equation_number": "18",
        "expected_latex": (
            r"b=\frac{1}{\sigma_P}\log\frac{P(r,t,s)}{P(r,t,T)X}+"
            r"\frac{\sigma_P}{2}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [236, 605, 781, 701],
        "source_asset_name": "7c81caa0685a9fdf05ca7cf2e0bf389845048da9566203188faf77c564799487.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p7-zcb-call-total-variance",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 7,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (
            r"\sigma_P^2=\int_t^T\sigma(\tau)^2"
            r"[B(\tau,s)-B(\tau,T)]^2\,d\tau"
        ),
        "expected_text": None,
        "source_bbox_normalized": [289, 854, 715, 900],
        "source_asset_name": "d9a22c9f4e8aab36d522fe59afc125781b8670a1ddb6f2f2bb1650ef6a374eaa.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p17-table4-ext-vas-102",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "1.0|Ext Vas",
        "column_key": "1.02",
        "expected_numeric": 0.35,
        "row_index": 2,
        "column_index": 5,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p17-table4-cir-102",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "1.0|Two-factor CIR",
        "column_key": "1.02",
        "expected_numeric": 0.34,
        "row_index": 3,
        "column_index": 5,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "hw-p17-table3-ext-vas-200-100",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "3",
        "row_key": "2.0|Ext Vas",
        "column_key": "1.00",
        "expected_numeric": 1.32,
        "row_index": 4,
        "column_index": 4,
        "source_bbox_normalized": [112, 118, 863, 287],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hw-p17-table4-cir-200-100",
        "paper_id": "1990-hull-white-interest-rate-derivative-securities",
        "page_number": 17,
        "kind": "table_cell",
        "table_number": "4",
        "row_key": "2.0|Two-factor CIR",
        "column_key": "1.00",
        "expected_numeric": 0.86,
        "row_index": 5,
        "column_index": 4,
        "source_bbox_normalized": [108, 660, 861, 827],
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "heston-p2-asset-dynamics",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 2,
        "kind": "display_formula",
        "equation_number": "1",
        "expected_latex": r"dS(t)=\mu S\,dt+\sqrt{v(t)}S\,dz_1(t)",
        "expected_text": None,
        "source_bbox_normalized": [316, 753, 664, 773],
        "source_asset_name": "7d2550f971e62816104a4e9c120942396953f9318494505cc45faaf4f095094f.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "heston-p3-variance-dynamics",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 3,
        "kind": "display_formula",
        "equation_number": "4",
        "expected_latex": (r"dv(t)=\kappa[\theta-v(t)]dt+\sigma\sqrt{v(t)}\,dz_2(t)"),
        "expected_text": None,
        "source_bbox_normalized": [291, 150, 729, 174],
        "source_asset_name": "846c1127d7ac89b375ce2de30eb0bf4890ed9ba6a297ecd023bb574a52ffef9a.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "heston-p5-g",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 5,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (r"g=\frac{b_j-\rho\sigma\phi i+d}{b_j-\rho\sigma\phi i-d}"),
        "expected_text": None,
        "source_bbox_normalized": [293, 534, 720, 606],
        "source_asset_name": "e99fb9e3a5803784f9a9d19b2307c336e30143e13abd1d501aa56531399c958e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "heston-p5-d",
        "paper_id": "1993-heston-closed-form-stochastic-volatility",
        "page_number": 5,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (r"d=\sqrt{(\rho\sigma\phi i-b_j)^2-\sigma^2(2u_j\phi i-\phi^2)}"),
        "expected_text": None,
        "source_bbox_normalized": [293, 534, 720, 606],
        "source_asset_name": "e99fb9e3a5803784f9a9d19b2307c336e30143e13abd1d501aa56531399c958e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "mcneil-frey-p8-gpd-quantile",
        "paper_id": "2000-mcneil-frey-tail-risk-evt",
        "page_number": 8,
        "kind": "display_formula",
        "equation_number": "10",
        "expected_latex": (
            r"\widehat{z_q}=z_{(k+1)}+\frac{\widehat{\beta}}{\widehat{\xi}}"
            r"\left[\left(\frac{1-q}{k/n}\right)^{-\widehat{\xi}}-1\right]"
        ),
        "expected_text": None,
        "source_bbox_normalized": [328, 540, 666, 587],
        "source_asset_name": "34b86d4d2e232f0ae4f780a80589c63017bbc8fd4c4efb2014a5fc4dad46b365.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "mcneil-frey-p14-es",
        "paper_id": "2000-mcneil-frey-tail-risk-evt",
        "page_number": 14,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": r"S_q^t=\mu_{t+1}+\sigma_{t+1}E[Z\mid Z>z_q]",
        "expected_text": None,
        "source_bbox_normalized": [372, 69, 627, 90],
        "source_asset_name": "698d8c62afa15d51b23ef7d6198a4f5e033a245a05e764be1d35fe7c20392781.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-22",
    },
    {
        "assertion_id": "mcneil-frey-p14-gpd-mean",
        "paper_id": "2000-mcneil-frey-tail-risk-evt",
        "page_number": 14,
        "kind": "display_formula",
        "equation_number": "14",
        "expected_latex": r"E[W\mid W>w]=\frac{w+\beta}{1-\xi}",
        "expected_text": None,
        "source_bbox_normalized": [398, 164, 599, 199],
        "source_asset_name": "81613ca563ec046c1e443d4e61a619f1af8a7c8744e23c83326fd6ddd0d10ef0.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p8-sabr-forward-dynamics",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 8,
        "kind": "display_formula",
        "equation_number": "2.15a",
        "expected_latex": (
            r"d\widehat{F}=\widehat{\alpha}\widehat{F}^{\beta}dW_1,"
            r"\qquad \widehat{F}(0)=f"
        ),
        "expected_text": None,
        "source_bbox_normalized": [385, 563, 611, 582],
        "source_asset_name": "90b95044c2178ee246ef6e415b9653868d64b30608e09d355d0bf369b48e3844.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p8-sabr-volatility-dynamics",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 8,
        "kind": "display_formula",
        "equation_number": "2.15b",
        "expected_latex": (
            r"d\widehat{\alpha}=\nu\widehat{\alpha}dW_2,"
            r"\qquad \widehat{\alpha}(0)=\alpha"
        ),
        "expected_text": None,
        "source_bbox_normalized": [395, 604, 601, 621],
        "source_asset_name": "a003aa97640ab95bf4af9bcd27057bf0db87989ef14175717f6b534000979f93.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p8-sabr-correlation",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 8,
        "kind": "display_formula",
        "equation_number": "2.15c",
        "expected_latex": r"dW_1dW_2=\rho\,dt",
        "expected_text": None,
        "source_bbox_normalized": [436, 659, 558, 674],
        "source_asset_name": "7798744f74f808183f9681de9a95249d2adc95cfd7c3d350b36bfc53976ba6d3.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p9-sabr-implied-volatility",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 9,
        "kind": "display_formula",
        "equation_number": "2.17a",
        "expected_latex": (
            r"\sigma_B(K,f)=\frac{\alpha}{(fK)^{(1-\beta)/2}"
            r"\left\{1+\frac{(1-\beta)^2}{24}\log^2(f/K)+"
            r"\frac{(1-\beta)^4}{1920}\log^4(f/K)+\cdots\right\}}"
            r"\frac{z}{x(z)}\left\{1+\left[\frac{(1-\beta)^2}{24}"
            r"\frac{\alpha^2}{(fK)^{1-\beta}}+\frac{1}{4}"
            r"\frac{\rho\beta\nu\alpha}{(fK)^{(1-\beta)/2}}+"
            r"\frac{2-3\rho^2}{24}\nu^2\right]t_{ex}+\cdots\right\}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [196, 425, 794, 503],
        "source_asset_name": "6f503b2de2dfaeacf3d91555455be238ef26847679069f4f9f1b0e00d896a09e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p9-sabr-z",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 9,
        "kind": "display_formula",
        "equation_number": "2.17b",
        "expected_latex": (r"z=\frac{\nu}{\alpha}(fK)^{(1-\beta)/2}\log(f/K)"),
        "expected_text": None,
        "source_bbox_normalized": [397, 535, 598, 561],
        "source_asset_name": "1ea347bbba3fc3187122505d69d0030c1c391e914ca6830cef286cce5d011739.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "hagan-p9-sabr-xz",
        "paper_id": "2002-hagan-et-al-managing-smile-risk",
        "page_number": 9,
        "kind": "display_formula",
        "equation_number": "2.17c",
        "expected_latex": (
            r"x(z)=\log\left\{\frac{\sqrt{1-2\rho z+z^2}+z-\rho}"
            r"{1-\rho}\right\}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [356, 597, 637, 637],
        "source_asset_name": "d0aa9b03649f20ecbe221a7bd939ee1c9a5f56f2e641fe8996194042f783bbd6.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "jy-p7-q-martingales",
        "paper_id": "2003-jarrow-yildirim-inflation-hjm",
        "page_number": 7,
        "kind": "display_formula",
        "equation_number": "8",
        "expected_latex": (
            r"\frac{P_n(t,T)}{B_n(t)},\quad\frac{I(t)P_r(t,T)}{B_n(t)},"
            r"\quad\frac{I(t)B_r(t)}{B_n(t)}\ \mathrm{are}\ Q\mathrm{-martingales}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [290, 410, 700, 449],
        "source_asset_name": "12543b92e79eed20490978efa83a97e86f09b5e2992a321f570258116008e19a.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "jy-p9-cpi-q-dynamics",
        "paper_id": "2003-jarrow-yildirim-inflation-hjm",
        "page_number": 9,
        "kind": "display_formula",
        "equation_number": "14",
        "expected_latex": (
            r"\frac{dI(t)}{I(t)}=[r_n(t)-r_r(t)]dt+"
            r"\sigma_I(t)d\widetilde{W}_I(t)"
        ),
        "expected_text": None,
        "source_bbox_normalized": [233, 203, 522, 246],
        "source_asset_name": "307cc86b537dab60956e2a43f4d674c72ea795333f8654d7a2cdecde2adaf965.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "jy-p21-cpi-call-payoff",
        "paper_id": "2003-jarrow-yildirim-inflation-hjm",
        "page_number": 21,
        "kind": "display_formula",
        "equation_number": "35",
        "expected_latex": r"C_T=\max[I(T)-K,0]",
        "expected_text": None,
        "source_bbox_normalized": [349, 155, 532, 172],
        "source_asset_name": "08bf32768e1e9429dd0f6f394f975827db8465f3b7280771f0c4385d0b25d2a6.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "jy-p21-cpi-call-risk-neutral-value",
        "paper_id": "2003-jarrow-yildirim-inflation-hjm",
        "page_number": 21,
        "kind": "display_formula",
        "equation_number": "36",
        "expected_latex": (
            r"C_t=\widetilde{E}_t\left[\max(I(T)-K,0)"
            r"e^{-\int_t^T r_n(s)\,ds}\right]"
        ),
        "expected_text": None,
        "source_bbox_normalized": [290, 223, 573, 280],
        "source_asset_name": "6a075ea6cdba45de7f7d993d7e5e03b246e48d13e6a3034d7047ae9246510e76.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "jy-p21-cpi-call-closed-form",
        "paper_id": "2003-jarrow-yildirim-inflation-hjm",
        "page_number": 21,
        "kind": "display_formula",
        "equation_number": "37",
        "expected_latex": (
            r"C_t=I(t)P_r(t,T)N\left(\frac{\log\left[\frac{I(t)P_r(t,T)}"
            r"{KP_n(t,T)}\right]+\frac{1}{2}\eta^2}{\eta}\right)-"
            r"KP_n(t,T)N\left(\frac{\log\left[\frac{I(t)P_r(t,T)}"
            r"{KP_n(t,T)}\right]-\frac{1}{2}\eta^2}{\eta}\right)"
        ),
        "expected_text": None,
        "source_bbox_normalized": [150, 401, 879, 489],
        "source_asset_name": "c639701a93366e99de4452b9b75a149b9c0e15fa55d8491424a58091b3361e3e.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "lyashenko-p4-risk-neutral-bond-price",
        "paper_id": "2019-lyashenko-mercurio-backward-looking-rates",
        "page_number": 4,
        "kind": "display_formula",
        "equation_number": "2",
        "expected_latex": (
            r"P(t,T)=\mathbb{E}\left[e^{-\int_t^T r(u)\,du}\mid\mathcal{F}_t\right]"
        ),
        "expected_text": None,
        "source_bbox_normalized": [372, 237, 609, 268],
        "source_asset_name": "94e9059002b3d485b0b193d3620c9992c6bc9adf9409025870571e37cdedfbb8.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "lyashenko-p4-bond-after-maturity",
        "paper_id": "2019-lyashenko-mercurio-backward-looking-rates",
        "page_number": 4,
        "kind": "display_formula",
        "equation_number": "3",
        "expected_latex": (
            r"P(t,T)=\mathbb{E}\left[e^{\int_T^t r(u)\,du}\mid\mathcal{F}_t\right]="
            r"e^{\int_T^t r(u)\,du}=\frac{B(t)}{B(T)}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [294, 343, 687, 382],
        "source_asset_name": "b3db4ca520947c7ceebb779f3fd90878f9ad6972cfc0b8942c4c8b6e3b860f86.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "canty-p2-seasonality-decomposition",
        "paper_id": "2009-canty-seasonally-adjusted-inflation-linked-bonds",
        "page_number": 2,
        "kind": "display_formula",
        "equation_number": "2",
        "expected_latex": r"I_t=T_tS_t",
        "expected_text": None,
        "source_bbox_normalized": [635, 862, 689, 876],
        "source_asset_name": "cbbe156f0312f97b3739d3ce42414957997b2c2cf4bc1506a21545b9adf81ed8.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "wu-p7-zciis-fixed-payoff",
        "paper_id": "2013-wu-inflation-rate-derivatives",
        "page_number": 7,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": r"\mathrm{Not.}\times\left((1+K(t,T))^{T-t}-1\right)",
        "expected_text": None,
        "source_bbox_normalized": [364, 816, 629, 838],
        "source_asset_name": "eb9582fcf619f74014c4cf10b2dcdd328aa4c31faf8a89eed2f69f3f5d805dbb.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "wu-p8-fisher-relation",
        "paper_id": "2013-wu-inflation-rate-derivatives",
        "page_number": 8,
        "kind": "display_formula",
        "equation_number": "4",
        "expected_latex": r"r(t)=R(t)+i(t)",
        "expected_text": None,
        "source_bbox_normalized": [416, 696, 575, 715],
        "source_asset_name": "fd17b8bee69708f302ee944cce4ebae94cb2539d3be590c1b827eb35fafb8ae2.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "wu-p9-yoy-floating-payoff",
        "paper_id": "2013-wu-inflation-rate-derivatives",
        "page_number": 9,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (r"\mathrm{Not.}\left(\frac{I(T_j)}{I(T_{j-1})}-1\right)"),
        "expected_text": None,
        "source_bbox_normalized": [403, 425, 588, 467],
        "source_asset_name": "314e360581628aa0602c50b06b1c26ea3d5fbc03042e43b6749b50ad3ecfa017.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
    {
        "assertion_id": "wu-p14-forward-measure-density",
        "paper_id": "2013-wu-inflation-rate-derivatives",
        "page_number": 14,
        "kind": "display_formula",
        "equation_number": None,
        "expected_latex": (
            r"\left.\frac{dQ_T}{dQ}\right|_{\mathcal{F}_t}="
            r"\frac{P(t,T)}{B(t)P(0,T)}"
        ),
        "expected_text": None,
        "source_bbox_normalized": [397, 364, 599, 406],
        "source_asset_name": "059658385dc1c0fba0a50a77284adb8421d96bdf202faa086f45a2bad4fbe78f.jpg",
        "verification_status": "verified",
        "reviewer": "codex-visual-audit-2026-07-23",
    },
)


def build_gold_manifest(references_root: Path = REFERENCES_ROOT) -> dict[str, Any]:
    """Build the deterministic selected-page manifest from tracked preflight data."""

    baseline = read_json(references_root / "corpus_baseline.json")
    preflight = read_json(references_root / "corpus_preflight.json")
    source_by_id = {item["paper_id"]: item for item in baseline["sources"]}
    profile_by_id = {item["paper_id"]: item for item in preflight["papers"]}
    selected_pages: list[dict[str, Any]] = []
    for paper_id, pages in GOLD_PAGE_SELECTIONS.items():
        source = source_by_id[paper_id]
        profile = profile_by_id[paper_id]
        page_by_number = {item["page_number"]: item for item in profile["pages"]}
        for page_number in pages:
            page = page_by_number[page_number]
            reasons = [page["route"]]
            if page_number == 1:
                reasons.append("front_matter")
            if page_number == source["source_page_count"]:
                reasons.append("final_page")
            if page["math_dense"]:
                reasons.append("math_dense")
            if page["damaged"] and "damaged" not in reasons:
                reasons.append("damaged")
            selected_pages.append(
                {
                    "gold_page_id": f"{paper_id}:p{page_number:04d}",
                    "paper_id": paper_id,
                    "page_number": page_number,
                    "source_pdf_sha256": source["source_sha256"],
                    "p0": paper_id in P0_PAPER_IDS,
                    "selection_reasons": reasons,
                    "annotation_status": "selected",
                }
            )
    return {
        "gold_manifest_version": "1.0.0",
        "paper_count": len(GOLD_PAGE_SELECTIONS),
        "page_count": len(selected_pages),
        "targets": {
            "minimum_pages": 60,
            "minimum_display_equations": 150,
            "minimum_inline_equations": 200,
            "minimum_table_cells": 500,
            "minimum_claims_per_paper": 5,
        },
        "selected_pages": selected_pages,
    }


def render_json(value: Any) -> str:
    """Serialize stable indented JSON."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_assertions(assertions: tuple[dict[str, Any], ...] = VERIFIED_ASSERTIONS) -> str:
    """Serialize one stable JSON record per manually reviewed assertion."""

    return "".join(
        json.dumps(item, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for item in assertions
    )
