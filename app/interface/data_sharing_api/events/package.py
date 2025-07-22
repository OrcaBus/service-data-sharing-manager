#!/usr/bin/env python3
from os import environ

from ..globals import EVENT_DETAIL_TYPE_PACKAGING_JOB_STATE_CHANGE_ENV_VAR
from ..models.package import PackageResponseDict
from . import put_event

# Update events
def put_package_update_event(package_response_object: PackageResponseDict):
    """
    Put a update event to the event bus.
    """
    put_event(environ[EVENT_DETAIL_TYPE_PACKAGING_JOB_STATE_CHANGE_ENV_VAR], package_response_object)
