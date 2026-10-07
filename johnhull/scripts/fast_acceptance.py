"""Build and accept Ch2–9 supplements under the explicitly approved fast-v1 policy.

Uses the existing ledger schema; exact hashes track provenance, not numerical
agreement. Numerical claims come from fresh source-pin and independent tests.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import html
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

PROJECT = Path(__file__).resolve().parents[1]
OUT = "docs/validation/fast-ch02-09"
CONFIG = "docs/acceptance/fast-ch02-09.json"
NOTE = "docs/CHAPTERS_02_09_ACCEPTANCE_2026-10-07.md"
POLICY = "docs/FAST_ACCEPTANCE.md"
DETAILS = "docs/lessons/early-chapter-details.json"
GROUPS = {
    2: ("futures_market", {"4": "margin", "6": "quotes", "10": "recognition", "11": "settlement"}),
    3: (
        "futures_hedging",
        {
            "1": "basic",
            "2": "business",
            "3": "basis",
            "4": "minimum_variance",
            "5": "index",
            "6": "roll",
            "appendix": "capm",
        },
    ),
    4: (
        "rates_foundations",
        {
            "2": "reference",
            "4": "compounding",
            "5": "zero",
            "6": "bond",
            "7": "bootstrap",
            "8": "forward",
            "9": "fra",
            "10": "duration",
            "11": "convexity",
        },
    ),
    5: (
        "forward_pricing",
        {
            "2": "short",
            "4": "no_income",
            "5": "income",
            "6": "yield",
            "7": "value",
            "9": "index",
            "10": "currency",
            "11": "commodity",
            "12": "carry",
            "14": "expected",
        },
    ),
    6: ("rate_futures", {"1": "conventions", "2": "bonds", "3": "short_rates", "4": "duration"}),
    7: (
        "swap_foundations",
        {
            "1": "cash",
            "2": "ois",
            "3": "transform",
            "4": "dealer",
            "5": "comparative",
            "6": "valuation",
            "7": "roll",
            "8": "currency_cash",
            "9": "currency_value",
            "10": "mixed",
            "12": "cds",
        },
    ),
    8: ("securitization_foundations", {"1": "waterfall"}),
    9: ("xva_foundations", {"1": "credit", "2": "funding", "4": "incremental"}),
}
LIMITS = {
    "5.7": "Business Snapshot 5.2には割引金利がないためforwardの現在価値4,000×DFの数値は確定できない。確定損益4,000と時点差だけを確認する。",
    "6.3": "convexity調整の数値に必要なモデル入力とTechnical Noteは原典本文にない。調整の減算構造だけを確認し、調整額の再現を主張しない。Julyの.55%やEx6.3の197000/102250/502250は本文の誤記として扱う。",
    "7.2": "p.175本文の$100,000は直後の$100 millionと不整合。Table7.2の単位は千ドル、最終元本100,000なので想定元本は100 million USD。本文の$100,000は原典の誤記として扱う。",
    "7.8": "通貨swapのdealer利益をhedgeしたPVにはFX forward曲線が必要だが本文にない。二通貨の受払と年率の説明を確認し、hedged利益PVは未検証。",
    "7.9": "丸め前の価値0.9627879765 millionは0.9628 millionとなる。印刷0.9629との不一致を記録し、許容幅を広げて一致させない。",
}
SAMPLE = {2: "2.4", 3: "3.4", 4: "4.4", 5: "5.10", 6: "6.3", 7: "7.9", 8: "8.1", 9: "9.2"}


def read(name):
    """Read a project-relative JSON record."""
    return json.loads((PROJECT / name).read_text())


def digest(name):
    """Hash a project-relative file."""
    return hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()


def hashes(names):
    """Track exact inputs for later freshness checks."""
    return {name: digest(name) for name in sorted(set(names))}


def text_sha(text):
    """Normalize whitespace, preserving every prose and mathematical character."""
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


class SemanticManifest(HTMLParser):
    """Read expected prose, math and tables from the generated source HTML."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.nodes = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        identifier = attrs.get("id", "")
        node = None
        if identifier.startswith("section-") or attrs.get("class") == "requirement":
            node = dict(text=[], math=[], tables=0)
            self.nodes[identifier] = node
        self.stack.append((tag, node))
        for _, target in self.stack:
            if target is not None:
                if "data-source-tex" in attrs:
                    target["math"].append(attrs["data-source-tex"])
                if tag == "table":
                    target["tables"] += 1

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        for _, target in self.stack:
            if target is not None:
                target["text"].append(data)

    def manifest(self):
        return {
            k: dict(text_sha256=text_sha("".join(v["text"])), math=v["math"], tables=v["tables"])
            for k, v in self.nodes.items()
        }


def write(name, value):
    """Write finite JSON, creating its parent directory."""
    target = PROJECT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def fresh(record):
    """Refuse failed, missing, or changed evidence."""
    if record.get("status") != "PASS":
        raise ValueError("not PASS")
    for key in ("source_sha256", "artifact_sha256"):
        if not record.get(key):
            raise ValueError("missing provenance: " + key)
        for name, expected in record[key].items():
            if digest(name) != expected:
                raise ValueError("stale: " + name)


def block(body, label):
    """Extract a prose block, including its indented paragraphs and equations."""
    match = re.search(r"^- \*\*" + label + r"[^：\n]*：\*\*\s*", body, re.M)
    if not match:
        return ""
    text = body[match.end() :]
    stop = re.search(r"\n- \*\*|\n\| ID|\n## ", text)
    text = text[: stop.start()] if stop else text
    return text.strip()


def sections():
    """Compile all original requirements, without carrying planning prose to readers."""
    state_rows = {}
    for line in (PROJECT / "docs/P6_STATUS.md").read_text().splitlines():
        if line.startswith("| §"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            state_rows[parts[0].removeprefix("§")] = parts
    result = []
    for chapter, (module, mapping) in GROUPS.items():
        prep = f"docs/prep/sections/ch{chapter:02}.md"
        text = (PROJECT / prep).read_text()
        matches = list(re.finditer(r"^## §(\d+\.(?:\d+|appendix)) ([^\n]+)", text, re.M))
        for i, match in enumerate(matches):
            sid, heading = match.groups()
            body = text[match.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)]
            body = body.split("\n## 申し送り", 1)[0]
            page = re.search(r"[（(]pp?\.\s*(\d+)(?:[–−—-](\d+))?[）)]", heading)
            if not page:
                raise ValueError("source pages missing: " + heading)
            reqs = []
            for line in body.splitlines():
                if line.startswith("| D"):
                    p = [x.strip() for x in line.strip("|").split("|")]
                    if len(p) != 3:
                        raise ValueError("requirement columns: " + line)
                    reqs.append(dict(id=p[0], statement=p[1], reading=p[2]))
            explanation = block(body, "原典の内容")
            if not explanation or not reqs:
                raise ValueError("empty lesson: " + sid)
            suffix = mapping.get(sid.split(".", 1)[1])
            item = dict(
                id=sid,
                chapter=chapter,
                heading=heading,
                source_pages=[int(page[1]), int(page[2] or page[1])],
                requirements=reqs,
                explanation=explanation,
                printed=block(body, "印刷値"),
                cautions=block(body, "依存・注意"),
                prep=prep,
                lesson=f"docs/lessons/ch{chapter:02}.md",
                page=f"report/site/chapters/ch{chapter:02}.html",
                implementation=f"hullkit/src/hullkit/_{module}.py" if suffix else None,
                tests=[f"hullkit/tests/test_{module}_{suffix}.py"] if suffix else [],
                limitation=LIMITS.get(sid, ""),
            )
            if suffix:
                row = state_rows.get(sid)
                if not row or not (PROJECT / item["tests"][0]).is_file():
                    raise ValueError("missing calculation/test mapping: " + sid)
                item["calculation"] = row[2]
                item["calculation_scope"] = (
                    row[3]
                    .replace("説明・受入保留", "")
                    .replace("補足教材・fast-v1受入済み（10/7）", "")
                    .strip()
                )
                if sid == "2.4":
                    item["calculation_scope"] = (
                        "利息と余剰引出しなし。原典表の2回のcallは翌日入金済み。最終日のcallが未入金なのは別の合成境界例。"
                    )
            result.append(item)
    wanted = {
        r["id"] for r in read("docs/section_inventory.json")["entries"] if r["chapter"] in GROUPS
    }
    if {r["id"] for r in result} != wanted or len(result) != 70:
        raise ValueError("chapter inventory differs")
    return result


def learner_prose(text):
    """Remove storage/planning terminology, preserving formulas and caveats."""
    text = re.sub(r"[✓✔]再計算一致", "", text)
    text = re.sub(r"\*\*([^*\n]+?)\s+\*\*", r"**\1**", text)
    text = text.replace("ピン不要", "説明用の条件・歴史的記述").replace("ピン候補", "本文の数値")
    text = text.replace("pin", "固定値").replace("hullkit", "計算部品")
    text = re.sub(r"\*\*(?:規模|関連)：\*\*.*", "", text)
    text = "\n".join(
        line
        for line in text.splitlines()
        if not re.search(
            r"既存.{0,12}(?:テスト|ピン|ノート|pin)|pytest|test_[a-z]|監査 FR|docstring|assert|business_dates|weather|vol\d{2}",
            line,
        )
    )
    return text.strip()


def lesson_text(row):
    """Return a compact section with all original learning requirements."""
    sid = row["id"]
    text = [
        f'<section class="lesson" id="section-{sid.replace(".", "-")}">',
        f"\n## §{sid} " + row["heading"].split("（", 1)[0].split("(", 1)[0],
        f"\n出典: Hull 11e Global Edition pp.{row['source_pages'][0]}–{row['source_pages'][1]}。\n",
        learner_prose(row["explanation"]),
    ]
    text.append("\n### 要点の読み方\n")
    detail = read(DETAILS).get(sid)
    if not detail:
        raise ValueError("missing explanatory supplement: " + sid)
    text.append(detail + "\n")
    for req in row["requirements"]:
        text += [
            f'<div class="requirement" id="{req["id"]}">\n',
            learner_prose(req["statement"]),
            "\n\n" + learner_prose(req["reading"]),
            "\n</div>\n",
        ]
    if row["printed"]:
        text += ["\n### 本文の数値と前提\n", learner_prose(row["printed"])]
    if row.get("calculation"):
        text += [
            "\n### 計算の読み方\n",
            row["calculation"],
            "\n\n"
            + row["calculation_scope"]
            .replace("計算完了。", "例の前提：")
            .replace("RED→GREEN確認", "確認"),
        ]
    if row["limitation"]:
        text += ['\n<div class="caution">\n', row["limitation"], "\n</div>\n"]
    if row["cautions"]:
        text += ["\n### 前提・注意\n", learner_prose(row["cautions"])]
    text += [
        "\n確認: 上の関係で、数量・通貨・金利の表示方法・受払の時点を変えると何が変わるか説明する。\n",
        "</section>\n",
    ]
    return "\n".join(text)


def build():
    """Generate repeatable standalone supplements without rebuilding frozen volumes."""
    rows = sections()
    cfg = dict(
        profile="fast-v1",
        base="d6c3a0e2",
        sections=rows,
        samples={str(k): v for k, v in SAMPLE.items()},
        template_sha256=hashlib.sha256(
            (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_bytes()
        ).hexdigest(),
    )
    write(CONFIG, cfg)
    tokens = (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_text()
    css = """.lesson{margin:2rem 0;padding:1.4rem;background:var(--surface);border-radius:10px}
    .requirement{padding:.6rem 0;border-bottom:1px solid var(--rule)}
    .caution{padding:.8rem;border-left:3px solid var(--series-2)}
    p,li{line-height:1.85} table{width:100%;border-collapse:collapse}
    th,td{padding:.5rem;text-align:left;border-bottom:1px solid var(--rule)}
    pre{overflow-x:auto} .lesson{overflow-wrap:anywhere} mjx-container{overflow-x:auto;max-width:100%}
    nav{line-height:2} .wrap{max-width:1060px;margin:auto;padding:1.3rem}
    """
    # Markdown raw block sections need blank lines before the inner prose.
    md = MarkdownIt("commonmark", {"html": True}).enable("table")
    md.use(
        dollarmath_plugin,
        allow_digits=False,
        renderer=lambda tex, options: (
            '<span data-source-tex="'
            + html.escape(tex, quote=True)
            + '">\\('
            + html.escape(tex)
            + "\\)</span>"
        ),
    )
    cfg["expected_dom"] = {}
    generated = []
    for chapter in GROUPS:
        selected = [r for r in rows if r["chapter"] == chapter]
        intro = f"# Ch{chapter} 節別補足教材\n\n刊行時点の原典本文を学ぶ。現在の市場条件や法令の適用はこの教材の対象に含めない。\n\n"
        content = intro + "\n".join(lesson_text(r) for r in selected)
        target = PROJECT / selected[0]["lesson"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        nav = " · ".join(f'<a href="ch{c:02}.html">Ch{c}</a>' for c in range(1, 10))
        anchors = "　".join(
            f'<a href="#section-{r["id"].replace(".", "-")}">§{r["id"]}</a>' for r in selected
        )
        page = '<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        page += f"<title>Hull Ch{chapter} 補足教材</title><style>{tokens}{css}</style>"
        page += """<script>window.MathJax={tex:{inlineMath:[['\\\\(','\\\\)']]},options:{skipHtmlTags:['script','noscript','style','textarea','pre','code']}};</script>
        <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script><body><main class="wrap">"""
        page += f'<nav>{nav} · <a href="../index.html">ポータル</a> · <a href="../../../book/_build/html/index.html">Book</a></nav><nav>{anchors}</nav>'
        # A number after $ is usually currency. Preserve genuine numerical TeX
        # with an explicit initial command, so it cannot absorb a later $ quote.
        protected = re.sub(
            r"\$(\d[^$\n]+)\$",
            lambda m: (
                "$\\," + m[1] + "$"
                if re.search(r"[\\^_]", m[1]) and not re.search(r"[\u3040-\u9fff]", m[1])
                else m[0]
            ),
            content,
        )
        page += md.render(protected) + "</main></body></html>"
        semantic = SemanticManifest()
        semantic.feed(page)
        cfg["expected_dom"].update(semantic.manifest())
        out = PROJECT / selected[0]["page"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page)
        generated += [selected[0]["lesson"], selected[0]["page"]]
    write(CONFIG, cfg)
    return dict(
        status="PASS",
        sections=len(rows),
        requirements=sum(len(r["requirements"]) for r in rows),
        files=generated,
    )


def inputs(cfg):
    """Declare every source used by the lightweight batch."""
    names = [
        "options, futures and other derivatives 11th.pdf",
        "docs/section_inventory.json",
        "docs/P6_STATUS.md",
        "hullkit/src/hullkit/rates.py",
        "hullkit/src/hullkit/swaps.py",
        DETAILS,
        CONFIG,
        POLICY,
        NOTE,
        "scripts/fast_acceptance.py",
        "scripts/verify_fast_acceptance_browser.cjs",
        "report/tests/test_fast_acceptance.py",
    ]
    for row in cfg["sections"]:
        names += [row["prep"], row["lesson"], *row["tests"]]
        if row["implementation"]:
            names.append(row["implementation"])
    return sorted(set(names))


def test():
    """Run the 49 numerical suites plus the acceptance rejection tests once."""
    cfg = read(CONFIG)
    tests = [
        "johnhull/" + n
        for n in inputs(cfg)
        if n.startswith("hullkit/tests/") or n == "report/tests/test_fast_acceptance.py"
    ]
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *tests,
        "--junitxml=" + str(PROJECT / OUT / "targeted-tests.xml"),
    ]
    start = time.monotonic()
    result = subprocess.run(
        command, cwd=PROJECT.parent, capture_output=True, text=True, check=False
    )
    (PROJECT / OUT / "targeted-tests.log").write_text(result.stdout + result.stderr)
    record = dict(
        status="PASS" if result.returncode == 0 else "FAIL",
        command=command,
        exit_code=result.returncode,
        seconds=round(time.monotonic() - start, 2),
        tests=tests,
        summary=result.stdout.strip().splitlines()[-1],
        source_sha256=hashes(inputs(cfg)),
        artifact_sha256=hashes([OUT + "/targeted-tests.xml", OUT + "/targeted-tests.log"]),
    )
    write(OUT + "/numerical-check.json", record)
    if result.returncode:
        raise ValueError(record["summary"])
    return dict(status="PASS", summary=record["summary"], seconds=record["seconds"])


def validate(cfg, numerical, browser):
    """Fail closed on missing tests/requirements, altered inputs or partial rendering."""
    fresh(numerical)
    fresh(browser)
    if cfg["sections"] != sections():
        raise ValueError("configuration differs from original chapter inventory/requirements")
    if set(inputs(cfg)) - set(numerical["source_sha256"]):
        raise ValueError("numerical provenance incomplete")
    if (
        cfg["template_sha256"]
        != hashlib.sha256(
            (PROJECT.parent / "docs/templates/claude-report/tokens.css").read_bytes()
        ).hexdigest()
    ):
        raise ValueError("shared template changed")
    required_tests = {"johnhull/" + name for row in cfg["sections"] for name in row["tests"]}
    if not required_tests.issubset(numerical.get("tests", [])) or numerical.get("exit_code") != 0:
        raise ValueError("numerical test coverage incomplete")
    required = {r["id"]: {q["id"] for q in r["requirements"]} for r in cfg["sections"]}
    observed = browser.get("sections", {})
    if set(required) != set(observed):
        raise ValueError("rendered section coverage incomplete")
    for sid, reqs in required.items():
        row = observed[sid]
        expected = cfg["expected_dom"]["section-" + sid.replace(".", "-")]
        if (
            row.get("text_sha256") != expected["text_sha256"]
            or row.get("math") != len(expected["math"])
            or row.get("tables") != expected["tables"]
        ):
            raise ValueError("rendered prose/math/table differs: " + sid)
        if (
            set(row.get("requirements", [])) != reqs
            or len(row["requirements"]) != len(reqs)
            or not all(
                row.get(k)
                for k in ["explanation_checked", "math_checked", "layout_checked", "links_checked"]
            )
        ):
            raise ValueError("unchecked requirement/rendering: " + sid)
    if {c["section"] for c in browser.get("captures", [])} != set(SAMPLE.values()) or len(
        browser["captures"]
    ) != 8:
        raise ValueError("representative captures missing/duplicate")
    if not browser.get("missing_requirement_rejected"):
        raise ValueError("missing negative browser control")
    if not browser.get("mutated_requirement_rejected"):
        raise ValueError("missing prose/math mutation control")


def check():
    """Bind successful fresh tests and a complete browser sweep."""
    cfg = read(CONFIG)
    numerical, browser = read(OUT + "/numerical-check.json"), read(OUT + "/browser-check.json")
    validate(cfg, numerical, browser)
    record = dict(
        status="PASS",
        profile="fast-v1",
        checked_at=datetime.now(UTC).isoformat(),
        sections=[r["id"] for r in cfg["sections"]],
        requirements=sum(len(r["requirements"]) for r in cfg["sections"]),
        numerical_summary=numerical["summary"],
        browser_states=70,
        captures=8,
        omitted=[
            "full-suite",
            "whole-Book rebuild and sweep",
            "all-section visual screenshots",
            "second viewport",
            "two-store restores",
        ],
        source_sha256=hashes(
            [*inputs(cfg), OUT + "/numerical-check.json", OUT + "/browser-check.json"]
        ),
        artifact_sha256=hashes(
            [r["page"] for r in cfg["sections"]] + [c["path"] for c in browser["captures"]]
        ),
    )
    write(OUT + "/acceptance-check.json", record)
    return dict(status="PASS", sections=70, requirements=record["requirements"])


def register():
    """Register actual requirements only after native validation of the prospective ledger."""
    cfg, record = read(CONFIG), read(OUT + "/acceptance-check.json")
    validate(cfg, read(OUT + "/numerical-check.json"), read(OUT + "/browser-check.json"))
    fresh(record)
    ledger = copy.deepcopy(read("docs/section_ledger.json"))
    by_id = {r["id"]: r for r in cfg["sections"]}
    old = {
        r["id"]: copy.deepcopy(r)
        for r in ledger["sections"]
        if r["status"] == "accepted" and r["id"] not in by_id
    }

    def item(name, kind):
        return dict(kind=kind, path=name, sha256=digest(name))

    for row in ledger["sections"]:
        if row["id"] not in by_id:
            continue
        spec = by_id[row["id"]]
        ev = dict(
            lesson=item(spec["lesson"], "source"),
            original_requirements=item(spec["prep"], "reference"),
            acceptance_note=item(NOTE, "note"),
            policy=item(POLICY, "note"),
            numerical=item(OUT + "/numerical-check.json", "record"),
            browser=item(OUT + "/browser-check.json", "record"),
            chapter_check=item(OUT + "/acceptance-check.json", "record"),
        )
        if spec["implementation"]:
            ev["implementation"] = item(spec["implementation"], "source")
            ev["test"] = item(spec["tests"][0], "test")
        requirements = []
        for req in spec["requirements"]:
            coverage = {
                k: dict(state="verified", refs=refs, locator=req["id"])
                for k, refs in [
                    ("explanation", ["lesson", "acceptance_note"]),
                    ("rendered", ["browser", "chapter_check"]),
                ]
            }
            for axis in ["implementation", "independent_validation"]:
                coverage[axis] = (
                    dict(
                        state="verified",
                        refs=["implementation"] if axis == "implementation" else ["numerical"],
                        locator=spec["tests"][0],
                    )
                    if spec["implementation"] and req["id"] not in {"D6.2-06", "D6.3-06"}
                    else dict(
                        state="not_applicable",
                        refs=[],
                        reason=(
                            "原典は定性説明を要求し、価格の数値化は要求しない。説明と配布HTMLを確認した。受渡選択権の価格とconvexity調整cの算出は範囲外。"
                            if req["id"] in {"D6.2-06", "D6.3-06"}
                            else "刊行時点の制度・用語・歴史・経済的説明の要求。数値計算モデルを要求しない。説明と配布HTMLの意味を確認した。"
                        ),
                    )
                )
            coverage["visualization"] = dict(
                state="not_applicable",
                refs=[],
                reason=f"fast-v1（2026-10-07承認）。{req['reading']}という関係は説明と原典値/受払・単位の記述で確認する。追加グラフと全節画像の再作成を省略し、既存巻の図を今回の検査済みと主張しない。",
            )
            requirements.append(dict(id=req["id"], statement=req["statement"], coverage=coverage))
        row.update(
            status="accepted",
            reviewed_at="2026-10-07",
            source_pages=spec["source_pages"],
            scope="原典本文の要点と計算をfast-v1で受入。配布先は節別補足HTML。既存Book本文の改訂、章末問題、現行制度、入力のないモデル価格は対象外。",
            assumptions=[
                "刊行時点の市場quote・制度例。単位・符号・複利頻度・日数は本文の設定に従う。",
                "原典外の独立検証例は合成入力であり、原典の印刷価格ではない。",
            ],
            limitations=[
                "幅1280の全節自動確認と代表1節/章の目視。全節2幅Book/portal巡回・全suite・二重保管庫復元は省略。",
                spec["limitation"]
                or spec.get("calculation_scope", "計算モデルと現在の制度判断は対象外。"),
            ],
            acceptance_note=NOTE,
            evidence=ev,
            requirements=requirements,
        )
    if any(old[r["id"]] != r for r in ledger["sections"] if r["id"] in old):
        raise ValueError("old acceptance decisions changed")
    from johnhull.scripts.verify_section_ledger import evaluate_ledger

    result = evaluate_ledger(PROJECT, read("docs/section_inventory.json"), ledger)
    if result["status"] != "PASS":
        raise ValueError("prospective ledger invalid: " + str(result["errors"]))
    write("docs/section_ledger.json", ledger)
    return dict(status="PASS", registered=70, counts=result["counts"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["build", "test", "check", "register"])
    print(json.dumps(globals()[parser.parse_args().phase](), ensure_ascii=False))
