[IMPORTANT: You are running as a scheduled cron job. DELIVERY: Your final response will be automatically delivered to the user — do NOT use send_message or try to deliver the output yourself. Just produce your report/output as your final response and the system handles the rest. SILENT: If there is genuinely nothing new to report, respond with exactly "[SILENT]" (nothing else) to suppress delivery. Never combine [SILENT] with content — either report your findings normally, or say [SILENT] and nothing more.]

You are maintaining a research wiki on {topic_name}, cloned at /root/wiki on GitHub (repo: kent-iscann/sri-lanka-china-finance). This topic lives in /root/wiki/{slug}/. Use the git credential helper for auth (no gh CLI).

TASK: Review the wiki corpus and create a new watch report or update the latest one.

Step 1: Read the full wiki corpus in /root/wiki/{slug}/ (index, sources, timeline, entities, concepts, latest watch report).

Step 2: Identify what has changed since the last watch report.

Step 3: Decide: new report (3+ new sources or major development) or update existing.

Step 4: Write/update the watch report at /root/wiki/{slug}/Watch Reports/Watch Report <DD-MM-YYYY>.md:
  - Prediction: exactly ONE sentence. Keep it identical to previous reports unless the prediction itself has genuinely changed.
  - Probability and target date
  - "What's New" section: ONLY if this is NOT the first report. Use bullet points.
  - Justification: Political, Economic, Military, Technological analysis
  - Key Sources

Step 5: Update /root/wiki/{slug}/index.md.

Step 6: Append to /root/wiki/{slug}/log.md.

Step 7: Generate PDF using the shared script:
  /tmp/pdfenv/bin/python3 /root/.hermes/scripts/watch-report-to-pdf.py "<md path>" "<pdf path>"
  If weasyprint is missing: /tmp/pdfenv/bin/pip install weasyprint

Step 8: Commit and push:
  cd /root/wiki
  git add -A
  git commit -m "Watch Report update ({slug}): [summary]"
  git push

Step 9: Report back with key changes, probability shift, and whether PDF succeeded.

IMPORTANT RULES:
- Prediction = exactly one sentence. Never rephrase for variety.
- First report has NO "What's New" section.
- Use the shared PDF script at /root/.hermes/scripts/watch-report-to-pdf.py — do not copy per-topic.
- Quality over quantity on sources.
