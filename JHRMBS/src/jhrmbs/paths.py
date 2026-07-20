from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DataPaths:
    root: Path

    @property
    def raw(self) -> Path:
        return self.root / "raw"

    @property
    def raw_objects(self) -> Path:
        return self.raw / "objects"

    @property
    def raw_manifests(self) -> Path:
        return self.raw / "manifests"

    @property
    def processed(self) -> Path:
        return self.root / "processed"

    @property
    def features(self) -> Path:
        return self.root / "features"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def predictions(self) -> Path:
        return self.root / "predictions"

    @property
    def cashflows(self) -> Path:
        return self.root / "cashflows"

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ensure(self) -> None:
        for path in (
            self.raw_objects,
            self.raw_manifests,
            self.processed,
            self.features,
            self.models,
            self.predictions,
            self.cashflows,
            self.reports,
            self.logs,
        ):
            path.mkdir(parents=True, exist_ok=True)
