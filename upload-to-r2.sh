#!/bin/bash
# Upload a Watch Report PDF to Cloudflare R2 and update the manifest.
# Usage: upload-to-r2.sh <pdf_path> <topic_slug> <topic_name> <prediction> <probability> <target_date>
#
# Example:
#   ./upload-to-r2.sh \
#     "/root/wiki/kazakhstan/Watch Reports/Watch Report 04-06-2026.pdf" \
#     "kazakhstan" "Kazakhstan" \
#     "Tech diversification advances but hydrocarbons remain dominant" \
#     70 "2027-12-01"

PDF_PATH="$1"
TOPIC_SLUG="$2"
TOPIC_NAME="$3"
PREDICTION="$4"
PROBABILITY="$5"
TARGET_DATE="$6"

python3 - "$PDF_PATH" "$TOPIC_SLUG" "$TOPIC_NAME" "$PREDICTION" "$PROBABILITY" "$TARGET_DATE" << 'PYEOF'
import json, sys, os, subprocess, re
from datetime import datetime

pdf_path = sys.argv[1]
topic_slug = sys.argv[2]
topic_name = sys.argv[3]
prediction = sys.argv[4]
probability = int(sys.argv[5])
target_date = sys.argv[6]

R2_ACCOUNT_ID = "9a79991ea25c968a06f52c4ecd949ff7"
R2_ACCESS_KEY_ID = "56afe22c0c7a5e9ac25cdecd1f363b31"
R2_SECRET_ACCESS_KEY = "bc810ece1600642490e6312097c85487b11bcd6fffa6f09841a259a17a362ef0"
R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
R2_BUCKET = "signal-fracture-content"
R2_PREFIX = "watch-reports"
R2_PUBLIC_BASE = f"https://pub-{R2_ACCOUNT_ID}.r2.dev/{R2_BUCKET}"

env = {
    "AWS_ACCESS_KEY_ID": R2_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": R2_SECRET_ACCESS_KEY,
    "AWS_ENDPOINT_URL": R2_ENDPOINT,
    "AWS_DEFAULT_REGION": "auto",
}

def aws_cli(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env={**os.environ, **env})
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        return None
    return result.stdout.strip()

# Extract date from filename
basename = os.path.basename(pdf_path)
date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', basename)
if date_match:
    date_str = f"{date_match.group(3)}-{date_match.group(2)}-{date_match.group(1)}"
else:
    date_str = datetime.now().strftime("%Y-%m-%d")

filename = f"Watch Report {date_match.group(0)}.pdf" if date_match else os.path.basename(pdf_path)

# Upload PDF
object_key = f"{R2_PREFIX}/{topic_slug}/{date_str}.pdf"
print(f"Uploading: {object_key}")
result = aws_cli(f'aws s3 cp "{pdf_path}" "s3://{R2_BUCKET}/{object_key}" --endpoint-url "{R2_ENDPOINT}"')
if result is None:
    print("PDF upload failed")
    sys.exit(1)

url = f"{R2_PUBLIC_BASE}/{object_key}"
print(f"Uploaded: {url}")

# Download existing manifest
manifest_key = f"{R2_PREFIX}/manifest.json"
local_manifest = "/tmp/watch-reports-manifest.json"
os.system(f'aws s3 cp "s3://{R2_BUCKET}/{manifest_key}" "{local_manifest}" --endpoint-url "{R2_ENDPOINT}" 2>/dev/null')

if os.path.exists(local_manifest):
    with open(local_manifest) as f:
        manifest = json.load(f)
else:
    manifest = {"reports": [], "updated_at": ""}

# Remove existing entry for same topic+date
manifest["reports"] = [r for r in manifest["reports"] if not (r["slug"] == topic_slug and r["date"] == date_str)]

# Add new entry
manifest["reports"].append({
    "topic": topic_name,
    "slug": topic_slug,
    "date": date_str,
    "filename": filename,
    "url": url,
    "prediction": prediction,
    "probability": probability,
    "target_date": target_date,
    "uploaded_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
})

manifest["reports"].sort(key=lambda r: r["date"], reverse=True)
manifest["updated_at"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

with open(local_manifest, "w") as f:
    json.dump(manifest, f, indent=2)

result = aws_cli(f'aws s3 cp "{local_manifest}" "s3://{R2_BUCKET}/{manifest_key}" --endpoint-url "{R2_ENDPOINT}"')
if result is not None:
    print(f"Manifest updated: {len(manifest['reports'])} reports")
    os.remove(local_manifest)
    print(f"Done. PDF at: {url}")
else:
    print("Manifest update failed (PDF was uploaded)")
PYEOF
