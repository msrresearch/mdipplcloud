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
