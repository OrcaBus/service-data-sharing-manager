import logging

logger = logging.getLogger()
logger.setLevel("INFO")

from orcabus_api_tools.data_sharing import get_data_sharing_url
from orcabus_api_tools.utils.requests_helpers import patch_request

# The deprecate endpoint returns HTTP 409 with this detail when the package is
# already deprecated. That is not a failure for us: the package is already in the
# desired state, so we treat it as a successful (idempotent) deprecation.
ALREADY_DEPRECATED_DETAIL = "Package is already deprecated"


def handler(event, context):
    """
    Deprecate a package via the data sharing API.

    Input event:
      { "packageId": "pkg.xxx" }

    Returns:
      { "deprecated": True,  "alreadyDeprecated": False, "errorCause": None }  on success
      { "deprecated": True,  "alreadyDeprecated": True,  "errorCause": None }  if it was already deprecated
      { "deprecated": False, "alreadyDeprecated": False, "errorCause": "..." } on failure
    """
    package_id = event.get("packageId")

    deprecate_api_url = get_data_sharing_url(f"/api/v1/package/{package_id}:deprecate")

    try:
        patch_request(url=deprecate_api_url)
        return {
            "deprecated": True,
            "alreadyDeprecated": False,
            "errorCause": None,
        }
    except Exception as e:
        # Already deprecated is an idempotent success, not an error.
        if ALREADY_DEPRECATED_DETAIL in str(e):
            logger.info("Package %s was already deprecated; treating as success.", package_id)
            return {
                "deprecated": True,
                "alreadyDeprecated": True,
                "errorCause": None,
            }

        logger.warning("Failed to deprecate package %s: %s", package_id, e)
        return {
            "deprecated": False,
            "alreadyDeprecated": False,
            "errorCause": str(e),
        }
