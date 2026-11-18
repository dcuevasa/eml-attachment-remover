#!/usr/bin/env python3
"""Create copies of EML files with MIME attachment parts removed."""

from __future__ import annotations

import argparse
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesParser
from pathlib import Path
import sys


def is_attachment(part: Message) -> bool:
    """Return True for parts that should be excluded as downloadable attachments."""
    disposition = part.get_content_disposition()
    if disposition == "attachment":
        return True

    # Some clients omit Content-Disposition but provide a filename.
    return disposition != "inline" and part.get_filename() is not None


def remove_attachments(message: Message) -> int:
    """Remove attachment children from message in place and return the count."""
    removed = 0

    if not message.is_multipart():
        return removed

    remaining = []
    for part in message.iter_parts() if isinstance(message, EmailMessage) else message.get_payload():
        if not isinstance(part, Message):
            continue
        if is_attachment(part):
            removed += 1
            continue
        removed += remove_attachments(part)
        remaining.append(part)

    message.set_payload(remaining)
    return removed


def strip_eml(source: Path, destination: Path) -> int:
    """Write a copy of source with attachments removed."""
    with source.open("rb") as source_file:
        message = BytesParser(policy=policy.default).parse(source_file)

    removed = remove_attachments(message)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as destination_file:
        destination_file.write(message.as_bytes(policy=policy.SMTP))
    return removed


def collect_eml_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise ValueError(f"Input path does not exist: {input_path}")

    pattern = "**/*.eml" if recursive else "*.eml"
    return sorted(
        (path for path in input_path.glob(pattern) if path.is_file()),
        key=lambda path: str(path).lower(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create EML copies without downloadable attachments."
    )
    parser.add_argument("input", type=Path, help="An EML file or directory")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        help="Output EML file or directory (default: a 'without-attachments' folder)",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Process nested directories",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        source_files = collect_eml_files(args.input, args.recursive)
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    if not source_files:
        print("No .eml files found.", file=sys.stderr)
        return 1

    if args.input.is_file():
        if args.output:
            output_path = args.output
            if args.output.is_dir() or args.output.suffix.lower() != ".eml":
                output_path = args.output / args.input.name
        else:
            output_path = args.input.parent / "without-attachments" / args.input.name
    else:
        output_root = args.output or args.input / "without-attachments"
        output_root.mkdir(parents=True, exist_ok=True)
        output_path = None

    total_removed = 0
    for source in source_files:
        if args.input.is_file():
            destination = output_path
        else:
            relative = source.relative_to(args.input)
            destination = output_root / relative

        removed = strip_eml(source, destination)
        total_removed += removed
        print(f"{source} -> {destination} ({removed} attachment(s) removed)")

    print(f"Done: {len(source_files)} file(s), {total_removed} attachment(s) removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
