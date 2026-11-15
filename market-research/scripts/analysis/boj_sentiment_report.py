"""Local BOJ paragraph report. See docs/BOJ_SENTIMENT.md for optional inference setup."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, date, datetime
from html import unescape
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parents[3]
DEFAULT_YEAR = datetime.now(UTC).year
DEFAULT_DATA = REPO / f"_data/market-research/boj-sentiment-{DEFAULT_YEAR}"
MODEL_ID = "Woochachino/cbsent"
MODEL_REVISION = "21c60231755d79fe9566bb8f0bfd08bd78233ce5"
LABELS = ("dovish", "hawkish", "neutral")
REPORT_PATH = REPO / f"market-research/docs/data/validation/boj_sentiment_{DEFAULT_YEAR}.html"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class OpinionParser(HTMLParser):
    """Extract only top-level opinion bullets from BOJ's main content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.section = None
        self.section_title = ""
        self.subsection = ""
        self.group = 0
        self.heading = None
        self.heading_text = []
        self.lists = []
        self.bullet = None
        self.sup_depth = 0
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "main" and dict(attrs).get("id") == "contents":
            self.active = True
        if not self.active:
            return
        if tag in ("h2", "h3"):
            self.heading, self.heading_text = tag, []
        if tag in ("ul", "ol"):
            self.lists.append(tag)
        if tag == "li" and self.section and self.lists == ["ul"]:
            if self.bullet is not None:
                raise ValueError("Unexpected nested opinion bullet")
            self.bullet = []
        if tag == "sup":
            self.sup_depth += 1

    def handle_data(self, data):
        if not self.active or self.sup_depth:
            return
        if self.heading:
            self.heading_text.append(data)
        if self.bullet is not None:
            self.bullet.append(data)

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag == "sup":
            self.sup_depth = max(0, self.sup_depth - 1)
        if tag == self.heading:
            title = clean_text("".join(self.heading_text))
            if tag == "h2":
                if "金融政策運営" in title or "Opinions on Monetary Policy" in title:
                    self.section = "policy"
                elif "金融経済情勢" in title or "Economic and Financial Developments" in title:
                    self.section = "economy"
                elif "政府の意見" in title or "Government Representatives" in title:
                    self.section = "government"
                else:
                    self.section = None
                self.section_title, self.subsection, self.group = title, "", 0
            else:
                self.subsection = title
                self.group += 1
            self.heading = None
        if tag == "li" and self.bullet is not None:
            text = clean_text("".join(self.bullet))
            if not text:
                raise ValueError("Empty opinion paragraph")
            self.rows.append(
                {
                    "section": self.section,
                    "section_title": self.section_title,
                    "subsection": self.subsection,
                    "group": self.group,
                    "text": text,
                }
            )
            self.bullet = None
        if tag in ("ul", "ol") and self.lists:
            if self.lists.pop() != tag:
                raise ValueError("Invalid BOJ list structure")
        if tag == "main":
            self.active = False


def parse_document(html: str) -> list[dict]:
    parser = OpinionParser()
    parser.feed(html)
    if set(r["section"] for r in parser.rows) != {"economy", "policy", "government"}:
        raise ValueError("Missing BOJ opinion section")
    return parser.rows


def parse_pdf_document(text: str, language: str) -> list[dict]:
    rows, chunks = [], []
    section, section_title, subsection, group = None, "", "", 0

    def flush() -> None:
        nonlocal chunks
        if not chunks:
            return
        joined = "\n".join(chunks)
        if language == "en":
            joined = re.sub(r"(?<=\w)-\n(?!(?:to|and|or)\b)(?=\w)", "-", joined)
        paragraph = clean_text(joined)
        if language == "ja":
            paragraph = re.sub(r"(?<=[^\x00-\x7f])\s+|\s+(?=[^\x00-\x7f])", "", paragraph)
        rows.append(
            {
                "section": section,
                "section_title": section_title,
                "subsection": subsection,
                "group": group,
                "text": paragraph,
            }
        )
        chunks = []

    for page in text.split("\f"):
        for raw_line in page.splitlines():
            line = raw_line.strip()
            normalized = unicodedata.normalize("NFKC", line)
            if not line:
                continue
            # BOJ page numbers and footnote numbers are isolated below the body.
            if re.fullmatch(r"\d{1,2}", normalized):
                break
            if re.match(
                r"^\d+\s*(?:「金融政策決定会合における主な意見|English translation prepared|"
                r'["“]?(?:The\s+)?Summary of Opinions)',
                normalized,
            ):
                break
            if normalized.replace(" ", "") == "以上":
                continue
            if re.match(r"^[IVX]+\.", normalized):
                flush()
                if "金融政策運営" in normalized or "Opinions on Monetary Policy" in normalized:
                    section = "policy"
                elif (
                    "金融経済情勢" in normalized
                    or "Economic and Financial Developments" in normalized
                ):
                    section = "economy"
                elif "政府の意見" in normalized or "Government Representatives" in normalized:
                    section = "government"
                else:
                    raise ValueError(f"Unknown BOJ PDF section: {line}")
                section_title, subsection, group = line, "", 0
                continue
            if section is None:
                continue
            if normalized.strip("()") in {
                "経済情勢",
                "物価",
                "財務省",
                "内閣府",
                "Economic Developments",
                "Prices",
                "Ministry of Finance",
                "Cabinet Office",
            }:
                flush()
                subsection, group = line, group + 1
                continue
            bullet = re.match(r"^[⚫●•\uf0b7]\s*(.+)", line)
            if bullet:
                flush()
                chunks.append(bullet[1])
            elif chunks:
                chunks.append(line)
    flush()
    if {row["section"] for row in rows} != {"economy", "policy", "government"}:
        raise ValueError("Missing BOJ PDF opinion section")
    return rows


def read_document(path: Path, language: str) -> list[dict]:
    if path.suffix == ".pdf":
        text = subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)
        return parse_pdf_document(text, language)
    return parse_document(path.read_text(encoding="utf-8"))


def align_documents(ja: list[dict], en: list[dict], meeting: str) -> list[dict]:
    keys_ja = [(r["section"], r["group"]) for r in ja]
    keys_en = [(r["section"], r["group"]) for r in en]
    if keys_ja != keys_en:
        raise ValueError(f"BOJ paragraph alignment mismatch: {meeting}")
    return [
        {
            "id": f"{meeting}-{i:03d}",
            "meeting": meeting,
            "ordinal": i,
            "section": j["section"],
            "section_title": j["section_title"],
            "subsection": j["subsection"],
            "ja": j["text"],
            "en": e["text"],
        }
        for i, (j, e) in enumerate(zip(ja, en, strict=True), 1)
    ]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch_document(url: str, destination: Path) -> dict:
    request = Request(url, headers={"User-Agent": "BOJ-sentiment-local-research/0.1"})
    with urlopen(request, timeout=45) as response:
        content = response.read(3_000_001)
    if len(content) > 3_000_000:
        raise ValueError("BOJ source exceeds the 3 MB download limit")
    destination.write_bytes(content)
    return {
        "url": url,
        "file": destination.name,
        "bytes": len(content),
        "sha256": sha256(content),
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def parse_index(source: str, year: int, as_of: date) -> list[dict]:
    meetings = {}
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", source, re.S):
        paths = re.findall(
            rf'href="(/mopo/mpmsche_minu/opinion_{year}/opi{year % 100:02d}\d{{4}}\.(?:htm|pdf))"',
            row,
        )
        if not paths:
            continue
        published = re.search(
            rf"{year}年\s*(\d+)月\s*(\d+)日", unescape(re.sub(r"<[^>]+>", " ", row))
        )
        if published is None:
            raise ValueError("Missing publication date in BOJ index")
        published_on = date(year, int(published[1]), int(published[2]))
        if published_on > as_of:
            continue
        path = min(paths, key=lambda candidate: (not candidate.endswith(".htm"), candidate))
        meeting = datetime.strptime(Path(path).stem[3:], "%y%m%d").date()
        if meeting.year != year or meeting > published_on:
            raise ValueError("Invalid BOJ meeting/publication dates")
        meetings[meeting.isoformat()] = {
            "path": path,
            "date": meeting.isoformat(),
            "published_on": published_on.isoformat(),
        }
    if not meetings:
        raise ValueError(f"No published BOJ meetings found for {year} as of {as_of}")
    return [meetings[key] for key in sorted(meetings)]


def collect(data_root: Path, year: int = DEFAULT_YEAR, as_of: date | None = None) -> dict:
    as_of = as_of or datetime.now(UTC).date()
    raw = data_root / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    index = fetch_document(
        f"https://www.boj.or.jp/mopo/mpmsche_minu/opinion_{year}/index.htm", raw / "index-ja.html"
    )
    source = (raw / index["file"]).read_text(encoding="utf-8")
    meetings, paragraphs = [], []
    for entry in parse_index(source, year, as_of):
        path, meeting = entry["path"], entry["date"]
        code = Path(path).stem[3:]
        documents = {}
        parsed = {}
        for lang, prefix in (("ja", ""), ("en", "/en")):
            documents[lang] = fetch_document(
                "https://www.boj.or.jp" + prefix + path, raw / f"{lang}-{code}{Path(path).suffix}"
            )
            parsed[lang] = read_document(raw / documents[lang]["file"], lang)
        aligned = align_documents(parsed["ja"], parsed["en"], meeting)
        meetings.append(
            {
                "date": meeting,
                "documents": documents,
                "published_on": entry["published_on"],
                "counts": dict(Counter(p["section"] for p in aligned)),
            }
        )
        paragraphs.extend(aligned)
        print(meeting, meetings[-1]["counts"], flush=True)
    result = {
        "schema": 1,
        "year": year,
        "as_of": as_of.isoformat(),
        "index": index,
        "meetings": meetings,
        "paragraphs": paragraphs,
    }
    write_json(data_root / "corpus.json", result)
    return result


def prediction(probabilities: dict[str, float]) -> dict:
    if (
        set(probabilities) != set(LABELS)
        or not all(math.isfinite(v) and 0 <= v <= 1 for v in probabilities.values())
        or not math.isclose(sum(probabilities.values()), 1, abs_tol=1e-5)
    ):
        raise ValueError("Invalid class probabilities")
    ordered = sorted(probabilities, key=probabilities.get, reverse=True)
    margin = probabilities[ordered[0]] - probabilities[ordered[1]]
    return {
        "probabilities": probabilities,
        "label": ordered[0],
        "margin": margin,
        "score": probabilities["hawkish"] - probabilities["dovish"],
        "review": margin < 0.2,
    }


def check_token_lengths(lengths: list[int], limit: int) -> None:
    if not lengths or any(n <= 0 or n > limit for n in lengths):
        raise ValueError(f"Input token length exceeds supported limit ({limit}) or is empty")


def summarize(paragraphs: list[dict], meetings: list[dict]) -> list[dict]:
    result = []
    for meeting in meetings:
        rows = [
            p for p in paragraphs if p["meeting"] == meeting["date"] and p["section"] == "policy"
        ]
        if not rows:
            raise ValueError("No policy paragraphs for meeting summary")
        counts = {label: sum(p["label"] == label for p in rows) for label in LABELS}
        result.append(
            {
                "meeting": meeting["date"],
                "n": len(rows),
                "counts": counts,
                "review": sum(p["review"] for p in rows),
                "mean_score": sum(p["score"] for p in rows) / len(rows),
            }
        )
    return result


def safe_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def historical_series(snapshots: list[dict], rates: dict) -> list[dict]:
    """Join comparable BERT policy counts to decisions, retaining publication timing."""
    models = {(s["model"]["id"], s["model"]["revision"]) for s in snapshots}
    if len(models) != 1:
        raise ValueError("History requires one fixed model revision")
    rate_rows = rates["sources"]
    by_date = {row["date"]: row for row in rate_rows}
    if len(by_date) != len(rate_rows):
        raise ValueError("Duplicate policy-rate decision")
    result = []
    seen = set()
    for snapshot in snapshots:
        for meeting in snapshot["meetings"]:
            day = meeting["date"]
            released = meeting["published_on"]
            if day in seen or day not in by_date:
                raise ValueError("Duplicate meeting or missing policy-rate decision")
            if date.fromisoformat(released) < date.fromisoformat(day):
                raise ValueError("Opinion release precedes its meeting")
            seen.add(day)
            policy = [
                p
                for p in snapshot["paragraphs"]
                if p["meeting"] == day and p["section"] == "policy"
            ]
            if (
                not policy
                or len({p["id"] for p in policy}) != len(policy)
                or any(p["label"] not in LABELS for p in policy)
            ):
                raise ValueError("Missing, duplicate or unclassified policy paragraphs")
            counts = {label: sum(p["label"] == label for p in policy) for label in LABELS}
            target = by_date[day]["target_percent"]
            if not isinstance(target, (int, float)) or not math.isfinite(target):
                raise ValueError("Nonfinite policy-rate target")
            result.append(
                {
                    "meeting": day,
                    "published_on": released,
                    "n": len(policy),
                    "counts": counts,
                    "balance": 100 * (counts["hawkish"] - counts["dovish"]) / len(policy),
                    "rate_percent": target,
                    "decision_url": by_date[day]["url"],
                    "opinion_url": meeting.get("documents", {}).get("ja", {}).get("url"),
                }
            )
    if set(by_date) != seen:
        raise ValueError("Policy-rate and sentiment coverage differ")
    return sorted(result, key=lambda row: row["meeting"])


def render_history(inputs: list[Path], rates_path: Path, output: Path) -> dict:
    snapshots = []
    for path in inputs:
        match = re.search(
            r'<script id="boj-data" type="application/json">(.*?)</script>',
            path.read_text(encoding="utf-8"),
            re.S,
        )
        if not match:
            raise ValueError("History input has no embedded BOJ snapshot")
        snapshot = json.loads(match[1])
        if summarize(snapshot["paragraphs"], snapshot["meetings"]) != snapshot["summary"]:
            raise ValueError("History input summary differs from its paragraph scores")
        snapshots.append(snapshot)
    rates = json.loads(rates_path.read_text(encoding="utf-8"))
    rows = historical_series(snapshots, rates)
    payload = {
        "as_of": rates["as_of"],
        "model": {k: snapshots[0]["model"][k] for k in ("id", "revision")},
        "rows": rows,
        "inputs": [{"file": p.name, "sha256": sha256(p.read_bytes())} for p in inputs],
        "rates_sha256": sha256(rates_path.read_bytes()),
    }
    if any(row["published_on"] > payload["as_of"] for row in rows):
        raise ValueError("History contains opinions unavailable at its cutoff")
    tokens = (REPO / "docs/templates/claude-report/tokens.css").read_text(encoding="utf-8")
    template = Path(__file__).with_name("boj_sentiment_history.html").read_text(encoding="utf-8")
    fragment = template.replace("/*__TOKENS__*/", tokens).replace("__HISTORY__", safe_json(payload))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(fragment, encoding="utf-8")
    print(f"Rendered policy-rate history: {len(rows)} meetings; {output.stat().st_size:,} bytes")
    return payload


def verify_sources(data_root: Path, corpus: dict) -> None:
    documents = [corpus["index"]] + [d for m in corpus["meetings"] for d in m["documents"].values()]
    for doc in documents:
        content = (data_root / "raw" / doc["file"]).read_bytes()
        if len(content) != doc["bytes"] or sha256(content) != doc["sha256"]:
            raise ValueError("Saved BOJ source hash mismatch")
    reconstructed = []
    for meeting in corpus["meetings"]:
        rows = [
            read_document(data_root / "raw" / meeting["documents"][lang]["file"], lang)
            for lang in ("ja", "en")
        ]
        reconstructed.extend(align_documents(*rows, meeting["date"]))
    if reconstructed != corpus["paragraphs"]:
        raise ValueError("Saved corpus differs from source reconstruction")


def score(data_root: Path, device: str) -> dict:
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForSequenceClassification, PreTrainedTokenizerFast

    corpus = json.loads((data_root / "corpus.json").read_text(encoding="utf-8"))
    verify_sources(data_root, corpus)
    cache = Path(
        snapshot_download(
            MODEL_ID,
            revision=MODEL_REVISION,
            allow_patterns=["*.json", "vocab.txt", "model.safetensors", "README.md"],
            max_workers=2,
        )
    )
    # The upstream tokenizer was exported by Transformers 5 as TokenizersBackend.
    # Load its complete serialized tokenizer with the supported 4.x fast wrapper.
    tokenizer_config = json.loads((cache / "tokenizer_config.json").read_text(encoding="utf-8"))
    special_tokens = {
        k: tokenizer_config[k]
        for k in ("pad_token", "cls_token", "sep_token", "unk_token", "mask_token")
    }
    tokenizer = PreTrainedTokenizerFast(
        tokenizer_file=str(cache / "tokenizer.json"),
        model_max_length=tokenizer_config["model_max_length"],
        model_input_names=["input_ids", "attention_mask"],
        **special_tokens,
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        cache,
        use_safetensors=True,
        local_files_only=True,
        reference_compile=False,
        attn_implementation="eager",
    )
    labels = {int(k): v.lower() for k, v in model.config.id2label.items()}
    if (
        set(labels) != {0, 1, 2}
        or set(labels.values()) != set(LABELS)
        or model.config.model_type != "modernbert"
    ):
        raise ValueError("Expected a ModernBERT model with hawkish/dovish/neutral labels")
    model.to(device).eval()
    torch.manual_seed(0)
    torch.set_num_threads(4)
    selected = [p for p in corpus["paragraphs"] if p["section"] != "government"]
    probes = [
        {
            "expected": "hawkish",
            "text": "We should raise interest rates promptly to contain inflation.",
        },
        {"expected": "dovish", "text": "We should cut interest rates to support the economy."},
        {
            "expected": "neutral",
            "text": "The next monetary policy meeting will take place in March.",
        },
        {
            "expected": "dovish",
            "text": "It is premature to raise interest rates given weak demand.",
        },
        {
            "expected": "hawkish",
            "text": "It would be inappropriate to cut interest rates while inflation is elevated.",
        },
    ]
    texts = [p["en"] for p in selected] + [p["text"] for p in probes]
    lengths = [len(tokenizer(text, truncation=False)["input_ids"]) for text in texts]
    limit = min(tokenizer.model_max_length, model.config.max_position_embeddings)
    check_token_lengths(lengths, limit)
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(texts), 8):
            batch = tokenizer(
                texts[start : start + 8], return_tensors="pt", padding=True, truncation=False
            )
            probabilities = model(**batch.to(device)).logits.softmax(-1).cpu().tolist()
            predictions.extend(
                prediction({labels[i]: float(v) for i, v in enumerate(row)})
                for row in probabilities
            )
            print(f"Scored {min(start + 8, len(texts))}/{len(texts)}", flush=True)
    for paragraph, result, length in zip(
        selected, predictions[: len(selected)], lengths[: len(selected)], strict=True
    ):
        paragraph.update(result, tokens=length)
    for probe, result in zip(probes, predictions[len(selected) :], strict=True):
        probe.update(result)
    model_files = [
        {"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p.read_bytes())}
        for p in sorted(cache.iterdir())
        if p.is_file()
    ]
    corpus.update(
        generated_at=datetime.now(UTC).isoformat(),
        git_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        script_sha256=sha256(Path(__file__).read_bytes()),
        model={
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "architecture": "ModernBERT (BERT family)",
            "training_domain": "Fed and Bank of Canada English communications / FOMC stance labels",
            "files": model_files,
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "device": device,
            "dtype": str(next(model.parameters()).dtype),
            "max_tokens": max(lengths[: len(selected)]),
            "input_limit": limit,
            "batch_size": 8,
            "training_performed": False,
            "card_weighted_f1_three_seed_mean": 0.658,
        },
        probes=probes,
    )
    diagnostics_path = data_root / "model-diagnostics.json"
    if diagnostics_path.exists():
        corpus["model_diagnostics"] = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    corpus["summary"] = summarize(corpus["paragraphs"], corpus["meetings"])
    write_json(data_root / "results.json", corpus)
    for row in corpus["summary"]:
        print(row["meeting"], row["counts"], "review", row["review"], flush=True)
    for probe in probes:
        print("Probe:", probe["expected"], "->", probe["label"], probe["text"], flush=True)
    return corpus


def validate_reading_review(snapshot: dict, review: dict) -> None:
    if review["schema"] != 1:
        raise ValueError("Unsupported BOJ reading review schema")

    policy = {p["id"]: p for p in snapshot["paragraphs"] if p["section"] == "policy"}
    reviewed_dates = set(review["reviewed_meetings"])
    reviewed_ids = {p["id"] for p in policy.values() if p["meeting"] in reviewed_dates}
    readings = review["readings"]
    if (
        not reviewed_ids
        or len(readings) != len(reviewed_ids)
        or {entry["id"] for entry in readings} != reviewed_ids
    ):
        raise ValueError("Reading review must cover every policy paragraph in its meeting scope")

    for entry in readings:
        p = policy[entry["id"]]
        if entry["label"] not in (*LABELS, None):
            raise ValueError(f"Invalid reading label for {p['id']}")
        if not entry["evidence"].strip() or entry["evidence"] not in p["ja"]:
            raise ValueError(f"Reading evidence not found in Japanese paragraph {p['id']}")
        if not entry["note"].strip():
            raise ValueError(f"Missing reading note for {p['id']}")

    meetings = sorted(snapshot["meetings"], key=lambda m: m["date"])
    dates = [m["date"] for m in meetings]
    previous_meeting = dict(zip(dates[1:], dates[:-1], strict=True))
    source_dates = set(reviewed_dates)
    for pair in review["comparisons"]:
        if pair["current_id"] not in reviewed_ids or pair["previous_id"] not in policy:
            raise ValueError("Comparison must reference policy paragraphs in the saved report")
        current = policy[pair["current_id"]]
        previous = policy[pair["previous_id"]]
        if previous_meeting.get(current["meeting"]) != previous["meeting"]:
            raise ValueError(f"Comparison must use the previous meeting for {current['id']}")
        for side, p in (("previous", previous), ("current", current)):
            excerpt = pair[f"{side}_evidence"]
            if not excerpt.strip() or excerpt not in p["ja"]:
                raise ValueError(f"Comparison evidence not found in Japanese paragraph {p['id']}")
        source_dates.add(previous["meeting"])

    source_hashes = {
        m["date"]: m["documents"]["ja"]["sha256"] for m in meetings if m["date"] in source_dates
    }
    if source_hashes != review["source_sha256"]:
        raise ValueError("Reading review source hash mismatch")


def render(
    data_root: Path,
    output: Path,
    from_html: Path | None = None,
    *,
    readings_path: Path | None = None,
) -> None:
    if from_html:
        saved = re.search(
            r'<script id="boj-data" type="application/json">(.*?)</script>',
            from_html.read_text(encoding="utf-8"),
            re.S,
        )
        if not saved:
            raise ValueError("No embedded BOJ snapshot")
        snapshot = json.loads(saved[1])
    else:
        snapshot = json.loads((data_root / "results.json").read_text(encoding="utf-8"))
    if summarize(snapshot["paragraphs"], snapshot["meetings"]) != snapshot["summary"]:
        raise ValueError("Saved report summary does not match paragraph scores")
    for paragraph in snapshot["paragraphs"]:
        if paragraph["section"] != "government" and prediction(paragraph["probabilities"]) != {
            k: paragraph[k] for k in ("probabilities", "label", "margin", "score", "review")
        }:
            raise ValueError("Saved paragraph prediction mismatch")
    if readings_path is not None:
        snapshot["reading_review"] = json.loads(readings_path.read_text(encoding="utf-8"))
    if "reading_review" in snapshot:
        validate_reading_review(snapshot, snapshot["reading_review"])
    template = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
    tokens = (REPO / "docs/templates/claude-report/tokens.css").read_text(encoding="utf-8")
    year = snapshot["meetings"][-1]["date"][:4]
    html = (
        template.replace("/*__TOKENS__*/", tokens)
        .replace("__SNAPSHOT__", safe_json(snapshot))
        .replace("__REPORT_YEAR__", year)
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(
        f"Rendered {len(snapshot['paragraphs'])} paragraphs; {output.stat().st_size:,} bytes",
        flush=True,
    )


def serve(output: Path, port: int) -> None:
    content = output.read_bytes()

    class ReportHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
            elif self.path in ("/", "/report.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    print(f"Local report: http://localhost:{port}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), ReportHandler).serve_forever()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["fetch", "score", "render", "serve", "history"])
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(UTC).date())
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--from-html", type=Path)
    parser.add_argument("--readings", type=Path, help="Attach Japanese reading notes to the report")
    parser.add_argument("--port", type=int, default=8772)
    parser.add_argument(
        "--history-html", type=Path, action="append", help="Saved report to combine"
    )
    parser.add_argument("--rates", type=Path, help="Verified BOJ decision-rate manifest")
    args = parser.parse_args()
    data_root = args.data_root or REPO / f"_data/market-research/boj-sentiment-{args.year}"
    output = (
        args.output or REPO / f"market-research/docs/data/validation/boj_sentiment_{args.year}.html"
    )
    if args.command == "fetch":
        collect(data_root, args.year, args.as_of)
    elif args.command == "score":
        score(data_root, args.device)
    elif args.command == "render":
        render(data_root, output, args.from_html, readings_path=args.readings)
    elif args.command == "history":
        folder = REPO / "market-research/docs/data"
        render_history(
            args.history_html
            or [
                folder / "validation/boj_sentiment_2025_2026-11-10.html",
                folder / "validation/boj_sentiment_2026.html",
            ],
            args.rates or folder / "boj_policy_rates_2025_2026.json",
            args.output or folder / "validation/boj_sentiment_history_2025_2026.html",
        )
    else:
        serve(output, args.port)


if __name__ == "__main__":
    main()
