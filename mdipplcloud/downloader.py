import fnmatch
import json
import os
import re
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .helpers import (
    Config,
    cfg_get,
    create_project_directory,
    format_project_name,
    get_logger,
    pass_filters,
    unpack_zip_file,
)

#recordings_url = f"{base_url}/workspaces/{workspace_id}/recordings"
#projects_url = f"{base_url}/workspaces/{workspace_id}/projects"


_resource_cache = {}
_SESSION = None
DEFAULT_TIMEOUT = 30


def _get_session():
    global _SESSION
    if _SESSION is None:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _SESSION = session
    return _SESSION


def _get_timeout(custom_cfg=None):
    if custom_cfg is not None and getattr(custom_cfg, "timeout", None) is not None:
        return custom_cfg.timeout
    if getattr(Config, "timeout", None) is not None:
        return Config.timeout
    return DEFAULT_TIMEOUT


def _request(method, url, **kwargs):
    custom_cfg = kwargs.pop("custom_cfg", None)
    if "timeout" not in kwargs:
        kwargs["timeout"] = _get_timeout(custom_cfg)
    return _get_session().request(method, url, **kwargs)


def _cfg_get(key, custom_cfg=None):
    if custom_cfg is None:
        return cfg_get(key)
    if key == 'headers':
        return custom_cfg.get_headers()
    elif key == 'api_key':
        return custom_cfg.api_key
    elif key == 'workspace_id':
        return custom_cfg.workspace_id
    elif key == 'base_url':
        return custom_cfg.base_url
    elif key == 'projects_url':
        return custom_cfg.get_projects_url()
    elif key == 'download_directory':
        return custom_cfg.download_directory
    else:
        raise ValueError(f"Unknown config value: {key}")


def download_single_file_from_url(url, local_filename, logger=None, custom_cfg=None):
    """
    Utility function to download a file from a URL.

    Parameters:
    url (str): URL of the file to be downloaded.
    local_filename (str): Path where the file should be saved.

    Returns:
    bool: True if the download was successful, False otherwise.

    Examples:
    >>> download_single_file_from_url("https://example.com/file.zip", "/path/to/save/file.zip", logger)

    """
    if logger is None:
        logger = get_logger()
    try:
        with _request(
            "GET",
            url,
            stream=True,
            headers=_cfg_get('headers', custom_cfg),
            custom_cfg=custom_cfg,
        ) as response:
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            with open(local_filename, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        file.write(chunk)
        logger.info(f"File downloaded successfully: {local_filename}")
        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error occurred while downloading the file: {e}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Error connecting to the server: {e}")
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout error: {e}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error occurred during the request: {e}")
    except Exception as e:
        logger.error(f"An error occurred while downloading the file: {e}")
    return False

def download_recording(recording_id, output_directory=None, unpack_zip=True, logger=None, custom_cfg=None):
    """
    Download a recording zip file given its ID.

    Parameters:
    recording_id (str): The ID of the recording.
    output_directory (str): The directory where the recording should be downloaded.
    unpack_zip (bool): Whether to unpack the zip file after downloading.

    Returns:
    bool: True if download and unpacking (if applicable) were successful, False otherwise.

    Examples:
    >>> download_recording("recording_id_here", logger)

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if output_directory is None:
        output_directory = _cfg_get('download_directory', cfg)
    if logger is None:
        logger = get_logger()
    base_url = _cfg_get('base_url', cfg)
    workspace_id = _cfg_get('workspace_id', cfg)
    success = False
    recording_download_url = f"{base_url}/workspaces/{workspace_id}/recordings/{recording_id}.zip"
    local_filename = os.path.join(output_directory, f"{recording_id}.zip")

    try:
        # Create the output directory if it does not exist
        if not os.path.exists(output_directory):
            logger.info(f"Creating output directory {output_directory}")
            os.makedirs(output_directory)

        logger.info(f"Downloading recording {recording_id} to {local_filename}...")
        if download_single_file_from_url(recording_download_url, local_filename, logger, custom_cfg=cfg):
            if unpack_zip:
                logger.info(f"Unpacking recording {recording_id}...")
                if not unpack_zip_file(local_filename, output_directory, logger):
                    logger.error(f"Failed to unpack recording {recording_id}")
                    raise Exception(f"Unpacking of recording {recording_id} failed")
            success = True
        else:
            raise Exception(f"Download of recording {recording_id} failed")
    except Exception as e:
        logger.error(f"Failed to download and process recording {recording_id}: {e}")

    return success


def download_files(file_list, download_directory=None, logger=None, custom_cfg=None):
    """
    Download specified files from the cloud.

    Parameters:
    file_list (list of dict): List of files, each represented as a dictionary.
    download_directory (str): Directory where the files should be downloaded.
    logger (Logger, optional): Logger for logging messages.
    custom_cfg (object, optional): Custom configuration object.

    Returns:
    None
    Examples:
    >>> download_files(file_list, "path/to/download_directory")

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if download_directory is None:
        download_directory = _cfg_get('download_directory', cfg)
    if logger is None:
        logger = get_logger()

    # Check if download directory exists, create if not
    if not os.path.exists(download_directory):
        logger.info(f"Creating download directory: {download_directory}")
        os.makedirs(download_directory)

    downloaded_files = 0
    logger.info(f"Starting file download ...")

    if not file_list:
        logger.error("No files to download.")
        return
    for file in file_list.values():
        # Download the file
        try:
            file_url = file['download_url']
            # save into subfolder using recording_id
            file_download_directory = os.path.join(download_directory, file['recording_id'])
            # Ensure download directory exists
            if not os.path.exists(file_download_directory):
                logger.info(f"Creating recording specific download directory for file download: {download_directory}")
                os.makedirs(file_download_directory)
            local_filename = os.path.join(file_download_directory, file['name'])
            logger.info(f"Downloading {file['name']} from {file_url}...")
            if download_single_file_from_url(file_url, local_filename, logger, custom_cfg=cfg):
                downloaded_files += 1
            else:
                logger.error(f"Failed to download {file['name']} from {file_url}")
        except Exception as e:
            logger.error(f"Exception occurred while downloading {file['name']}: {e}")

    if downloaded_files == 0:
        logger.info("No files downloaded.")


def get_workspace_info(workspace_id=None, custom_cfg=None):
    """
    Retrieve information for a specific workspace.

    Parameters:
    workspace_id (str): The ID of the workspace.

    Returns:
    dict: Information about the workspace.

    Examples:
    >>> workspace_info = get_workspace_info("your_workspace_id")
    >>> print(workspace_info)

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if workspace_id is None:
        workspace_id = _cfg_get('workspace_id', cfg)
    base_url = _cfg_get('base_url', cfg)
    headers = _cfg_get('headers', cfg)
    workspace_url = f"{base_url}/workspaces/{workspace_id}"
    response = _request("GET", workspace_url, headers=headers, custom_cfg=cfg)
    if response.status_code != 200:
        raise Exception(f"Failed to retrieve workspace {workspace_id}: {response.text}")

    return response.json()

def get_resource_list(resource_type, id=None, date_range=None, name_pattern=None, regex_pattern=False, return_dict=False, source='workspace', custom_cfg=None, logger=None, force_reload=False):
    """
    Unified function to retrieve lists of different resources with filtering options.

    Parameters:
    resource_type (str): The type of resource to retrieve, either 'project', 'enrichment', or 'recording'.
    id (str, optional): The ID of the project or workspace to retrieve resources from.
    date_range (tuple of datetime.date, optional): Range of dates (start_date, end_date) to filter resources.
    name_pattern (str, optional): Unix shell-style wildcard or regex pattern to match resource names.
    regex_pattern (bool, default False): Interpret name_pattern as a regular expression if True.
    return_dict (bool, default False): If True, returns a dictionary of resources with IDs as keys; otherwise, returns a list of IDs.
    source (str, default 'project'): The source of the resource IDs, either 'project' or 'workspace'.

    Returns:
    list: A list of resource IDs for the specified workspace or project.


    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    workspace_id = _cfg_get('workspace_id', cfg)
    if source == 'workspace':
        id = workspace_id
    if logger is None:
        logger = get_logger()
    # Generating a simple cache key to avoid unnecessary API calls
    cache_key = f"{resource_type}_{source}_{id}_{workspace_id}"
    # Check cache first, unless force_reload is True
    if cache_key in _resource_cache and not force_reload:
        logger.info(f"Returning cached {resource_type} data for {source} with id {id}.")
        items = _resource_cache[cache_key]
    else:
        base_url = _cfg_get('base_url', cfg)
        headers = _cfg_get('headers', cfg)
        # Constructing the appropriate API endpoint URL
        if resource_type == 'project':
            url = f"{base_url}/workspaces/{workspace_id}/projects"
        elif resource_type == 'enrichment':
            if id is not None:
                url = f"{base_url}/workspaces/{workspace_id}/projects/{id}/enrichments"
            else:
                logger.error(f"Project id must be specified when listing enrichments")
                return None
        elif resource_type == 'recording':
            if source == 'project':
                if id is not None:
                    url = f"{base_url}/workspaces/{workspace_id}/projects/{id}/recordings"
                else:
                    logger.error(f"Project id must be specified when listing project recordings. Did you intend to list workspace recordings (source='workspace')?")
                    return None
            elif source == 'workspace':
                url = f"{base_url}/workspaces/{workspace_id}/recordings"
        elif resource_type == 'file':
            if id is not None:
                url = f"{base_url}/workspaces/{workspace_id}/recordings/{id}/files"
            else:
                logger.error(f"Recording id must be specified when listing files")
                return None
        response = _request("GET", url, headers=headers, custom_cfg=cfg)
        if response.status_code != 200:
            logger.error(f"Failed to retrieve {resource_type} info for {source} with id {id}: {response.text}")
            return None
        else:
            logger.info(f"Successfully retrieved {resource_type} info for {source} with id {id}.")

        items = response.json()['result']
        _resource_cache[cache_key] = items
        logger.info(f"Cached {resource_type} data for {source} with id {id}.")
    # Apply filters
    filtered_items = [item for item in items if pass_filters(item, resource_type, date_range, name_pattern, regex_pattern)]
    if not filtered_items:
        logger.info(f"No {resource_type} matched the given criteria.")
        return {} if return_dict else []
    if return_dict:
        result = {}
        for item in filtered_items:
            item_id = item.get('id', item.get('recording_id'))
            if item_id is None:
                continue
            result[item_id] = item
        return result
    result = []
    for item in filtered_items:
        item_id = item.get('id', item.get('recording_id'))
        if item_id is None:
            continue
        result.append(item_id)
    return result

# Example usage (commented out):
# project_list = get_resource_list('project', name_pattern="*dyad*", regex_pattern=False, return_dict=True)
# enrichment_list = get_resource_list('enrichment', id="your_project_id", return_dict=False)
# recording_list = get_resource_list('recording', id="your_project_id", source='project', return_dict=False)

def get_file_list(recording_id, workspace_id=None, date_range=None, name_pattern=None, regex_pattern=False, return_dict=False, logger=None, custom_cfg=None, force_reload=False):
    """
    Retrieve a list of files for a specific recording, with options for filtering by date range and name pattern.
    Convenience function that can be replaced by a call to:
    get_resource_list(resource_type='file', id=recording_id, ...)

    Args:
    recording_id (str): The ID of the recording to retrieve files from.
    workspace_id (str, optional): The ID of the workspace.
    date_range (tuple of datetime.date, optional): Range of dates (start_date, end_date) to filter files.
    name_pattern (str, optional): Unix shell-style wildcard or regex pattern to match file names.
    regex_pattern (bool, default False): Interpret name_pattern as a regular expression if True.
    return_dict (bool, default False): If True, returns a dictionary of files with IDs as keys; otherwise, returns a list of IDs.
    logger (Logger, optional): Logger for logging messages.
    custom_cfg (object, optional): Custom configuration object.
    force_reload (bool, default False): If True, bypasses the cache and reloads data.

    Returns:
    list or dict: A list or dictionary of file dictionaries for the specified recording.
    """
    return get_resource_list(
        resource_type='file',
        id=recording_id,
        date_range=date_range,
        name_pattern=name_pattern,
        regex_pattern=regex_pattern,
        return_dict=return_dict,
        source='recording',  # As files are related to recordings
        custom_cfg=custom_cfg,
        logger=logger,
        force_reload=force_reload
    )

def get_project_list(name_pattern=None, workspace_id=None, regex_pattern=False, return_dict=False, custom_cfg=None):
    """
    Retrieve projects for a specific workspace, optionally filtering by project name.
    Convenience function that can be replaced by a call to:
    get_resource_list(resource_type='project', id=workspace_id, ...)

    Parameters:
    name_pattern (str, optional): A Unix shell-style wildcard or regex pattern to filter the projects by name.
    regex_pattern (bool, default False): If True, name_pattern will be interpreted as a regular expression.
    return_dict (bool, default False): If True, returns a dictionary of projects with IDs as keys; otherwise, returns a list of IDs.

    Returns:
    dict or list: A dictionary of projects with IDs as keys or a list of project IDs.

    Examples:
    >>> project_ids = get_project_list(name_pattern="*dyad*", regex_pattern=False)
    >>> project_dicts = get_project_list(name_pattern="*dyad*", regex_pattern=False, return_dict=True)
    >>> print(project_ids)
    >>> print(project_dicts)
    """
    return get_resource_list(
        resource_type='project',
        id=workspace_id,
        name_pattern=name_pattern,
        regex_pattern=regex_pattern,
        return_dict=return_dict,
        source='workspace',  # Assuming projects are always from workspace
        custom_cfg=custom_cfg
    )

def get_enrichment_list(project_id, return_dict=False, custom_cfg=None):
    """
    Retrieve a list of enrichment IDs for a specific project.
    Convenience function that can be replaced by a call to:
    get_resource_list(resource_type='enrichment', id=project_id, ...)

    Parameters:
    project_id (str): The ID of the project to retrieve enrichments from.
    return_dict (bool, default False): If True, returns a dictionary of enrichments with IDs as keys; otherwise, returns a list of IDs.

    Returns:
    list: A list of enrichment IDs for the specified project.

    Examples:
    >>> enrichment_ids = get_enrichment_list("your_project_id")
    >>> print(enrichment_ids)

    """
    return get_resource_list(
        resource_type='enrichment',
        id=project_id,
        return_dict=return_dict,
        source='project',  # Assuming enrichments are always related to a project
        custom_cfg=custom_cfg
    )

def get_recording_list(id, source='project', return_dict=False, custom_cfg=None):
    """
    Retrieve a list of recording IDs for a specific project.
    Convenience function that can be replaced by a call to:
    get_resource_list(resource_type='recording', id=project_id, ...)

    Parameters:
    id (str): The ID of the project or workspace to retrieve recordings from.
    source (str, default 'project'): The source of the recording IDs, either 'project' or 'workspace'.
    return_dict (bool, default False): If True, returns a dictionary of recordings with IDs as keys; otherwise, returns a list of IDs.

    Returns:
    list: A list of recording IDs for the specified project.

    Examples:
    >>> recording_ids = get_recording_list("your_project_id")
    >>> print(recording_ids)

    """
    return get_resource_list(
        resource_type='recording',
        id=id,
        return_dict=return_dict,
        source=source,
        custom_cfg=custom_cfg
    )


def download_project_enrichments(project_id, download_directory=None, name_pattern=None, regex_pattern=False,
                                 logger=None, custom_cfg=None):
    """
    Download all enrichments from a given project that match a specified pattern and have a status of SUCCESS.

    Parameters:
    project_id (str): The ID of the project to download enrichments from.
    download_directory (str): Directory where the enrichments should be downloaded.
    name_pattern (str, optional): A Unix shell-style wildcard or regex pattern to filter the enrichments by name.
    regex_pattern (bool, default False): If True, name_pattern will be interpreted as a regular expression.

    Returns:
    bool: True if all enrichments were downloaded successfully, False otherwise.

    Examples:
    >>> download_project_enrichments("your_project_id", logger, "path/to/download_directory", name_pattern=None, regex_pattern=False, unpack_zip=True)

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if download_directory is None:
        download_directory = _cfg_get('download_directory', cfg)
    base_url = _cfg_get('base_url', cfg)
    workspace_id = _cfg_get('workspace_id', cfg)
    headers = _cfg_get('headers', cfg)
    if logger is None:
        logger = get_logger()
    projects_url = base_url + '/workspaces/' + workspace_id + '/projects'
    enrichments_url = f"{projects_url}/{project_id}/enrichments"
    err = False
    success = False
    logger.info(f"Downloading enrichments for project {project_id}...")
    try:
        response = requests.get(enrichments_url, headers=headers)
        response.raise_for_status()

        enrichments = response.json()['result']


        for enrichment in enrichments:
            # Apply filters
            if not pass_filters(enrichment, item_type='enrichment', name_pattern=name_pattern, regex_pattern=regex_pattern):
                continue

            # Check if the status is SUCCESS
            if enrichment['status']['SUCCESS'] != 1:
                logger.warning(f"Enrichment {enrichment['name']} has status {enrichment['status']}")
                #err = True
            else:
                enrichment_download_directory = os.path.join(download_directory, 'enrichments', enrichment['name'])
                # Ensure download directory exists
                if not os.path.exists(enrichment_download_directory):
                    logger.info(f"Creating download directory: {enrichment_download_directory}")
                    os.makedirs(enrichment_download_directory)
                # Download enrichment
                if not download_enrichment(enrichments_url, enrichment, enrichment_download_directory):
                    logger.error(f"Failed to download enrichment: {enrichment['name']}")
                    err = True
    except Exception as e:
        logger.error(f"Failed to retrieve enrichments for project {project_id}: {e}")
        err = True
    if not err:
        success = True
        logger.info(f"Successfully downloaded all enrichments for project {project_id}")
    return success


def download_enrichment(enrichments_url, enrichment, download_directory=None, logger=None, custom_cfg=None):
    """
    Download a single enrichment.

    Parameters:
    enrichments_url (str): The URL of the enrichments endpoint.
    enrichment (dict): The enrichment to download.
    download_directory (str): The directory where the enrichment should be downloaded.
    logger (logging.Logger): Logger object for logging messages.

    Returns:
    bool: True if the download was successful, False otherwise.
    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    workspace_id = _cfg_get('workspace_id', cfg)
    base_url = _cfg_get('base_url', cfg)
    headers = _cfg_get('headers', cfg)
    if not download_directory:
        download_directory = _cfg_get('download_directory', cfg)
    if not logger:
        logger = get_logger()
    enrichment_export_url = f"{enrichments_url}/{enrichment['id']}/export"
    local_filename = os.path.join(download_directory, f"{enrichment['name']}.zip")

    try:
        download_response = _request("GET", enrichment_export_url, headers=headers, stream=True, custom_cfg=cfg)
        download_response.raise_for_status()

        logger.info(f"Downloading enrichment: {enrichment['name']} id: {enrichment['id']} to {local_filename}...")
        with open(local_filename, 'wb') as f:
            for chunk in download_response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Downloaded enrichment: {enrichment['name']}")
        unpack_zip_file(local_filename, download_directory)
        return True
    except Exception as e:
        logger.error(f"Failed to download enrichment {enrichment['name']}: {e}")
        return False


def bulk_download_project_enrichments(project_ids=None, output_directory=None, workspace_id=None,
                                      name_pattern=None, regex_pattern=False, project_info_json=True, logger=None, custom_cfg=None):
    """
    Bulk download enrichments from a list of project IDs.

    Parameters:
    project_ids (list of str, optional): A list of project IDs to download. If None, all projects in the workspace will be downloaded.
    output_directory (str, optional): The directory where the enrichments should be downloaded.
    name_pattern (str, optional): A Unix shell-style wildcard or regex pattern to filter the enrichments by name.
    regex_pattern (bool, default False): If True, name_pattern will be interpreted as a regular expression.
    project_info_json (bool, default True): If True, a JSON file containing project information will be downloaded for each project.

    Returns:
    None

    Examples:
    >>> bulk_download_project_enrichments(project_ids=["project_id1", "project_id2"], output_directory="path/to/download_directory", name_pattern="*dyad*", regex_pattern=False)

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if workspace_id is None:
        workspace_id = _cfg_get('workspace_id', cfg)
    if output_directory is None:
        output_directory = _cfg_get('download_directory', cfg)
    if logger is None:
        logger = get_logger()
    if project_ids is None:
        project_dicts = get_project_list(return_dict=True)
        project_ids = list(project_dicts.keys())
    else:
        project_dicts = {}
        for project_id in project_ids:
            project_dicts[project_id] = get_project_list(return_dict=True)[project_id]
    failed_projects = []
    logger.info("Starting bulk download of project enrichments")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Project IDs: {project_ids}")
    logger.info(f"Enrichment name pattern: {name_pattern}")
    logger.info(f"Enrichment name regex pattern: {regex_pattern}")
    logger.info(f"Download project info JSON: {project_info_json}")
    for project_id in project_ids:
        proj_name = format_project_name(project_id, project_dicts)
        output_dir = create_project_directory(proj_name, output_directory, project_dicts, project_id)
        if download_project_enrichments(project_id, output_dir, name_pattern, regex_pattern):
            logger.info(f"Successfully downloaded enrichments for project {project_id}")
            if project_info_json:
                project_info_path = os.path.join(output_dir, f"project_{project_id}_info.json")
                try:
                    with open(project_info_path, 'w') as f:
                        json.dump(project_dicts[project_id], f, indent=4)
                    logger.info(f"Project information saved for project {project_id}")
                except Exception as e:
                    logger.error(f"Failed to save project information for project {project_id}: {e}")
                    failed_projects.append(project_id)
        else:
            failed_projects.append(project_id)

    logger.info("Finished bulk download of project enrichments")
    if failed_projects:
        logger.error(f"Failed to download enrichments for the following projects: {failed_projects}")


def bulk_download_recordings(recording_ids=None, output_directory=None, unpack_zip=True, recordings_info_json=True, logger=None, custom_cfg=None):
    """
    Bulk download recordings from a list of recording IDs.
    This is the direct download of the zip from workspace recordings, not recordings within a project.
    recordings within a project are downloaded with bulk_download_projects

    Parameters:
    recording_ids (list of str): A list of recording IDs to download, if None all recordings in the workspace will be downloaded.
    output_directory (str, optional): The directory where the recordings should be downloaded.

    Returns:
    None

    Examples:
    >>> bulk_download_recordings(recording_ids=["recording_id1", "recording_id2"], output_directory="path/to/download_directory")

    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    workspace_id = _cfg_get('workspace_id', cfg)
    if output_directory is None:
        output_directory = _cfg_get('download_directory', cfg)
    if logger is None:
        logger = get_logger()
    logger.info("Starting bulk_download_recordings from workspace")
    logger.info(f"Workspace ID: {workspace_id}")
    all_recording_ids = get_resource_list('recording', id=workspace_id, source='workspace')
    all_recordings_dict = get_resource_list('recording', id=workspace_id, source='workspace', return_dict=True)
    if recording_ids is None:
        recording_ids = all_recording_ids
        recordings_dict = all_recordings_dict
    # otherwise get recordings_dict from list of recording_ids
    else:
        recordings_dict = {}
        for recording_id in recording_ids:
            recordings_dict[recording_id] = all_recordings_dict[recording_id]
    logger.info(f"RecordingIDs: {recording_ids}")
    if recordings_info_json:
        logger.info(f"Saving recordings information for workspace {workspace_id}...")
        # save recordings_dict to json file
        try:
            with open(os.path.join(output_directory, f"workspace_{workspace_id}_recordings.json"), 'w') as f:
                json.dump(recordings_dict, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to save recordings information for workspace {workspace_id}: {e}")
    failed_recordings = []
    for recording_id in recording_ids:
        success = download_recording(recording_id, output_directory, unpack_zip)
        if not success:
            logger.error(f"Failed to download recording {recording_id}")
            failed_recordings.append(recording_id)
    if failed_recordings:
        logger.info(f"Failed to download the following recordings: {failed_recordings}, check the logs for details")
    else:
        logger.info("All recordings downloaded successfully")

def bulk_download_projects(project_ids=None, exclude_enrichment_files=None, exclude_recording_files=None,
                           output_directory=None, all_recordings=True, all_enrichments=True,
                           project_info_json=True, proj_name_pattern=None, proj_regex_pattern=None, unpack_zip=True,
                           logger=None, custom_cfg=None):
    """
    Bulk download recordings and enrichments for specified projects or all projects in a workspace.

    Parameters:
    project_ids (list of str, optional): A list of project IDs to download. If None, all projects in the workspace will be downloaded.
    exclude_enrichment_files (list of str, optional): A list of enrichment file names to exclude from the download.
    exclude_recording_files (list of str, optional): A list of recording file names to exclude from the download.
    output_directory (str, optional): The directory where the projects should be downloaded.
    all_recordings (bool, default True): If True, all recordings will be downloaded for each project.
    all_enrichments (bool, default True): If True, all enrichments will be downloaded for each project.
    project_info_json (bool, default True): If True, a JSON file containing project information will be downloaded for each project.

    Returns:
    None

    Examples:
    >>> bulk_download_projects(project_ids=["project_id1", "project_id2"], exclude_enrichment_files=["enrichment1", "enrichment2"], exclude_recording_files=["recording1", "recording2"], output_directory="path/to/download_directory", all_recordings=True, all_enrichments=True, project_info_json=True)
    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if exclude_enrichment_files is None:
        exclude_enrichment_files = []
    if exclude_recording_files is None:
        exclude_recording_files = []
    if output_directory is None:
        output_directory = _cfg_get('download_directory', cfg)
    if logger is None:
        logger = get_logger()
    base_url = _cfg_get('base_url', cfg)
    headers = _cfg_get('headers', cfg)
    workspace_id = _cfg_get('workspace_id', cfg)
    if project_ids is None:
        project_dicts = get_project_list(name_pattern=proj_name_pattern, regex_pattern=proj_regex_pattern, return_dict=True)
        project_ids = list(project_dicts.keys())
    # otherwise get project_dicts from list of project_ids
    else:
        project_dicts = {}
        for project_id in project_ids:
            project_dicts[project_id] = get_project_list(name_pattern=proj_name_pattern, regex_pattern=proj_regex_pattern, return_dict=True)[project_id]
    failed_projects = []
    logger.info("Starting bulk_download_projects")
    logger.info(f"Workspace ID: {workspace_id}")
    logger.info(f"Project IDs: {project_ids}")
    logger.info(f"Exclude enrichment files: {exclude_enrichment_files}")
    logger.info(f"Exclude recording files: {exclude_recording_files}")
    logger.info(f"Download recordings: {all_recordings}")
    logger.info(f"Download enrichments: {all_enrichments}")
    logger.info(f"Download project info JSON: {project_info_json}")
    for project_id in project_ids:
        proj_name= f"project_{project_id}"
        # if name is not empty string or space, use it, otherwise use project id
        given_proj_name = project_dicts[project_id]['name']
        # convert proj_name to a suitable directory name
        given_proj_name = re.sub('[^0-9a-zA-Z]+', '_', given_proj_name)
        if given_proj_name != "" and given_proj_name != " " and given_proj_name != None and given_proj_name != "_":
            proj_name = given_proj_name
        output_dir = os.path.join(output_directory, proj_name)
        # if output_dir exists, add a timestamp to the directory name
        if os.path.exists(output_dir):
            # add a timestamp to the directory name
            # output_dir = output_dir + datetime.now().strftime("%Y%m%d_%H%M%S")
            # use created_at from project_dict to create a directory name, format is 2021-03-04T14:00:00.000Z, convert to 20210304_140000
            created_at = project_dicts[project_id]['created_at']
            created_at = created_at.replace("T", "_").replace(":","").replace(".","_").replace("Z", "")
            output_dir = (output_dir + "_" + created_at)
        # create the output directory
        # additional safety-net need to not overwrite anything
        if os.path.exists(output_dir):
            output_dir = output_dir + datetime.now().strftime("%Y%m%d_%H%M%S")
        # create the output directory
        os.makedirs(output_dir, exist_ok=True)

        if all_recordings:
            recordings = get_recording_list(project_id, source='project')
            recordings_dict = get_recording_list(project_id, source='project', return_dict=True)
        if all_enrichments:
            enrichments = get_enrichment_list(project_id)
            enrichments_dict = get_enrichment_list(project_id, return_dict=True)
        project_download_url = f"{base_url}/workspaces/{workspace_id}/projects/{project_id}/download"
        # Prepare the payload, depending on whether we download all recordings and/or enrichments
        if all_recordings and all_enrichments:
            payload = {
            'recordings': [{'recording_id': recording, 'exclude_files': exclude_recording_files} for recording in recordings],
            'enrichments': [{'enrichment_id': enrichment, 'exclude_files': exclude_enrichment_files} for enrichment in enrichments]
            }
        elif all_recordings:
            payload = {
            'recordings': [{'recording_id': recording, 'exclude_files': exclude_recording_files} for recording in recordings]
            }
        elif all_enrichments:
            payload = {
            'enrichments': [{'enrichment_id': enrichment, 'exclude_files': exclude_enrichment_files} for enrichment in enrichments]
            }
        #save project information to json file
        if project_info_json:
            logger.info(f"Saving project information for project {project_id}...")
            # save proj_dict to json file
            try:
                with open(os.path.join(output_dir, f"project_{project_id}.json"), 'w') as f:
                    json.dump(project_dicts[project_id], f, indent=4)
                # save enrichment and recordings lists to json files
                if all_recordings:
                    with open(os.path.join(output_dir, f"project_{project_id}_recordings.json"), 'w') as f:
                        json.dump(recordings_dict, f, indent=4)
                if all_enrichments:
                    with open(os.path.join(output_dir, f"project_{project_id}_enrichments.json"), 'w') as f:
                        json.dump(enrichments_dict, f, indent=4)
            except Exception as e:
                logger.error(f"Failed to save project information for project {project_id}: {e}")
                failed_projects.append(project_id)
        if all_recordings or all_enrichments:
            logger.info(f"Preparing download for project {project_id}...")
            response = _request("POST", project_download_url, json=payload, headers=headers, stream=True, custom_cfg=cfg)
            if response.status_code != 200:
                logger.error(f"Failed to retrieve data for project {project_id}: {response.text}")
                logger.error(f"Skipping project {project_id}")
                failed_projects.append(project_id)
            else:
                # Download the data in chunks and save to disk
                local_filename = os.path.join(output_dir, f"project_{project_id}.zip")
                logger.info(f"Downloading and saving data for project {project_id} to {local_filename} ...")
                try:
                    with open(local_filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:  # filter out keep-alive new chunks
                                f.write(chunk)
                    logger.info(f"Downloaded data for project {project_id}")
                except Exception as e:
                    logger.error(f"Failed to download data for project {project_id}: {e}")
                    failed_projects.append(project_id)
                try:
                    if unpack_zip:
                        logger.info(f"Unpacking data from {local_filename}...")
                        unpack_zip_file(local_filename, output_dir,  logger)
                except Exception as e:
                    logger.error(f"Failed to unpack data for project {project_id}: {e}")
                    failed_projects.append(project_id)
        else:
            logger.error(f"to download the data of project {project_id} set either all_enrichments or all_recordings to True")

        logger.info(f"Downloaded data for project {project_id}")
    logger.info("Finished bulk_download_projects")
    if failed_projects:
        logger.error(f"Failed to download data for the following projects: {failed_projects}, check the logs for details")
