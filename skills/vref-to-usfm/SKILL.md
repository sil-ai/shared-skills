---
name: vref-to-usfm
description: Convert VREF-aligned text files (41,899 lines) into SFM/USFM files with proper markers for use with Bible translation software like Paratext. Use when transforming verse-aligned plain text back into standard USFM format with \id, \c, and \v markers.
---

# vref-to-usfm

Convert VREF-aligned text files (41,899 lines) into SFM/USFM files with proper markers.

## Overview

This skill converts verse-aligned plain text files into Standard Format Markers (SFM/USFM) files suitable for use with Bible translation software like Paratext.

### Input Format
- VREF-aligned text file: one verse per line (41,899 lines total)
- Empty lines indicate missing/untranslated verses
- `<range>` markers indicate verse ranges (text is on the previous verse)

### Output Format
SFM files with proper markers:
```
\id GEN
\c 1
\v 1 In the beginning God created the heavens and the earth.
\v 2 And the earth was without form...
\c 2
\v 1 Thus the heavens and the earth were finished...
```

## Usage

The script is located in the `scripts/` subdirectory of this skill. After installing the skill, you can run it with Python.

### Convert with project ID (recommended)
```bash
python ~/.claude/skills/vref-to-usfm/scripts/vref_to_usfm.py \
    input.txt \
    --output-dir ./output \
    --project-id MalBT
```
This creates files like `./output/MalBT/01GENMalBT.SFM`, `./output/MalBT/02EXOMalBT.SFM`, etc.

### Convert all books (without project ID)
```bash
python ~/.claude/skills/vref-to-usfm/scripts/vref_to_usfm.py \
    input.txt \
    --output-dir ./output
```

### Convert a single book
```bash
python ~/.claude/skills/vref-to-usfm/scripts/vref_to_usfm.py \
    input.txt \
    --book GEN \
    --output-dir ./output \
    --project-id MalBT
```

### Use a custom vref.txt (different versification)
```bash
python ~/.claude/skills/vref-to-usfm/scripts/vref_to_usfm.py \
    input.txt \
    --vref /path/to/custom/vref.txt \
    --output-dir ./output \
    --project-id MalBT
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `input` | Path to VREF-aligned text file | (required) |
| `--vref` | Path to vref.txt reference file | `vref.txt` in skill directory |
| `--output-dir` | Output directory for SFM files | (required) |
| `--book` | Convert only this book (e.g., GEN, MAT) | All books |
| `--project-id` | Project ID for directory and filenames | None |

## Output Files

### With `--project-id`
Files are placed in a subdirectory named after the project ID, with filenames in the format `<booknum><bookcode><projectid>.SFM`:
- `MalBT/01GENMalBT.SFM`, `MalBT/02EXOMalBT.SFM`, ... (Old Testament)
- `MalBT/40MATMalBT.SFM`, `MalBT/41MRKMalBT.SFM`, ... (New Testament)

### Without `--project-id`
Files are named by book code with `.sfm` extension:
- `GEN.sfm`, `EXO.sfm`, `LEV.sfm`, ...
- `MAT.sfm`, `MRK.sfm`, `LUK.sfm`, ...

## Handling Special Cases

- **Empty lines**: Verse is skipped (not included in output)
- **`<range>` markers**: Creates verse ranges in output (e.g., `\v 1-2 text` when v1 has text and v2 is `<range>`)
- **Chapter boundaries**: New `\c` marker inserted automatically
- **Book boundaries**: New file created with `\id` marker
