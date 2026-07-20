import argparse
from pathlib import Path

from gto.bench import load_dir, render_markdown


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gto.bench", description="Render a P0a solver audit report"
    )
    parser.add_argument("dir", type=Path, help="directory containing RunRecord JSON files")
    parser.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args()

    markdown = render_markdown(load_dir(args.dir))
    if args.out is None:
        print(markdown, end="")
        return

    args.out.write_text(markdown, encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
