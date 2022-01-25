import logging
import os
from pathlib import Path
import socket


__all__ = ("settings",)


log = logging.getLogger(__file__)


class _Settings:
    _boot_node = None
    _db_host = None

    @property
    def boot_node(self):
        if self._boot_node is None:
            from pychain.node.models import GUID, Node

            self._boot_node = Node(GUID(0), self._boot_node_address)
        return self._boot_node

    @property
    def _boot_node_address(self) -> str:
        return os.environ["BOOT_NODE"]

    @property
    def db_host(self) -> str:
        if self._db_host is None:
            self._db_host = socket.gethostbyname(os.environ["DB_HOST"])
        return self._db_host

    @property
    def db_password(self) -> str:
        return os.environ["DB_PASSWORD"]

    @property
    def is_boot_node(self) -> bool:
        return "BOOT_NODE" not in os.environ

    @property
    def log_dir(self) -> Path:
        return Path(os.getenv("LOG_DIR", "/var/log/pychain"))

    @property
    def network_sync_interval(self) -> int:
        return int(os.getenv("NETWORK_SYNC_INTERVAL", "60"))

    @property
    def storage_dir(self) -> Path:
        return Path(os.getenv("STORAGE_DIR", "/usr/local/etc/pychain"))


settings = _Settings()
