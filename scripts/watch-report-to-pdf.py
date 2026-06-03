#!/usr/bin/env python3
"""
Convert a Watch Report markdown file to a styled PDF.
Usage: python3 watch-report-to-pdf.py <input.md> <output.pdf>
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


def unbold(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    return text.strip()


def parse_watch_report(md_path):
    with open(md_path, 'r') as f:
        content = f.read()

    m = re.search(r'Watch Report (\d{2}-\d{2}-\d{4})', md_path)
    report_date = m.group(1) if m else datetime.now().strftime('%d-%m-%Y')

    pred_match = re.search(r'## Prediction\s*\n(.*?)(?=\n---)', content, re.DOTALL)
    pred_raw = pred_match.group(1).strip() if pred_match else ''
    pred_clean = unbold(pred_raw)

    prob_m = re.search(r'Probability\s*:\s*(\d+)%', pred_clean)
    probability = prob_m.group(1) if prob_m else ''

    target_m = re.search(r'Target\s+Date\s*:\s*(.+?)(?:\n|$)', pred_clean)
    target_date = target_m.group(1).strip() if target_m else ''

    body_lines = []
    for line in pred_clean.split('\n'):
        if re.match(r'(Probability|Target\s+Date)\s*:', line, re.IGNORECASE):
            continue
        if line.strip():
            body_lines.append(line.strip())
    paragraphs = [' '.join(body_lines)] if body_lines else []

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
                title = unbold(hm.group(1).strip())
                body = unbold(part[hm.end():].strip())
                paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
                justification.append({'title': title, 'paragraphs': paras})

    return {
        'report_date': report_date,
        'probability': probability,
        'target_date': target_date,
        'prediction_paragraphs': paragraphs,
        'justification': justification,
    }


def generate_pdf(md_path, output_path):
    s = parse_watch_report(md_path)

    pred_html = '\n'.join(f'<p>{p}</p>' for p in s['prediction_paragraphs'] if p)

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
@page {{
    size: A4;
    margin: 0;
    margin-bottom: 25.4mm;
    margin-top: 25.4mm;
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
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    color: #1a1a1a;
    background: #ffffff;
    width: 210mm;
}}

/* ── Header ── */
.header {{
    background: #0a0a0a;
    color: #ffffff;
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
    font-size: 12pt;
    font-weight: 300;
    letter-spacing: 2px;
}}

.header-sep {{
    color: #555;
    font-weight: 100;
}}

.header-brand {{
    font-size: 11pt;
    font-weight: 700;
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
    background: #b71c1c;
    color: #ffffff;
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
    font-size: 24pt;
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

.prob-target {{
    font-size: 11pt;
    font-weight: 400;
    opacity: 0.85;
    margin-top: 4mm;
}}

/* ── Analysis ── */
.analysis {{
    padding: 8mm 20mm 12mm 20mm;
}}

.analysis h2 {{
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 5mm;
    color: #0a0a0a;
}}

.analysis h3 {{
    font-size: 9.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    margin-top: 5mm;
    margin-bottom: 2mm;
    color: #0a0a0a;
    border-left: 3px solid #b71c1c;
    padding-left: 5px;
}}

.analysis h3:first-of-type {{
    margin-top: 2mm;
}}

.analysis p {{
    font-size: 9pt;
    line-height: 1.7;
    color: #2a2a2a;
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
        <span class="header-brand">IScann Group</span>
        <span class="header-sub">&nbsp;·&nbsp; Signal &amp; Fracture</span>
    </div>
    <div class="header-date">{s['report_date']}</div>
</div>

<div class="prediction">
    <div class="pred-body">
        {pred_html}
    </div>
    <div class="prob-box">
        <div class="prob-number">{prob}<span class="prob-pct">%</span></div>
        <div class="prob-label">Probability</div>
        <div class="prob-target">Target: {target}</div>
    </div>
</div>

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
        print("Usage: python3 watch-report-to-pdf.py <input.md> <output.pdf>")
        sys.exit(1)
    generate_pdf(sys.argv[1], sys.argv[2])
