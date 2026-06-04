# PDF Script Parsing Reference

## File: `/root/wiki/watch-report-to-pdf.py`

The shared PDF generation script parses watch report markdown files and converts them to styled PDFs via WeasyPrint.

## Section Delimiters

The script uses regex to extract sections from the markdown. Sections can be delimited by either:
- `---` horizontal rule
- `## ` markdown heading

Example of correct structure:
```markdown
## Prediction
[one sentence prediction]
**Probability:** [XX%]
**Target Date:** [date]

---

## What's New
[only for 2nd+ reports]
- [bullet points]

---

## Justification
### Political
[analysis]

### Economic
[analysis]

### Military
[analysis]

### Technological
[analysis]

---

## Key Sources
1. [source]
2. [source]
```

## Critical Parsing Details

- **Prediction regex:** `r'## Prediction\s*\n(.*?)(?=\n---|\n## )'` — extracts everything between `## Prediction` and the next `---` or `## ` delimiter
- **What's New regex:** `r"## What[-\u2019']?s New\s*\n(.*?)(?=\n---|\n## )"` — flexible matching for the apostrophe character
- **Justification regex:** `r'## Justification\s*\n(.*?)(?=\n---|\n## Key Sources)'` — extracts up to Key Sources section

## Common Pitfalls

- If `---` separators are missing AND the regex can't find `## ` headings, the entire document after `## Prediction` gets treated as the prediction section
- Probability format must include `%` symbol (e.g., `70%`) for the regex to extract it
- Target date line must match `Target\s+Date\s*:\s*(.+)` pattern
