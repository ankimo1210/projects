# AISAN TECHNOLOGY LBO Case Study

Reproducible public-information research and modeling repository for an HTML-based investment case study on AISAN TECHNOLOGY CO., LTD. (`4667.T`).

The output is an investment-committee style HTML report, not Excel or PowerPoint:

- `output/aisan_lbo_investment_report.html`
- `output/model_summary.json`
- `output/model_outputs.csv`
- `output/sources_bibliography.csv`
- `output/assumptions_log.md`

## Setup

```bash
cd /home/kazumasa/projects/aisan_lbo_case
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

The scripts also run in a Python environment that already has `pandas`, `numpy`, `requests`, `beautifulsoup4`, `PyYAML` and `Jinja2`. `plotly` is loaded in the final HTML through CDN.

If `python3-venv` is unavailable in the WSL image, use the workspace `uv` runner:

```bash
uv run --with pandas --with numpy --with pyyaml --with jinja2 --with requests --with beautifulsoup4 --with pytest python -m src.report.render_html
uv run --with pandas --with numpy --with pyyaml --with jinja2 --with requests --with beautifulsoup4 --with pytest pytest tests
```

## Data Refresh

```bash
python -m src.fetch.fetch_company_ir
python -m src.fetch.fetch_market_data
python -m src.fetch.fetch_filings
python -m src.fetch.fetch_peer_data
```

If a source cannot be fetched automatically, the fetcher writes a clear placeholder or manifest under `data/raw/`.

## Model and Report Generation

```bash
python -m src.parse.parse_financials
python -m src.parse.parse_segments
python -m src.parse.parse_shareholders
python -m src.model.lbo_model
python -m src.model.sensitivities
python -m src.report.render_html
```

The report renderer also rebuilds the parsed CSVs, model outputs, sensitivity outputs and bibliography before writing the HTML report.

## Tests

```bash
pytest
```

Tests cover:

- Sources = Uses
- Share price times diluted shares equals equity purchase price
- Enterprise value bridge
- Debt schedule never goes negative
- Ending cash never falls below minimum cash
- Exit equity value bridge
- IRR and MOIC calculations

## Known Data Limitations

- The repository uses public information only.
- EDINET annual securities reports may require an API key or manual download. `src.fetch.fetch_filings` creates a manifest and instructions rather than inventing filing data.
- Peer and precedent valuation multiples are not silently filled when public data is unavailable. Update `config/peer_set.yaml` after reviewing official transaction filings or a licensed market database.
- EBITDA is estimated as EBIT plus D&A estimated at 3.0% of revenue until official D&A is parsed from filings.
- FY2026 annual results were treated as unresolved in the public-source framing because AISAN disclosed a subsidiary investigation and a delay in the FY2026 results process.
- Excess cash availability is a sponsor estimate. Legal, operational and lender constraints must be confirmed before relying on cash extraction in a bid.

## Updating Assumptions

Primary inputs are YAML files:

- `config/sources.yaml` - source registry and bibliography
- `config/assumptions.yaml` - historical financials, share count, market fallback, transaction assumptions
- `config/scenarios.yaml` - Downside, Base, Upside and Sponsor operating cases
- `config/peer_set.yaml` - peer set and precedent transaction table

After editing assumptions, rerun:

```bash
python -m src.report.render_html
pytest
```

## Interpreting the Output

The model intentionally does not force a high-leverage LBO. AISAN is evaluated as a potential small-cap, growth-oriented take-private where returns are mainly driven by EBITDA growth, margin improvement, excess cash treatment and exit multiple.

The current recommendation logic is conservative:

- `Recommend` only if return thresholds are met and no gating issue remains.
- `Recommend with conditions` if the model works but bid conditions are material.
- `Do not recommend` if economics fail without a credible path.
- `Too early; proceed to confirmatory DD only` if public-source gating issues remain.

For this case, the unresolved subsidiary investigation and delayed FY2026 reporting are treated as gating items.
