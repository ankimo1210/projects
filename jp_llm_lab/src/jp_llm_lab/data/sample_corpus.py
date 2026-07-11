"""Milestone-1 sample corpus: a couple of public-domain Aozora Bunko texts.

This is NOT the training corpus infrastructure (that is Milestone 2, with
snapshots of FineWeb2-ja / Wikipedia). It is a small, license-clear, real
Japanese text used to validate the whole pipeline end-to-end.

Sources are Aozora Bunko (青空文庫) files whose authors died >70 years ago —
public domain in Japan. The fetch script records url + sha256 + char count in
`data/manifests/sample_v1.json`. If the network is unavailable, a clearly
labeled synthetic fallback corpus is generated instead (manifest field
`synthetic: true`) so that measured results are never silently mixed with
illustrative data.
"""

from __future__ import annotations

import io
import re
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from ..utils.io import load_json, repo_root, save_json, sha256_text

MANIFEST_REL = Path("data/manifests/sample_v1.json")
SAMPLES_REL = Path("data/samples")

AOZORA_SOURCES: dict[str, dict] = {
    "kokoro": {
        "title": "こころ",
        "author": "夏目漱石",
        "url": "https://www.aozora.gr.jp/cards/000148/files/773_ruby_5968.zip",
    },
    "hashire_merosu": {
        "title": "走れメロス",
        "author": "太宰治",
        "url": "https://www.aozora.gr.jp/cards/000035/files/1567_ruby_4948.zip",
    },
}


def clean_aozora(raw: str) -> str:
    """Strip Aozora markup: header block, footer, ruby readings, annotations.

    Aozora text files look like:
        title / author
        ---------------- (metadata block) ----------------
        body with ruby: 漢字《かんじ》, ｜range markers, ［＃…］ annotations
        底本：…  (bibliographic footer)
    """
    parts = re.split(r"-{10,}\r?\n", raw)
    body = parts[2] if len(parts) >= 3 else raw
    body = re.split(r"\r?\n底本：", body)[0]
    body = re.sub(r"《[^》]*》", "", body)  # ruby readings
    body = body.replace("｜", "")  # ruby range marker
    body = re.sub(r"［＃[^］]*］", "", body)  # editorial annotations
    body = body.replace("\r\n", "\n")
    return body.strip("\n") + "\n"


def _download_zip_text(url: str, timeout: float = 30.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "jp_llm_lab/0.1 (educational)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        blob = resp.read()
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        txt_names = [n for n in zf.namelist() if n.lower().endswith(".txt")]
        if not txt_names:
            raise FileNotFoundError(f"no .txt inside {url}")
        raw = zf.read(txt_names[0]).decode("cp932", errors="replace")
    return raw


# A tiny deterministic fallback so the pipeline can be validated offline.
_SYNTHETIC_SENTENCES = [
    "むかしむかし、ある山のふもとに小さな村がありました。",
    "村の人々は毎朝、川の水をくんで畑に運びました。",
    "春になると桜が咲き、子どもたちは野原をかけまわりました。",
    "夏の夜には星がよく見えて、祭りの太鼓が遠くまで響きました。",
    "秋には稲が実り、村じゅうが収穫の準備で忙しくなりました。",
    "冬の朝は霜が降りて、白い息をはきながら道を歩きました。",
    "ある日、旅人が村を訪れて、遠い town の話をしてくれました。",
    "「世界は広い。だが、帰る場所があるのは幸せなことだ」と旅人は言いました。",
]


def build_synthetic_corpus(n_repeat: int = 120) -> str:
    """Deterministic synthetic text (~50k chars). Clearly labeled, never mixed
    with real measurements without the manifest saying so."""
    block = "\n".join(_SYNTHETIC_SENTENCES) + "\n\n"
    return block * n_repeat


def fetch_sample_corpus(
    names: tuple[str, ...] = ("kokoro", "hashire_merosu"),
    root: Path | None = None,
    force: bool = False,
) -> dict:
    """Download+clean the sample texts, write data/samples/*.txt and manifest."""
    root = root or repo_root()
    samples_dir = root / SAMPLES_REL
    samples_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = root / MANIFEST_REL
    manifest = load_json(manifest_path) if manifest_path.exists() else {"version": "sample_v1", "sources": {}}

    for name in names:
        out = samples_dir / f"{name}.txt"
        if out.exists() and not force and name in manifest["sources"]:
            continue
        src = AOZORA_SOURCES[name]
        try:
            text = clean_aozora(_download_zip_text(src["url"]))
            synthetic = False
            url = src["url"]
        except Exception as e:  # network blocked / site down → labeled fallback
            print(f"[fetch_sample_corpus] download failed for {name}: {e!r} → synthetic fallback")
            text = build_synthetic_corpus()
            synthetic = True
            url = None
        out.write_text(text, encoding="utf-8")
        manifest["sources"][name] = {
            "title": src["title"],
            "author": src["author"],
            "url": url,
            "license": "Aozora Bunko public domain (author died >70y ago)" if not synthetic else "synthetic (generated in-repo)",
            "synthetic": synthetic,
            "sha256": sha256_text(text),
            "n_chars": len(text),
            "fetched_at": datetime.now(UTC).isoformat(),
        }
    manifest["updated_at"] = datetime.now(UTC).isoformat()
    save_json(manifest, manifest_path)
    return manifest


def load_sample_corpus(name: str = "kokoro", root: Path | None = None) -> str:
    """Load a fetched sample text; verifies sha256 against the manifest."""
    root = root or repo_root()
    path = root / SAMPLES_REL / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run `uv run --no-sync python jp_llm_lab/scripts/fetch_sample_corpus.py` first"
        )
    text = path.read_text(encoding="utf-8")
    manifest_path = root / MANIFEST_REL
    if manifest_path.exists():
        entry = load_json(manifest_path)["sources"].get(name)
        if entry and entry["sha256"] != sha256_text(text):
            raise ValueError(f"sha256 mismatch for {name}: file changed since manifest was written")
    return text
