#!/usr/bin/env python3

"""

SFN LAMBDA PLACEHOLDER: __list_portal_run_ids_in_library_lambda_function_arn__

List portal run ids from the library.

We also retrieve the portal run id exclusion list, so we filter out any portal run ids
that are in the exclusion list.
"""

import typing
from textwrap import dedent
from typing import List, Dict, Tuple
from urllib.parse import urlparse
import pandas as pd
import ulid

from data_sharing_tools.utils.models import WorkflowRunModelSlim
from orcabus_api_tools.workflow import (
    get_workflows_from_library_id
)
from orcabus_api_tools.mart import run_athena_sql_query

if typing.TYPE_CHECKING:
    from orcabus_api_tools.metadata import Library

# Globals
WORKFLOW_NAME_CONVERSION_MAP = {
    "tumor-normal": "WGS_TUMOR_NORMAL",
    "oncoanalyser_wgs": "oncoanalyser-wgts-dna",
}



def get_bucket_key_tuple_from_s3_uri(s3_uri: str) -> Tuple[str, str]:
    urlobj = urlparse(s3_uri)

    return urlobj.netloc, urlobj.path.lstrip('/')



def get_legacy_workflows_from_library_id_legacy(library_id: str) -> List[WorkflowRunModelSlim]:
    workflow_query = dedent(
        """
        SELECT
            portal_run_id AS portalRunId,
            workflow_name AS workflowName,
            workflow_version AS workflowVersion
        FROM workflow
        WHERE (
            library_id IN ('{__LIBRARY_ID__}')
        )
        """.format(
            __LIBRARY_ID__=library_id
        )
    )

    df = run_athena_sql_query(workflow_query)

    if df.shape[0] == 0:
        return []

    # Coerce workflow names
    df['workflowName'] = df['workflowName'].apply(
        lambda workflow_name_iter_: (
            WORKFLOW_NAME_CONVERSION_MAP[workflow_name_iter_]
            if workflow_name_iter_ in WORKFLOW_NAME_CONVERSION_MAP
            else workflow_name_iter_
        ),
    )

    df['timestamp'] = df['portalRunId'].apply(
        lambda portal_run_id_iter_: pd.to_datetime(portal_run_id_iter_[:8], errors='coerce')
    )

    df = df.dropna(
        how='any',
        subset='timestamp'
    )

    df['orcabusId'] = df['portalRunId'].apply(
        lambda portal_run_id_iter_: (
                "wv1." + str(ulid.from_timestamp(pd.to_datetime(portal_run_id_iter_[:8], errors='coerce')))
        )
    )

    df = df[[
        'orcabusId',
        'timestamp',
        'workflowName',
        'workflowVersion',
        'portalRunId'
    ]]

    return df.to_dict(orient='records')


def handler(event, context) -> Dict[str, List[str]]:
    """
    Given a library object, list the portal run ids in the library
    :param event:
    :param context:
    :return:
    """

    # Get library object
    library: 'Library' = event['libraryObject']
    portal_run_id_exclusion_list: List[str] = event['portalRunIdExclusionList']
    secondary_analyses_type_list: List[str] = event['secondaryAnalysisTypeList']

    # List portal run ids in the library
    workflows_list: List[WorkflowRunModelSlim] = list(map(
        lambda workflow_obj_iter_: {
            "orcabusId": workflow_obj_iter_['orcabusId'],
            "timestamp": workflow_obj_iter_['currentState']['timestamp'],
            "workflowName": workflow_obj_iter_['workflow']['name'],
            "portalRunId": workflow_obj_iter_['portalRunId'],
            "workflowVersion": workflow_obj_iter_['workflow']['version'],
        },
        get_workflows_from_library_id(library['libraryId'])
    ))

    # Query the datamart for legacy workflows
    workflows_list.extend(get_legacy_workflows_from_library_id_legacy(library['libraryId']))

    # Run athena query to get legacy workflows in the library

    # Filter workflows not in the secondary analyses list
    workflows_list = list(filter(
        lambda workflow_iter_: workflow_iter_['workflowName'] in secondary_analyses_type_list,
        workflows_list
    ))

    # Filter workflows in the exclusion list
    if portal_run_id_exclusion_list:
        workflows_list = list(filter(
            lambda workflow_iter_: workflow_iter_['portalRunId'] not in portal_run_id_exclusion_list,
            workflows_list
        ))

    # For each workflow type, return the most recent workflow of that type
    workflows_list_filter_duplicates = []
    workflows_list.sort(
        key=lambda workflow_iter_: pd.to_datetime(workflow_iter_['timestamp']).timestamp(),
        reverse=True
    )
    # Get the names of all the workflows in the library workflows list
    workflow_names_in_library_workflows = list(set(list(map(
        lambda workflow_iter_: workflow_iter_['workflowName'],
        workflows_list
    ))))
    # Get only the most recent workflow of each type
    for workflow_name_iter_ in workflow_names_in_library_workflows:
        workflows_list_filter_duplicates.append(
            next(filter(
                lambda workflow_iter_: workflow_iter_['workflowName'] == workflow_name_iter_,
                workflows_list
            ))
        )

    # Return the portal run ids of the most recent workflows
    return {
        'portalRunIdList': list(map(
            lambda workflow_iter_: workflow_iter_['portalRunId'],
            workflows_list_filter_duplicates
        ))
    }
