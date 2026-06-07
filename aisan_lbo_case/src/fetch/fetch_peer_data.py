from __future__ import annotations

import pandas as pd

from src.utils.sources import CONFIG_DIR, PROJECT_ROOT, load_yaml


def main() -> None:
    peer_cfg = load_yaml(CONFIG_DIR / "peer_set.yaml")
    raw_dir = PROJECT_ROOT / "data" / "raw" / "peers"
    processed_dir = PROJECT_ROOT / "data" / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    peers = pd.DataFrame(peer_cfg["peers"])
    peers["valuation_status"] = "manual_update_required"
    peers["notes"] = "Peer relevance is curated; current peer multiples should be refreshed before final bid submission."
    peers.to_csv(processed_dir / "peer_set.csv", index=False)

    precedents = pd.DataFrame(peer_cfg["precedent_transactions"])
    precedents.to_csv(processed_dir / "precedent_transactions.csv", index=False)
    peers.to_csv(raw_dir / "peer_set_manual.csv", index=False)
    precedents.to_csv(raw_dir / "precedent_transactions_manual.csv", index=False)


if __name__ == "__main__":
    main()
