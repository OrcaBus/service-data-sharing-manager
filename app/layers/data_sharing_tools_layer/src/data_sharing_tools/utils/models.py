#!/usr/bin/env python3

"""
This file contains the models for the database.
"""

from typing import Union, TypedDict, NotRequired, List, Dict, Literal
from pathlib import Path
from datetime import datetime
from typing import Optional
from orcabus_api_tools.filemanager.models import FileObject

# Literals
DataType = Literal[
    "fastq",
    "secondaryAnalysis",
]

PrimaryDataPathPrefixType = Literal[
    'fastq',
    'primary',
    '',  # Replaces '/' at interface level
]

SecondaryAnalysisPathPrefixType = Literal[
    'secondary-analysis',
    'analysis',
    '',  # Replaces '/' at interface level
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
    # ARCHIVED
    "tumor-normal",
    "wts",
    "cttsov2",
    'umccrise',

    # DRAGEN CURRENT
    'dragen-wgts-dna',
    'dragen-wgts-rna',
    'dragen-tso500-ctdna',

    # ONCOANALYSER CURRENT
    'oncoanalyser-wgts-dna',
    'oncoanalyser-wgts-rna',
    'oncoanalyser-wgts-dna-rna',

    # TERTIARY CURRENT
    'sash',
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
