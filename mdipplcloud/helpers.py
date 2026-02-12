import logging
import os
from datetime import datetime
import configparser
import zipfile
import re
import fnmatch

# Modifying the Config class to include getter methods for headers, recordings_url, and projects_url

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls.api_key = None
            cls.workspace_id = None
            cls.base_url = None
            cls.download_directory = None
            cls.timeout = None
            cls.logger_name = None
        return cls._instance

    @classmethod
    def load_config(cls, optional_file_path=None):
        config = configparser.ConfigParser()
        file_path = optional_file_path or 'config.ini'
        try:
            config.read(file_path)
        except Exception as e:
            raise RuntimeError(f"Error reading config file: {e}")

        cls.api_key = config['API']['key']
        cls.workspace_id = config['API']['workspace_id']
        cls.base_url = config['API']['base_url']
        cls.download_directory = config['Download']['directory']
        # if download_directory is not set, use current directory
        if cls.download_directory == "":
            cls.download_directory = os.getcwd()
        # if download_directory is not an absolute path, make it one
        if not os.path.isabs(cls.download_directory):
            cls.download_directory = os.path.join(os.getcwd(), cls.download_directory)
        # create download directory if it doesn't exist
        os.makedirs(cls.download_directory, exist_ok=True)
        return cls

    @classmethod
    def get_headers(cls):
        if cls.api_key is None:
            raise ValueError("API Key not set. Please load the configuration first.")
        return {
            "X-API-Key": cls.api_key,
            "Content-Type": "application/json"
        }
    @classmethod
    def is_config_loaded(cls):
        if cls.api_key is None or cls.workspace_id is None or cls.base_url is None:
            return False
        return True
    @classmethod
    def get_config(cls):
        if not cls.is_config_loaded():
            raise ValueError("Configuration not loaded. Please call Config.load_config() first.")
        return cls
    @classmethod
    def get_recordings_url(cls):
        if cls.base_url is None or cls.workspace_id is None:
            raise ValueError("Base URL or Workspace ID not set. Please load the configuration first.")
        return f"{cls.base_url}/workspaces/{cls.workspace_id}/recordings"

    @classmethod
    def get_projects_url(cls):
        if cls.base_url is None or cls.workspace_id is None:
            raise ValueError("Base URL or Workspace ID not set. Please load the configuration first.")
        return f"{cls.base_url}/workspaces/{cls.workspace_id}/projects"

# Usage:
# cfg = Config.load_config()
# headers = cfg.get_headers()
# recordings_url = cfg.get_recordings_url()
# projects_url = cfg.get_projects_url()

def load_config(optional_file_path=None):
    """
    Loads the configuration from the config.ini file.
    Args:
        optional_file_path:
    """
    return Config.load_config(optional_file_path)

#simplified convenience method to get values that depend on the config file
def cfg_get(key): #e.g. 'headers', 'recordings_url', 'projects_url'
    cls = Config
    #if not cls.is_config_loaded():
    #    raise ValueError("Configuration not loaded. Please call load_config() first.")
    try:
        if key == 'headers':
            return cls.get_headers()
        elif key == 'api_key':
            return cls.api_key
        elif key == 'workspace_id':
            return cls.workspace_id
        elif key == 'base_url':
            return cls.base_url
        elif key == 'projects_url':
            return cls.get_projects_url()
        elif key == 'download_directory':
            return cls.download_directory
        else:
            raise ValueError(f"Unknown config value: {key}")
    except Exception as e:
        raise ValueError(f"Error getting config value, did you use load_config()?  {e}")

def setup_logging(log_directory=None, workspace_id=None, enable_console_logging=True, enable_file_logging=True,
                  log_filename=None, get_workspace_info=None, custom_cfg=None, append=True):
    """
    Sets up logging for the application with optional console and file handlers.

    Parameters:
    download_directory (str): The directory where the log file will be saved.
    workspace_id (str, optional): The workspace ID used for naming the log file.
    enable_console_logging (bool): Enable logging to the console.
    enable_file_logging (bool): Enable logging to a file.
    log_filename (str): Optional custom filename for the log file.
    get_workspace_info (function): Optional function to get workspace information.

    Returns:
    logging.Logger: The configured logger object.

    Examples:
    >>> logger = setup_logging('.')
    """
    if custom_cfg is None:
        cfg = Config.get_config()
    else:
        cfg = custom_cfg
    if log_directory is None:
        log_directory = cfg_get('download_directory')
    if workspace_id is None:
        workspace_id = cfg_get('workspace_id')
    logger_name = 'pupilcloudwrapper_logger'
    logger = logging.getLogger(logger_name) # Naming the logger
    # add logger name to Config class
    if not logger.handlers:  # Ensures singleton pattern: only add handlers if not already added
        # Define a format for the log messages
        Config.logger_name = logger_name
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logger.setLevel(logging.INFO)

        # Setup console logging
        if enable_console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(console_handler)

        # Setup file logging
        if enable_file_logging:
            if log_filename is None:
                # Use workspace_id in the filename if it's provided
                log_filename = "pcwlogger"
                if workspace_id:
                    log_filename += f"_{workspace_id}"
                if append is False:
                    log_filename += f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            logfile = os.path.join(log_directory, log_filename)
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(logging.Formatter(log_format))
            logger.addHandler(file_handler)

        # Log workspace info if the function and workspace_id are provided
        if get_workspace_info and workspace_id:
            workspace_info = get_workspace_info(workspace_id)
            logger.info(f"Workspace info: {workspace_info}")

    return logger

# utility function to get the configured logger
def get_logger():
    """
    Utility function to get the configured logger.
    This function should be imported and used by other modules in the package.
    """
    logger = logging.getLogger('pupilcloudwrapper_logger')
    # if no configured logger setup, setup a default one in current directory
    if not logger.handlers:
        logger = setup_logging('.')
    return logger


# def load_config(optional_file_path=None):
#     """
#     Loads the configuration from the config.ini file.
#     Args:
#         optional_file_path:
#
#     Returns:
#         api_key, base_url, download_directory
#     Examples:
#         >>> api_key, base_url, download_directory = load_config()
#         >>> api_key, base_url, download_directory = load_config("my/path/config.ini")
#     """
#     config = configparser.ConfigParser()
#     if optional_file_path:
#         file_path = optional_file_path
#     else:
#         file_path = 'config.ini'
#     try:
#         config.read(file_path)
#     except:
#         # throw an error and exit
#         print("No config.ini file found!")
#         exit()
#     api_key = config['API']['key']
#     base_url = config['API']['base_url']
#     download_directory = config['Download']['directory']
#     workspace_id = config['API']['workspace_id']
#     return api_key, workspace_id, base_url, download_directory


def create_project_directory(proj_name, output_directory, project_dicts, project_id):
    """
    Creates a directory for the project, appending a timestamp if it already exists.
    """
    output_dir = os.path.join(output_directory, proj_name)
    if os.path.exists(output_dir):
        created_at = project_dicts[project_id].get('created_at', datetime.now().strftime("%Y%m%d_%H%M%S")).replace("T",
                                                                                                                   "_").replace(
            ":", "").replace(".", "_").replace("Z", "")
        output_dir += "_" + created_at
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def format_project_name(project_id, project_dicts):
    """
    Formats the project name for directory creation.
    """
    given_proj_name = project_dicts.get(project_id, {}).get('name', f"project_{project_id}")
    return re.sub('[^0-9a-zA-Z]+', '_', given_proj_name)


def _is_within_directory(directory, target):
    abs_directory = os.path.abspath(directory)
    abs_target = os.path.abspath(target)
    return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])


def unpack_zip_file(zip_filename, output_directory=None, logger=None):
    """
    Utility function to unpack a downloaded ZIP file.

    Parameters:
    zip_filename (str): Path of the ZIP file to be unpacked.
    output_directory (str): Directory where the contents of the ZIP file should be extracted.
    logger (logging.Logger): Logger object for logging messages.

    Returns:
    bool: True if the unpacking was successful, False otherwise.

    Examples:
    >>> unpack_zip_file("path/to/zip/file.zip", "path/to/output/directory")

    """
    if logger is None:
        logger = get_logger()
    if output_directory is None:
        output_directory = cfg_get('download_directory')
    try:
        with zipfile.ZipFile(zip_filename, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.join(output_directory, member.filename)
                if not _is_within_directory(output_directory, member_path):
                    logger.error(f"Unsafe ZIP path detected: {member.filename}")
                    return False
            for member in zip_ref.infolist():
                zip_ref.extract(member, output_directory)
        os.remove(zip_filename)
        logger.info(f"Successfully unpacked and removed ZIP file: {zip_filename}")
        return True
    except zipfile.BadZipFile as e:
        logger.error(f"Bad ZIP file error: {e}")
    except zipfile.LargeZipFile as e:
        logger.error(f"Large ZIP file error (file exceeds ZipFile's size limit): {e}")
    except Exception as e:
        logger.error(f"An error occurred while unpacking the ZIP file: {e}")
    return False


def pass_filters(item, item_type='file', date_range=None, name_pattern=None,
                 regex_pattern=False, id=None, recording_id=None):
    """
    Check if an item (file or resource) passes the given filters.

    Args:
    item (dict): The file or ressource to check.
    item_type (str): Type of the item ('file' or 'enrichment' or 'project' or 'recording').
    date_range (tuple): The range of dates to filter files.
    name_pattern (str): Pattern to match the name of the file or enrichment.
    regex_pattern (bool): If True, treat name_pattern as a regular expression.
    id (int): The id to filter files.
    recording_id (int): The recording id to filter files.

    Returns:
    bool: True if the item passes all filters, False otherwise.
    """
    # Filter by name pattern
    if name_pattern:
        regex = re.compile(name_pattern) if regex_pattern else re.compile(fnmatch.translate(name_pattern))
        if not regex.match(item['name']):
            return False

    # Filter by id
    try:
        if id and item['id'] != id:
            return False
    except KeyError:
        pass

    # Additional filters just for files
    if item_type == 'file':
        # Filter by date range
        if date_range:
            created_at = datetime.strptime(item['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            if not date_range[0] <= created_at <= date_range[1]:
                return False

        # Filter by recording id
        if recording_id and item['recording_id'] != recording_id:
            return False

    return True
