# Wiki Schema

## Domain
China's financial relationship with Sri Lanka, including debt, infrastructure investment, the Belt and Road Initiative, the debt-trap diplomacy debate, and the 2022 sovereign default and subsequent restructuring.

## Conventions
- File names: lowercase, hyphens, no spaces
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- Provenance markers: append `^[raw/articles/source-file.md]` at end of paragraphs from specific sources

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary | timeline
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true
contradictions: [other-page-slug]
---
```

## Tag Taxonomy
- debt: debt, lending, loans, restructuring, default, creditors
- infrastructure: port, airport, power-plant, highway, land-reclamation
- diplomacy: debt-trap, sovereignty, BRI, geopolitics, india-china-rivalry
- politics: rajapaksa, sirisena, domestic-politics, civil-war
- economics: trade, investment, FDI, macroeconomics, IMF, reserves
- timeline: chronology, events, milestones
- actors: china-exim-bank, china-dev-bank, china-merchants-port, imf, paris-club, adb

## Page Thresholds
- Create a page when an entity/concept appears in 2+ sources OR is central to one source
- Add to existing page when a source mentions something already covered
- DON'T create a page for passing mentions
- Split a page when it exceeds ~200 lines
