import json
import logging
from pathlib import Path

from mdipplcloud import plugin


def test_get_plugin_contract_is_json_serializable():
    contract = plugin.get_plugin()
    assert contract["meta"]["api_version"] == plugin.API_VERSION
    assert contract["meta"]["id"] == plugin.PLUGIN_ID
    assert contract["meta"]["kind"] == "python"
    assert contract["entry"]["callable"] == plugin.ENTRY_CALLABLE
    assert contract["meta"]["inputs"][0]["path_globs"] == ["**/*"]
    assert any(item["name"] == "resultbundle" for item in contract["meta"]["outputs"])
    json.dumps(contract)


def test_run_writes_manifest_and_provenance_without_download(tmp_path):
    dataset_dir = tmp_path / "dataset_in"
    (dataset_dir / "nested").mkdir(parents=True)
    (dataset_dir / "nested" / "sample.txt").write_text("sample", encoding="utf-8")
    out_dir = tmp_path / "out"

    config = {
        "cloud": {
            "api_key": "secret-value",
            "workspace_id": "workspace",
            "base_url": "https://example.invalid",
        }
    }
    result = plugin.run(dataset_dir=dataset_dir, out_dir=out_dir, config=config)

    assert result["status"] == "ok"
    assert result["entry"] == plugin.ENTRY_CALLABLE
    assert result["out_dir"] == str(out_dir)
    assert len(result["config_sha256"]) == 64
    assert "indexed_input_dataset" in result["actions"]
    manifest_path = out_dir / "dataset" / "input_dataset_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["file_count"] == 1
    assert manifest["sample_files"] == ["nested/sample.txt"]

    resultbundle_path = out_dir / "resultbundle.json"
    assert resultbundle_path.exists()
    resultbundle = json.loads(resultbundle_path.read_text(encoding="utf-8"))
    assert resultbundle["resultbundle_type"] == plugin.RESULTBUNDLE_TYPE
    assert resultbundle["schema_version"] == plugin.RESULTBUNDLE_SCHEMA_VERSION
    assert isinstance(resultbundle["files"], list)

    provenance_path = out_dir / "provenance.json"
    assert provenance_path.exists()
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["inputs"]["dataset_dir"] == str(dataset_dir)
    assert provenance["inputs"]["out_dir"] == str(out_dir)
    assert provenance["inputs"]["config"]["cloud"]["api_key"] == "***REDACTED***"


def test_run_skips_downloads_when_cloud_config_missing(tmp_path):
    result = plugin.run(
        out_dir=tmp_path / "out",
        config={"recording_ids": ["rec-1", "rec-2"]},
    )

    assert result["status"] == "no_download"
    assert result["downloaded_recordings"] == []
    assert result["failed_recordings"] == []
    assert result["skipped_recordings"] == ["rec-1", "rec-2"]
    assert "missing_cloud_config_for_download" in result["warnings"]


def test_run_dry_run_marks_recordings_as_skipped(tmp_path):
    result = plugin.run(
        out_dir=tmp_path / "out",
        config={"recording_ids": ["rec-1"]},
        dry_run=True,
    )
    assert result["status"] == "dry_run"
    assert result["downloaded_recordings"] == []
    assert result["failed_recordings"] == []
    assert result["skipped_recordings"] == ["rec-1"]
    assert "dry_run_skipped_downloads" in result["actions"]


def test_run_download_smoke_with_monkeypatched_downloader(tmp_path, monkeypatch):
    calls = []

    def fake_download_recording(
        recording_id,
        output_directory=None,
        unpack_zip=True,
        logger=None,
        custom_cfg=None,
    ):
        calls.append(
            {
                "recording_id": recording_id,
                "output_directory": output_directory,
                "unpack_zip": unpack_zip,
                "api_key": custom_cfg.api_key,
                "workspace_id": custom_cfg.workspace_id,
                "base_url": custom_cfg.base_url,
                "timeout": custom_cfg.timeout,
                "logger_name": logger.name if isinstance(logger, logging.Logger) else None,
            }
        )
        marker = Path(output_directory) / f"{recording_id}.txt"
        marker.write_text("ok", encoding="utf-8")
        return recording_id != "bad"

    monkeypatch.setattr(plugin, "download_recording", fake_download_recording)

    out_dir = tmp_path / "run_out"
    work_dir = tmp_path / "work"
    result = plugin.run(
        out_dir=out_dir,
        work_dir=work_dir,
        config={
            "recording_ids": ["ok", "bad"],
            "unpack_zip": False,
            "timeout": 12,
            "cloud": {
                "api_key": "api-key",
                "workspace_id": "workspace-1",
                "base_url": "https://example.invalid",
            },
        },
    )

    assert result["status"] == "partial"
    assert result["downloaded_recordings"] == ["ok"]
    assert result["failed_recordings"] == ["bad"]
    assert result["skipped_recordings"] == []
    assert result["work_dir"] == str(work_dir)
    assert result["resultbundle_path"] == str(out_dir / "resultbundle.json")
    assert "downloaded_requested_recordings" in result["actions"]
    assert "wrote_resultbundle_sidecar" in result["actions"]
    assert [item["recording_id"] for item in calls] == ["ok", "bad"]
    assert {item["output_directory"] for item in calls} == {str(out_dir / "dataset")}
    assert {item["unpack_zip"] for item in calls} == {False}
    assert {item["api_key"] for item in calls} == {"api-key"}
    assert {item["workspace_id"] for item in calls} == {"workspace-1"}
    assert {item["base_url"] for item in calls} == {"https://example.invalid"}
    assert {item["timeout"] for item in calls} == {12}
