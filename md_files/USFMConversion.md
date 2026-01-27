# Converting USFM/Paratext Projects to VREF Format

This document describes how to convert Bible text from USFM/Paratext formats into the line-based VREF format using the SIL `machine` library.

For details on the VREF output format, see [vref.md](vref.md).

## Format Overview

### SFM (Standard Format Markers)

The original marker-based format for Scripture text, using backslash markers like `\c` for chapters and `\v` for verses. Plain text files with embedded formatting codes.

```
\c 1
\v 1 In the beginning God created the heavens and the earth.
\v 2 And the earth was without form, and void...
```

### USFM (Unified Standard Format Markers)

An extension of SFM with additional markers for richer formatting. The current standard for Bible translation projects. Files typically use `.usfm` or `.sfm` extensions.

```
\id GEN
\c 1
\p
\v 1 In the beginning God created the heavens and the earth.
\v 2 And the earth was without form, and void...
```

### USX (Unified Scripture XML)

An XML representation of USFM. Used internally by Paratext and for data interchange. Files use `.usx` extension.

```xml
<usx version="3.0">
  <book code="GEN" style="id">Genesis</book>
  <chapter number="1" style="c" />
  <para style="p">
    <verse number="1" style="v" />In the beginning God created...
    <verse number="2" style="v" />And the earth was without form...
  </para>
</usx>
```

### Paratext Projects

Paratext is a Bible translation software that stores projects as a directory containing:
- Individual book files (USX or USFM format)
- `Settings.xml` - Project configuration including versification and file naming
- Other supporting files

## The `machine` Library

The SIL `machine` library provides corpus classes for reading Scripture text and extracting it to VREF format.

**Installation:**
```bash
pip install sil-machine
```

**Key imports:**
```python
from machine.corpora import ParatextTextCorpus, extract_scripture_corpus
from machine.scripture import Versification, VersificationType
```

## Converting a Paratext Project

Paratext projects include a `Settings.xml` file that specifies versification and file naming conventions. The `ParatextTextCorpus` class reads this automatically.

```python
from pathlib import Path
from machine.corpora import ParatextTextCorpus, extract_scripture_corpus

# Point to the Paratext project directory
project_path = Path("/path/to/paratext/project")

# Create corpus (reads Settings.xml automatically)
corpus = ParatextTextCorpus(project_path.resolve())

# Extract to VREF format
output = list(extract_scripture_corpus(corpus))

# Write to file
with open("output.txt", "wb") as f:
    for line, _, _ in output:
        f.write(line.encode() + b"\n")
```

### From a Zip Archive

If you have a Paratext backup zip file:

```python
import tempfile
from pathlib import Path
from zipfile import ZipFile
from machine.corpora import ParatextTextCorpus, extract_scripture_corpus

def convert_paratext_zip(zip_path: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile(zip_path, "r") as z:
            z.extractall(tmpdir)

        # Handle case where zip contains a single subdirectory
        contents = [d for d in Path(tmpdir).iterdir() if d.name != "__MACOSX"]
        project_path = contents[0] if len(contents) == 1 else Path(tmpdir)

        corpus = ParatextTextCorpus(project_path.resolve())
        output = list(extract_scripture_corpus(corpus))

        return b"\n".join(line.encode() for line, _, _ in output) + b"\n"
```

## Converting Non-Paratext USFM Files

For USFM/SFM files that are not part of a Paratext project, you must create a `Settings.xml` file to specify the versification and file naming pattern.

### Minimal Settings.xml

Create a `Settings.xml` file in the same directory as your USFM files:

```xml
<ScriptureText>
  <Versification>4</Versification>
  <LanguageIsoCode>en:::</LanguageIsoCode>
  <Naming PrePart="" PostPart=".usfm" BookNameForm="MAT" />
</ScriptureText>
```

### Settings.xml Fields

| Field | Description | Example |
|-------|-------------|---------|
| `Versification` | Numeric code for versification scheme (see table below) | `4` (English) |
| `LanguageIsoCode` | ISO 639-1 language code with colons | `en:::` or `ur:::` |
| `Naming/@PrePart` | Prefix before book name in filenames | `""` or `"P"` |
| `Naming/@PostPart` | Suffix after book name in filenames | `.usfm` or `.SFM` |
| `Naming/@BookNameForm` | Pattern for book names in filenames | `MAT` or `41MAT` |

### Book Name Forms

The `BookNameForm` attribute tells the library how your files are named:

| BookNameForm | Example Filename | Description |
|--------------|------------------|-------------|
| `MAT` | `MAT.usfm` | 3-letter book code only |
| `41MAT` | `41MAT.usfm` | Book number + 3-letter code |
| `Matthew` | `Matthew.usfm` | Full book name |

With `PrePart="P"` and `PostPart=".SFM"` and `BookNameForm="41MAT"`:
- Matthew would be: `P41MAT.SFM`

### Complete Example

Given USFM files named like `GEN.usfm`, `EXO.usfm`, etc.:

```xml
<ScriptureText>
  <Versification>4</Versification>
  <LanguageIsoCode>en:::</LanguageIsoCode>
  <Naming PrePart="" PostPart=".usfm" BookNameForm="MAT" />
</ScriptureText>
```

Then convert:

```python
from pathlib import Path
from machine.corpora import ParatextTextCorpus, extract_scripture_corpus

# Directory containing Settings.xml and USFM files
project_path = Path("/path/to/usfm/files")

corpus = ParatextTextCorpus(project_path.resolve())
output = list(extract_scripture_corpus(corpus))

with open("output.txt", "wb") as f:
    for line, _, _ in output:
        f.write(line.encode() + b"\n")
```

## Converting USX Files Directly

If you have USX files without a Paratext project structure, use `UsxFileTextCorpus` with an explicit versification:

```python
from pathlib import Path
from machine.corpora import UsxFileTextCorpus, extract_scripture_corpus
from machine.scripture import Versification, VersificationType

# Get the versification object
versification = Versification.get_builtin(VersificationType.ENGLISH)

# Directory containing .usx files
usx_dir = Path("/path/to/usx/files")

corpus = UsxFileTextCorpus(usx_dir, versification=versification)
output = list(extract_scripture_corpus(corpus))

with open("output.txt", "wb") as f:
    for line, _, _ in output:
        f.write(line.encode() + b"\n")
```

## Versification

Different Bible traditions have different verse numbering schemes. The `machine` library supports these versification types:

| Code | Name | Description |
|------|------|-------------|
| 0 | UNKNOWN | Could not be determined |
| 1 | ORIGINAL | Original language versification |
| 2 | SEPTUAGINT | Septuagint (LXX) versification |
| 3 | VULGATE | Latin Vulgate versification |
| 4 | ENGLISH | Standard English versification (most common) |
| 5 | RUSSIAN_PROTESTANT | Russian Protestant tradition |
| 6 | RUSSIAN_ORTHODOX | Russian Orthodox tradition |

### Using Versification Types

```python
from machine.scripture import Versification, VersificationType

# By enum
versification = Versification.get_builtin(VersificationType.ENGLISH)

# By name string
vers_type = VersificationType["ENGLISH"]
versification = Versification.get_builtin(vers_type)
```

### Choosing the Right Versification

If unsure which versification your text uses, ENGLISH (code 4) is the most common for modern translations. Key differences between versifications appear in:

- **Daniel 3** - ranges from 30 verses (English) to 100 verses (Vulgate/Russian Orthodox)
- **John 6** - 71 verses (Original) vs 72 verses (Vulgate)
- **Acts 19** - 40 verses (Original) vs 41 verses (English)
- **Romans 16** - 24 verses (Russian) vs 27 verses (others)

## Output Format

The `extract_scripture_corpus()` function returns an iterable of tuples:

```python
output = list(extract_scripture_corpus(corpus))
# Each item is: (text, verse_ref, additional_info)

for text, verse_ref, _ in output:
    print(f"{verse_ref}: {text}")
```

**Important:** The output is always in ORIGINAL versification, regardless of the source versification. The `extract_scripture_corpus()` function automatically maps verses from the source versification to ORIGINAL. This ensures all vref-aligned files use a consistent verse numbering system.

The output is already aligned to VREF line numbers (which use ORIGINAL versification):
- Line 1 = GEN 1:1
- Line 23214 = MAT 1:1
- 41,899 total lines for a complete Bible

Empty strings indicate missing verses. The `<range>` marker indicates a verse combined with the previous verse.

See [vref.md](vref.md) for complete VREF format documentation.

## Summary

| Scenario | Corpus Class | Settings.xml Required? |
|----------|--------------|------------------------|
| Paratext project directory | `ParatextTextCorpus` | Already present |
| Paratext backup zip | `ParatextTextCorpus` | Already present |
| USFM files (non-Paratext) | `ParatextTextCorpus` | Yes, create manually |
| USX files only | `UsxFileTextCorpus` | No, specify versification in code |