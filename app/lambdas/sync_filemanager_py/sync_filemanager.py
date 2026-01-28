#!/usr/bin/env python3

"""
Sync the filemanager
"""

from orcabus_api_tools.filemanager import crawl_filemanager_sync

def handler(event, context):
    """
    Sync the filemanager
    :param event:
    :param context:
    :return:
    """
    try:
        crawl_filemanager_sync(
            bucket=event['bucket']
        )
    except Exception as e:
        raise ValueError("Failed to sync filemanager") from e
