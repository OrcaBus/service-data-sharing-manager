#!/usr/bin/env python3

"""
Sync the filemanager at the data artefacts bucket location
"""

from orcabus_api_tools.filemanager import crawl_filemanager_sync

def handler(event, context):
    """
    Sync the filemanager
    :param event:
    :param context:
    :return:
    """
    # Get input
    bucket = event.get('bucket')

    if not bucket:
        raise ValueError("Bucket name must be provided in the event")

    try:
        crawl_filemanager_sync(
            bucket=bucket
        )
    except Exception as e:
        raise ValueError("Failed to sync filemanager") from e

    return {
        "status": "success"
    }
