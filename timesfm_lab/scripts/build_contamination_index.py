"""Download the GiftEvalPretrain copies of the shared datasets and index them."""

from __future__ import annotations

import urllib.request

from timesfm_lab.contamination import (
    GEP_ALIASES,
    GEP_REPO,
    GEP_URL,
    build_index,
    save_index,
)
from timesfm_lab.datasets import DATA_DIR

CACHE = DATA_DIR / "gifteval_pretrain"


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    for gep_name in GEP_ALIASES:
        dest = CACHE / f"{gep_name}.arrow"
        if dest.exists():
            print(f"skip {dest.name}")
            continue
        url = GEP_URL.format(repo=GEP_REPO, name=gep_name)
        print(f"fetch {url}")
        urllib.request.urlretrieve(url, dest)

    index = build_index(CACHE)
    save_index(index)
    for key, cov in index.items():
        print(
            f"{key:16s} gep={cov.gep_name:15s} series {cov.n_series_gep}/{cov.n_series_local} "
            f"identical {cov.identical}/{cov.checked} verified={cov.verified}"
        )
        lens = sorted(cov.lengths.values())
        print(f"   corpus lengths: min {lens[0]} median {lens[len(lens)//2]} max {lens[-1]}")


if __name__ == "__main__":
    main()
