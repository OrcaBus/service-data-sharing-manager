import logging

logger = logging.getLogger()
logger.setLevel("INFO")

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import patch_request


def handler(event, context):
    """
    Deprecate a package via the data sharing API.

    Input event:
      { "packageId": "pkg.xxx" }

    Returns:
      { "deprecated": True }                       on success
      { "deprecated": False, "errorCause": "..." } on failure
    """
    package_id = event.get("packageId")

    deprecate_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:deprecate")

    try:
        patch_request(url=deprecate_api_url)
        return {
            "deprecated": True,
            "errorCause": None,
        }
    except Exception as e:
        logger.warning("Failed to deprecate package %s: %s", package_id, e)
        return {
            "deprecated": False,
            "errorCause": str(e),
        }
