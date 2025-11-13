#!/usr/bin/env python3
"""
Render Markdown reports to PDF with consistent styling.

Requires `pandoc` and a LaTeX engine (e.g. xelatex) installed on the host.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_FLAGS = [
    "--from=markdown+pipe_tables+table_captions",
    "--number-sections",
    "--table-of-contents",
    "--pdf-engine=xelatex",
    "--variable=geometry:margin=1in",
    "--variable=fontsize=11pt",
    "--variable=mainfont=DejaVu Serif",
    "--variable=sansfont=DejaVu Sans",
    "--variable=monofont=DejaVu Sans Mono",
]


def _check_dependencies() -> None:
    """Ensure pandoc is available."""
    if shutil.which("pandoc") is None:
        print("Error: pandoc not found in PATH. Install pandoc to continue.", file=sys.stderr)
        sys.exit(1)


def render_markdown(
    md_path: Path,
    pdf_path: Path,
    extra_args: list[str] | None = None,
) -> None:
    """Invoke pandoc to convert Markdown to PDF."""
    cmd = ["pandoc", str(md_path), "-o", str(pdf_path), *DEFAULT_FLAGS]
    if extra_args:
        cmd.extend(extra_args)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"pandoc failed with exit code {exc.returncode}", file=sys.stderr)
        sys.exit(exc.returncode)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "markdown",
        type=Path,
        help="Path to the input Markdown file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Destination PDF file (defaults to <markdown>.pdf).",
    )
    parser.add_argument(
        "--extra-arg",
        action="append",
        default=[],
        help="Additional pandoc CLI argument(s) to append.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    md_path: Path = args.markdown.resolve()
    if not md_path.exists():
        print(f"Error: Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    pdf_path: Path
    if args.output:
        pdf_path = args.output.resolve()
    else:
        pdf_path = md_path.with_suffix(".pdf")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    _check_dependencies()
    render_markdown(md_path, pdf_path, extra_args=args.extra_arg)

    print(f"PDF created at {pdf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

