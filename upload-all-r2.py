#!/usr/bin/env python3
"""
Upload all Watch Report PDFs to Cloudflare R2 and update the manifest.
Topic names, slugs, paths, and date prefix all come from _config.yaml.

Usage: python3 upload-all-r2.py <wiki_root> <config_path>
"""
import json, os, re, sys, subprocess
from datetime import datetime, timezone
from pathlib import Path

wiki_root = sys.argv[1] if len(sys.argv) > 1 else "/root/wiki"
config_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(wiki_root, "_config.yaml")

# ── Parse _config.yaml ──────────────────────────────────────────────
try:
    import yaml
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml", "-q", "--break-system-packages"])
    import yaml

with open(config_path) as f:
    config = yaml.safe_load(f)
topics = config.get("topics", [])

# ── R2 config ───────────────────────────────────────────────────────
R2_ACCOUNT_ID = "9a79991ea25c968a06f52c4ecd949ff7"
R2_ACCESS_KEY_ID = "56afe22c0c7a5e9ac25cdecd1f363b31"
R2_SECRET_ACCESS_KEY = "bc810ece1600642490e6312097c85487b11bcd6fffa6f09841a259a17a362ef0"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_BUCKET = "signal-fracture-content"
R2_PREFIX = "watch-reports"
R2_PUBLIC_BASE = f"https://pub-70e08d62c8314675b40c42f0fe4be6fb.r2.dev/"

try:
    import boto3
    from botocore.config import Config
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3", "-q", "--break-system-packages"])
    import boto3
    from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

# ── Download existing manifest ───────────────────────────────────────
manifest_key = f"{R2_PREFIX}/manifest.json"
local_manifest = "/tmp/watch-reports-manifest.json"
manifest = {"topics": [], "updated_at": ""}

try:
    s3.download_file(R2_BUCKET, manifest_key, local_manifest)
    with open(local_manifest) as f:
        manifest = json.load(f)
    if "reports" in manifest and "topics" not in manifest:
        old = manifest.pop("reports", [])
        tm = {}
        for r in old:
            slug = r.pop("slug", "")
            tn = r.pop("topic", slug)
            tm.setdefault(slug, {"topic": tn, "slug": slug, "reports": []})["reports"].append(r)
        manifest["topics"] = sorted(tm.values(), key=lambda t: t["slug"])
    print(f"Loaded existing manifest: {len(manifest['topics'])} topics")
except Exception as e:
    print(f"No existing manifest ({e}), creating fresh")
    manifest = {"topics": [], "updated_at": ""}

topic_map = {t["slug"]: t for t in manifest["topics"]}

# ── Process each topic ──────────────────────────────────────────────
md_pattern = re.compile(r"Watch Report (\d{2})-(\d{2})-(\d{4})\.md")

for topic in topics:
    topic_name = topic["name"]
    topic_slug = topic["slug"]
    topic_path = topic["path"]
    date_prefix = topic.get("created", "2026-01-01")[:4]  # year from created date

    reports_dir = os.path.join(topic_path, "Watch Reports")
    if not os.path.isdir(reports_dir):
        print(f"SKIP: No Watch Reports dir for {topic_name}")
        continue

    uploaded_any = False
    for fname in sorted(os.listdir(reports_dir)):
        m = md_pattern.match(fname)
        if not m:
            continue

        day, month, year = m.groups()
        date_str = f"{year}-{month}-{day}"
        # R2 object key uses created year from config as prefix? No — use the slug + date
        # Actually the object key should be: watch-reports/{slug}/{date}.pdf

        fpath = os.path.join(reports_dir, fname)
        pdf_path = fpath.replace(".md", ".pdf")

        if not os.path.exists(pdf_path):
            print(f"  SKIP PDF missing: {pdf_path}")
            continue

        # Parse markdown for prediction/probability/target
        with open(fpath) as f:
            content = f.read()

        prediction = ""
        in_pred = False
        for line in content.split("\n"):
            if "## Prediction" in line:
                in_pred = True
                continue
            if in_pred:
                s = line.strip()
                if s.startswith("---") or s.startswith("## "):
                    break
                if s:
                    prediction = s
                    break

        prob_m = re.search(r"\*\*Probability:\*\* (\d+)%", content)
        probability = int(prob_m.group(1)) if prob_m else 0

        target_m = re.search(r"\*\*Target Date:\*\* (.+)", content)
        target_date = target_m.group(1).strip() if target_m else ""

        # Upload
        object_key = f"{R2_PREFIX}/{topic_slug}/{date_str}.pdf"
        print(f"\nUploading: {object_key}")
        print(f"  {prediction[:70]}...")
        try:
            s3.upload_file(pdf_path, R2_BUCKET, object_key, ExtraArgs={"ContentType": "application/pdf"})
            url = f"{R2_PUBLIC_BASE}{object_key}"
            print(f"  OK: {url}")
        except Exception as e:
            print(f"  FAILED: {e}")
            continue

        # Update manifest
        if topic_slug not in topic_map:
            topic_map[topic_slug] = {"topic": topic_name, "slug": topic_slug, "reports": []}

        topic_entry = topic_map[topic_slug]
        topic_entry["topic"] = topic_name  # always use latest name from config

        # Upsert report entry
        existing = {r["date"]: i for i, r in enumerate(topic_entry["reports"])}
        report_entry = {
            "date": date_str,
            "filename": fname.replace(".md", ".pdf"),
            "url": url,
            "prediction": prediction,
            "probability": probability,
            "target_date": target_date,
            "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if date_str in existing:
            topic_entry["reports"][existing[date_str]] = report_entry
        else:
            topic_entry["reports"].append(report_entry)

        uploaded_any = True

    if uploaded_any:
        # Sort reports by date descending
        topic_entry = topic_map[topic_slug]
        topic_entry["reports"].sort(key=lambda r: r["date"], reverse=True)
        print(f"  Manifest: {len(topic_entry['reports'])} reports for {topic_name}")

# ── Save and upload manifest ────────────────────────────────────────
manifest["topics"] = sorted(topic_map.values(), key=lambda t: t["slug"])
manifest["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open(local_manifest, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"\nUploading manifest: {manifest_key} ({len(manifest['topics'])} topics)")
s3.upload_file(local_manifest, R2_BUCKET, manifest_key, ExtraArgs={"ContentType": "application/json"})
print("Done.")
