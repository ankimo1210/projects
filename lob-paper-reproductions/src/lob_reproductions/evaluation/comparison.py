from __future__ import annotations

from typing import Any

COMPARABILITY_FIELDS = (
    "dataset_variant",
    "split",
    "label_formula",
    "horizon",
    "feature_set",
    "metric",
)


def comparison_compatibility(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    differences = {
        field: {"left": left.get(field), "right": right.get(field)}
        for field in COMPARABILITY_FIELDS
        if left.get(field) != right.get(field)
    }
    return {
        "comparable": not differences,
        "differences": differences,
        "required_fields": list(COMPARABILITY_FIELDS),
    }
