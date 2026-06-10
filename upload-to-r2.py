#!/usr/bin/env python3
"""
Upload a Watch Report PDF to Cloudflare R2 and update the manifest.
Uses boto3 (S3-compatible) — no AWS CLI required.

Usage:
  python3 upload-to-r2.py --md-path <report.md> <pdf_path> <topic_slug> <topic_name>
  python3 upload-to-r2.py <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>

  --md-path  Parse the Prediction section from the markdown file automatically.
             When used, prediction/probability/target_date are not needed as args.
"""
import json, sys, os, re, subprocess, traceback
from datetime import datetime
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3", "-q", "--break-system-packages"])
    import boto3
    from botocore.config import Config

# R2 Configuration
R2_ACCOUNT_ID = "9a79991ea25c968a06f52c4ecd949ff7"
R2_ACCESS_KEY_ID = "56afe22c0c7a5e9ac25cdecd1f363b31"
R2_SECRET_ACCESS_KEY = "bc810ece1600642490e6312097c85487b11bcd6fffa6f09841a259a17a362ef0"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_BUCKET = "signal-fracture-content"
R2_PREFIX = "watch-reports"
R2_PUBLIC_BASE = f"https://pub-70e08d62c8314675b40c42f0fe4be6fb.r2.dev"

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)


def upload_pdf(pdf_path, topic_slug, date_str):
    object_key = f"{R2_PREFIX}/{topic_slug}/{date_str}.pdf"
    print(f"Uploading: {object_key}")
    try:
        s3.upload_file(pdf_path, R2_BUCKET, object_key, ExtraArgs={"ContentType": "application/pdf"})
        url = f"{R2_PUBLIC_BASE}/{object_key}"
        print(f"Uploaded: {url}")
        return url
    except Exception as e:
        print(f"Upload failed: {e}")
        return None


def update_manifest(topic_slug, topic_name, date_str, filename, url, prediction, probability, target_date):
    manifest_key = f"{R2_PREFIX}/manifest.json"
    local_manifest = "/tmp/watch-reports-manifest.json"

    # Download existing manifest
    try:
        s3.download_file(R2_BUCKET, manifest_key, local_manifest)
        with open(local_manifest) as f:
            manifest = json.load(f)
        # Migrate old flat format to new nested format
        if "reports" in manifest and "topics" not in manifest:
            old_reports = manifest.pop("reports", [])
            topics_map = {}
            for r in old_reports:
                slug = r.pop("slug", "")
                topic_name = r.pop("topic", slug)
                if slug not in topics_map:
                    topics_map[slug] = {"topic": topic_name, "slug": slug, "reports": []}
                topics_map[slug]["reports"].append(r)
            manifest["topics"] = sorted(topics_map.values(), key=lambda t: t["slug"])
    except Exception:
        manifest = {"topics": [], "updated_at": ""}

    # Find or create topic entry
    topic_entry = None
    for t in manifest["topics"]:
        if t["slug"] == topic_slug:
            topic_entry = t
            break
    if topic_entry is None:
        topic_entry = {
            "topic": topic_name,
            "slug": topic_slug,
            "reports": [],
        }
        manifest["topics"].append(topic_entry)

    # Remove existing report for same date
    topic_entry["reports"] = [
        r for r in topic_entry["reports"] if r["date"] != date_str
    ]

    # Add new report
    topic_entry["reports"].append({
        "date": date_str,
        "filename": filename,
        "url": url,
        "prediction": prediction,
        "probability": probability,
        "target_date": target_date,
        "uploaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

    # Sort reports within topic by date descending
    topic_entry["reports"].sort(key=lambda r: r["date"], reverse=True)

    # Sort topics alphabetically
    manifest["topics"].sort(key=lambda t: t["slug"])

    manifest["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Upload manifest
    with open(local_manifest, "w") as f:
        json.dump(manifest, f, indent=2)

    try:
        s3.upload_file(local_manifest, R2_BUCKET, manifest_key, ExtraArgs={"ContentType": "application/json"})
        print(f"Manifest updated: {len(manifest['topics'])} topics")
        os.remove(local_manifest)
        return True
    except Exception as e:
        print(f"Manifest upload failed: {e}")
        traceback.print_exc()
        return False


def parse_prediction(md_path):
    """Parse the Prediction section from a Watch Report markdown file.
    Returns (prediction_text, probability_int, target_date_str).
    Handles **bold:** markdown markers.
    """
    with open(md_path) as f:
        md = f.read()
    pred_match = re.search(r'## Prediction\s*\n(.*?)(?=\n---)', md, re.DOTALL)
    if not pred_match:
        return '', 0, ''
    pred_raw = pred_match.group(1)

    # Prediction sentence: first non-blank line that isn't a **Key:** metadata line
    pred_text = ''
    for line in pred_raw.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        if re.match(r'\*{1,2}\w+\s*:\*{1,2}', line):
            continue
        pred_text = line
        break

    # Probability: **Probability:** 75%  or  Probability: 75%
    prob_val = 0
    prob_m = re.search(r'\*{0,2}Probability\s*:\*{0,2}\s*(\d+)%', pred_raw)
    if prob_m:
        prob_val = int(prob_m.group(1))

    # Target: **Target:** June 2027  or  Target: June 2027
    target_val = ''
    target_m = re.search(r'\*{0,2}Target\s*:\*{0,2}\s*(.+?)(?:\n|$)', pred_raw)
    if target_m:
        target_val = target_m.group(1).strip().replace('**', '')

    return pred_text, prob_val, target_val


if __name__ == "__main__":
    use_md = False
    md_path = None
    args = list(sys.argv[1:])

    if args and args[0] == '--md-path':
        use_md = True
        md_path = args[1]
        args = args[2:]  # remove --md-path and its value

    if use_md:
        if len(args) < 3:
            print("Usage:")
            print("  python3 upload-to-r2.py --md-path <report.md> <pdf_path> <topic_slug> <topic_name>")
            print("  python3 upload-to-r2.py <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>")
            sys.exit(1)
    else:
        if len(args) < 6:
            print("Usage:")
            print("  python3 upload-to-r2.py --md-path <report.md> <pdf_path> <topic_slug> <topic_name>")
            print("  python3 upload-to-r2.py <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>")
            sys.exit(1)

    pdf_path = args[0]
    topic_slug = args[1]
    topic_name = args[2]

    if use_md:
        prediction, probability, target_date = parse_prediction(md_path)
    else:
        prediction = args[3]
        probability = int(args[4])
        target_date = args[5]

    # Extract date from PDF filename (DD-MM-YYYY → YYYY-MM-DD)
    basename = os.path.basename(pdf_path)
    date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', basename)
    if date_match:
        date_str = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
    else:
        date_str = datetime.now().strftime("%Y-%m-%d")

    filename = f"Watch Report {date_match.group(0)}.pdf" if date_match else os.path.basename(pdf_path)

    url = upload_pdf(pdf_path, topic_slug, date_str)
    if not url:
        sys.exit(1)

    success = update_manifest(topic_slug, topic_name, date_str, filename, url, prediction, probability, target_date)
    if success:
        print(f"Done. PDF at: {url}")
    else:
        print("Manifest update failed (PDF was uploaded)")
