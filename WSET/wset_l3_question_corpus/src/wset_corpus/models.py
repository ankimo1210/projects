from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator

SourceType = Literal[
    "official_pdf",
    "official_webpage",
    "school_blog",
    "independent_blog",
    "public_quiz",
    "public_pdf",
    "video",
    "flashcard_site",
    "app_listing",
    "forum",
    "unknown",
]
AccessType = Literal[
    "public",
    "public_with_terms_restrictions",
    "registration_required",
    "paid",
    "inaccessible",
    "unknown",
]
CrawlPolicy = Literal[
    "metadata_only",
    "metadata_and_excerpt",
    "metadata_and_public_document",
    "manual_review_required",
    "do_not_fetch",
]


class SourceConfig(BaseModel):
    source_id: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    publisher: str | None = None
    language: str
    source_type: SourceType
    urls: list[HttpUrl]
    access_type: AccessType
    expected_content: list[str] = Field(default_factory=list)
    crawl_policy: CrawlPolicy
    copyright_risk: Literal["low", "medium", "high", "unknown"]
    enabled: bool = True
    reviewed_at: str | None = None
    notes: str | None = None


class SourceRecord(BaseModel):
    source_id: str
    name: str
    publisher: str | None = None
    author: str | None = None
    language: str
    source_type: SourceType
    url: str
    access_type: AccessType
    crawl_policy: CrawlPolicy
    copyright_risk: str
    retrieved_at: datetime | None = None
    content_hash: str | None = None
    status: str
    notes: str | None = None


class QuestionRecord(BaseModel):
    question_id: str
    source_id: str
    source_url: str
    language: str
    raw_text: str | None = None
    normalized_text: str | None = None
    answer_text: str | None = None
    answer_choices: list[str] = Field(default_factory=list)
    correct_answer_index: int | None = Field(default=None, ge=0)
    explanation_text: str | None = None
    mark_allocation: float | None = Field(default=None, ge=0)
    question_format: str = "unknown"
    command_verb: str | None = None
    topic_primary: str | None = None
    topic_secondary: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    grape_varieties: list[str] = Field(default_factory=list)
    learning_outcome: str | None = None
    cognitive_skill: str | None = None
    difficulty: str | None = None
    extraction_confidence: float = Field(ge=0, le=1)
    extraction_method: str = "heuristic"
    parser_version: str = "0.1.0"
    source_position: int = Field(ge=0)
    copyright_risk: str
    redistribution_status: str = "private_research_only"
    source_attribution_required: bool = True
    human_review_status: str = "unreviewed"
    quality_score: float | None = Field(default=None, ge=0, le=100)
    quality_category: str | None = None
    review_notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def require_lineage(self) -> QuestionRecord:
        if not self.source_id or not self.source_url:
            raise ValueError("source lineage is required")
        if self.correct_answer_index is not None:
            if not self.answer_choices:
                raise ValueError("correct answer index requires answer choices")
            if self.correct_answer_index >= len(self.answer_choices):
                raise ValueError("correct answer index is outside answer choices")
        return self


class QuestionPatternRecord(BaseModel):
    pattern_id: str
    abstract_pattern: str
    question_format: str
    command_verb: str
    required_reasoning_chain: list[str]
    suitable_topics: list[str]
    suggested_mark_range: tuple[int, int] | None = None
    examples_authored_internally: list[str]
    derived_from_source_ids: list[str] = Field(default_factory=list)
    copyright_safe_summary: str
    human_review_status: str = "human_reviewed"


class DuplicateMember(BaseModel):
    question_id: str
    similarity: float = Field(ge=0, le=100)


class DuplicateCluster(BaseModel):
    cluster_id: str
    match_type: Literal["exact", "near", "semantic"]
    members: list[DuplicateMember]
    probable_original_source: str | None = None
    language_relationship: str = "same_language"
    human_review_status: str = "unreviewed"
