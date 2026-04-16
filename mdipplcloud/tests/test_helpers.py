import logging
import os
import zipfile

import pytest

from mdipplcloud import helpers


@pytest.fixture(autouse=True)
def restore_config():
    helpers.Config()
    saved = {
        "api_key": getattr(helpers.Config, "api_key", None),
        "workspace_id": getattr(helpers.Config, "workspace_id", None),
        "base_url": getattr(helpers.Config, "base_url", None),
        "download_directory": getattr(helpers.Config, "download_directory", None),
        "timeout": getattr(helpers.Config, "timeout", None),
    }
    yield
    for key, value in saved.items():
        setattr(helpers.Config, key, value)


@pytest.fixture()
def logger():
    test_logger = logging.getLogger("mdipplcloud-test")
    if not test_logger.handlers:
        test_logger.addHandler(logging.NullHandler())
    return test_logger


def test_is_config_loaded():
    helpers.Config.api_key = None
    helpers.Config.workspace_id = None
    helpers.Config.base_url = None
    assert not helpers.Config.is_config_loaded()
    helpers.Config.api_key = "k"
    helpers.Config.workspace_id = "w"
    helpers.Config.base_url = "u"
    assert helpers.Config.is_config_loaded()


def test_unpack_zip_safe(tmp_path, logger):
    zip_path = tmp_path / "ok.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("ok.txt", "ok")
    result = helpers.unpack_zip_file(str(zip_path), output_directory=str(tmp_path), logger=logger)
    assert result is True
    assert (tmp_path / "ok.txt").exists()


def test_unpack_zip_rejects_traversal(tmp_path, logger):
    zip_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../evil.txt", "nope")
    result = helpers.unpack_zip_file(str(zip_path), output_directory=str(tmp_path), logger=logger)
    assert result is False
    assert not os.path.exists(os.path.join(str(tmp_path), "..", "evil.txt"))


def test_load_config_populates_fields_and_urls(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[API]\n"
        "key = test-key\n"
        "workspace_id = ws-123\n"
        "base_url = https://api.example.test/v2\n"
        "\n"
        "[Download]\n"
        "directory = downloads\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cfg = helpers.load_config(str(cfg_path))

    assert cfg.api_key == "test-key"
    assert cfg.workspace_id == "ws-123"
    assert cfg.base_url == "https://api.example.test/v2"
    assert cfg.download_directory == str(tmp_path / "downloads")
    assert os.path.isdir(cfg.download_directory)
    assert cfg.get_recordings_url() == "https://api.example.test/v2/workspaces/ws-123/recordings"
    assert cfg.get_projects_url() == "https://api.example.test/v2/workspaces/ws-123/projects"
    assert helpers.cfg_get("projects_url") == "https://api.example.test/v2/workspaces/ws-123/projects"


def test_load_config_empty_download_directory_uses_cwd(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[API]\n"
        "key = test-key\n"
        "workspace_id = ws-123\n"
        "base_url = https://api.example.test/v2\n"
        "\n"
        "[Download]\n"
        "directory = \n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cfg = helpers.load_config(str(cfg_path))

    assert cfg.download_directory == str(tmp_path)
    assert os.path.isdir(cfg.download_directory)


def test_load_config_strips_wrapping_quotes(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.ini"
    cfg_path.write_text(
        "[API]\n"
        'key = "test-key"\n'
        "workspace_id = 'ws-123'\n"
        'base_url = "https://api.example.test/v2"\n'
        "\n"
        "[Download]\n"
        'directory = "downloads"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    cfg = helpers.load_config(str(cfg_path))

    assert cfg.api_key == "test-key"
    assert cfg.workspace_id == "ws-123"
    assert cfg.base_url == "https://api.example.test/v2"
    assert cfg.download_directory == str(tmp_path / "downloads")
    assert cfg.get_recordings_url() == "https://api.example.test/v2/workspaces/ws-123/recordings"
