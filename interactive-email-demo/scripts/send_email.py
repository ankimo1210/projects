#!/usr/bin/env python3
"""Send a generated .eml over SMTP, with an offline dry-run by default on request."""

from __future__ import annotations

import argparse
import os
import smtplib
import ssl
from email import policy
from email.message import Message
from email.parser import BytesParser
from pathlib import Path

from check_email import inspect_email


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eml", type=Path, required=True)
    parser.add_argument("--from-address", required=True)
    parser.add_argument("--to-address", required=True)
    parser.add_argument("--host", default=os.environ.get("SMTP_HOST"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SMTP_PORT", "587")))
    parser.add_argument("--username", default=os.environ.get("SMTP_USERNAME"))
    parser.add_argument("--password-env", default="SMTP_PASSWORD")
    parser.add_argument("--ssl", action="store_true", help="Use implicit TLS instead of STARTTLS")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only; do not connect or send"
    )
    return parser.parse_args()


def send_via_smtp(
    message: Message,
    *,
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    from_address: str,
    to_address: str,
    use_ssl: bool,
) -> None:
    context = ssl.create_default_context()
    if use_ssl:
        smtp_connection = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    else:
        smtp_connection = smtplib.SMTP(host, port, timeout=30)

    with smtp_connection as smtp:
        if not use_ssl:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        if username:
            smtp.login(username, password)
        smtp.send_message(message, from_addr=from_address, to_addrs=[to_address])


def main() -> None:
    args = parse_args()
    errors = inspect_email(args.eml)
    if errors:
        raise SystemExit("Email validation failed:\n- " + "\n- ".join(errors))
    if args.from_address.casefold() == args.to_address.casefold():
        raise SystemExit("From and To must be different for Gmail AMP testing")

    message = BytesParser(policy=policy.SMTP).parsebytes(args.eml.read_bytes())
    message.replace_header("From", args.from_address)
    message.replace_header("To", args.to_address)

    if args.dry_run:
        part_types = [part.get_content_type() for part in message.iter_parts()]
        print(f"DRY RUN: {args.from_address} -> {args.to_address}")
        print(f"Subject: {message['Subject']}")
        print(f"MIME parts: {', '.join(part_types)}")
        return

    if not args.host:
        raise SystemExit("SMTP host is required via --host or SMTP_HOST")
    password = os.environ.get(args.password_env)
    if args.username and not password:
        raise SystemExit(f"Password is required in environment variable {args.password_env}")

    send_via_smtp(
        message,
        host=args.host,
        port=args.port,
        username=args.username,
        password=password,
        from_address=args.from_address,
        to_address=args.to_address,
        use_ssl=args.ssl,
    )
    print(f"SENT: {args.from_address} -> {args.to_address}")


if __name__ == "__main__":
    main()
