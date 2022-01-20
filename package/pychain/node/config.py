import logging
import os
from pathlib import Path

from pychain.node.models import Peer


__all__ = ("settings",)


log = logging.getLogger(__file__)


class _Settings:
    @property
    def boot_node(self) -> Peer:
        address = os.environ["BOOT_NODE"]
        return Peer(None, address)

    @property
    def is_boot_node(self) -> bool:
        return "BOOT_NODE" not in os.environ

    @property
    def log_dir(self) -> Path:
        s = os.getenv("LOG_DIR", "/var/log/pychain")
        return Path(s)

    @property
    def network_sync_interval(self) -> int:
        return int(os.getenv("NETWORK_SYNC_INTERVAL", "60"))

    @property
    def storage_dir(self) -> Path:
        s = os.getenv("STORAGE_DIR", "/usr/local/etc/pychain")
        return Path(s)


settings = _Settings()
