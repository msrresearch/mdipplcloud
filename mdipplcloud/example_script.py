import mdipplcloud as pplc
import os

## Load config file with your custom settings (config.ini file in the current directory)
pplc.load_config()
# setup a logger, if no logger is setup explicitely, a default logger will be used
pplc.setup_logging() # creates a logfile in the download directory

## Example usage

# Replace 'recording_id' with an actual recording ID
recording_id="your_recording_id"
recording_ids=["your_recording_id"]
# Replace 'project_id' with an actual project ID
project_id = "your_project_id"

## Get a list of all projects of a workspace; recordings and enrichments of a project; files of a recording
project_list = pplc.get_resource_list('project', regex_pattern=False, return_dict=True)
enrichment_list = pplc.get_resource_list('enrichment', source= 'project', id=project_id, return_dict=True)
recording_list = pplc.get_resource_list('recording', source='workspace', return_dict=True)
file_list = pplc.get_resource_list('file', source='recording', id=recording_id, return_dict=True)

# Download all files from a recording (zipped) (raw recordings from workspace, like device data)
pplc.download_recording(recording_id)
## Bulk download all recordings (raw recordings from workspace, like device data)
pplc.bulk_download_recordings(recording_ids=recording_ids)

## Download matching files from a recording (file by file)
# Replace 'recording_id' with the actual ID of the recording you want to download
test_record = recording_id
file_list = pplc.get_file_list(test_record, name_pattern="*.json", regex_pattern=False, return_dict=True)
pplc.download_files(file_list)

## Bulk download enrichments and recordings from a list of projects
project_ids = pplc.get_project_list(name_pattern="*dyad*")  # Replace '*pattern*' with your filter pattern
pplc.bulk_download_projects(project_ids=project_ids, exclude_enrichment_files=[], exclude_recording_files=[])

## Bulk download enrichments and recordings from all projects in a workspace
pplc.bulk_download_projects(exclude_enrichment_files=[], exclude_recording_files=[])

## If the bulk download fails, try downloading just the enrichments
## Download all enrichments from a single project
pplc.download_project_enrichments(project_id, name_pattern="*raw*")
## Bulk download enrichments from a list of projects
project_ids = pplc.get_project_list(name_pattern="*dyad*")
pplc.bulk_download_project_enrichments(project_ids=project_ids)