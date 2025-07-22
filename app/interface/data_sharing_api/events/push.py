#!/usr/bin/env python3

"""
Generate datasharing push events to push to the server
"""
from os import environ

from ..globals import EVENT_DETAIL_TYPE_PUSH_JOB_STATE_CHANGE_ENV_VAR
from ..models.push import PushJobResponse
from . import put_event


# Update events
def put_push_job_update_event(push_response_object: PushJobResponse):
    """
    Put a update event to the event bus.
    """
    put_event(environ[EVENT_DETAIL_TYPE_PUSH_JOB_STATE_CHANGE_ENV_VAR], push_response_object)
