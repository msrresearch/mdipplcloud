# mdipplcloud: Pupil Labs Cloud API Wrapper

**A Python wrapper for the Pupil Labs Cloud API** - enabling efficient interaction and data management.  
This repository is a **standalone package** and also integrates as an optional plugin for [mdivicomtools](https://github.com/msrresearch/mdivicomtools).

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
   git clone https://github.com/msrresearch/mdipplcloud.git
   cd mdipplcloud
   ```

2. Install:
    ```bash
    pip install .
    ```

   Or for local development:
   ```bash
   pip install -e .
   ```

3. (Optional) Install into an existing mdivicomtools environment
- Keep plugin installation package-based (no submodule required):
  ```bash
  pip install git+https://github.com/msrresearch/mdipplcloud.git
  ```

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
import mdipplcloud as pplc

# Load config.ini from the current directory (or pass an explicit path)
pplc.load_config()

# Configure logging (defaults to console + file in the download directory)
logger = pplc.setup_logging()

# Download one recording ZIP and unpack it
pplc.download_recording("recording_id_here", unpack_zip=True, logger=logger)

# List recordings from the workspace (dict form for downstream processing)
recordings = pplc.get_resource_list(
    "recording",
    source="workspace",
    return_dict=True,
)

# List files for a recording and download them
file_list = pplc.get_file_list("recording_id_here", return_dict=True)
pplc.download_files(file_list, logger=logger)

# Bulk download recordings from workspace IDs
pplc.bulk_download_recordings(recording_ids=["recording_id_here"], logger=logger)

# Bulk download project recordings/enrichments
pplc.bulk_download_projects(
    project_ids=["project_id_here"],
    exclude_enrichment_files=[],
    exclude_recording_files=[],
    logger=logger,
)
```

Canonical runnable reference: `mdipplcloud/example_script.py`.

⸻

## mdivicom Plugin Usage (v0.1)

`mdipplcloud` is also registered as an `mdivicomtools` plugin via the `mdivicomtools.plugins` entry-point group.

### Discover and inspect

```bash
mdivicom plugins list
mdivicom plugins info mdipplcloud
```

### Run through mdivicom

```bash
mdivicom run mdipplcloud \
  --dataset /path/to/input_dataset \
  --out /path/to/run_output \
  --config '{"recording_ids":["recording_id_here"],"cloud":{"api_key":"***","workspace_id":"***","base_url":"https://api.cloud.pupil-labs.com"}}'
```

Contract notes:
- Registration uses v0.1 JSON-safe shape: `{"meta": {...}, "entry": {"callable": "mdipplcloud.plugin:run"}}`.
- Python execution entrypoint is `run(dataset_dir, out_dir, config, *, work_dir=None, dry_run=False)`.
- Plugin outputs are plugin-scoped under `out_dir/`:
  - `out_dir/dataset/**`
  - `out_dir/provenance.json`
  - `out_dir/resultbundle.json`

⸻

## Contract Checks (API Compatibility)

To verify whether the live Pupil Cloud API still matches what this package expects, run the opt-in pytest contract tests. These hit the real API and validate response shape and required fields, without downloading data.

Enable the tests by setting `PPL_CLOUD_CONTRACT=1` and provide credentials via `config.ini` or env vars.

Example (using a config file):
```bash
PPL_CLOUD_CONTRACT=1 \
PPL_CLOUD_CONFIG=/path/to/config.ini \
pytest mdipplcloud/tests/test_contract_api.py
```

Example (using env vars):
```bash
PPL_CLOUD_CONTRACT=1 \
PPL_CLOUD_API_KEY=your_api_key \
PPL_CLOUD_WORKSPACE_ID=your_workspace_id \
PPL_CLOUD_BASE_URL=https://api.cloud.pupil-labs.com/v2 \
pytest mdipplcloud/tests/test_contract_api.py
```

Optional environment variables:
- `PPL_CLOUD_PROJECT_ID` to force a stable project for project-scoped checks.
- `PPL_CLOUD_RECORDING_ID` to force a stable recording for file checks.
- `PPL_CLOUD_TIMEOUT` to adjust HTTP timeout (seconds).

These tests are intended to be run occasionally (for example before releases) to detect breaking API changes early.

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
