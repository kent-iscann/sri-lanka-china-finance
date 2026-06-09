---
name: topic-watcher
description: "Manage multi-topic research wikis with automated source monitoring, watch reports, and PDF generation. Add new topics, list active topics, remove topics, or trigger manual runs."
metadata:
  hermes:
    tags: [research, wiki, cron, pdf, multi-topic, watch-report]
---

# Topic Watcher

Manage a multi-topic research wiki system. Each topic lives in its own folder under `/root/wiki/` with standardized structure: sources, timeline, entities, concepts, and automated watch reports with PDF generation.

## Support Files

| File | Purpose |
|------|---------|
| `references/weekly-source-monitor-prompt.md` | Cron prompt template for weekly source monitor |
| `references/monthly-watch-report-prompt.md` | Cron prompt template for monthly watch report |
| `references/watch-report-review-prompt.md` | Quality review checklist for watch reports (pre-publication) |
| `references/pdf-script-parsing.md` | PDF script parsing rules and regex details |
| `templates/index.md` | Starter index.md for a new topic |
| `templates/sources.md` | Starter sources.md |
| `templates/timeline.md` | Starter timeline file |
| `templates/watch-report.md` | Starter watch report with correct structure |
| `templates/watch-reports-summary.md` | Starter summary table for watch report history |

## Central Config

All topics are registered in `/root/wiki/_config.yaml`. The skill reads and updates this file to track active topics.

Config structure:
```yaml
topics:
  - name: "Sri Lanka-China"
    slug: "sri-lanka-china"
    path: "/root/wiki/sri-lanka-china"
    created: "2026-05-20"
    search_queries:
      - "Sri Lanka China debt restructuring"
      - "Sri Lanka China Belt and Road"
      - "Sri Lanka China bilateral loan"
      - "Sri Lanka China Hambantota port"
      - "Sri Lanka China IMF creditor"
    cron_jobs:
      weekly_source_monitor: "<job_id>"
      monthly_watch_report: "<job_id>"
```

## Operations

### Add a New Topic

**Trigger:** User says "add topic", "new topic", "create topic", or provides a topic name + description.

**Input needed from user:**
- Topic name (e.g., "Vietnam-Philippines maritime finance")
- 2-3 sentence brief describing what to track

**Steps:**

1. **Generate slug and search queries from the brief:**
   - Slug = lowercase, hyphenated (e.g., "vietnam-philippines")
   - Generate 5-8 targeted search queries based on the brief

2. **Scaffold the folder structure** (use `templates/` files):
   ```
   /root/wiki/<slug>/
   ├── index.md              (from templates/index.md)
   ├── sources.md            (from templates/sources.md)
   ├── timeline/
   │   └── <slug>-timeline.md  (from templates/timeline.md)
   ├── entities/
   ├── concepts/
   ├── Watch Reports/
   └── watch-reports-summary.md  (from templates/watch-reports-summary.md)
   ```

3. **Seed initial research:**
   - Run each search query via `tavily_search` with `time_range="month"`, `max_results=5`
   - For top results, use `tavily_extract` to get full content
   - Populate `sources.md` with numbered entries
   - Create 3-5 timeline events
   - Create 2-4 entity pages for key actors
   - Create 2-3 concept pages for key themes
   - Write `index.md` with page count and last-updated date

4. **Generate the first watch report** (use `templates/watch-report.md`):
   - Filename: `Watch Reports/Watch Report <DD-MM-YYYY>.md`
   - Fill in **Metadata** (Topic, Geography)
   - Fill in **Signal & Fracture** (one sentence each: key observable development, stress point)
   - **Prediction** = exactly one sentence, plus Probability, Target date, and Confidence
   - **NO "What's New" section** (first report never has it)
   - **Analysis** with relevant subsections (Political, Economic, Military, Technological)
   - **Watch Indicators** — key things to monitor
   - **Probability Triggers** — table of things that would shift probability up/down
   - **Key Sources** — numbered list with links
   - **Disclaimer** and **Notes** (auto-generated footer)
   - **MUST use `---` separators** between ALL sections (see Pitfalls)

Step 4b: **Run the review prompt** (load `references/watch-report-review-prompt.md`):
  - Substitute `{report_path}` with the path to the markdown file written in Step 4
  - Execute the review and capture the JSON output
  - If overall is FAIL: revise the report to address all FAIL issues, then re-run the review
  - If overall is PASS: proceed to Step 5
  - WARN items should be addressed but are not blockers

Step 5: **Generate the PDF** using the shared script:
   ```bash
   /tmp/pdfenv/bin/python3 /root/wiki/watch-report-to-pdf.py \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.md" \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.pdf"
   ```

5b. **Upload PDF to Cloudflare R2:**
   ```bash
   python3 /root/wiki/upload-to-r2.py \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.pdf" \
     "<slug>" "<Topic Name>" "<prediction sentence>" <probability> "<target_date>"
   ```
   This uploads the PDF to the `signal-fracture-content` R2 bucket at `watch-reports/<slug>/<date>.pdf` and updates the `watch-reports/manifest.json` index.
   - The `<prediction sentence>` argument is the full one-sentence prediction passed as a quoted string.
   - The upload script extracts date from the PDF filename, so ensure the filename follows the `Watch Report DD-MM-YYYY.pdf` convention.
   - **See `references/r2-upload.md` for full details on the upload script, manifest format, and common issues.**

5c. **Rebuild the full manifest** after uploading — the upload script updates manifest per-upload, but when regenerating multiple reports (e.g., after a PDF script update), rebuild the entire manifest from scratch:
   ```bash
   cd /root/wiki
   # Parse all watch report markdown files and rebuild manifest.json
   # See references/r2-upload.md for manifest format details
   ```
   The manifest lives at `watch-reports/manifest.json` in the repo root. It uses a nested `topics → reports` structure. See `references/r2-upload.md` for the full format.

5d. **Create the per-topic watch report summary** at `/root/wiki/<slug>/watch-reports-summary.md` (use `templates/watch-reports-summary.md`):
   - Include the **full prediction sentence**, probability, and target date

5e. **Update the global summary** at `/root/wiki/watch-reports-summary.md`:
   - Add a section for this topic with a link to the per-topic summary
   - **Format:** Use an abbreviated prediction (~5-8 words) in the global table — NOT the full sentence. The per-topic summary holds the full sentence.
   - Example row: `| 1 | 06-06-2026 | BARMM election survives but BTA extension required | 70% | Mar 2027 |`

6. **Create cron jobs** using the prompt templates in `references/`:
   - Load `references/weekly-source-monitor-prompt.md`, substitute `{topic_name}`, `{slug}`, `{search_queries}` → create weekly cron job (every 10080 minutes)
   - Load `references/monthly-watch-report-prompt.md`, substitute `{topic_name}`, `{slug}` → create monthly cron job (1st of each month at 12:00 UTC)

7. **Update `_config.yaml`** with the new topic entry (slug, path, search_queries, both cron job IDs).

8. **Commit and push everything:**
   ```bash
   cd /root/wiki
   git add -A
   git commit -m "Add new topic: {topic_name}"
   git push
   ```

9. **Report back tersely:**
   - Topic, path, sources found, entity/concept pages created
   - First report: prediction + probability
   - PDF status, cron job IDs + next run times

### List Topics

**Trigger:** User says "list topics", "show topics", "status", or "check topics".

Read `/root/wiki/_config.yaml` and for each topic show: name, slug, path, creation date, source count, latest watch report, cron job next runs.

### Remove a Topic

**Trigger:** User says "remove topic", "delete topic", "archive topic".

1. Confirm with user
2. Remove both cron jobs
3. Optionally archive folder (rename to `_<slug>-archived/`)
4. Remove entry from `_config.yaml`
5. Commit and push

### Run Now

**Trigger:** User says "run <topic>", "update <topic>", "check <topic>".

Trigger the appropriate cron job early via `cronjob(action='run', job_id=<id>)`.

### Review a Watch Report

**Trigger:** User says "review <topic>", "check <topic> report", or asks for a quality review of a specific report.

1. Read the latest watch report markdown file for the topic
2. Load `references/watch-report-review-prompt.md`
3. Substitute `{report_path}` with the report path
4. Execute the review against all 9 criteria
5. Output the JSON review result
6. If FAIL: suggest specific revisions and offer to apply them
7. If PASS: confirm the report is ready for publication

This can also be run manually on any report markdown file by providing the full path.

## Analytical Framework

### Purpose & Audience

The Watch Report serves two functions simultaneously:

1. **Build a track record.** Every report produces a time-bound, falsifiable prediction. Over time, this track record is the core product — it demonstrates analytical rigor and gives subscribers confidence in the paid offering.
2. **Attract subscribers.** Reports are distributed free as a showcase of analytical quality. The free tier proves the value; the paid offering goes deeper.

**Audience:** Professionals whose decisions are directly impacted by geopolitical developments — hedge fund analysts, private equity teams, logistics operators, corporate strategy — plus serious geopolitics readers. These readers are sophisticated. They've seen enough "analysis" that's really just news summaries with a confident tone. Don't be that.

### What Makes a Strong Prediction

The prediction is the single most important sentence in the report. It's what gets tracked, scored, and remembered. Standards:

- **Falsifiable.** A reader should be able to point to a future date and say "that happened" or "that didn't." "Tensions will remain elevated" is not falsifiable. "Country X will impose export controls on rare earths to Country Y before [date]" is.
- **Time-bound.** Every prediction has a target date. No target date = no track record.
- **Specific enough to matter.** The prediction should be precise enough that getting it right demonstrates real analytical skill, not luck. "Something will happen in Sri Lanka" is worthless. "China will restructure Sri Lanka's bilateral debt on terms that defer principal payments by 18+ months, announced before Q3 2026" is a prediction.
- **One sentence. Always.** No compound predictions, no "either X or Y." If you can't state it in one sentence, you haven't sharpened the thinking enough. Avoid clarifying clauses, be concise.
- **End with the outcome, not the consequence.** The prediction should state what *will happen*, not what it *means* or *leads to*. Example — BAD: "Kazakhstan's diversification will advance, leaving the country caught between Russia and China without a viable third path." GOOD: "Kazakhstan's economic diversification will not advance enough over the next 18 months to provide the country with a viable third path." The prediction sentence ends with the concrete outcome. Do not trail off into implications.

### Signal & Fracture Writing Style

These are the headline takeaways — they must be crisp and direct.

- **Signal:** One sentence. The key observable development or trend. No data points, no clarifiers, no subordinate clauses. Example: "Kazakhstan's tech ecosystem is gaining genuine momentum." NOT "Kazakhstan's tech ecosystem is gaining genuine momentum — top 10 'Rising Stars' in Dealroom.co's 2026 index, a dedicated Ministry of AI, and major international forums."
- **Fracture:** One sentence. The stress point or risk that could disrupt the status quo. Concise, no examples or caveats. Example: "Hydrocarbon reliance, Russian sanctions-era pressure, and an aversion to Western conditionality are forcing Kazakhstan into an untenable position."
- **Prediction:** One sentence. Direct and concise. Avoid "leaving the country increasingly caught between X and Y without a viable third path" — just state what will happen. Example: "Kazakhstan's economic diversification will continue to advance over the next 18 months but not enough to provide the country with a viable third path."
- **Rule:** If a reader only reads Signal, Fracture, and Prediction, they should understand the entire thesis. The Analysis section provides the evidence and reasoning — the headline sections should not duplicate it.

### Prediction Distinctness Rule

**The prediction must NOT restate the Signal or Fracture.** This is the most common failure mode in watch report writing.

- **Signal** = what is happening now (observable development)
- **Fracture** = the tension or stress point (why it matters)
- **Prediction** = what *results* from this dynamic (the outcome, not the conflict)

Test: If the prediction can be rewritten by simply changing the Signal's tense from present to future, it's not a prediction — it's a restatement. Example — BAD: Signal says "Georgia is pursuing transactional relationships," Prediction says "Georgia will continue its strategic drift." GOOD: "The US reset will deepen, giving Georgian Dream enough cover to further delay EU accession reforms."

The prediction should say something the Signal and Fracture *don't* say — it should project the consequence of the dynamic, not describe the dynamic itself.

### Analytical Reasoning: Evidence → Inference → Prediction

The Analysis section is where the thinking lives. Structure it as a causal chain:

1. **What do we know?** (Evidence from sources — cite specific developments, data points, statements)
2. **What does it mean?** (Inference — connect the evidence to the broader dynamic. Why does this development matter? What pressures does it create or relieve?)
3. **What happens next?** (Prediction — the logical conclusion of the inference, stated as the one-sentence prediction)

The Political / Economic / Military / Technological subheadings are lenses, not silos. Use whichever are relevant. A report might be heavy on Economic and light on Military. That's fine. But if all four sections are thin, the analysis isn't ready — go back to sources.

### Source Quality

Not all sources are equal. Weight accordingly:

- **Primary sources first:** Official statements, regulatory filings, legislative actions, central bank data, company disclosures.
- **Specialized reporting second:** Industry-specific outlets, regional experts, trade publications.
- **General news third:** Use for context and timeline, not as the basis for predictions.
- **Discount:** Opinion pieces presented as analysis, unnamed "sources say," anything that can't be traced to a specific origin.

Flag source quality in the Key Sources list. If the prediction rests heavily on a single source, say so — it's a risk factor the reader should know about.

### Confidence Levels

The report includes a confidence rating (Low/Medium/High). Be honest:

- **High:** Multiple independent sources point in the same direction. The causal mechanism is clear. Historical precedent supports it.
- **Medium:** The direction seems right but the timing or magnitude is uncertain. Or the evidence is mostly from one source category.
- **Low:** The prediction is a judgment call based on limited or conflicting signals. Flag this — a low-confidence prediction that lands is more impressive than a high-confidence one that misses.

### Common Analytical Pitfalls

- **Narrative bias.** You've been tracking this topic for months. You have a story in your head about where it's going. Every new source gets filtered through that story. Fight this. Ask: "If I were new to this topic, would this source change my mind?"
- **Recency overweighting.** The last article you read feels more important than it is. Weight by significance, not by timing.
- **Prediction drift.** The temptation to subtly shift the prediction each month to fit new developments. Don't. If the prediction genuinely changed, say so explicitly and explain why. If it hasn't, keep the sentence identical.
- **Justification after the fact.** Writing the prediction first and then reverse-engineering the justification. The justification should be the *reason* for the prediction, not a post-hoc rationalization.
- **False precision.** "67% probability" signals false precision. Use broad bands: 50-60% (coin flip leaning), 60-75% (likely), 75%+ (high confidence). Round numbers.
- **Cross-topic references in Analysis.** Analysis sections must be self-contained. Do not reference concepts, events, projects, or place names from other topics (e.g., "the Georgia dynamic with Anaklia port" in a Kazakhstan report). Readers of one topic may not have read others. Even well-known place names (Anaklia, Hambantota, Gwadar) should be briefly contextualized, not dropped in as assumed knowledge. Explain the concept inline or use generic language.
- **Probability Triggers directional logic.** The Up/Down direction for each trigger is relative to the prediction being TRUE — NOT to the topic being "good" or "bad" in some absolute sense. Up = this event makes the prediction MORE likely. Down = this event makes the prediction LESS likely. Always verify by asking: "If this trigger fires, does my prediction become more or less probable?" A common failure mode is inverting all directions when the prediction is phrased negatively (e.g., "X will NOT happen" vs "X will happen"). The direction follows the prediction's truth value, not the emotional valence of the trigger.
- **Signal & Fracture extraction from Analysis.** When migrating old-format reports (Justification section) to the new template, Signal and Fracture must be concise distillations of the Analysis — not new unsupported claims. The Signal is the key observable trend; the Fracture is the stress point that could disrupt the status quo. Both must be grounded in evidence already presented in the Analysis.

## Migrating Old-Format Reports to New Template

Old-format reports have: `## Justification` with Political/Economic/Military/Technological subsections, bare `## Key Sources`, and a bare footer.

To migrate:
1. Add **Metadata** section at top (Topic, Geography)
2. Add **Signal & Fracture** — extract from existing Analysis content
3. Keep **Prediction** (Probability, Target, Confidence) as-is
4. Rename `## Justification` → `## Analysis` (keep Political/Economic/Military/Technological subsections)
5. Add **Watch Indicators** — 5-7 bullet points of key things to monitor
6. Add **Probability Triggers** — table with Thing/Direction columns (verify directional logic against the prediction)
7. Keep **Key Sources** (add hyperlinks if missing)
8. Add **Disclaimer** section
9. Format **Notes** with `*italic*` markers on separate lines
10. Add `---` separators between ALL sections
11. Regenerate PDF and upload to R2
12. Commit and push

## Key Rules

- **Prediction = exactly one sentence.** Never more.
- **Prediction stays the same** across reports unless the underlying prediction genuinely changes. No rephrasing for variety.
- **First watch report has NO "What's New" section.** Only subsequent reports include it.
- **All topics live in one repo** (`/root/wiki/`, remote: `kent-iscann/signal-fracture-content`).
- **Git auth** via credential helper (no gh CLI). PAT stored in remote URL.
- **PDF script** is shared at `/root/wiki/watch-report-to-pdf.py` (repo root) — do NOT copy per topic. Also mirrored at `/root/.hermes/scripts/watch-report-to-pdf.py` and `/root/.hermes/skills/productivity/pdf-report-generation/scripts/watch-report-to-pdf.py`.
- **PDF venv** at `/tmp/pdfenv/`.
- **R2 upload script** at `/root/wiki/upload-to-r2.py` — uploads PDFs to Cloudflare R2 bucket `signal-fracture-content` at path `watch-reports/<slug>/<date>.pdf` and updates `watch-reports/manifest.json`.
- **Batch R2 upload script** at `/root/wiki/upload-all-r2.py` — reads `_config.yaml`, finds all watch report PDFs, parses metadata from markdown, uploads everything, and builds the manifest. Use this when regenerating multiple reports.
- **Manifest** lives at `watch-reports/manifest.json` in the repo root. Nested `topics → reports` structure. See `references/r2-upload.md`.
- **R2 public base URL:** `https://pub-9a79991ea25c968a06f52c4ecd949ff7.r2.dev/signal-fracture-content/` (includes bucket name, no trailing slash on object keys).
- **Report back tersely.** User prefers direct, concise output — no verbose summaries or "let me know" closings.
- **PDF prediction box** renders: probability, delta indicator, target, and confidence level. Confidence is extracted from `**Confidence:** [Low/Medium/High]` in the Prediction section (not the footer).
- **PDF sections rendered:** Metadata badges (Topic, Geography), Signal & Fracture, Prediction, What's New, Analysis (Political/Economic/Military/Technological), Watch Indicators, Probability Triggers (table), Key Sources (numbered list with links), Disclaimer, Notes.
- **PDF script dark theme** — body font is JetBrains Mono (monospace), headers are Source Serif 4 (serif). Background is dark navy (#05080F), prediction banner is burnt red (#C8463A), accents are gold (#E8A33D). Do NOT swap body to serif.

## Pitfalls

- **Global vs per-topic summary format:** The per-topic `watch-reports-summary.md` stores the full prediction sentence. The global `watch-reports-summary.md` uses an abbreviated (~5-8 word) version in its table. Never put the full sentence in the global table — it breaks the layout.
- **Watch report MUST use `---` separators** between all sections (Metadata, Signal & Fracture, Prediction, What's New, Analysis, Watch Indicators, Probability Triggers, Key Sources, Disclaimer, Notes). The PDF generation script's regex uses these as section delimiters. If `---` is missing, the regex captures everything up to the next `## ` heading, which can swallow multiple sections. **Always use the template at `templates/watch-report.md`** which has the correct `---` structure.
- **PDF script uses shared path** — always reference `/root/wiki/watch-report-to-pdf.py` (repo root), never copy into topic folders. Also mirrored at `/root/.hermes/scripts/watch-report-to-pdf.py`.
- **Verification step** — after generating the first PDF for a new topic, always visually verify (or have the user check) that all sections render correctly: metadata badges, signal & fracture, prediction box, analysis subsections, watch indicators, probability triggers table, key sources, and disclaimer. If any section is missing, check that `---` separators are present in the markdown.
- **Keep summary files in sync** — when creating or updating a watch report, always update both the per-topic `watch-reports-summary.md` and the global `watch-reports-summary.md` at the repo root.
- **Topic name/slug must come from `_config.yaml`** — never hardcode topic names or slugs when calling `upload-to-r2.py`. Folder names on disk (e.g., `sri-lanka-china`) differ from config slugs (e.g., `sri-lankan-financial-relationship-china`). Parse `_config.yaml` using `yaml.safe_load` — do NOT try to parse YAML with string splitting, the indented list format will break custom parsers.
- **R2_PUBLIC_BASE has no trailing slash on object keys** — the base URL ends with `/`. Object keys should NOT start with `/` (e.g., `watch-reports/slug/date.pdf`, not `/watch-reports/...`). Double-slash (`//`) in URLs breaks links.
- **Batch upload** — when regenerating multiple PDFs (e.g., after a PDF script style change), use `/root/wiki/upload-all-r2.py` which reads `_config.yaml`, parses all markdown files, and handles the full upload + manifest cycle. Generate PDFs first, then run the batch upload.
- **PDF script dark theme** — body font is JetBrains Mono (monospace), headers are Source Serif 4 (serif). This is intentional. Background is dark navy (#05080F), prediction banner is burnt red (#C8463A), accents are gold (#E8A33D). Do NOT swap body to serif.
- **Bold/italic in PDF** — the PDF script's `convert_markdown()` function converts `**bold**` and `*italic*` to HTML `<strong>`/`<em>` tags. Do NOT use the old `unbold()` approach — it strips formatting. Bold and italic markdown in What's New and Justification sections will render correctly in the PDF.
- **Confidence parsing** — extract the Confidence value from the **raw markdown** (`pred_raw`) using the regex `\*\*Confidence:\*\*\s*(\w+)`, NOT from `pred_clean` (after `convert_markdown`). The `convert_markdown` function turns `**Confidence:**` into `<strong>Confidence:</strong>`, which breaks simple regex patterns like `Confidence\s*:\s*(\w+)`.
- **Notes trailing asterisks** — when parsing the Notes section, use `strip('*')` (both sides) not `lstrip('*')` (leading only). The markdown `*Report generated: 2026-06-04*` leaves a trailing `*` with lstrip, which renders as a visible asterisk in the PDF footer.
- **Sync skill files to repo after edits** — when SKILL.md or any support file in `~/.hermes/skills/devops/topic-watcher/` is modified, copy the updated files to `/root/wiki/topic-watcher-skill/` and commit/push. This ensures the repo has the latest version for posterity. The repo copy mirrors the skill directory structure exactly.

## Search Quality

- **Disambiguate geographic names.** When researching countries or regions whose names collide with US states, cities, or other common terms (e.g., Georgia, Armenia, Azerbaijan, Congo, Niger, Jordan, Syria, etc.), always include a disambiguating term in search queries: the capital city name ("Tbilisi"), "country," or the specific context (e.g., "Georgia Caucasus"). Without this, Tavily results will be dominated by irrelevant US domestic content.
- **Verify source relevance before extracting.** After running a search, scan the results for relevance before calling `tavily_extract`. If the top results are off-topic, refine the query before proceeding. Don't waste extract calls on irrelevant pages.
