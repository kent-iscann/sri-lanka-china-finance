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

*Report generated: <date>*
*Confidence level: [Low/Medium/High]*
*Next review: <date 3 months out>*
```

## Critical Parsing Details

- **Prediction regex:** `r'## Prediction\s*\n(.*?)(?=\n---|\\n## )'` — extracts everything between `## Prediction` and the next `---` or `## ` delimiter
- **What's New regex:** `r"## What[-\u2019']?s New\s*\n(.*?)(?=\n---|\\n## )"` — flexible matching for the apostrophe character
- **Justification regex:** `r'## Justification\s*\n(.*?)(?=\n---|\\n## Key Sources)'` — extracts up to Key Sources section
- **Confidence regex:** `r'\*Confidence level:\s*([LowMediumHigh]+)\*'` — extracts confidence level from end of document (outside prediction section)

## Markdown Conversion

The script uses `convert_markdown()` (not `unbold()`) to convert markdown formatting to HTML:
- `**bold**` → `<strong>bold</strong>`
- `*italic*` → `<em>italic</em>`

This applies to all sections: prediction, What's New, and Justification subsections. The prediction sentence has HTML tags stripped before rendering since it's displayed as plain text in the `<p>` tag.

## Prediction Box Output

The PDF prediction box renders:
- Prediction sentence (left side, large text)
- Probability number (right side, very large font)
- "Probability" label
- Delta indicator (▲/▼ from previous report, if applicable)
- "Target: [date]"
- "Confidence: [Low/Medium/High]"

## Common Pitfalls

- If `---` separators are missing AND the regex can't find `## ` headings, the entire document after `## Prediction` gets treated as the prediction section
- Probability format must include `%` symbol (e.g., `70%`) for the regex to extract it
- Target date line must match `Target\s+Date\s*:\s*(.+)` pattern
- Confidence level must be in `*Confidence level: [Low/Medium/High]*` format at the end of the document
- Bold/italic markdown in What's New and Justification sections is now rendered as HTML — do NOT use `unbold()` as it strips formatting
