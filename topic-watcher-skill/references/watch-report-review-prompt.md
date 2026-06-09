# Watch Report Review Prompt

You are reviewing a watch report for quality and consistency BEFORE it is published. Read the report markdown file at the path below and evaluate it against each criterion. Output your findings as structured JSON.

## Report to review
{report_path}

## Review Criteria

Evaluate each criterion. For each, output: PASS, FAIL, or WARN. If FAIL or WARN, include a specific explanation and suggested fix.

### 1. Prediction Distinctness
- The prediction must NOT be a restatement of the Signal or Fracture.
- Test: If you can rewrite the prediction by changing the Signal's tense from present to future, it's a restatement.
- The prediction must project an OUTCOME — what *results* from the dynamic — not describe the dynamic itself.

### 2. Prediction Quality
- Exactly one sentence. No compound predictions, no "either X or Y."
- Falsifiable: a reader can point to the target date and verify whether it happened.
- Time-bound: has a specific target date.
- Specific enough that getting it right demonstrates analytical skill.
- Ends with the outcome, not trailing into implications or consequences.

### 3. Signal & Fracture Quality
- Signal: one sentence, observable development, no data points or clarifiers.
- Fracture: one sentence, stress point, no examples or caveats.
- Both are concise and direct.

### 4. Analysis Supports Prediction
- The Analysis sections (Political, Economic, Military, Technological) provide evidence and reasoning that logically lead to the prediction.
- No major analytical gaps — if a section is thin, flag it.
- No cross-topic references (place names, projects, or concepts from other topics without context).

### 5. Source Quality
- Sources are numbered and include hyperlinks.
- Source quality hierarchy is respected (primary > specialized > general).
- No over-reliance on a single source for the core prediction.

### 6. Watch Indicators & Probability Triggers
- Watch Indicators: 5-7 bullet points of key things to monitor.
- Probability Triggers: table with Thing/Direction columns.
- Trigger directional logic is correct: Up = makes prediction MORE likely, Down = makes prediction LESS likely.
- Triggers are specific and actionable, not vague.

### 7. Confidence Level
- Confidence (Low/Medium/High) is stated and matches the evidence quality.
- If confidence is High, multiple independent sources should support the prediction.
- If confidence is Low, this should be flagged as a risk.

### 8. Formatting
- All required sections present: Metadata, Signal & Fracture, Prediction, [What's New if 2nd+], Analysis, Watch Indicators, Probability Triggers, Key Sources, Disclaimer, Notes.
- `---` separators between all sections.
- Notes use `*italic*` markers on separate lines.
- No trailing asterisks on Notes lines.

### 9. What's New (if applicable)
- Only present on 2nd+ reports.
- Bullet points describe specific developments, not vague summaries.
- Probability changes are explained.

## Output Format

Respond with a JSON object:

```json
{
  "overall": "PASS | FAIL",
  "criteria": {
    "prediction_distinctness": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "prediction_quality": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "signal_fracture_quality": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "analysis_supports_prediction": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "source_quality": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "watch_indicators_triggers": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "confidence_level": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "formatting": {"status": "PASS | FAIL | WARN", "detail": "..."},
    "whats_new": {"status": "PASS | FAIL | WARN | N/A", "detail": "..."}
  },
  "issues": [
    {
      "criterion": "...",
      "severity": "FAIL | WARN",
      "description": "...",
      "suggested_fix": "..."
    }
  ]
}
```

If overall is PASS, the report can proceed to PDF generation. If overall is FAIL, the report must be revised before proceeding. WARN items should be addressed but are not blockers.
