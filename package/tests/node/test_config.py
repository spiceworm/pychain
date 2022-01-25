from pathlib import Path

import pytest

from pychain.node.config import settings


def test_boot_node_name(monkeypatch):
    monkeypatch.setenv("BOOT_NODE", "boot.com")
    assert settings.boot_node_address == "boot.com"
    monkeypatch.undo()


def test_boot_node_unset():
    with pytest.raises(KeyError):
        settings.boot_node_address


def test_is_boot_node():
    assert settings.is_boot_node


def test_is_boot_node_unset(monkeypatch):
    monkeypatch.setenv("BOOT_NODE", "boot.com")
    assert not settings.is_boot_node
    monkeypatch.undo()


def test_log_dir_custom(monkeypatch):
    path = Path("/var/log/something")
    monkeypatch.setenv("LOG_DIR", str(path))
    assert settings.log_dir == path
    monkeypatch.undo()


def test_log_dir_default():
    assert settings.log_dir == Path("/var/log/pychain")


def test_network_sync_interval_custom(monkeypatch):
    monkeypatch.setenv("NETWORK_SYNC_INTERVAL", "5")
    assert settings.network_sync_interval == 5
    monkeypatch.undo()


def test_network_sync_interval_default():
    assert settings.network_sync_interval == 60


def test_storage_dir_custom(monkeypatch):
    path = Path("/usr/local/etc/something")
    monkeypatch.setenv("STORAGE_DIR", str(path))
    assert settings.storage_dir == path
    monkeypatch.undo()


def test_storage_dir_default():
    assert settings.storage_dir == Path("/usr/local/etc/pychain")
