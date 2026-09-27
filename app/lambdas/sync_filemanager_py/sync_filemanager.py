#!/usr/bin/env python3

"""
Sync the filemanager at a given bucket location.

Accepts either:
  - s3UriPrefix: a full S3 URI (e.g. 's3://bucket/prefix/') which is parsed
    into its bucket and prefix components, or
  - bucket (+ optional prefix): the bucket name and an optional key prefix.
"""

from typing import Optional, Tuple
from urllib.parse import urlparse

from orcabus_api_tools.filemanager import crawl_filemanager_sync


def parse_s3_uri(s3_uri: str) -> Tuple[str, Optional[str]]:
    """
    Parse an S3 URI into its bucket and prefix components.
    :param s3_uri: e.g. 's3://my-bucket/some/prefix/'
    :return: (bucket, prefix) where prefix is None when the URI has no key
    """
    parsed = urlparse(s3_uri)

    if parsed.scheme != "s3":
        raise ValueError(f"Expected an s3:// URI, got '{s3_uri}'")

    bucket = parsed.netloc
    if not bucket:
        raise ValueError(f"Could not determine bucket from s3 uri '{s3_uri}'")

    # Strip the leading slash from the path to get the key prefix
    prefix = parsed.path.lstrip("/") or None

    return bucket, prefix


def handler(event, context):
    """
    Sync the filemanager
    :param event:
    :param context:
    :return:
    """
    # Get input
    s3_uri_prefix = event.get('s3UriPrefix')

    if s3_uri_prefix:
        bucket, prefix = parse_s3_uri(s3_uri_prefix)
    else:
        bucket = event.get('bucket')
        prefix = event.get('prefix')

    if not bucket:
        raise ValueError("Either 's3UriPrefix' or 'bucket' must be provided in the event")

    try:
        crawl_filemanager_sync(
            bucket=bucket,
            prefix=prefix
        )
    except Exception as e:
        raise ValueError("Failed to sync filemanager") from e

    return {
        "status": "success"
    }
