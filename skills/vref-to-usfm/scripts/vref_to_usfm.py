#!/usr/bin/env python3
r"""
Convert VREF-aligned text files to SFM/USFM format.

Takes a 41,899-line text file (one verse per line) and converts it to
SFM files with \id, \c, and \v markers.
"""

import argparse
import re
from pathlib import Path
from collections import defaultdict


# Default vref.txt location (relative to this script)
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_VREF = SCRIPT_DIR.parent / "vref.txt"

# Canonical Bible book order (1-66)
BOOK_ORDER = {
    "GEN": 1, "EXO": 2, "LEV": 3, "NUM": 4, "DEU": 5,
    "JOS": 6, "JDG": 7, "RUT": 8, "1SA": 9, "2SA": 10,
    "1KI": 11, "2KI": 12, "1CH": 13, "2CH": 14, "EZR": 15,
    "NEH": 16, "EST": 17, "JOB": 18, "PSA": 19, "PRO": 20,
    "ECC": 21, "SNG": 22, "ISA": 23, "JER": 24, "LAM": 25,
    "EZK": 26, "DAN": 27, "HOS": 28, "JOL": 29, "AMO": 30,
    "OBA": 31, "JON": 32, "MIC": 33, "NAM": 34, "HAB": 35,
    "ZEP": 36, "HAG": 37, "ZEC": 38, "MAL": 39,
    "MAT": 40, "MRK": 41, "LUK": 42, "JHN": 43, "ACT": 44,
    "ROM": 45, "1CO": 46, "2CO": 47, "GAL": 48, "EPH": 49,
    "PHP": 50, "COL": 51, "1TH": 52, "2TH": 53, "1TI": 54,
    "2TI": 55, "TIT": 56, "PHM": 57, "HEB": 58, "JAS": 59,
    "1PE": 60, "2PE": 61, "1JN": 62, "2JN": 63, "3JN": 64,
    "JUD": 65, "REV": 66,
}


def parse_vref_line(line: str) -> tuple[str, int, int]:
    """Parse a vref line like 'GEN 1:1' into (book, chapter, verse)."""
    match = re.match(r"(\w+)\s+(\d+):(\d+)", line.strip())
    if not match:
        raise ValueError(f"Invalid vref line: {line}")
    return match.group(1), int(match.group(2)), int(match.group(3))


def load_vref(vref_path: str) -> list[tuple[str, int, int]]:
    """Load vref.txt and return list of (book, chapter, verse) tuples."""
    refs = []
    with open(vref_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                refs.append(parse_vref_line(line))
    return refs


def load_text(text_path: str) -> list[str]:
    """Load the VREF-aligned text file."""
    with open(text_path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n\r") for line in f]


def convert_to_sfm(
    refs: list[tuple[str, int, int]],
    texts: list[str],
    book_filter: str | None = None,
) -> dict[str, list[str]]:
    """
    Convert aligned refs and texts to SFM format.

    Returns dict mapping book code to list of SFM lines.
    """
    if len(refs) != len(texts):
        raise ValueError(
            f"Mismatch: {len(refs)} refs but {len(texts)} text lines"
        )

    # Group by book
    books: dict[str, list[str]] = defaultdict(list)
    current_book = None
    current_chapter = None

    i = 0
    while i < len(refs):
        book, chapter, verse = refs[i]
        text = texts[i].strip()

        # Skip if filtering to a specific book
        if book_filter and book != book_filter:
            i += 1
            continue

        # Skip empty lines and <range> markers (range is handled by previous verse)
        if not text or text == "<range>":
            i += 1
            continue

        # New book
        if book != current_book:
            current_book = book
            current_chapter = None
            books[book].append(f"\\id {book}")

        # New chapter
        if chapter != current_chapter:
            current_chapter = chapter
            books[book].append(f"\\c {chapter}")

        # Look ahead for <range> markers to determine verse range
        end_verse = verse
        j = i + 1
        while j < len(refs):
            next_book, next_chapter, next_verse = refs[j]
            next_text = texts[j].strip()
            # Stop if different book/chapter or not a range marker
            if next_book != book or next_chapter != chapter or next_text != "<range>":
                break
            end_verse = next_verse
            j += 1

        # Add verse (with range if applicable)
        if end_verse > verse:
            books[book].append(f"\\v {verse}-{end_verse} {text}")
        else:
            books[book].append(f"\\v {verse} {text}")

        i += 1

    return dict(books)


def write_sfm_files(
    books: dict[str, list[str]], output_dir: Path, project_id: str | None = None
) -> None:
    """Write SFM content to files."""
    # If project_id provided, create subdirectory
    if project_id:
        output_dir = output_dir / project_id
    output_dir.mkdir(parents=True, exist_ok=True)

    for book, lines in books.items():
        if project_id:
            # Format: <bookint><bookabbrev><projectid>.SFM (e.g., 01GENMalBT.SFM)
            book_num = BOOK_ORDER.get(book, 0)
            filename = f"{book_num:02d}{book}{project_id}.SFM"
        else:
            filename = f"{book}.sfm"
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
            f.write("\n")
        print(f"Written: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert VREF-aligned text to SFM/USFM format"
    )
    parser.add_argument(
        "input",
        help="Path to VREF-aligned text file (41,899 lines)",
    )
    parser.add_argument(
        "--vref",
        default=str(DEFAULT_VREF),
        help=f"Path to vref.txt reference file (default: {DEFAULT_VREF})",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for SFM files",
    )
    parser.add_argument(
        "--book",
        help="Convert only this book (e.g., GEN, MAT)",
    )
    parser.add_argument(
        "--project-id",
        help="Project ID for output directory and filenames (e.g., MalBT)",
    )

    args = parser.parse_args()

    # Load data
    print(f"Loading vref from: {args.vref}")
    refs = load_vref(args.vref)
    print(f"Loaded {len(refs)} verse references")

    print(f"Loading text from: {args.input}")
    texts = load_text(args.input)
    print(f"Loaded {len(texts)} text lines")

    # Convert
    books = convert_to_sfm(refs, texts, args.book)
    print(f"Converting {len(books)} book(s)")

    # Write output
    write_sfm_files(books, Path(args.output_dir), args.project_id)
    print("Done!")


if __name__ == "__main__":
    main()
