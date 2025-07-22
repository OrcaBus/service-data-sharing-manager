#!/usr/bin/env python3

"""
This file contains the models for the database.
"""

from typing import Union, TypedDict, NotRequired, List, Dict, Literal
from pathlib import Path
from datetime import datetime
from typing import Optional
from orcabus_api_tools.filemanager.models import FileObject


DataType = Literal[
    "fastq",
    "secondaryAnalysis",
]


class FileObjectWithRelativePathTypeDef(FileObject):
    dataType: DataType
    relativePath: Union[Path, str]


JobStatusType = Literal[
    "PENDING",
    "RUNNING",
    "FAILED",
    "ABORTED",
    "SUCCEEDED",
]


class FileObjectWithPresignedUrlTypeDef(FileObjectWithRelativePathTypeDef):
    presignedUrl: str
    relativePath: Union[Path, str]


SecondaryAnalysisDataType = Literal[
    # CURRENT
    "tumor-normal",
    "wts",
    "cttsov2",

    # FUTURE
    'dragen-wgts-dna',
    'dragen-wgts-rna',
    'dragen-tso500-ctdna',

    # ONCOANALYSER
    'oncoanalyser-wgts-dna',
    'oncoanalyser-wgts-rna',
    'oncoanalyser-wgts-dna-rna',

    'sash',
    'umccrise',
    'rnasum',
]


class PackageResponseDict(TypedDict):
    id: str
    packageName: str
    stepsExecutionArn: str
    status: JobStatusType
    requestTime: datetime
    completionTime: datetime


class PushJobResponseDict(TypedDict):
    id: str
    stepFunctionsExecutionArn: str
    status: JobStatusType
    startTime: datetime
    packageId: str
    shareDestination: str
    logUri: str
    endTime: Optional[datetime]
    errorMessage: Optional[str]


class WorkflowRunModelSlim(TypedDict):
    orcabusId: str
    timestamp: str
    portalRunId: str
    workflowName: str
    workflowVersion: str
    libraries: NotRequired[List[Dict[str, str]]]
