#!/usr/bin/env python
"""
Convert HLD-Parana-<Author>.txt files to the benchmark submission format.

For each .txt file found directly inside submissions/, this script:
  1. Skips the 5-line header.
  2. Parses the space-separated H / L / D columns.
  3. Writes  submissions/<author>/result.csv  with the canonical column names.
  4. Writes  submissions/<author>/metadata.yaml  pre-filled from the filename.

Run from the benchmarks/river_dunes/ directory:
    python convert_submissions.py

The original .txt files are left untouched — delete them manually once you are
satisfied with the output.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUBMISSIONS_DIR = HERE / "submissions"

# Number of header lines to skip in each source file (lines 1-5).
HEADER_LINES = 5


def parse_txt(path: Path) -> list[tuple[str, str, str]]:
    """
    Read a source .txt file and return a list of (height, length, depth) tuples
    (as strings, preserving original precision).
    """
    rows: list[tuple[str, str, str]] = []
    with open(path) as fh:
        for i, line in enumerate(fh):
            if i < HEADER_LINES:
                continue
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 3:
                print(
                    f"  WARNING: unexpected number of columns on line {i+1} "
                    f"of {path.name!r} — skipping: {line!r}",
                    file=sys.stderr,
                )
                continue
            rows.append((parts[0], parts[1], parts[2]))
    return rows


def author_from_filename(path: Path) -> str:
    """
    Extract the author name from a filename like 'HLD-Parana-Scheiber.txt'.
    Returns the last hyphen-separated segment with the extension stripped.
    """
    stem = path.stem  # e.g. 'HLD-Parana-Scheiber'
    parts = stem.split("-")
    return parts[-1]  # e.g. 'Scheiber'


def write_result_csv(out_path: Path, rows: list[tuple[str, str, str]]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["height_m", "length_m", "depth_m"])
        writer.writerows(rows)


METADATA_TEMPLATE = """\
# Submission metadata — fill in the fields marked TODO.

method_name: "{author}"
method_description: >
  Expert human digitization of Paraná River bedforms by {author}.

tool_name: null          # e.g. "Bedforms-ATM", "manual digitization"
tool_version: null
tool_url: null           # link to tool repo or paper

author_name: "{author}"  # TODO: replace with full name
author_orcid: null       # optional

date: null               # TODO: ISO 8601, e.g. 2025-01-15
notes: null
"""


def write_metadata(out_path: Path, author: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(METADATA_TEMPLATE.format(author=author))


def main() -> None:
    txt_files = sorted(SUBMISSIONS_DIR.glob("*.txt"))

    if not txt_files:
        print("No .txt files found directly inside submissions/ — nothing to do.")
        return

    print(f"Found {len(txt_files)} file(s) to convert:\n")

    for txt_path in txt_files:
        author = author_from_filename(txt_path)
        folder_name = author.lower()
        out_dir = SUBMISSIONS_DIR / folder_name

        print(f"  {txt_path.name}  →  submissions/{folder_name}/")

        rows = parse_txt(txt_path)

        result_path = out_dir / "result.csv"
        write_result_csv(result_path, rows)
        print(f"    wrote {len(rows)} rows  →  {result_path.relative_to(HERE)}")

        metadata_path = out_dir / "metadata.yaml"
        if metadata_path.exists():
            print(f"    metadata.yaml already exists, skipping.")
        else:
            write_metadata(metadata_path, author)
            print(f"    wrote stub  →  {metadata_path.relative_to(HERE)}")

    print(
        "\nDone. Review the output files, then delete the original .txt files."
    )


if __name__ == "__main__":
    main()
