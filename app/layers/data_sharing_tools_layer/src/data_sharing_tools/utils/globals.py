#!/usr/bin/env python3

import re
from enum import Enum
from typing import Literal

# AWS PARAMETERS
DATA_SHARING_SUBDOMAIN_NAME = "data-sharing"

# API ENDPOINTS
PACKAGING_ENDPOINT = "api/v1/package"
PUSH_JOB_ENDPOINT = "api/v1/push"

# REGEX
ORCABUS_ULID_REGEX_MATCH = re.compile(r'^[a-z0-9]{3}\.[A-Z0-9]{26}$')


JobStatusType = Literal[
    "PENDING",
    "RUNNING",
    "FAILED",
    "ABORTED",
    "SUCCEEDED",
]
