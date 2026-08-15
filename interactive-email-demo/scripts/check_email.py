#!/usr/bin/env python3
"""Check the MIME layout and basic AMP-for-Email delivery requirements."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
from pathlib import Path

AMP_LIMIT_BYTES = 200_000
REQUIRED_AMP_MARKUP = (
    "<!doctype html>",
    "<html amp4email",
    '<meta charset="utf-8">',
    "https://cdn.ampproject.org/v0.js",
    "<style amp4email-boilerplate>",
)


def inspect_email(path: Path) -> list[str]:
    errors: list[str] = []
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    if message.get_content_type() != "multipart/alternative":
        errors.append("root content type must be multipart/alternative")

    parts = list(message.iter_parts()) if message.is_multipart() else []
    content_types = [part.get_content_type() for part in parts]
    expected = ["text/plain", "text/x-amp-html", "text/html"]
    if content_types != expected:
        errors.append(f"MIME order must be {expected}, got {content_types}")

    from_address = str(message.get("From", "")).casefold()
    to_address = str(message.get("To", "")).casefold()
    if not from_address or not to_address:
        errors.append("From and To headers are required")
    elif from_address == to_address:
        errors.append("From and To must differ for Gmail AMP testing")

    amp_parts = [part for part in parts if part.get_content_type() == "text/x-amp-html"]
    if len(amp_parts) != 1:
        errors.append(f"exactly one AMP MIME part is required, found {len(amp_parts)}")
        return errors

    amp = amp_parts[0].get_content()
    amp_bytes = amp.encode("utf-8")
    if len(amp_bytes) > AMP_LIMIT_BYTES:
        errors.append(f"AMP part is {len(amp_bytes)} bytes; limit is {AMP_LIMIT_BYTES}")
    lower_amp = amp.lower()
    for token in REQUIRED_AMP_MARKUP:
        if token not in lower_amp:
            errors.append(f"AMP part is missing required markup: {token}")
    if "<script>" in lower_amp or "javascript:" in lower_amp:
        errors.append("custom JavaScript is not allowed in AMP email")
    if "[hidden]=" not in amp or "AMP.setState" not in amp:
        errors.append("interactive state bindings were not found")
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("eml", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = inspect_email(args.eml)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print(f"PASS: {args.eml}")


if __name__ == "__main__":
    main()
