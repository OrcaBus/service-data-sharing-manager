#!/usr/bin/env python3

"""
SFN LAMBDA PLACEHOLDER: __list_fastqs_in_library_as_file_ids_lambda_function_arn__
Intro:

Given a list of json files, convert them into a single csv file and return as a string
"""

# Imports
import typing
from typing import List, Dict, Optional

# Get layer tools
from orcabus_api_tools.fastq import (
    get_fastqs_in_library, get_fastq_set, get_fastq_sets, get_fastq,
)
from orcabus_api_tools.fastq.models import Fastq, FastqSet

if typing.TYPE_CHECKING:
    from orcabus_api_tools.metadata import Library

# Set logging
import logging
logger = logging.getLogger()
logger.setLevel("INFO")


def handler(event, context) -> Dict[str, List[str]]:
    """
    Generate fastqs from library ids as file objects.
    Given a library object as input, convert to fastq objects.
    :param event:
    :param context:
    :return:
    """

    # Get the library object
    library: Library = event.get("libraryObject", None)
    instrument_run_id_list: Optional[List[str]] = event.get("instrumentRunIdList")

    # Assert the library object is not None
    assert library is not None, "Library object is None"

    # Get fastq sets for this library
    fastq_set_obj_list = get_fastq_sets(
        library=library['libraryId'],
        currentFastqSet=True,
    )

    # Check that the fastq set object list is of len 1
    assert len(fastq_set_obj_list) == 1, "Fastq set object list is not of len 1"

    fastq_set_obj = fastq_set_obj_list[0]

    # If instrument runs ids is not None, we will filter the fastqs by the instrument run ids
    if instrument_run_id_list is not None:
        fastq_id_list = list(filter(
            lambda fastq_obj: fastq_obj['instrumentRunId'] in instrument_run_id_list,
            fastq_set_obj['fastqSet']
        ))
    else:
        fastq_id_list = list(map(
            lambda fastq_set_obj_iter_: fastq_set_obj_iter_['id'],
            fastq_set_obj['fastqSet']
        ))

    return {
        "fastqIdList": fastq_id_list
    }
