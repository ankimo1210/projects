from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import nbformat
import yaml
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS = ROOT / "notebooks"


def execute_notebook(name: str, cells: list[object]) -> None:
    notebook = new_notebook(cells=cells)
    notebook.metadata.kernelspec = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    client = NotebookClient(notebook, timeout=120, kernel_name="python3")
    client.execute(cwd=str(ROOT))
    nbformat.write(notebook, NOTEBOOKS / name)


def current_counts() -> tuple[int, int, Counter[str]]:
    sources = yaml.safe_load((ROOT / "config" / "sources.yaml").read_text())["sources"]
    path = ROOT / "data" / "reviewed" / "questions.jsonl"
    questions = [json.loads(line) for line in path.read_text().splitlines() if line]
    return len(sources), len(questions), Counter(row["human_review_status"] for row in questions)


def main() -> None:
    NOTEBOOKS.mkdir(exist_ok=True)
    source_count, question_count, statuses = current_counts()
    execute_notebook(
        "01_source_inventory.ipynb",
        [
            new_markdown_cell(
                f"## tl;dr\n\nThe registry contains **{source_count} reviewed source candidates**. "
                "Only explicitly approved public URLs are enabled for automatic fetch."
            ),
            new_markdown_cell(
                "## Context & Methods\n\nGrain: one row per source registry entry. "
                "The notebook reads `config/sources.yaml`; it does not fetch the web."
            ),
            new_code_cell(
                "from pathlib import Path\n"
                "from collections import Counter\n"
                "import yaml\n"
                "root = Path.cwd()\n"
                "sources = yaml.safe_load((root/'config/sources.yaml').read_text())['sources']\n"
                "print('sources:', len(sources))\n"
                "for field in ['language','source_type','access_type','crawl_policy','copyright_risk']:\n"
                "    print(field, dict(Counter(row[field] for row in sources)))"
            ),
            new_markdown_cell("## Data\n\nThe registry stores URL, publisher, access status, crawl policy, rights risk, review date, and notes."),
            new_code_cell(
                "enabled = [row for row in sources if row['enabled']]\n"
                "[(row['source_id'], row['crawl_policy']) for row in enabled]"
            ),
            new_markdown_cell(
                "## Results\n\nPaid, registered, member-only, and uncertain-provenance sources remain disabled."
            ),
            new_markdown_cell(
                "## Takeaways\n\nNew sources should begin disabled and require explicit rights/access review before fetching."
            ),
        ],
    )
    execute_notebook(
        "02_question_analysis.ipynb",
        [
            new_markdown_cell(
                f"## tl;dr\n\nThe current public-source pass produced **{question_count} machine candidates**. "
                "They are research candidates, not app-ready questions."
            ),
            new_markdown_cell(
                "## Context & Methods\n\nGrain: one extracted question-like text span per source position. "
                "Counts include learning-outcome-like statements and extraction fragments."
            ),
            new_code_cell(
                "from pathlib import Path\n"
                "from collections import Counter\n"
                "import json\n"
                "root = Path.cwd()\n"
                "rows = [json.loads(line) for line in (root/'data/reviewed/questions.jsonl').read_text().splitlines() if line]\n"
                "print('rows:', len(rows), 'unique ids:', len({row['question_id'] for row in rows}))\n"
                "for field in ['source_id','language','question_format','topic_primary']:\n"
                "    print(field, dict(Counter(row.get(field) for row in rows)))"
            ),
            new_markdown_cell("## Data\n\nRaw and normalized text stay in ignored local files. This notebook displays only aggregate counts."),
            new_code_cell(
                "print('mark allocation present:', sum(row.get('mark_allocation') is not None for row in rows))\n"
                "print('low extraction confidence:', sum(row['extraction_confidence'] < .75 for row in rows))"
            ),
            new_markdown_cell(
                "## Results\n\nThe corpus is dominated by English community flashcards; "
                "Japanese and constructed-response coverage remain comparatively small."
            ),
            new_markdown_cell(
                "## Takeaways\n\nDo not use the corpus for study delivery until human review and Japanese-source coverage improve."
            ),
        ],
    )
    execute_notebook(
        "03_quality_review.ipynb",
        [
            new_markdown_cell(
                "## tl;dr\n\n"
                f"Screening status: **{statuses.get('machine_screened', 0)} machine-screened**, "
                f"**{statuses.get('fact_check_required', 0)} fact-check required**, "
                f"and **{statuses.get('rejected', 0)} rejected**. "
                "Public-safe export contains no question or answer text."
            ),
            new_markdown_cell(
                "## Context & Methods\n\n### Key Assumptions\n\n"
                "The intended grain is one candidate span at one source position. "
                "Machine screening is conservative and does not replace human review."
            ),
            new_code_cell(
                "from pathlib import Path\n"
                "from collections import Counter\n"
                "import csv, json\n"
                "root = Path.cwd()\n"
                "rows = [json.loads(line) for line in (root/'data/reviewed/questions.jsonl').read_text().splitlines() if line]\n"
                "public = [json.loads(line) for line in (root/'data/exports/questions_public_safe.jsonl').read_text().splitlines() if line]\n"
                "duplicates = list(csv.DictReader((root/'data/exports/duplicate_clusters.csv').open(encoding='utf-8-sig')))\n"
                "print('rows / columns:', len(rows), len(rows[0]))\n"
                "print('unique question ids:', len({row['question_id'] for row in rows}))\n"
                "print('statuses:', dict(Counter(row['human_review_status'] for row in rows)))\n"
                "print('duplicate member rows:', len(duplicates))"
            ),
            new_markdown_cell("## Data\n\nChecks cover completeness, uniqueness, enum validity, extraction confidence, review status, and public-safe leakage."),
            new_code_cell(
                "required = ['question_id','source_id','source_url','language','normalized_text','extraction_confidence']\n"
                "print('required-field nulls:', {field: sum(not row.get(field) for row in rows) for field in required})\n"
                "print('out-of-range confidence:', sum(not 0 <= row['extraction_confidence'] <= 1 for row in rows))\n"
                "print('public-safe text leaks:', sum(any(row.get(field) for field in ['raw_text','normalized_text','answer_text']) for row in public))"
            ),
            new_markdown_cell(
                "## Results\n\nRequired fields and stable IDs are complete, but extraction quality is partial: "
                "PDF character-spacing damage, fragments, and marketing headings are present. "
                "Japanese candidates are present but remain a small minority."
            ),
            new_markdown_cell(
                "## Takeaways\n\n1. Human-review the machine-screened queue.\n"
                "2. Repair multi-line PDF reconstruction before expanding volume.\n"
                "3. Add a rights-reviewed Japanese public source.\n"
                "4. Keep public-safe leakage tests blocking every export."
            ),
        ],
    )


if __name__ == "__main__":
    main()
