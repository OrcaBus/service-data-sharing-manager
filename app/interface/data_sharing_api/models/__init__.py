# Standard models

from typing import TypedDict, Optional, Literal

from pydantic import BaseModel


class LibraryDict(TypedDict):
    orcabusId: Optional[str]
    libraryId: Optional[str]


class SecondaryAnalysisDict(TypedDict):
    orcabusId: Optional[str]
    portalRunId: Optional[str]
    workflowRunName: Optional[str]


class FastqDict(TypedDict):
    orcabusId: Optional[str]
    sampleId: Optional[str]
    fileName: Optional[str]
    instrumentRunId: Optional[str]
    lane: Optional[str]
    fileSize: Optional[str]


JobStatusType = Literal[
    'PENDING',
    'RUNNING',
    'FAILED',
    'ABORTED',
    'SUCCEEDED',
]


class JobPatch(BaseModel):
    status: JobStatusType
    errorMessage: Optional[str] = None
