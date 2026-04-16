import json
import logging
from hashlib import sha256
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .downloader import download_recording


API_VERSION = "mdivicomtools.plugin.v0.1"
PLUGIN_ID = "mdipplcloud"
ENTRY_CALLABLE = "mdipplcloud.plugin:run"
RESULTBUNDLE_TYPE = "mdipplcloud.dataset.v0"
RESULTBUNDLE_SCHEMA_VERSION = "0.1.0"
MAX_RESULTBUNDLE_FILES = 500
SENSITIVE_KEY_MARKERS = ("api_key", "key", "token", "secret", "password")


class _RuntimeConfig:
    def __init__(self, api_key, workspace_id, base_url, download_directory, timeout=None):
        self.api_key = api_key
        self.workspace_id = workspace_id
        self.base_url = base_url
        self.download_directory = download_directory
        self.timeout = timeout

    def get_headers(self):
        return {"X-API-Key": self.api_key, "Content-Type": "application/json"}

    def get_projects_url(self):
        return f"{self.base_url}/workspaces/{self.workspace_id}/projects"


def _get_version():
    try:
        return version("mdipplcloud")
    except PackageNotFoundError:
        return "0.0.0+local"


def _now_utc():
    return datetime.now(timezone.utc).isoformat()


def _new_run_id():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _config_sha256(config):
    payload = json.dumps(config or {}, sort_keys=True, default=str).encode("utf-8")
    return sha256(payload).hexdigest()


def _build_logger(logger=None):
    if logger is not None:
        return logger
    plugin_logger = logging.getLogger("mdipplcloud.plugin")
    if not plugin_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        plugin_logger.addHandler(handler)
    plugin_logger.setLevel(logging.INFO)
    return plugin_logger


def _normalize_recording_ids(config):
    recording_ids = config.get("recording_ids", config.get("download_recording_ids", []))
    if isinstance(recording_ids, str):
        return [recording_ids]
    if recording_ids is None:
        return []
    return list(recording_ids)


def _cloud_setting(config, key):
    cloud_config = config.get("cloud", {})
    if isinstance(cloud_config, dict) and key in cloud_config:
        return cloud_config[key]
    return config.get(key)


def _redact(value, key_hint=None):
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, key_hint) for v in value]
    if key_hint and any(marker in key_hint.lower() for marker in SENSITIVE_KEY_MARKERS):
        return "***REDACTED***"
    return value


def _write_json(path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)


def _collect_relative_files(path_root):
    if not path_root.exists():
        return []
    return sorted(
        str(file_path.relative_to(path_root))
        for file_path in path_root.rglob("*")
        if file_path.is_file()
    )


def _file_format_from_path(rel_path):
    suffix = Path(rel_path).suffix.lower().lstrip(".")
    return suffix or "binary"


def _write_input_dataset_manifest(dataset_dir, output_dir):
    if not dataset_dir.exists():
        return None
    files = _collect_relative_files(dataset_dir)
    manifest = {
        "dataset_dir": str(dataset_dir),
        "file_count": len(files),
        "sample_files": files[:200],
    }
    manifest_path = output_dir / "input_dataset_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _write_resultbundle(output_root, output_dataset_dir, run_id):
    files = _collect_relative_files(output_dataset_dir)
    resultbundle_files = []
    for rel_path in files[:MAX_RESULTBUNDLE_FILES]:
        resultbundle_files.append(
            {
                "role": "artifact",
                "path": f"dataset/{rel_path}",
                "format": _file_format_from_path(rel_path),
                "required": False,
            }
        )

    resultbundle = {
        "resultbundle_type": RESULTBUNDLE_TYPE,
        "schema_version": RESULTBUNDLE_SCHEMA_VERSION,
        "created_at": _now_utc(),
        "upstream_tool": "pupilcloud",
        "producer": {
            "tool_ref": "msrresearch/mdipplcloud",
            "tool_version": _get_version(),
            "pipeline_run_id": run_id,
        },
        "time_reference": {"kind": "timestamp", "unit": "ns"},
        "files": resultbundle_files,
    }
    if len(files) > MAX_RESULTBUNDLE_FILES:
        resultbundle["warnings"] = [
            f"resultbundle_file_inventory_truncated:{len(files)}>{MAX_RESULTBUNDLE_FILES}"
        ]

    resultbundle_path = output_root / "resultbundle.json"
    _write_json(resultbundle_path, resultbundle)
    return resultbundle_path


def get_plugin():
    return {
        "meta": {
            "api_version": API_VERSION,
            "id": PLUGIN_ID,
            "kind": "python",
            "version": _get_version(),
            "publisher": "msrresearch",
            "description": "Pupil Cloud downloader plugin for mdivicomtools.",
            "inputs": [
                {
                    "name": "dataset_root",
                    "path_globs": ["**/*"],
                }
            ],
            "outputs": [
                {"name": "dataset", "paths": ["dataset/**"]},
                {"name": "provenance", "paths": ["provenance.json"]},
                {"name": "resultbundle", "paths": ["resultbundle.json"]},
            ],
            "config_schema": {
                "type": "object",
                "properties": {
                    "recording_ids": {"type": "array", "items": {"type": "string"}},
                    "download_recording_ids": {"type": "array", "items": {"type": "string"}},
                    "unpack_zip": {"type": "boolean"},
                    "timeout": {"type": "number"},
                    "cloud": {
                        "type": "object",
                        "properties": {
                            "api_key": {"type": "string"},
                            "workspace_id": {"type": "string"},
                            "base_url": {"type": "string"},
                        },
                    },
                },
            },
        },
        "entry": {"callable": ENTRY_CALLABLE},
    }


def run(dataset_dir=None, out_dir=None, config=None, *, work_dir=None, dry_run=False, logger=None, **kwargs):
    config = dict(config or {})
    out_dir = out_dir or kwargs.get("plugin_out_dir") or config.get("plugin_out_dir")
    if out_dir is None:
        raise ValueError("out_dir (or plugin_out_dir for compatibility) is required for mdipplcloud.plugin:run")

    logger = _build_logger(logger)
    output_root = Path(out_dir)
    output_dataset_dir = output_root / "dataset"
    output_dataset_dir.mkdir(parents=True, exist_ok=True)
    work_dir_path = Path(work_dir).expanduser() if work_dir else None
    if work_dir_path is not None:
        work_dir_path.mkdir(parents=True, exist_ok=True)

    run_id = _new_run_id()
    run_started_at = _now_utc()
    actions = []
    warnings = []

    source_dataset_dir = dataset_dir or config.get("dataset_dir")
    if source_dataset_dir:
        source_dataset_dir = Path(source_dataset_dir)
        manifest_path = _write_input_dataset_manifest(source_dataset_dir, output_dataset_dir)
        if manifest_path:
            actions.append("indexed_input_dataset")
        else:
            warnings.append(f"dataset_dir_not_found:{source_dataset_dir}")

    recording_ids = _normalize_recording_ids(config)
    downloaded_recordings = []
    failed_recordings = []
    skipped_recordings = []

    if recording_ids:
        if dry_run:
            skipped_recordings = list(recording_ids)
            actions.append("dry_run_skipped_downloads")
        else:
            api_key = _cloud_setting(config, "api_key")
            workspace_id = _cloud_setting(config, "workspace_id")
            base_url = _cloud_setting(config, "base_url")
            timeout = _cloud_setting(config, "timeout")
            if not all([api_key, workspace_id, base_url]):
                skipped_recordings = recording_ids
                warnings.append("missing_cloud_config_for_download")
                logger.warning("Skipping recording downloads: missing api_key/workspace_id/base_url in config.")
            else:
                runtime_cfg = _RuntimeConfig(
                    api_key=api_key,
                    workspace_id=workspace_id,
                    base_url=base_url,
                    download_directory=str(output_dataset_dir),
                    timeout=timeout,
                )
                unpack_zip = bool(config.get("unpack_zip", True))
                for recording_id in recording_ids:
                    if download_recording(
                        recording_id,
                        output_directory=str(output_dataset_dir),
                        unpack_zip=unpack_zip,
                        logger=logger,
                        custom_cfg=runtime_cfg,
                    ):
                        downloaded_recordings.append(recording_id)
                    else:
                        failed_recordings.append(recording_id)
                actions.append("downloaded_requested_recordings")

    resultbundle_path = _write_resultbundle(output_root, output_dataset_dir, run_id)
    actions.append("wrote_resultbundle_sidecar")

    status = "ok"
    if dry_run and recording_ids:
        status = "dry_run"
    elif failed_recordings:
        status = "partial"
    elif skipped_recordings and not downloaded_recordings:
        status = "no_download"

    result = {
        "status": status,
        "run_id": run_id,
        "plugin_id": PLUGIN_ID,
        "plugin_version": _get_version(),
        "entry": ENTRY_CALLABLE,
        "out_dir": str(output_root),
        "work_dir": str(work_dir_path) if work_dir_path is not None else None,
        "dataset_output_dir": str(output_dataset_dir),
        "resultbundle_path": str(resultbundle_path),
        "dry_run": bool(dry_run),
        "downloaded_recordings": downloaded_recordings,
        "failed_recordings": failed_recordings,
        "skipped_recordings": skipped_recordings,
        "warnings": warnings,
        "actions": actions,
        "config_sha256": _config_sha256(config),
        "started_at": run_started_at,
        "finished_at": _now_utc(),
    }

    provenance = {
        "plugin": get_plugin(),
        "result": result,
        "inputs": {
            "dataset_dir": str(source_dataset_dir) if source_dataset_dir else None,
            "out_dir": str(output_root),
            "work_dir": str(work_dir_path) if work_dir_path is not None else None,
            "recording_ids_requested": recording_ids,
            "config": _redact(config),
        },
    }
    _write_json(output_root / "provenance.json", provenance)
    return result
