---
name: md-to-sil-docx
description: Convert a Markdown document into a professional .docx using the SIL document template (title block, Heading 1/2/3 styles, tables, footer). Use for proposals, reports, or any deliverable that should look like a standard SIL document.
---

# md-to-sil-docx

Converts a Markdown file into a `.docx` rendered with the bundled SIL document template (`sil-template.docx`). The template provides the SIL title block, heading styles, page layout, and footer; this skill replaces the body with content parsed from Markdown.

## When to use

- You have a Markdown document (proposal, report, memo, spec) and need a shareable SIL-branded `.docx`.
- You want consistent headings, pricing tables, and a title block without hand-formatting Word.

## Requirements

- Python with `python-docx` installed (`pip install python-docx`).

## Usage

```bash
python convert.py INPUT.md OUTPUT.docx \
    --title "Document Title" \
    --subtitle "Subtitle · Date · Status"
```

Flags:

- `--title` — replaces the Title cell in the template's title block.
- `--subtitle` — replaces the Subtitle cell.
- `--template PATH` — use a different `.docx` template (defaults to the bundled `sil-template.docx`).
- `--keep-front-matter` — by default, if the input starts with a `# Heading` followed by a metadata block ending in a `---` horizontal rule, that block is stripped (since it's already represented in the title block). Pass this flag to keep it.

As a library:

```python
from pathlib import Path
from convert import convert

convert(
    md_path=Path("proposal.md"),
    out_path=Path("proposal.docx"),
    template_path=Path("sil-template.docx"),
    title="My Proposal",
    subtitle="For Customer · 2026 · Draft",
)
```

## Markdown features supported

- `#`, `##` → Heading 1; `###` → Heading 2; `####` → Heading 3
- Numbered lists (`1. item`) and bulleted lists (`- item`), including nested indentation
- Markdown tables (`| col | col |`) — rendered as Word tables with a bold header row and the "Table Grid" style when available
- Inline `**bold**`, `*italic*`, and `` `code` ``
- A trailing italic-only paragraph (e.g. a contact line) is preserved as italic
- `---` horizontal rules are ignored (used only as section separators in source)

## Notes

- Numbered and bulleted lists use **native Word numbering** (numPr references into `numbering.xml`), so Word will auto-renumber when items are added or removed. Each separate list in the source gets its own `numId` and therefore its own counter starting at 1.
- If the template's first table contains paragraphs styled `Title` and `Subtitle`, they are replaced in place; other cells (e.g. a logo placeholder) are left untouched.
- All top-level body paragraphs in the template are removed before rendering; tables (including the title block) and the section properties are kept.
