
from orcabus_api_tools.sequence import get_libraries_from_instrument_run_id
from orcabus_api_tools.metadata import get_library_from_library_id

def get_all_project_ids_in_an_instrument_run(instrument_run_id):
    """
    Retrieve all unique project IDs associated with all the libraries in a given instrument run.
    """
    lib_ids = get_libraries_from_instrument_run_id(instrument_run_id)

    project_ids = set()
    for lib_id in lib_ids:
        library = get_library_from_library_id(lib_id)
        for project in library["projectSet"]:
            project_ids.add(project["projectId"])

    return list(project_ids)

def handler(event, context):
    """
    Check if any requested projects are found in the specified instrument run.
    """
    project_id_list = event["projectIdList"]
    instrument_run_id = event["instrumentRunId"]
    project_ids_in_run = get_all_project_ids_in_an_instrument_run(instrument_run_id)

    intersection = set(project_id_list).intersection(project_ids_in_run)
    project_found = len(intersection) > 0

    return {
        "project_found": project_found
    }
