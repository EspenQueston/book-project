#!/usr/bin/env python
"""
sync_from_r2.py
===============
Download ALL media files from Cloudflare R2 (production) to local media/ folder.
Production is the source of truth — local files are overwritten.

Usage:
    python sync_from_r2.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print('ERROR: boto3 not installed. Run: pip install boto3')
    sys.exit(1)

# ── R2 Config ────────────────────────────────────────────────────────────────
R2_ACCESS_KEY = os.environ.get('SUPABASE_S3_ACCESS_KEY_ID', '')
R2_SECRET_KEY = os.environ.get('SUPABASE_S3_SECRET_ACCESS_KEY', '')
R2_ENDPOINT   = os.environ.get('SUPABASE_S3_ENDPOINT', '')
R2_BUCKET     = os.environ.get('SUPABASE_STORAGE_BUCKET', 'duno360')
R2_PREFIX     = 'media'

if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT]):
    print('ERROR: R2 credentials missing in .env')
    sys.exit(1)

LOCAL_MEDIA = BASE_DIR / 'media'
LOCAL_MEDIA.mkdir(exist_ok=True)

s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name='auto',
)

# ── List all objects under media/ prefix ─────────────────────────────────────
print(f'\n🔄  Syncing R2 bucket "{R2_BUCKET}/{R2_PREFIX}/" → local media/\n')

paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(Bucket=R2_BUCKET, Prefix=f'{R2_PREFIX}/')

downloaded = 0
skipped    = 0
errors     = 0
all_keys   = []

for page in pages:
    for obj in page.get('Contents', []):
        all_keys.append(obj['Key'])

print(f'    Found {len(all_keys)} files in R2\n')

for key in sorted(all_keys):
    # Strip the 'media/' prefix to get the relative local path
    rel_path   = key[len(R2_PREFIX) + 1:]   # e.g. 'marketplace/products/xxx.jpg'
    if not rel_path:
        continue

    local_path = LOCAL_MEDIA / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        s3.download_file(R2_BUCKET, key, str(local_path))
        print(f'  ✓  {rel_path}')
        downloaded += 1
    except ClientError as e:
        print(f'  ✗  {rel_path}  →  {e}')
        errors += 1

print(f'\n{"="*55}')
print(f'  ✅  Downloaded : {downloaded}')
print(f'  ❌  Errors     : {errors}')
print(f'  Total      : {len(all_keys)}')
print(f'{"="*55}')

if errors == 0:
    print('\n🎉  Local media/ is now in sync with production R2!')
else:
    print(f'\n⚠️   {errors} file(s) failed. Check errors above.')
