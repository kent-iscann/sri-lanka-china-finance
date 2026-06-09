#!/usr/bin/env python3
"""
Convert a Watch Report markdown file to a styled PDF.
Usage: python3 watch-report-to-pdf.py <input.md> <output.pdf> [previous.md]
  previous.md — optional previous watch report for probability delta comparison
"""
import sys, re, subprocess
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
    m = re.search(r'(\d+)%', text)
    return m.group(1) if m else ''


def extract_prob_delta(text):
    m = re.search(r'\((up|down)\s+from\s+(\d+)%\)', text, re.IGNORECASE)
    if m:
        return m.group(1).lower(), m.group(2)
    return None, None


def parse_list(raw):
    """Parse markdown bullet list into list of strings."""
    items = re.findall(r'^\s*-\s+(.+?)(?=\n\s*-|\Z)', raw, re.MULTILINE | re.DOTALL)
    return [' '.join(item.strip().split()) for item in items]


def parse_table(raw):
    """Parse a markdown table into list of dicts."""
    lines = [l.strip() for l in raw.strip().split('\n') if l.strip()]
    if len(lines) < 2:
        return []
    # Skip header and separator
    headers = [h.strip() for h in lines[0].split('|')[1:-1]]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def parse_watch_report(md_path, prev_md_path=None):
    with open(md_path, 'r') as f:
        content = f.read()

    m = re.search(r'Watch Report (\d{2}-\d{2}-\d{4})', md_path)
    report_date = m.group(1) if m else datetime.now().strftime('%d-%m-%Y')

    # ---- Metadata ----
    meta = {}
    meta_match = re.search(r'## Metadata\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    if meta_match:
        for line in meta_match.group(1).strip().split('\n'):
            mm = re.match(r'\*\*(\w+)\:\*\*\s*(.+)', line.strip())
            if mm:
                meta[mm.group(1).lower()] = mm.group(2).strip()

    # ---- Signal & Fracture ----
    sf = {}
    sf_match = re.search(r'## Signal & Fracture\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    if sf_match:
        for line in sf_match.group(1).strip().split('\n'):
            mm = re.match(r'\*\*Signal:\*\*\s*(.+)', line.strip())
            if mm:
                sf['signal'] = mm.group(1).strip()
            mm = re.match(r'\*\*Fracture:\*\*\s*(.+)', line.strip())
            if mm:
                sf['fracture'] = mm.group(1).strip()

    # ---- Prediction section ----
    pred_match = re.search(r'## Prediction\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    pred_raw = pred_match.group(1).strip() if pred_match else ''
    pred_clean = convert_markdown(pred_raw)

    prob_line = re.search(r'Probability\s*:\s*(.+)', pred_clean)
    prob_text = prob_line.group(1).strip() if prob_line else ''
    probability = extract_prob(prob_text)
    delta_dir, delta_from = extract_prob_delta(prob_text)

    # Delta from previous report
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

    target_m = re.search(r'Target\s*:\s*(.+?)(?:\n|$)', pred_clean)
    target_date = target_m.group(1).strip() if target_m else ''

    # Extract confidence from raw markdown (before convert_markdown)
    conf_m = re.search(r'\*\*Confidence:\*\*\s*(\w+)', pred_raw)
    confidence = conf_m.group(1).strip() if conf_m else ''

    # Prediction sentence = first non-meta paragraph
    cleaned_lines = []
    for line in pred_clean.split('\n'):
        if re.match(r'(Probability|Target|Confidence)\s*:', line, re.IGNORECASE):
            continue
        if line.strip():
            cleaned_lines.append(line.strip())
    full_text = ' '.join(cleaned_lines)
    first_sentence = re.split(r'(?<=[.!?])\s+', full_text)[0].strip()
    first_sentence = re.sub(r'<[^>]+>', '', first_sentence)

    # ---- What's New ----
    whatsnew_match = re.search(r"## What[-\xe2\x80\x99']?s New\s*\n(.*?)(?=\n---|\n## )", content, re.DOTALL)
    whatsnew_items = []
    if whatsnew_match:
        whatsnew_items = parse_list(whatsnew_match.group(1))

    # ---- Analysis ----
    analysis_match = re.search(r'## Analysis\s*\n(.*?)(?=\n---|\n## Watch Indicators)', content, re.DOTALL)
    analysis = []
    if analysis_match:
        just_text = analysis_match.group(1)
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
                analysis.append({'title': title, 'paragraphs': paras})

    # ---- Watch Indicators ----
    wi_match = re.search(r'## Watch Indicators\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    watch_indicators = parse_list(wi_match.group(1)) if wi_match else []

    # ---- Probability Triggers ----
    pt_match = re.search(r'## Probability Triggers\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    prob_triggers = parse_table(pt_match.group(1)) if pt_match else []

    # ---- Key Sources ----
    ks_match = re.search(r'## Key Sources\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    key_sources = []
    if ks_match:
        raw = ks_match.group(1).strip()
        # Parse numbered list with optional links
        for line in raw.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Match "1. [title](url)" or "1. title" or "1. title — url"
            sm = re.match(r'\d+\.\s*(.+)', line)
            if sm:
                entry = sm.group(1).strip()
                # Extract link if present
                link_m = re.match(r'\[(.+?)\]\((.+?)\)', entry)
                if link_m:
                    key_sources.append({'title': link_m.group(1), 'url': link_m.group(2)})
                else:
                    key_sources.append({'title': entry, 'url': ''})

    # ---- Disclaimer ----
    disc_match = re.search(r'## Disclaimer\s*\n(.*?)(?=\n---|\n## )', content, re.DOTALL)
    disclaimer = disc_match.group(1).strip() if disc_match else ''

    # ---- Notes ----
    notes = {}
    notes_match = re.search(r'## Notes\s*\n(.*?)(?=\n---|\Z)', content, re.DOTALL)
    if notes_match:
        for line in notes_match.group(1).strip().split('\n'):
            line = line.strip().strip('*').strip()
            if 'Report generated:' in line:
                notes['generated'] = line.split(':', 1)[1].strip()
            elif 'Sources:' in line:
                notes['sources'] = line.split(':', 1)[1].strip()
            elif 'Methodology:' in line:
                notes['methodology'] = line.split(':', 1)[1].strip()
            elif 'Next review:' in line:
                notes['next_review'] = line.split(':', 1)[1].strip()

    return {
        'report_date': report_date,
        'meta': meta,
        'signal': sf.get('signal', ''),
        'fracture': sf.get('fracture', ''),
        'probability': probability,
        'target_date': target_date,
        'delta_dir': delta_dir,
        'delta_from': delta_from,
        'confidence': confidence,
        'prediction_sentence': first_sentence,
        'whatsnew_items': whatsnew_items,
        'analysis': analysis,
        'watch_indicators': watch_indicators,
        'prob_triggers': prob_triggers,
        'key_sources': key_sources,
        'disclaimer': disclaimer,
        'notes': notes,
    }


def generate_pdf(md_path, output_path, prev_md_path=None):
    s = parse_watch_report(md_path, prev_md_path)

    # Delta indicator
    delta_html = ''
    if s['delta_dir'] and s['delta_from']:
        arrow = '&#9650;' if s['delta_dir'] == 'up' else '&#9660;'
        delta_html = f'<span class="prob-delta">{arrow} from {s["delta_from"]}%</span>'

    # Metadata badges
    meta_html = ''
    if s['meta']:
        badges = []
        for k, v in s['meta'].items():
            badges.append(f'<span class="badge">{v}</span>')
        meta_html = '<div class="meta-badges">' + ''.join(badges) + '</div>'

    # Signal & Fracture
    sf_html = ''
    if s['signal'] or s['fracture']:
        sf_html = '<div class="signal-fracture">'
        if s['signal']:
            sf_html += f'<div class="sf-item"><span class="sf-label">Signal</span><span class="sf-text">{s["signal"]}</span></div>'
        if s['fracture']:
            sf_html += f'<div class="sf-item"><span class="sf-label">Fracture</span><span class="sf-text">{s["fracture"]}</span></div>'
        sf_html += '</div>'

    # What's New
    wn_html = ''
    if s['whatsnew_items']:
        wn_html = '<div class="whats-new"><h3>What&rsquo;s New</h3><ul>'
        for item in s['whatsnew_items']:
            wn_html += f'<li>{item}</li>'
        wn_html += '</ul></div>'

    # Analysis
    analysis_html = ''
    for sub in s['analysis']:
        analysis_html += f'<h3>{sub["title"]}</h3>\n'
        analysis_html += '\n'.join(f'<p>{p}</p>' for p in sub['paragraphs'] if p)

    # Watch Indicators
    wi_html = ''
    if s['watch_indicators']:
        wi_html = '<div class="watch-indicators"><h3>Watch Indicators</h3><ul>'
        for item in s['watch_indicators']:
            wi_html += f'<li>{item}</li>'
        wi_html += '</ul></div>'

    # Probability Triggers
    pt_html = ''
    if s['prob_triggers']:
        pt_html = '<div class="prob-triggers"><h3>Probability Triggers</h3><table><thead><tr>'
        headers = list(s['prob_triggers'][0].keys())
        for h in headers:
            pt_html += f'<th>{h}</th>'
        pt_html += '</tr></thead><tbody>'
        for row in s['prob_triggers']:
            pt_html += '<tr>'
            for h in headers:
                pt_html += f'<td>{row.get(h, "")}</td>'
            pt_html += '</tr>'
        pt_html += '</tbody></table></div>'

    # Key Sources
    ks_html = ''
    if s['key_sources']:
        ks_html = '<div class="key-sources"><h3>Key Sources</h3><ol>'
        for src in s['key_sources']:
            if src['url']:
                ks_html += f'<li><a href="{src["url"]}">{src["title"]}</a></li>'
            else:
                ks_html += f'<li>{src["title"]}</li>'
        ks_html += '</ol></div>'

    # Disclaimer
    disc_html = ''
    if s['disclaimer']:
        disc_html = f'<div class="disclaimer"><p>{s["disclaimer"]}</p></div>'

    # Notes
    notes_html = '<div class="notes">'
    if s['notes'].get('generated'):
        notes_html += f'<p><em>Report generated: {s["notes"]["generated"]}</em></p>'
    if s['notes'].get('sources'):
        notes_html += f'<p><em>Sources: {s["notes"]["sources"]}</em></p>'
    if s['notes'].get('methodology'):
        notes_html += f'<p><em>Methodology: {s["notes"]["methodology"]}</em></p>'
    if s['notes'].get('next_review'):
        notes_html += f'<p><em>Next review: {s["notes"]["next_review"]}</em></p>'
    notes_html += '</div>'

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
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}}
.header-brand {{
    font-size: 10pt;
    font-weight: 300;
    letter-spacing: 0.5px;
    color: #A6B3C2;
}}
.header-date {{
    font-size: 9pt;
    color: #A6B3C2;
    font-weight: 300;
    letter-spacing: 0.5px;
}}

/* ── Metadata Badges ── */
.meta-badges {{
    padding: 4mm 20mm 2mm 20mm;
    display: flex;
    gap: 3mm;
    flex-wrap: wrap;
}}
.badge {{
    background: #5FA8C4;
    color: #05080F;
    font-size: 8pt;
    font-weight: 600;
    padding: 1.5mm 3mm;
    letter-spacing: 0.5px;
}}

/* ── Signal & Fracture ── */
.signal-fracture {{
    margin: 2mm 20mm;
    padding: 5mm 0;
}}
.sf-item {{
    display: flex;
    gap: 4mm;
    margin-bottom: 3mm;
}}
.sf-item:last-child {{
    margin-bottom: 0;
}}
.sf-label {{
    font-size: 9.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #5FA8C4;
    border-left: 2px solid #E8A33D;
    min-width: 22mm;
    flex-shrink: 0;
    padding-left: 5px;
}}
.sf-text {{
    font-size: 9pt;
    line-height: 1.6;
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
    font-size: 48pt;
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
    font-size: 9pt;
    font-weight: 600;
    opacity: 0.9;
    margin-top: 2mm;
    display: block;
}}
.prob-target {{
    font-size: 9pt;
    font-weight: 600;
    opacity: 0.8;
    margin-top: 3mm;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}}
.prob-confidence {{
    font-size: 9pt;
    font-weight: 600;
    opacity: 0.8;
    margin-top: 2mm;
    text-transform: uppercase;
    letter-spacing: 1.5px;
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
    padding: 8mm 20mm 6mm 20mm;
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

/* ── Watch Indicators ── */
.watch-indicators {{
    padding: 4mm 20mm;
}}
.watch-indicators h3 {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4mm;
    color: #E8E6DF;
    font-family: 'Source Serif 4', sans-serif;
}}
.watch-indicators ul {{
    list-style-type: square;
    padding-left: 5mm;
    margin: 0;
}}
.watch-indicators li {{
    font-size: 9pt;
    line-height: 1.7;
    color: #A6B3C2;
    margin-bottom: 2mm;
    padding-left: 2mm;
}}

/* ── Probability Triggers ── */
.prob-triggers {{
    padding: 4mm 20mm;
}}
.prob-triggers h3 {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4mm;
    color: #E8E6DF;
    font-family: 'Source Serif 4', sans-serif;
}}
.prob-triggers table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 8.5pt;
}}
.prob-triggers th {{
    background: #0A1426;
    color: #5FA8C4;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 2.5mm 3mm;
    text-align: left;
    border-bottom: 2px solid #1E3A5F;
}}
.prob-triggers td {{
    padding: 2.5mm 3mm;
    border-bottom: 1px solid #0F1D32;
    color: #A6B3C2;
    line-height: 1.5;
}}
.prob-triggers tr:nth-child(even) td {{
    background: #060D18;
}}

/* ── Key Sources ── */
.key-sources {{
    padding: 4mm 20mm;
}}
.key-sources h3 {{
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 4mm;
    color: #E8E6DF;
    font-family: 'Source Serif 4', sans-serif;
}}
.key-sources ol {{
    padding-left: 5mm;
    margin: 0;
}}
.key-sources li {{
    font-size: 8.5pt;
    line-height: 1.6;
    color: #A6B3C2;
    margin-bottom: 2mm;
}}
.key-sources a {{
    color: #5FA8C4;
    text-decoration: none;
}}
.key-sources a:hover {{
    text-decoration: underline;
}}

/* ── Disclaimer ── */
.disclaimer {{
    padding: 4mm 20mm;
    border-top: 1px solid #1E3A5F;
}}
.disclaimer p {{
    font-size: 7.5pt;
    line-height: 1.6;
    color: #6B7B8D;
    font-style: italic;
}}

/* ── Notes ── */
.notes {{
    padding: 2mm 20mm 6mm 20mm;
}}
.notes p {{
    font-size: 7.5pt;
    line-height: 1.5;
    color: #6B7B8D;
    margin-bottom: 1mm;
}}
</style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <span class="header-title">Watch Report | </span>
        <span class="header-brand">Signal &amp; Fracture by IScann Group</span>
    </div>
    <div class="header-date">{s['report_date']}</div>
</div>

{meta_html}

{sf_html}

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

{wn_html}

<div class="analysis">
    <h2>Analysis</h2>
    {analysis_html}
</div>

{wi_html}

{pt_html}

{ks_html}

{disc_html}

{notes_html}

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
