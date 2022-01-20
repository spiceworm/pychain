from pathlib import Path
import socket

import pytest

from pychain.node.config import settings
from pychain.node.models import Peer


def test_boot_node(monkeypatch):
    def gethostbyname(s):
        return "0.0.0.0"

    monkeypatch.setenv("BOOT_NODE", "boot.com")
    monkeypatch.setattr(socket, "gethostbyname", gethostbyname)
    boot_node = settings.boot_node
    assert isinstance(boot_node, Peer)
    assert boot_node.guid is None
    assert boot_node.address == "0.0.0.0"
    monkeypatch.undo()


def test_boot_node_unset():
    with pytest.raises(KeyError):
        settings.boot_node


def test_is_boot_node():
    assert settings.is_boot_node


def test_is_boot_node_unset(monkeypatch):
    def gethostbyname(s):
        return "0.0.0.0"

    monkeypatch.setenv("BOOT_NODE", "boot.com")
    monkeypatch.setattr(socket, "gethostbyname", gethostbyname)
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
