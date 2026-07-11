# ruff: noqa: E501
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from jinja2 import Environment, select_autoescape

from .models import QuestionRecord
from .registry import load_sources
from .utils import ROOT, read_jsonl

TEMPLATE = """<!doctype html>
<html lang=\"ja\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width\">
<title>WSET L3 Research Corpus</title><style>
:root{color-scheme:light;--wine:#722f37;--ink:#252120;--soft:#f6f1ed}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;color:var(--ink);background:#fff}
header{padding:2.5rem max(1.25rem,6vw);background:linear-gradient(120deg,#4d1824,#8f3d4b);color:white}main{max-width:1120px;margin:auto;padding:2rem 1.25rem}.notice{background:#fff5d9;border-left:4px solid #c58a00;padding:1rem}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1rem;margin:1.5rem 0}.card{background:var(--soft);border-radius:12px;padding:1rem}.value{font-size:2rem;font-weight:700;color:var(--wine)}table{width:100%;border-collapse:collapse;font-size:.9rem}th,td{text-align:left;padding:.65rem;border-bottom:1px solid #ddd;vertical-align:top}th{position:sticky;top:0;background:#fff}.pill{display:inline-block;background:#eee;border-radius:999px;padding:.15rem .55rem}.restricted{color:#8b1d2c}section{margin:2.5rem 0}a{color:#7b2431}</style></head>
<body><header><h1>WSET Level 3 Question Corpus</h1><p>Private research inventory · generated locally</p></header><main>
<div class=\"notice\"><strong>Copyright notice:</strong> Third-party text is private-research-only. This report shows metadata and short previews only and is not an official WSET product.</div>
<div class=\"cards\"><div class=\"card\"><div class=\"value\">{{ source_count }}</div>sources</div><div class=\"card\"><div class=\"value\">{{ question_count }}</div>candidates</div><div class=\"card\"><div class=\"value\">{{ reviewed_count }}</div>reviewed</div><div class=\"card\"><div class=\"value\">{{ duplicate_count }}</div>duplicate rows</div><div class=\"card\"><div class=\"value\">{{ pattern_count }}</div>original patterns</div></div>
<section><h2>Coverage</h2><h3>Languages</h3><p>{{ languages }}</p><h3>Formats</h3><p>{{ formats }}</p><h3>Topics</h3><p>{{ topics }}</p></section>
<section><h2>Source inventory</h2><table><thead><tr><th>Source</th><th>Language</th><th>Type / Access</th><th>Policy</th><th>Risk</th><th>Notes</th></tr></thead><tbody>{% for s in sources %}<tr><td><a href=\"{{ s.urls[0] }}\">{{ s.name }}</a><br><small>{{ s.publisher or '' }}</small></td><td>{{ s.language }}</td><td>{{ s.source_type }}<br>{{ s.access_type }}</td><td><span class=\"pill\">{{ s.crawl_policy }}</span></td><td class=\"restricted\">{{ s.copyright_risk }}</td><td>{{ s.notes or '' }}</td></tr>{% endfor %}</tbody></table></section>
<section><h2>Question catalog</h2><table><thead><tr><th>ID</th><th>Source</th><th>Language</th><th>Format</th><th>Topic</th><th>Score</th><th>Private preview</th></tr></thead><tbody>{% for q in questions %}<tr><td>{{ q.question_id }}</td><td>{{ q.source_id }}</td><td>{{ q.language }}</td><td>{{ q.question_format }}</td><td>{{ q.topic_primary or '' }}</td><td>{{ q.quality_score or '' }}</td><td>{{ (q.normalized_text or '')[:180] }}</td></tr>{% endfor %}</tbody></table></section>
<section><h2>Known gaps</h2><ul><li>Japanese-language public sources require manual rights and access review.</li><li>Automated labels and quality scores require human review.</li><li>No paid, registered, or member-only material is fetched.</li><li>Question count targets are not allowed to override copyright or access controls.</li></ul></section>
</main></body></html>"""


def _counter_text(values: list[str]) -> str:
    return " · ".join(f"{key}: {value}" for key, value in Counter(values).most_common()) or "none"


def build_report(output: Path | None = None) -> Path:
    output = output or ROOT / "reports" / "index.html"
    reviewed_path = ROOT / "data" / "reviewed" / "questions.jsonl"
    normalized_path = ROOT / "data" / "normalized" / "questions.jsonl"
    question_path = reviewed_path if reviewed_path.exists() else normalized_path
    questions = [QuestionRecord.model_validate(row) for row in read_jsonl(question_path)]
    duplicate_path = ROOT / "data" / "exports" / "duplicate_clusters.csv"
    duplicates = []
    if duplicate_path.exists() and duplicate_path.stat().st_size:
        with duplicate_path.open(encoding="utf-8-sig") as handle:
            duplicates = list(csv.DictReader(handle))
    patterns = read_jsonl(ROOT / "data" / "reviewed" / "question_patterns.jsonl")
    env = Environment(autoescape=select_autoescape(["html"]))
    html = env.from_string(TEMPLATE).render(
        source_count=len(load_sources()),
        question_count=len(questions),
        reviewed_count=sum(q.human_review_status == "human_reviewed" for q in questions),
        duplicate_count=len(duplicates),
        pattern_count=len(patterns),
        languages=_counter_text([q.language for q in questions]),
        formats=_counter_text([q.question_format for q in questions]),
        topics=_counter_text([q.topic_primary or "unknown" for q in questions]),
        sources=[source.model_dump(mode="json") for source in load_sources()],
        questions=questions,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    for filename in (
        "source_inventory.html",
        "question_catalog.html",
        "coverage_matrix.html",
        "duplicate_analysis.html",
    ):
        (output.parent / filename).write_text(html, encoding="utf-8")
    return output
