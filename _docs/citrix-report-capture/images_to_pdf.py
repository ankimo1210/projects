# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow==12.3.0",
#   "reportlab==4.4.9",
#   "pypdf==6.10.0",
# ]
# ///
"""Verify the private handoff files or rebuild a PDF from ordered screenshots."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify_manifest(root: Path, manifest_path: Path) -> dict:
    root = root.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe manifest path: {relative}")
        path = (root / relative).resolve(strict=True)
        path.relative_to(root)
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise ValueError(f"File or size mismatch: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch: {relative}")
    return {"verified_files": len(manifest["files"]), "result": "all hashes match"}


def build_pdf(source_dir: Path, output_path: Path, count: int) -> dict:
    from PIL import Image, ImageChops
    from pypdf import PdfReader
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    if count < 1:
        raise ValueError("Expected count must be positive.")
    sources = sorted(source_dir.glob("report_*.png"))
    if [p.name for p in sources] != [f"report_{i:03d}.png" for i in range(1, count + 1)]:
        raise ValueError("Screenshots must be consecutive, starting at report_001.png.")
    if output_path.exists():
        raise FileExistsError(f"Preserving existing file: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(
        str(output_path),
        pagesize=(page_width, page_height),
        pageCompression=1,
        invariant=1,
    )
    pdf.setTitle("Report screenshots")
    pdf.setCreator("Screenshot to PDF")
    for number, source in enumerate(sources, 1):
        with Image.open(source) as original:
            image = original.convert("RGB")
        scale = min((page_width - 12) / image.width, (page_height - 12) / image.height)
        width, height = image.width * scale, image.height * scale
        x, y = (page_width - width) / 2, (page_height - height) / 2
        pdf.bookmarkPage(f"capture-{number:02d}")
        pdf.addOutlineEntry(f"Screenshot {number:02d}", f"capture-{number:02d}")
        pdf.drawImage(ImageReader(image), x, y, width=width, height=height)
        pdf.showPage()
        image.close()
    pdf.save()

    reader = PdfReader(str(output_path))
    if len(reader.pages) != count:
        raise ValueError("PDF page count mismatch.")
    for page, source in zip(reader.pages, sources, strict=True):
        images = list(page.images)
        if len(images) != 1:
            raise ValueError(f"Expected one embedded image: {source.name}")
        embedded = images[0].image.convert("RGB")
        with Image.open(source) as original:
            expected = original.convert("RGB")
        if (
            embedded.size != expected.size
            or ImageChops.difference(embedded, expected).getbbox() is not None
        ):
            raise ValueError(f"Embedded image mismatch: {source.name}")
        embedded.close()
        expected.close()
    return {"pages": count, "lossless_images_verified": count, "output": str(output_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path(__file__).with_name("artifact-manifest.json"),
    )
    parser.add_argument("--images", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-count", type=int, default=17)
    args = parser.parse_args()
    if args.verify_only:
        if args.artifact_root is None:
            parser.error("--verify-only requires --artifact-root")
        result = verify_manifest(args.artifact_root, args.manifest)
    else:
        if args.images is None or args.output is None:
            parser.error("PDF creation requires --images and --output")
        result = build_pdf(args.images, args.output, args.expected_count)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
