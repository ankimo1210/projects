"""Versioned constants and lightweight records for paper-corpus artifacts."""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

CORPUS_SCHEMA_VERSION = "2.0.0"

P0_PAPER_IDS = (
    "1990-hull-white-interest-rate-derivative-securities",
    "1993-heston-closed-form-stochastic-volatility",
    "2000-mcneil-frey-tail-risk-evt",
    "2002-hagan-et-al-managing-smile-risk",
    "2019-lyashenko-mercurio-backward-looking-rates",
)

REQUIRED_SEMANTIC_SOURCES = (
    {
        "source_id": "2003-jarrow-yildirim-inflation-hjm",
        "title": "Pricing Treasury Inflation Protected Securities and Related Derivatives Using an HJM Model",
        "status": "missing_source",
        "reason": "catalogue contains a source link but no permitted local PDF",
    },
    {
        "source_id": "japan-mof-jgbi-conventions",
        "title": "Official Japanese inflation-linked government bond conventions",
        "status": "missing_source",
        "reason": "implementation cites conventions but the paper corpus has no catalogued official source PDF",
    },
)

VerificationStatus = Literal["verified", "auto", "unverified", "failed", "missing_source"]
PdfStructureStatus = Literal["clean", "warning", "error", "unavailable"]
BlockType = Literal[
    "title",
    "heading",
    "paragraph",
    "list",
    "equation",
    "table",
    "figure",
    "caption",
    "footnote",
    "header",
    "footer",
    "other",
]
ClaimType = Literal[
    "research_question",
    "model_assumption",
    "state_dynamics",
    "measure_and_numeraire",
    "payoff",
    "pricing_equation",
    "calibration_input",
    "numerical_method",
    "empirical_result",
    "limitation",
    "implementation_warning",
]

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NUMBER_RE = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?%?")


@dataclass(frozen=True)
class PdfStructureCheck:
    """Normalized result from ``qpdf --check``."""

    status: PdfStructureStatus
    return_code: int | None
    warning_count: int
    error_count: int

    def to_dict(self) -> dict[str, int | str | None]:
        """Return a stable JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class BoundingBox:
    """PDF-coordinate rectangle in points, measured from the top-left."""

    x0: float
    y0: float
    x1: float
    y1: float

    def validate(self) -> None:
        """Raise ``ValueError`` when the rectangle is non-finite or inverted."""

        values = (self.x0, self.y0, self.x1, self.y1)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("bounding-box coordinates must be finite")
        if self.x0 < 0 or self.y0 < 0 or self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("bounding box must be positive and non-empty")

    def to_list(self) -> list[float]:
        """Return ``[x0, y0, x1, y1]`` for JSON artifacts."""

        self.validate()
        return [self.x0, self.y0, self.x1, self.y1]


@dataclass(frozen=True)
class Provenance:
    """Source and extractor identity attached to every derived record."""

    source_pdf_sha256: str
    extractor_name: str
    extractor_version: str
    model_hash: str | None = None

    def validate(self) -> None:
        """Validate required provenance fields."""

        if not SHA256_RE.fullmatch(self.source_pdf_sha256):
            raise ValueError("source_pdf_sha256 must be a lowercase SHA-256 digest")
        if not self.extractor_name.strip() or not self.extractor_version.strip():
            raise ValueError("extractor name and version are required")
        if self.model_hash is not None and not self.model_hash.strip():
            raise ValueError("model_hash must be non-empty when provided")

    def to_dict(self) -> dict[str, str | None]:
        """Return stable JSON fields."""

        self.validate()
        return asdict(self)


def validate_record_identity(record_id: str, paper_id: str, page_number: int) -> None:
    """Validate a stable paper/page-scoped record identifier."""

    if not paper_id.strip():
        raise ValueError("paper_id is required")
    if page_number < 1:
        raise ValueError("page_number must be positive")
    prefix = f"{paper_id}:p{page_number:04d}:"
    if not record_id.startswith(prefix):
        raise ValueError(f"record id must start with {prefix}")


def stable_record_id(paper_id: str, page_number: int, kind: str, ordinal: int) -> str:
    """Build a deterministic paper/page/kind identifier."""

    if not paper_id.strip() or page_number < 1 or ordinal < 1 or not kind.strip():
        raise ValueError("paper_id, positive page/ordinal, and kind are required")
    return f"{paper_id}:p{page_number:04d}:{kind}:{ordinal:04d}"


@dataclass(frozen=True)
class BlockRecord:
    """Ordered spatial block extracted from one source page."""

    block_id: str
    paper_id: str
    page_number: int
    block_type: BlockType
    bbox: BoundingBox
    reading_order: int
    raw_text: str
    normalized_text: str
    verification_status: VerificationStatus
    provenance: Provenance
    confidence: float | None = None
    asset_path: str | None = None

    def validate(self) -> None:
        """Validate block identity, geometry, provenance, and confidence."""

        validate_record_identity(self.block_id, self.paper_id, self.page_number)
        self.bbox.validate()
        self.provenance.validate()
        if self.reading_order < 0:
            raise ValueError("reading_order must be non-negative")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")
        if self.verification_status == "verified" and not (
            self.normalized_text.strip() or self.asset_path
        ):
            raise ValueError("verified blocks require text or a source asset")

    def to_dict(self) -> dict[str, Any]:
        """Return a validated JSON-compatible record."""

        self.validate()
        result = asdict(self)
        result["bbox"] = self.bbox.to_list()
        result["provenance"] = self.provenance.to_dict()
        return result


@dataclass(frozen=True)
class EquationRecord:
    """Machine-readable equation linked to its exact source crop."""

    equation_id: str
    paper_id: str
    page_number: int
    bbox: BoundingBox
    source_asset: str
    latex: str | None
    equation_number: str | None
    verification_status: VerificationStatus
    provenance: Provenance
    confidence: float | None = None

    def validate(self) -> None:
        """Reject untraceable or falsely verified equations."""

        validate_record_identity(self.equation_id, self.paper_id, self.page_number)
        self.bbox.validate()
        self.provenance.validate()
        if not self.source_asset.strip():
            raise ValueError("equations require a source crop")
        if self.verification_status == "verified" and not (self.latex or "").strip():
            raise ValueError("verified equations require LaTeX")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between zero and one")


@dataclass(frozen=True)
class TableCell:
    """One structural table cell with raw and typed values."""

    row: int
    column: int
    raw_text: str
    normalized_text: str
    row_span: int = 1
    column_span: int = 1
    numeric_value: float | None = None

    def validate(self) -> None:
        """Validate cell coordinates, spans, and numeric values."""

        if self.row < 0 or self.column < 0:
            raise ValueError("table-cell coordinates must be non-negative")
        if self.row_span < 1 or self.column_span < 1:
            raise ValueError("table-cell spans must be positive")
        if self.numeric_value is not None and not math.isfinite(self.numeric_value):
            raise ValueError("numeric table values must be finite")


@dataclass(frozen=True)
class TableRecord:
    """Structured table linked to a source region and exported artifacts."""

    table_id: str
    paper_id: str
    page_number: int
    bbox: BoundingBox
    source_asset: str
    cells: tuple[TableCell, ...]
    caption: str | None
    verification_status: VerificationStatus
    provenance: Provenance
    csv_path: str | None = None
    html_path: str | None = None

    def validate(self) -> None:
        """Validate structure and reject duplicate table coordinates."""

        validate_record_identity(self.table_id, self.paper_id, self.page_number)
        self.bbox.validate()
        self.provenance.validate()
        if not self.source_asset.strip() or not self.cells:
            raise ValueError("tables require a source crop and at least one cell")
        coordinates: set[tuple[int, int]] = set()
        for cell in self.cells:
            cell.validate()
            coordinate = (cell.row, cell.column)
            if coordinate in coordinates:
                raise ValueError(f"duplicate table-cell coordinate: {coordinate}")
            coordinates.add(coordinate)
        if self.verification_status == "verified" and not (self.csv_path and self.html_path):
            raise ValueError("verified tables require CSV and HTML exports")


@dataclass(frozen=True)
class ClaimRecord:
    """Evidence-backed semantic claim about one paper."""

    claim_id: str
    paper_id: str
    claim_type: ClaimType
    statement: str
    page_numbers: tuple[int, ...]
    evidence_block_ids: tuple[str, ...]
    equation_ids: tuple[str, ...] = field(default_factory=tuple)
    table_ids: tuple[str, ...] = field(default_factory=tuple)
    verification_status: VerificationStatus = "unverified"

    def validate(self) -> None:
        """Reject unsupported, unpaged, or numeric-without-source claims."""

        if not self.paper_id.strip() or not self.claim_id.startswith(f"{self.paper_id}:claim:"):
            raise ValueError("claim id must be paper scoped")
        if not self.statement.strip() or not self.page_numbers or not self.evidence_block_ids:
            raise ValueError("claims require text, pages, and evidence blocks")
        if any(page < 1 for page in self.page_numbers):
            raise ValueError("claim page numbers must be positive")
        if NUMBER_RE.search(self.statement) and not (self.equation_ids or self.table_ids):
            raise ValueError("numeric claims require equation or table evidence")
