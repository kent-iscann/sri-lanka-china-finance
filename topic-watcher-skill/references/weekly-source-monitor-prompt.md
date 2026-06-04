[IMPORTANT: You are running as a scheduled cron job. DELIVERY: Your final response will be automatically delivered to the user — do NOT use send_message or try to deliver the output yourself. Just produce your report/output as your final response and the system handles the rest. SILENT: If there is genuinely nothing new to report, respond with exactly "[SILENT]" (nothing else) to suppress delivery. Never combine [SILENT] with content — either report your findings normally, or say [SILENT] and nothing more.]

You are maintaining a research wiki on {topic_name}, cloned at /root/wiki on GitHub (repo: kent-iscann/sri-lanka-china-finance). This topic lives in /root/wiki/{slug}/. Use the git credential helper for auth (no gh CLI).

TASK: Search for new sources on {topic_name} and add any substantive new findings to the wiki.

Step 1: Read /root/wiki/{slug}/sources.md to understand what sources already exist.

Step 2: Run the following searches using the tavily_search tool:
{search_queries, one per line, numbered}

For each search, use time_range="month" and max_results=5.

Step 3: For each promising new source, use tavily_extract to get full content.

Step 4: For each substantive new source:
  a. Summarize key findings in 2-3 sentences
  b. Append to /root/wiki/{slug}/sources.md
  c. Update timeline if needed
  d. Update relevant entity/concept pages
  e. Update /root/wiki/{slug}/index.md

Step 5: Append entry to /root/wiki/{slug}/log.md:
  ## [YYYY-MM-DD] ingest | [source title]
  - [Brief summary]

Step 6: Commit and push:
  cd /root/wiki
  git add -A
  git commit -m "Weekly source update ({slug}): [summary]"
  git push

Step 7: Report back with number of new sources and summary of each.

IMPORTANT: Only add sources with real, substantive new information. Quality over quantity.
