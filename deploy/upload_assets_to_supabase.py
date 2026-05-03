#!/usr/bin/env python3
"""Upload local static/media assets to Supabase Storage (S3 API)."""

import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.client import Config


BASE_DIR = Path(__file__).resolve().parents[1]
DOTENV_PATH = BASE_DIR / ".env"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def derive_endpoint(project_url: str) -> str:
    host = urlparse(project_url).netloc
    if not host:
        raise RuntimeError("SUPABASE_PROJECT_URL is invalid")
    project_ref = host.split(".")[0]
    return f"https://{project_ref}.storage.supabase.co/storage/v1/s3"


def upload_tree(client, bucket: str, root: Path, prefix: str) -> int:
    if not root.exists():
        return 0
    uploaded = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        key = f"{prefix}/{rel}"
        content_type, _ = mimetypes.guess_type(path.name)
        extra = {"ContentType": content_type} if content_type else {}
        client.upload_file(str(path), bucket, key, ExtraArgs=extra)
        uploaded += 1
    return uploaded


def main() -> None:
    load_dotenv(DOTENV_PATH)

    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "duno360_bucket").strip()
    project_url = required_env("SUPABASE_PROJECT_URL")
    endpoint = os.environ.get("SUPABASE_S3_ENDPOINT", "").strip() or derive_endpoint(project_url)
    region = os.environ.get("SUPABASE_S3_REGION", "us-east-1").strip()
    access_key = required_env("SUPABASE_S3_ACCESS_KEY_ID")
    secret_key = required_env("SUPABASE_S3_SECRET_ACCESS_KEY")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )

    static_root = BASE_DIR / "staticfiles"
    media_root = BASE_DIR / "media"

    static_count = upload_tree(client, bucket, static_root, "static")
    media_count = upload_tree(client, bucket, media_root, "media")

    print(f"Uploaded static files: {static_count}")
    print(f"Uploaded media files: {media_count}")
    print("Done.")


if __name__ == "__main__":
    main()
