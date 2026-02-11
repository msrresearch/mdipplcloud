import configparser
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytest
import requests

DEFAULT_BASE_URL = "https://api.cloud.pupil-labs.com/v2"
API_TIMEOUT = float(os.getenv("PPL_CLOUD_TIMEOUT", "20"))

RUN_CONTRACT = os.getenv("PPL_CLOUD_CONTRACT", "").strip().lower() in {"1", "true", "yes"}
if not RUN_CONTRACT:
    pytest.skip(
        "Set PPL_CLOUD_CONTRACT=1 to run live API contract tests.",
        allow_module_level=True,
    )


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    workspace_id: str
    api_key: str


def _read_ini(path: Path) -> ApiConfig:
    parser = configparser.ConfigParser()
    parser.read(path)
    try:
        api_key = parser["API"]["key"].strip()
        workspace_id = parser["API"]["workspace_id"].strip()
        base_url = parser["API"].get("base_url", DEFAULT_BASE_URL).strip()
    except KeyError as exc:
        raise RuntimeError(f"Missing config key {exc} in {path}") from exc
    return ApiConfig(base_url=base_url, workspace_id=workspace_id, api_key=api_key)


@pytest.fixture(scope="session")
def api_config() -> ApiConfig:
    env_key = os.getenv("PPL_CLOUD_API_KEY", "").strip()
    env_ws = os.getenv("PPL_CLOUD_WORKSPACE_ID", "").strip()
    env_base = os.getenv("PPL_CLOUD_BASE_URL", DEFAULT_BASE_URL).strip()
    if env_key and env_ws:
        return ApiConfig(base_url=env_base, workspace_id=env_ws, api_key=env_key)

    cfg_path = os.getenv("PPL_CLOUD_CONFIG", "").strip()
    if cfg_path:
        return _read_ini(Path(cfg_path))

    if Path("config.ini").exists():
        return _read_ini(Path("config.ini"))

    pytest.skip(
        "Set PPL_CLOUD_API_KEY/PPL_CLOUD_WORKSPACE_ID or PPL_CLOUD_CONFIG, or provide config.ini",
        allow_module_level=True,
    )


def _headers(api_config: ApiConfig) -> dict:
    return {"X-API-Key": api_config.api_key, "Content-Type": "application/json"}


def _get_json(url: str, headers: dict) -> dict:
    response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
    assert response.status_code == 200, f"GET {url} -> {response.status_code}: {response.text[:300]}"
    payload = response.json()
    assert isinstance(payload, dict), f"Expected JSON object from {url}"
    return payload


def _assert_result_list(payload: dict, url: str) -> list:
    assert "result" in payload, f"Missing 'result' in response from {url}"
    items = payload["result"]
    assert isinstance(items, list), f"Expected 'result' list from {url}"
    return items


def _require_keys(item: dict, keys: List[str], context: str) -> None:
    for key in keys:
        assert key in item, f"Missing key '{key}' in {context} item: {item}"


def _pick_id(items: List[dict]) -> Optional[str]:
    for item in items:
        if "id" in item:
            return item["id"]
        if "recording_id" in item:
            return item["recording_id"]
    return None


@pytest.fixture(scope="session")
def api_context(api_config: ApiConfig) -> dict:
    base_url = api_config.base_url.rstrip("/")
    workspace_id = api_config.workspace_id
    headers = _headers(api_config)

    projects_url = f"{base_url}/workspaces/{workspace_id}/projects"
    recordings_url = f"{base_url}/workspaces/{workspace_id}/recordings"

    projects_payload = _get_json(projects_url, headers)
    recordings_payload = _get_json(recordings_url, headers)

    projects = _assert_result_list(projects_payload, projects_url)
    recordings = _assert_result_list(recordings_payload, recordings_url)

    project_id = os.getenv("PPL_CLOUD_PROJECT_ID", "").strip() or _pick_id(projects)
    recording_id = os.getenv("PPL_CLOUD_RECORDING_ID", "").strip() or _pick_id(recordings)

    return {
        "base_url": base_url,
        "workspace_id": workspace_id,
        "headers": headers,
        "projects": projects,
        "recordings": recordings,
        "project_id": project_id,
        "recording_id": recording_id,
    }


def test_workspace_info(api_context: dict) -> None:
    url = f"{api_context['base_url']}/workspaces/{api_context['workspace_id']}"
    payload = _get_json(url, api_context["headers"])
    assert isinstance(payload, dict)


def test_projects_list_shape(api_context: dict) -> None:
    for project in api_context["projects"]:
        assert isinstance(project, dict)
        _require_keys(project, ["id", "name"], "project")


def test_recordings_list_shape(api_context: dict) -> None:
    for recording in api_context["recordings"]:
        assert isinstance(recording, dict)
        assert "id" in recording or "recording_id" in recording, (
            "Recording item missing 'id' or 'recording_id': " + str(recording)
        )


def test_project_recordings_list_shape(api_context: dict) -> None:
    project_id = api_context["project_id"]
    if not project_id:
        pytest.skip("No project id available to check project recordings")
    url = f"{api_context['base_url']}/workspaces/{api_context['workspace_id']}/projects/{project_id}/recordings"
    payload = _get_json(url, api_context["headers"])
    items = _assert_result_list(payload, url)
    for recording in items:
        assert isinstance(recording, dict)
        assert "id" in recording or "recording_id" in recording


def test_enrichments_list_shape(api_context: dict) -> None:
    project_id = api_context["project_id"]
    if not project_id:
        pytest.skip("No project id available to check enrichments")
    url = f"{api_context['base_url']}/workspaces/{api_context['workspace_id']}/projects/{project_id}/enrichments"
    payload = _get_json(url, api_context["headers"])
    items = _assert_result_list(payload, url)
    for enrichment in items:
        assert isinstance(enrichment, dict)
        _require_keys(enrichment, ["id", "name", "status"], "enrichment")
        assert isinstance(enrichment["status"], dict)
        assert "SUCCESS" in enrichment["status"], "Missing status.SUCCESS in enrichment"


def test_files_list_shape(api_context: dict) -> None:
    recording_id = api_context["recording_id"]
    if not recording_id:
        pytest.skip("No recording id available to check files")
    url = f"{api_context['base_url']}/workspaces/{api_context['workspace_id']}/recordings/{recording_id}/files"
    payload = _get_json(url, api_context["headers"])
    items = _assert_result_list(payload, url)
    for file_item in items:
        assert isinstance(file_item, dict)
        _require_keys(file_item, ["download_url", "recording_id", "name"], "file")
        created_at = file_item.get("created_at")
        if created_at:
            try:
                datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                pytest.fail(f"Unexpected created_at format: {created_at}")
