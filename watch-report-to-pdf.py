#!/usr/bin/env python3
"""
Convert a Watch Report markdown file to a styled PDF.
Usage: python3 watch-report-to-pdf.py <input.md> <output.pdf> [previous.md]
  previous.md — optional previous watch report for probability delta comparison
"""
import sys
import re
import subprocess
from datetime import datetime

try:
    from weasyprint import HTML
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint",
                          "-q", "--break-system-packages"])
    from weasyprint import HTML


def convert_markdown(text):
    """Convert markdown bold/italic to HTML tags."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text.strip()


def extract_prob(text):
    """Extract probability number from text like '70%' or '70% (up from 65%)'."""
    m = re.search(r'(\d+)%', text)
    return m.group(1) if m else ''


def extract_prob_delta(text):
    """Extract delta info like '(up from 65%)' or '(down from 65%)'."""
    m = re.search(r'\((up|down)\s+from\s+(\d+)%\)', text, re.IGNORECASE)
    if m:
        return m.group(1).lower(), m.group(2)
    return None, None


def parse_watch_report(md_path, prev_md_path=None):
    with open(md_path, 'r') as f:
        content = f.read()

    m = re.search(r'Watch Report (\d{2}-\d{2}-\d{4})', md_path)
    report_date = m.group(1) if m else datetime.now().strftime('%d-%m-%Y')

    # ---- Prediction section ----
    pred_match = re.search(r'## Prediction\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    pred_raw = pred_match.group(1).strip() if pred_match else ''
    pred_clean = convert_markdown(pred_raw)

    # Extract probability
    prob_line = re.search(r'Probability\s*:\s*(.+)', pred_clean)
    prob_text = prob_line.group(1).strip() if prob_line else ''
    probability = extract_prob(prob_text)
    delta_dir, delta_from = extract_prob_delta(prob_text)

    # If no inline delta, check previous report for comparison
    if not delta_dir and prev_md_path:
        try:
            with open(prev_md_path, 'r') as f:
                prev_content = f.read()
            prev_pred = re.search(r'## Prediction\s*\n(.*?)(?=\n---)', prev_content, re.DOTALL)
            if prev_pred:
                prev_clean = convert_markdown(prev_pred.group(1))
                prev_prob_m = re.search(r'Probability\s*:\s*(.+)', prev_clean)
                if prev_prob_m:
                    prev_prob = extract_prob(prev_prob_m.group(1))
                    if prev_prob and probability:
                        diff = int(probability) - int(prev_prob)
                        if diff > 0:
                            delta_dir, delta_from = "up", prev_prob
                        elif diff < 0:
                            delta_dir, delta_from = "down", prev_prob
        except (FileNotFoundError, ValueError):
            pass

    # Extract target date
    target_m = re.search(r'Target\s+Date\s*:\s*(.+?)(?:\n|$)', pred_clean)
    target_date = target_m.group(1).strip() if target_m else ''

    # Extract confidence level from end of document
    conf_m = re.search(r'\*Confidence level:\s*([LowMediumHigh]+)\*', content)
    confidence = conf_m.group(1).strip() if conf_m else ''

    # Prediction statement = first sentence only (up to first period within the first line/paragraph)
    # Remove meta lines first
    cleaned_lines = []
    for line in pred_clean.split('\n'):
        if re.match(r'(Probability|Target\s+Date)\s*:', line, re.IGNORECASE):
            continue
        if line.strip():
            cleaned_lines.append(line.strip())

    full_text = ' '.join(cleaned_lines)
    # Take first sentence
    first_sentence = re.split(r'(?<=[.!?])\s+', full_text)[0].strip()
    # Strip any HTML tags from the prediction sentence (it's rendered as plain text)
    first_sentence = re.sub(r'<[^>]+>', '', first_sentence)

    # ---- What's New section ----
    whatsnew_match = re.search(r"## What[-\xe2\x80\x99']?s New\s*\n(.*?)(?=\n---|\n## )", content, re.DOTALL)
    whatsnew_html = ''
    if whatsnew_match:
        raw = convert_markdown(whatsnew_match.group(1).strip())
        whatsnew_html = '<div class="whats-new">\n'
        whatsnew_html += '<h3>What&rsquo;s New</h3>\n'
        # Check if content uses bullet points
        if raw.startswith('- '):
            items = re.findall(r'^\s*-\s+(.+?)(?=\n\s*-|\Z)', raw, re.MULTILINE | re.DOTALL)
            whatsnew_html += '<ul>\n'
            for item in items:
                item_text = ' '.join(item.strip().split())
                whatsnew_html += f'<li>{item_text}</li>\n'
            whatsnew_html += '</ul>\n'
        else:
            paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
            for p in paragraphs:
                whatsnew_html += f'<p>{p}</p>\n'
        whatsnew_html += '</div>'

    # ---- Justification (Analysis) section ----
    just_match = re.search(r'## Justification\s*\n(.*?)(?=\n---|\n## Key Sources)', content, re.DOTALL)
    justification = []
    if just_match:
        just_text = just_match.group(1)
        sub_parts = re.split(r'(?=^### )', just_text, flags=re.MULTILINE)
        for part in sub_parts:
            part = part.strip()
            if not part:
                continue
            hm = re.match(r'^### (.+?)\s*\n', part, re.MULTILINE)
            if hm:
                title = convert_markdown(hm.group(1).strip())
                body = convert_markdown(part[hm.end():].strip())
                paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
                justification.append({'title': title, 'paragraphs': paras})

    return {
        'report_date': report_date,
        'probability': probability,
        'target_date': target_date,
        'delta_dir': delta_dir,
        'delta_from': delta_from,
        'prediction_sentence': first_sentence,
        'whatsnew_html': whatsnew_html,
        'justification': justification,
        'confidence': confidence,
    }


def generate_pdf(md_path, output_path, prev_md_path=None):
    s = parse_watch_report(md_path, prev_md_path)

    # Probability delta indicator
    delta_html = ''
    if s['delta_dir'] and s['delta_from']:
        arrow = '&#9650;' if s['delta_dir'] == 'up' else '&#9660;'
        delta_html = f'<span class="prob-delta">{arrow} from {s["delta_from"]}%</span>'

    # Analysis HTML
    analysis_html = ''
    for sub in s['justification']:
        analysis_html += f'<h3>{sub["title"]}</h3>\n'
        analysis_html += '\n'.join(f'<p>{p}</p>' for p in sub['paragraphs'] if p)

    prob = s['probability']
    target = s['target_date']

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url("https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,200..900;1,8..60,200..900&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap");
@page {{
    size: A4;
    margin: 0;
    margin-bottom: 25.4mm;
    margin-top: 25.4mm;
    background: #05080F;
}}

@page :first {{
    margin-top: 0;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'JetBrains Mono', Arial, sans-serif;
    color: #A6B3C2;
    background: #05080F;
    width: 210mm;
}}

/* ── Header ── */
.header {{
    background: #001C3C;
    color: #E8E6DF;
    padding: 0 20mm;
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 12mm;
}}

.header-left {{
    display: flex;
    align-items: baseline;
    gap: 7px;
    white-space: nowrap;
}}

.header-title {{
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}}

.header-sep {{
    color: #555;
    font-weight: 100;
}}

.header-brand {{
    font-size: 10pt;
    font-weight: 300;
    letter-spacing: 0.5px;
}}

.header-sub {{
    font-size: 6pt;
    font-weight: 400;
    color: #999;
    letter-spacing: 1px;
    text-transform: uppercase;
}}

.header-date {{
    font-size: 9pt;
    color: #bbb;
    font-weight: 300;
    letter-spacing: 0.5px;
}}

/* ── Prediction banner ── */
.prediction {{
    background: #C8463A;
    color: #E8E6DF;
    display: flex;
    justify-content: space-between;
    align-items: center;
    min-height: 68mm;
    padding: 10mm 20mm;
}}

.pred-body {{
    flex: 1;
    padding-right: 10mm;
}}

.pred-body p {{
    font-size: 14pt;
    font-weight: 500;
    line-height: 1.6;
}}

.prob-box {{
    text-align: right;
    flex-shrink: 0;
}}

.prob-number {{
    font-size: 72pt;
    font-weight: 300;
    line-height: 1;
}}

.prob-pct {{
    font-size: 22pt;
    font-weight: 300;
    vertical-align: super;
}}

.prob-label {{
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    opacity: 0.8;
    margin-top: 3mm;
}}

.prob-delta {{
    font-size: 10pt;
    font-weight: 600;
    opacity: 0.9;
    margin-top: 2mm;
    display: block;
}}

.prob-target {{
    font-size: 11pt;
    font-weight: 400;
    opacity: 0.85;
    margin-top: 3mm;
}}

.prob-confidence {{
    font-size: 11pt;
    font-weight: 400;
    opacity: 0.85;
    margin-top: 2mm;
}}

/* ── What's New ── */
.whats-new {{
    background: #0A1426;
    border-left: 4px solid #E8A33D;
    padding: 6mm 20mm;
}}

.whats-new h3 {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 5mm;
    color: #E8E6DF;
    font-family: 'Source Serif 4', sans-serif;
}}

.whats-new p {{
    font-size: 9pt;
    line-height: 1.7;
    color: #A6B3C2;
    margin-bottom: 2mm;
}}

.whats-new p:last-child {{
    margin-bottom: 0;
}}

.whats-new ul {{
    list-style-type: square;
    padding-left: 5mm;
    margin: 0;
}}

.whats-new li {{
    font-size: 9pt;
    line-height: 1.7;
    color: #A6B3C2;
    margin-bottom: 3mm;
    padding-left: 2mm;
}}

.whats-new li:last-child {{
    margin-bottom: 0;
}}

/* ── Analysis ── */
.analysis {{
    padding: 8mm 20mm 12mm 20mm;
}}

.analysis h2 {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 5mm;
    color: #E8E6DF;
    font-family: 'Source Serif 4', sans-serif;
}}

.analysis h3 {{
    font-size: 9.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-top: 5mm;
    margin-bottom: 2mm;
    color: #5FA8C4;
    border-left: 2px solid #E8A33D;
    padding-left: 5px;
    font-family: 'JetBrains Mono', sans-serif;
}}

.analysis h3:first-of-type {{
    margin-top: 2mm;
}}

.analysis p {{
    font-size: 9pt;
    line-height: 1.7;
    color: #A6B3C2;
    margin-bottom: 2.5mm;
    text-align: justify;
}}

.analysis p:last-child {{
    margin-bottom: 0;
}}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="header-left">
        <span class="header-title">Watch Report</span>
        <span class="header-sep">|</span>
        <span class="header-brand">Signal & Fracture by IScann Group</span>
    </div>
    <div class="header-date">{s['report_date']}</div>
</div>

<!-- Prediction -->
<div class="prediction">
    <div class="pred-body">
        <p>{s['prediction_sentence']}</p>
    </div>
    <div class="prob-box">
        <div class="prob-number">{prob}<span class="prob-pct">%</span></div>
        <div class="prob-label">Probability</div>
        {delta_html}
        <div class="prob-target"><strong>Target:</strong> {target}</div>
        <div class="prob-confidence"><strong>Confidence:</strong> {s['confidence']}</div>
    </div>
</div>

{ s['whatsnew_html'] }

<!-- Analysis -->
<div class="analysis">
    <h2>Analysis</h2>
    {analysis_html}
</div>

</body>
</html>"""

    HTML(string=html).write_pdf(output_path)
    print(f"PDF generated: {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 watch-report-to-pdf.py <input.md> <output.pdf> [previous.md]")
        sys.exit(1)
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    generate_pdf(sys.argv[1], sys.argv[2], prev)
