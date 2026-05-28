#!/usr/bin/env python
"""
upload_to_r2.py
===============
ONE-TIME script: Upload all local media/ files to Cloudflare R2.
Run from your LOCAL machine before deploying to production.

Usage:
    python upload_to_r2.py
"""
import os
import sys
import mimetypes
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print('ERROR: boto3 not installed.  Run: pip install boto3')
    sys.exit(1)

# ── R2 Config (reads from .env) ───────────────────────────────────────────────
R2_ACCESS_KEY = os.environ.get('SUPABASE_S3_ACCESS_KEY_ID', '')
R2_SECRET_KEY = os.environ.get('SUPABASE_S3_SECRET_ACCESS_KEY', '')
R2_ENDPOINT   = os.environ.get('SUPABASE_S3_ENDPOINT', '')
R2_BUCKET     = os.environ.get('SUPABASE_STORAGE_BUCKET', 'duno360')
R2_PREFIX     = 'media'   # must match settings.py  location='media'

if not all([R2_ACCESS_KEY, R2_SECRET_KEY, R2_ENDPOINT]):
    print('ERROR: R2 credentials missing in .env')
    sys.exit(1)

MEDIA_DIR = BASE_DIR / 'media'
if not MEDIA_DIR.exists():
    print(f'ERROR: media/ directory not found at {MEDIA_DIR}')
    sys.exit(1)

# ── S3/R2 Client ─────────────────────────────────────────────────────────────
s3 = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name='auto',
)

def content_type(suffix: str) -> str:
    ct, _ = mimetypes.guess_type(f'file{suffix}')
    return ct or 'application/octet-stream'

# ── Upload ────────────────────────────────────────────────────────────────────
all_files = [p for p in MEDIA_DIR.rglob('*') if p.is_file()]
total     = len(all_files)
uploaded  = 0
skipped   = 0
errors    = 0

print(f'\n🚀  Uploading {total} files from media/ → R2 bucket "{R2_BUCKET}"\n')
print(f'    Endpoint : {R2_ENDPOINT}')
print(f'    Prefix   : {R2_PREFIX}/\n')

for local_path in sorted(all_files):
    rel   = local_path.relative_to(MEDIA_DIR)
    r2key = f'{R2_PREFIX}/{rel.as_posix()}'
    ct    = content_type(local_path.suffix)

    try:
        s3.upload_file(
            str(local_path),
            R2_BUCKET,
            r2key,
            ExtraArgs={'ContentType': ct},
        )
        print(f'  ✓  {r2key}')
        uploaded += 1
    except ClientError as e:
        print(f'  ✗  {r2key}  →  {e}')
        errors += 1

print(f'\n{"="*55}')
print(f'  ✅  Uploaded : {uploaded}')
print(f'  ❌  Errors   : {errors}')
print(f'  Total    : {total}')
print(f'{"="*55}')
if errors == 0:
    print('\n🎉  All files uploaded successfully!')
    print(f'\n    Public base URL:')
    pub = os.environ.get('SUPABASE_STORAGE_PUBLIC_BASE_URL', '')
    if pub:
        print(f'    {pub}/{R2_PREFIX}/')
    print('\n👉  Next step: update SUPABASE_STORAGE_ENABLED=True on the VPS')
else:
    print(f'\n⚠️   {errors} file(s) failed. Check errors above and retry.')
