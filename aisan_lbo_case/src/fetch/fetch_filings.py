from __future__ import annotations

import pandas as pd

from src.utils.sources import PROJECT_ROOT, now_jst_iso


def main() -> None:
    raw_dir = PROJECT_ROOT / "data" / "raw" / "filings"
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "filing_type": "Annual securities reports",
            "status": "manual_or_api_key_required",
            "source_id": "edinet_api",
            "url": "https://disclosure2.edinet-fsa.go.jp/",
            "retrieved_at": now_jst_iso(),
            "instructions": (
                "Use EDINET API with a valid subscription key, or manually download AISAN TECHNOLOGY "
                "annual securities reports by EDINET code E04980. Save PDFs/XBRL under data/raw/filings/ "
                "and update config/sources.yaml."
            ),
        },
        {
            "filing_type": "TDnet disclosures",
            "status": "covered_by_company_ir_fetcher",
            "source_id": "tdnet_investigation_20260403;tdnet_results_delay_20260430;tdnet_q3_20260212",
            "url": "https://irbank.net/4667/ir",
            "retrieved_at": now_jst_iso(),
            "instructions": "Run python -m src.fetch.fetch_company_ir to download selected TDnet PDFs via IRBANK links.",
        },
    ]
    pd.DataFrame(rows).to_csv(raw_dir / "filings_manifest.csv", index=False)
    (raw_dir / "README_manual_filings.md").write_text(
        "# Manual Filing Retrieval\n\n"
        "EDINET official annual securities reports are not silently fabricated. If the API key is unavailable, "
        "download filings manually from EDINET for AISAN TECHNOLOGY CO., LTD. / EDINET code E04980 and place "
        "the raw files in this directory. Then update `config/sources.yaml` and rerun the parse/report scripts.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
