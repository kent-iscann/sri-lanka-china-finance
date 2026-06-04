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
   - Prediction = exactly one sentence
   - **NO "What's New" section** (first report never has it)
   - **MUST use `---` separators** between sections (see Pitfalls)

5. **Generate the PDF** using the shared script:
   ```bash
   /tmp/pdfenv/bin/python3 /root/wiki/watch-report-to-pdf.py \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.md" \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.pdf"
   ```

5b. **Create the watch report summary** at `/root/wiki/<slug>/watch-reports-summary.md` (use `templates/watch-reports-summary.md`):
   - Include the full prediction sentence, probability, and target date

5c. **Create the global summary** at `/root/wiki/watch-reports-summary.md`:
   - Add a section for this topic with a compact table row linking to the topic's detailed summary

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
- **One sentence. Always.** No compound predictions, no "either X or Y." If you can't state it in one sentence, you haven't sharpened the thinking enough.

### Analytical Reasoning: Evidence → Inference → Prediction

The Justification section is where the thinking lives. Structure it as a causal chain:

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

## Key Rules

- **Prediction = exactly one sentence.** Never more.
- **Prediction stays the same** across reports unless the underlying prediction genuinely changes. No rephrasing for variety.
- **First watch report has NO "What's New" section.** Only subsequent reports include it.
- **All topics live in one repo** (`/root/wiki/`, remote: `kent-iscann/signal-fracture-content`).
- **Git auth** via credential helper (no gh CLI). PAT stored in remote URL.
- **PDF script** is shared at `/root/wiki/watch-report-to-pdf.py` (repo root) — do NOT copy per topic. Also mirrored at `/root/.hermes/scripts/watch-report-to-pdf.py`.
- **PDF venv** at `/tmp/pdfenv/`.
- **Report back tersely.** User prefers direct, concise output — no verbose summaries or "let me know" closings.

## Pitfalls

- **Watch report MUST use `---` separators** between sections (Prediction, What's New, Justification, Key Sources). The PDF generation script's regex `(?=\\n---|\\n## )` uses these as section delimiters. If `---` is missing, the prediction section regex captures everything up to the next `## ` heading, which can swallow the entire report into the prediction field, leaving the prediction box blank in the rendered PDF. **Always use the template at `templates/watch-report.md`** which has the correct `---` structure.
- **PDF script uses shared path** — always reference `/root/wiki/watch-report-to-pdf.py` (repo root), never copy into topic folders. Also mirrored at `/root/.hermes/scripts/watch-report-to-pdf.py`.
- **Verification step** — after generating the first PDF for a new topic, always visually verify (or have the user check) that the prediction section renders correctly. If the prediction box is blank, check that `---` separators are present in the markdown.
- **Keep summary files in sync** — when creating or updating a watch report, always update both the per-topic `watch-reports-summary.md` and the global `watch-reports-summary.md` at the repo root.