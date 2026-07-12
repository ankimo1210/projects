from __future__ import annotations

from pathlib import Path

import yaml

from .models import SourceConfig
from .utils import ROOT


def load_sources(path: Path | None = None) -> list[SourceConfig]:
    source_path = path or ROOT / "config" / "sources.yaml"
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    return [SourceConfig.model_validate(item) for item in payload.get("sources", [])]


def approved_sources(
    sources: list[SourceConfig], source_id: str | None = None
) -> list[SourceConfig]:
    approved_policies = {"metadata_and_excerpt", "metadata_and_public_document"}
    return [
        source
        for source in sources
        if source.enabled
        and source.crawl_policy in approved_policies
        and (source_id is None or source.source_id == source_id)
    ]
