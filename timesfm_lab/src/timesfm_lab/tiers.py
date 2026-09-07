"""How each dataset stands in relation to TimesFM's pretraining corpus.

Four tiers, ordered by how strong the claim "the model had not seen this" is:

- ``A`` — verified present. The series were downloaded from the corpus and
  compared value by value.
- ``B`` — absent from the corpus listing. A weaker claim: it rests on the file
  listing being complete and the model card being accurate.
- ``C_synthetic`` — generated here from a seed. Cannot have been seen by anyone.
- ``C_post_cutoff`` — market data whose every held-out point falls in 2026:
  after every cutoff the model card names.
- ``C_domain_control`` — UK motorway sensor counts from 2026. Also post-cutoff,
  but kept apart because it exists to answer a *different* question: it shares
  a domain, a frequency and a seasonal structure with tier A's
  ``traffic_hourly`` while sitting on the other side of the cutoff. Averaging
  it in with finance would hide the one comparison it was built for.

The point of the split is that the tiers disagree, and the size of that
disagreement is the finding.
"""

from __future__ import annotations

VERIFIED_IN_CORPUS = frozenset({"traffic_hourly", "weather_daily"})

TIER_ORDER = ("A", "B", "C_synthetic", "C_post_cutoff", "C_domain_control")

TIER_LABEL = {
    "A": "A 学習済み（実データ照合で確認）",
    "B": "B コーパスの一覧に無い",
    "C_synthetic": "C 生成物（存在し得ない）",
    "C_post_cutoff": "C 金融 2026年（カットオフ後）",
    "C_domain_control": "C 交通 2026年（領域対照）",
}

TIER_SHORT = {
    "A": "学習済み",
    "B": "一覧に無い",
    "C_synthetic": "合成",
    "C_post_cutoff": "金融2026",
    "C_domain_control": "交通2026",
}


def tier_of(dataset: str) -> str:
    if dataset in VERIFIED_IN_CORPUS:
        return "A"
    if dataset.startswith("syn_"):
        return "C_synthetic"
    if dataset == "traffic_uk_2026":
        return "C_domain_control"
    if dataset.startswith("fin_"):
        return "C_post_cutoff"
    return "B"
