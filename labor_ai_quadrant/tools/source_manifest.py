"""生スナップショットの manifest を作る（ファイル名・SHA-256・サイズ・取得日）。

参照 TOML は `build_reference.py` が `_data/sources/` の生ファイルから生成する。
`_data/` は gitignore されているので、別 clone で同じ参照値を再生成できるかどうかは
**生ファイルが同一かどうか**に懸かっている。URL だけでは足りない（e-Stat の
`file-download?statInfId=` は同じ URL で中身が更新される）。そこで checksum を
`docs/SOURCES.md` に固定し、次に取得した人が突き合わせられるようにする。

    uv run python labor_ai_quadrant/tools/source_manifest.py          # 生成
    uv run python labor_ai_quadrant/tools/source_manifest.py --check   # 突合のみ

`--check` は差異があれば非0で終わる。参照 TOML を作り直したのに manifest を
更新していない、あるいは手元の生ファイルが manifest と違う、のどちらか。
"""

from __future__ import annotations

import argparse
import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
SRC = PKG / "_data" / "sources"
MANIFEST = PKG / "docs" / "SOURCES.md"

#: 生ファイル名 → それを使っている `build_reference.SOURCES` のキー。
#: 1つの配布物から複数の表を作るものもあるので、対応は手で宣言する。
FILE_TO_SOURCE = {
    "koyou_doukou_r7_zuhyo.xlsx": "vacancy_separation",
    "boj_tankan_co.csv": "tankan",
    "boj_tankan_code.html": "tankan_code",
    "mhlw_occupation_market_r8_06.xlsx": "job_openings",
    "mkt_jissu.csv": "overtime",
    "estat_lfs_2_5_1_2025.json": "mix",
    "estat_lfs_age_industry_2025.json": "age_industry",
    "ilo_wp140_scores.xlsx": "ilo",
}

#: URL の代わりに e-Stat の統計表IDで指定されている入力（API 取得なので固定 URL が無い）。
E_STAT_TABLE = {
    "age_industry": "e-Stat statsDataId=0003007108（労働力調査 年齢階級，産業別就業者数）",
    "mix": "e-Stat statsDataId=0003024266（労働力調査 表2-5-1 産業，職業別就業者数）",
}

HEADER = """# SOURCES — 生スナップショットの manifest

`_data/sources/` は gitignore されている（統計の再配布を避けるため）。参照 TOML を
別 clone で再生成するには、下の URL から取り直したファイルがここに記録した
SHA-256 と一致することを確認する。

再生成と突合:

```bash
uv run python labor_ai_quadrant/tools/source_manifest.py --check   # 手元の生ファイルを突合
uv run python labor_ai_quadrant/tools/build_reference.py           # reference/*.toml を再生成
uv run --no-sync pytest labor_ai_quadrant/tests -q                 # 117 tests
```

**URL が同じでも中身は変わる。** e-Stat の `file-download?statInfId=` と日銀の
`co.zip` は更新のたびに同じ URL で別の中身を返す。だから URL ではなく checksum を
正本にしている。値が変わっていた場合は、参照 TOML を作り直して差分を見ること
（黙って新しい vintage を混ぜないため）。

"""


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def source_urls() -> dict[str, str]:
    """`build_reference.SOURCES` の説明文から URL を抜く（import せずに読む）。"""
    text = (PKG / "tools" / "build_reference.py").read_text(encoding="utf-8")
    block = text.split("SOURCES = {", 1)[1].split("\n}", 1)[0]
    # 説明文の中に括弧が入るので、キーの位置で切って次のキーまでを本文とする
    # （`\(([^)]*)\)` だと最初の閉じ括弧で切れて URL に届かない）。
    marks = [(m.group(1), m.end()) for m in re.finditer(r'^\s{4}"([a-z_]+)":', block, re.M)]
    out: dict[str, str] = {}
    for i, (key, start) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(block)
        urls = re.findall(r"https?://[^\s\"']+", block[start:end])
        out[key] = urls[0] if urls else ""
    return out


def rows() -> list[tuple[str, int, str, str, str]]:
    urls = source_urls()
    found = []
    for path in sorted(SRC.iterdir()) if SRC.exists() else []:
        if path.is_dir():
            continue
        key = FILE_TO_SOURCE.get(path.name, "")
        stamp = datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime("%Y-%m-%d")
        url = urls.get(key, "") or E_STAT_TABLE.get(key, "")
        found.append((path.name, path.stat().st_size, digest(path), stamp, url))
    return found


def render(found: list[tuple[str, int, str, str, str]]) -> str:
    lines = [HEADER, "| ファイル | バイト | SHA-256 | 取得日 | 出典 URL |", "|---|---:|---|---|---|"]
    for name, size, sha, stamp, url in found:
        lines.append(f"| `{name}` | {size:,} | `{sha}` | {stamp} | {url or '—'} |")
    unmapped = [n for n, *_ in found if n not in FILE_TO_SOURCE]
    if unmapped:
        lines += ["", f"対応する SOURCES キーが宣言されていないファイル: {unmapped}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="生成せず、既存 manifest と突合する")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"{SRC} が無いので manifest は作れません（生ファイルを置いてください）")
        return 1

    text = render(rows())
    if not args.check:
        MANIFEST.write_text(text, encoding="utf-8")
        print(f"wrote {MANIFEST.relative_to(PKG)} ({len(rows())} files)")
        return 0

    if not MANIFEST.exists():
        print(f"{MANIFEST.relative_to(PKG)} が無い。まず --check なしで実行してください")
        return 1
    if MANIFEST.read_text(encoding="utf-8") == text:
        print(f"manifest 一致（{len(rows())} files）")
        return 0
    print("manifest が手元の生ファイルと一致しません。差分:")
    old = MANIFEST.read_text(encoding="utf-8").splitlines()
    for line in text.splitlines():
        if line.startswith("| `") and line not in old:
            print(f"  + {line}")
    for line in old:
        if line.startswith("| `") and line not in text.splitlines():
            print(f"  - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
