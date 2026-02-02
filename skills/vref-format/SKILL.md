---
name: vref-format
description: Understand and work with the VREF (Verse Reference) format, a line-based system for aligning Bible text with 41,899 canonical verse references. Use when creating, reading, or processing vref-aligned files, understanding the vref.txt structure, or handling `<range>` markers for combined verses.
---

# VREF Format Documentation

The VREF (Verse Reference) format is a simple line-based system for aligning Bible text with a standardized verse reference list. It enables consistent alignment of Scripture text across different translations and makes it easy to work with verse-level or passage-level data.

## Overview

The format consists of two parallel files:
1. **vref.txt** - A master reference file containing verse references (one per line)
2. **A text file** - Contains the actual Bible text, with each line corresponding to the same line in vref.txt

## The vref.txt File

The `vref.txt` file is a canonical list of all verse references in order. Each line contains a single verse reference in the format:

```
BOOK CHAPTER:VERSE
```

### Format Details

- **Line number** = verse position (1-indexed)
- **Book code** = 2-3 uppercase characters (e.g., `GEN`, `MAT`, `1CO`)
- **Chapter** = chapter number (no leading zeros)
- **Verse** = verse number (no leading zeros)

### Example (first 10 lines of vref.txt)

```
GEN 1:1
GEN 1:2
GEN 1:3
GEN 1:4
GEN 1:5
GEN 1:6
GEN 1:7
GEN 1:8
GEN 1:9
GEN 1:10
```

### Book Order and Line Numbers

The vref.txt file follows canonical book order. Key reference points:

| Line | Reference | Notes |
|------|-----------|-------|
| 1 | GEN 1:1 | Start of Old Testament |
| 1534 | EXO 1:1 | Exodus begins |
| 2747 | LEV 1:1 | Leviticus begins |
| 23214 | MAT 1:1 | Start of New Testament |
| 30766 | REV 1:1 | Revelation begins |
| 31170 | REV 22:21 | End of Protestant canon |
| 31171+ | Additional books | Deuterocanonical/extra-canonical books |

The file contains 41,899 lines total, including additional books beyond the 66-book Protestant canon (such as 1 Enoch abbreviated as `ENO`).

### Standard Book Abbreviations

**Old Testament:**
```
GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL
```

**New Testament:**
```
MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV
```

## Creating a VREF-Aligned Text File

When creating a text file aligned to vref.txt:

1. **Each line corresponds to the same line number in vref.txt**
2. **Line contains the verse text** for that reference in your translation
3. **Empty lines** indicate the verse doesn't exist or isn't translated
4. **`<range>` marker** indicates a verse range (see below)

### Example Text File

If your translation has Matthew 1:1-3, your file at lines 23214-23216 would look like:

```
The book of the genealogy of Jesus Christ, son of David, son of Abraham.
Abraham begot Isaac, and Isaac begot Jacob, and Jacob begot Judah and his brothers.
Judah begot Perez and Zerah by Tamar, and Perez begot Hezron, and Hezron begot Ram.
```

## The `<range>` Marker

The `<range>` marker handles cases where a translation combines multiple verses into one.

### When to Use

When a translation combines verses (e.g., verses 12-13 are translated together as a single unit), use `<range>` on the continuation lines.

### Example

If a translation combines 1 Corinthians 5:12-13 into a single verse:

| Line | vref.txt | Text File |
|------|----------|-----------|
| ... | 1CO 5:12 | Full text of combined verses 12-13 here... |
| ... | 1CO 5:13 | `<range>` |

### Processing `<range>` Markers

When reading a VREF-aligned text file:

```python
# Load verse references
with open('vref.txt', 'r', encoding='utf-8') as f:
    vrefs = [line.strip() for line in f.readlines()]

# Load text data, filtering out <range> markers
with open('translation.txt', 'r', encoding='utf-8') as f:
    texts = [line.replace("<range>", "").strip() for line in f.readlines()]

# Now vrefs[i] corresponds to texts[i]
# Empty strings in texts indicate no text for that verse (either missing or part of a range)
```

## Common Use Cases

### 1. Verse-Level Dataset Creation

```python
# Create (reference, text) pairs for non-empty verses
verse_pairs = [(vrefs[i], texts[i]) for i in range(len(vrefs)) if texts[i]]
```

### 2. Chapter-Level Aggregation

```python
from collections import defaultdict

chapters = defaultdict(list)
for vref, text in zip(vrefs, texts):
    if not text:
        continue
    parts = vref.split()
    book = parts[0]
    chapter = parts[1].split(':')[0]
    chapter_key = f"{book}_{chapter}"
    chapters[chapter_key].append(text)

# Combine verses into chapter text
for chapter_key, verses in chapters.items():
    chapter_text = " ".join(verses)
```

### 3. Passage/Range Matching

When matching audio files that span verse ranges:

```python
# Parse a range like "MAT 7:1-12"
book = "MAT"
start_chapter, start_verse = 7, 1
end_chapter, end_verse = 7, 12

# Collect all verses in range
passage_text = []
for verse in range(start_verse, end_verse + 1):
    verse_key = (book, start_chapter, verse)
    if verse_key in verse_lookup:
        passage_text.append(verse_lookup[verse_key])

combined = " ".join(passage_text)
```

## Writing VREF-Aligned Files

When creating a new VREF-aligned text file:

1. **Start with the correct number of lines** (41,899 for the full vref.txt)
2. **Align each verse** to its corresponding line number
3. **Use empty lines** for verses not in your translation
4. **Use `<range>`** for verses combined with the previous verse

### Validation Checklist

- [ ] File has exactly the same number of lines as vref.txt
- [ ] No text appears on lines where the translation doesn't have that verse
- [ ] `<range>` markers are used correctly for combined verses
- [ ] Text encoding is UTF-8

## File Naming Convention

VREF-aligned text files typically follow this pattern:
```
{language_code}-{translation_code}.txt
```

Examples:
- `senga-MAT.txt` - Senga language, Matthew only
- `acf-acfNT.txt` - Antillean Creole French, New Testament

## Audio File Naming

When working with audio files for VREF-aligned text, common naming patterns include:

**Chapter-level:**
```
{BOOK}_{CHAPTER}.mp3
```
Example: `MAT_001.mp3`, `1CO_012.mp3`

**Passage-level:**
```
{BookNum}_{BookName}_{StartChapter}_{StartVerse}-{EndChapter}_{EndVerse}___{ID}.mp3
```
Example: `B01_Mateyo_007_001-007_012___P1SGQPIT.mp3`

Book number mapping (New Testament):
```
B01=MAT  B02=MRK  B03=LUK  B04=JHN  B05=ACT  B06=ROM  B07=1CO  B08=2CO
B09=GAL  B10=EPH  B11=PHP  B12=COL  B13=1TH  B14=2TH  B15=1TI  B16=2TI
B17=TIT  B18=PHM  B19=HEB  B20=JAS  B21=1PE  B22=2PE  B23=1JN  B24=2JN
B25=3JN  B26=JUD  B27=REV
```

## Summary

The VREF format provides a simple, line-based alignment system for Bible text:

1. Every verse has a fixed line number in vref.txt
2. Parallel text files use the same line numbering
3. Empty lines = missing verses
4. `<range>` = verse combined with previous
5. Line count must match exactly (41,899 for full Bible + extras)

This format enables easy creation of verse-level, chapter-level, or passage-level datasets for speech recognition, text-to-speech, translation alignment, and other Bible-related NLP tasks.
