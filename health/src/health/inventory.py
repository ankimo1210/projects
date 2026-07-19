"""Data inventory: what the account actually has, per catalog and derived series."""
from __future__ import annotations

import pandas as pd

from health.endpoints import CATALOG, Metric
from health.store import Store


def build_inventory(store: Store, catalog: list[Metric] = CATALOG) -> pd.DataFrame:
    stats = store.series_stats().set_index("metric")
    states = store.sync_states().set_index("metric")

    def stat(idx, name, col, default):
        return idx.loc[name, col] if name in idx.index else default

    rows = []
    for m in catalog:
        rows.append({
            "metric": m.name, "source": "catalog", "kind": m.kind, "scope": m.scope,
            "n_days": int(stat(stats, m.name, "n", 0)),
            "first_date": stat(stats, m.name, "first_date", None),
            "last_date": stat(stats, m.name, "last_date", None),
            "last_synced": stat(states, m.name, "last_synced_date", None),
            "status": stat(states, m.name, "status", None),
        })
    catalog_names = {m.name for m in catalog}
    for name, row in stats.iterrows():
        if name not in catalog_names:
            rows.append({"metric": name, "source": "derived", "kind": "", "scope": "",
                         "n_days": int(row["n"]), "first_date": row["first_date"],
                         "last_date": row["last_date"], "last_synced": None, "status": None})
    return pd.DataFrame(rows).sort_values("metric").reset_index(drop=True)
