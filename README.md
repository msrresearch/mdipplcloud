# mdipplcloud: Pupil Labs Cloud API Wrapper

**A Python wrapper for the Pupil Labs Cloud API** – enabling efficient interaction and data management.  
This submodule is **standalone** but also integrates seamlessly into the [mdivicomtools](https://github.com/msrresearch/mdivicomtools) umbrella repository.

---

## Overview

`mdipplcloud` is designed for researchers and developers working with Pupil Labs eye trackers. It streamlines the process of accessing and handling eye-tracking data stored in Pupil Cloud (API v2). The current focus is on **downloading** data, but future updates may expand functionality.

### Features
- **API v2 usage**: Connect to Pupil Labs Cloud with your custom API key and workspace ID.  
- **Download Recordings**: Download entire recordings (ZIP-based) from Pupil Cloud.  
- **Download Specific Files**: Filter individual or multiple files by name, date range, or patterns.  
- **Workspace & Project Tools**: Retrieve and process information about your workspace(s), projects, and associated recordings/enrichments.  
- **Bulk Operations**: Download data from multiple projects at once, saving time for large datasets.  
- **Customizability**: Easily filter or refine your download criteria.  
- **Logging**: Comprehensive logs for tracking operations and debugging.

---

## Prerequisites

- **Pupil Labs API key** and **workspace ID**  
- **Python 3.x**  
- Libraries: `requests`, `json`, `os`, `zipfile`, `re`, `fnmatch`, `datetime`, `logging` (Most are in the Python standard library, but ensure you have `requests` installed).

---

## Installation

1. **Clone this repository**:
   ```bash
   git clone https://github.com/yourname/mdipplcloud.git
   cd mdipplcloud
   ```

2. Install:
    ```bash
	pip install .
    ```

	Or for local development:
	```
	pip install -e .
	```

3. (Optional) Integration with mdivicomtools
- If you use this repository within mdivicomtools, you can simply add this repository as a Git submodule or install it via pip install -e ./mdipplcloud within the umbrella environment.

⸻

## Configuration
	1.	Copy the config_template.ini file to a new file, e.g. config.ini.
	2.	Open config.ini and enter your API key, base URL, and download directory.
	3.	Keep config.ini private (especially your API key). If you keep it in your repo, add config.ini to .gitignore.
	4.	Load the config in your Python script:

```python
import mdipplcloud as pplc

# If config.ini is in the same directory as your script:
pplc.load_config()

# Or provide a custom path:
pplc.load_config("path/to/config.ini")
```

⸻

## Example Usage

```python
# Setup
import mdipplcloud as pplc

# Load config
pplc.load_config()

# Initialize logger (logs to download directory)
logger = pplc.setup_logging()

# Download a Single Recording
pplc.download_recording("recording_id_here", logger=logger)

# Bulk Download from Multiple Projects
project_ids = ['project1_id', 'project2_id']
pplc.bulk_download_projects(project_ids=project_ids)

# Fetch Project/Workspace Info
workspace_info = pplc.get_workspace_info()
print("Workspace info:", workspace_info)

# Download Specific Files
file_list = pplc.get_file_list("specific_recording_id", return_dict=True)
pplc.download_files(file_list, logger=logger)
```

For more usage examples, see example_script.py.

⸻

## Caution
- Not extensively tested for all use cases. Use at your own risk.
- Empty download directories recommended to avoid accidental file overwrites.
- Always manage your API keys and config files securely.

⸻

## Citation
If you use this code in your research, please cite
- www.github.com/msrresearch/mdivicomtools

## License

This work is licensed under the MIT License. Copyright (c) 2025 Martin Schulte-Rüther
⸻

## Contributing
1. Fork this repository and clone it locally.
2. Create a feature branch, e.g. git checkout -b feature/new-download-mode.
3. Make changes and test them locally.
4. Submit a Pull Request to the main branch of mdipplcloud.

⸻
