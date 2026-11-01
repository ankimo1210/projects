"""Reject API-key literals in supplied files; never print matching values."""

import re
import sys
from pathlib import Path

KEY_PATTERNS = (
    re.compile(r"\bsk-(?:ant-|proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"""REINFOLIB_API_KEY\s*(?:=|:)\s*(?:\\?["'])?[0-9a-fA-F]{32}(?![0-9a-fA-F])"""),
)


def main(arguments: list[str] | None = None) -> int:
    failed = False
    for name in sys.argv[1:] if arguments is None else arguments:
        path = Path(name)
        if not path.is_file():
            continue
        private_env = path.name != ".env.example" and (
            path.name == ".env" or path.name.startswith(".env.") or path.name.endswith(".env")
        )
        if private_env:
            print(f"{path}: keep real env files outside the public repository.")
            failed = True
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        lines = {
            content.count("\n", 0, match.start()) + 1
            for pattern in KEY_PATTERNS
            for match in pattern.finditer(content)
        }
        for line in sorted(lines):
            print(f"{path}:{line}: possible API-key literal; value withheld.")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
