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
| `templates/index.md` | Starter index.md for a new topic |
| `templates/sources.md` | Starter sources.md |
| `templates/timeline.md` | Starter timeline file |
| `templates/watch-report.md` | Starter watch report with correct structure |

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
   └── Watch Reports/
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

5. **Generate the PDF** using the shared script:
   ```bash
   /tmp/pdfenv/bin/python3 /root/.hermes/scripts/watch-report-to-pdf.py \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.md" \
     "/root/wiki/<slug>/Watch Reports/Watch Report <DD-MM-YYYY>.pdf"
   ```

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

## Key Rules

- **Prediction = exactly one sentence.** Never more.
- **Prediction stays the same** across reports unless the underlying prediction genuinely changes. No rephrasing for variety.
- **First watch report has NO "What's New" section.** Only subsequent reports include it.
- **All topics live in one repo** (`/root/wiki/`, remote: `kent-iscann/sri-lanka-china-finance`).
- **Git auth** via credential helper (no gh CLI). PAT stored in remote URL.
- **PDF script** is shared at `/root/.hermes/scripts/watch-report-to-pdf.py` — do NOT copy per topic.
- **PDF venv** at `/tmp/pdfenv/`.
- **Report back tersely.** User prefers direct, concise output — no verbose summaries or "let me know" closings.
