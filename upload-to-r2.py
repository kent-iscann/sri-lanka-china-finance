#!/usr/bin/env python3
"""
Upload a Watch Report PDF to Cloudflare R2 and update the manifest.
Uses boto3 (S3-compatible) — no AWS CLI required.

Usage: python3 upload-to-r2.py <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>
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
R2_PUBLIC_BASE = f"https://pub-{R2_ACCOUNT_ID}.r2.dev/{R2_BUCKET}"

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


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: python3 upload-to-r2.py <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    topic_slug = sys.argv[2]
    topic_name = sys.argv[3]
    prediction = sys.argv[4]
    probability = int(sys.argv[5])
    target_date = sys.argv[6]

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
