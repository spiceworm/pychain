from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Union

from .models import (
    GUID,
    Message,
    Node,
)


__all__ = ("Storage",)


log = logging.getLogger(__name__)


class Storage:
    def __init__(self, data_dir: pathlib.Path):
        self.data_dir = data_dir

        self.nodes_dir = self.data_dir / "nodes"
        self.nodes_dir.mkdir(parents=True, exist_ok=True)

        self.client_dir = self.nodes_dir / "client"
        self.client_dir.mkdir(parents=True, exist_ok=True)

        self.pool_dir = self.nodes_dir / "pool"
        self.pool_dir.mkdir(parents=True, exist_ok=True)

        self.messages_dir = self.data_dir / "messages"
        self.messages_dir.mkdir(parents=True, exist_ok=True)

    def add_node(self, address: str) -> Node:
        # Only boot nodes should invoke this method
        max_guid = int(self.get_max_guid())
        next_guid = max_guid + 1
        node_fp = self.pool_dir / str(next_guid)
        node_fp.write_text(address)
        return Node(next_guid, address)

    def ensure_node(self, address: str, guid: Union[GUID, int, str]) -> None:
        node_fp = self.pool_dir / str(guid)
        if not node_fp.exists():
            node_fp.write_text(address)

    def get_client(self) -> Union[Node, None]:
        if contents := os.listdir(self.client_dir):
            client_fp = self.client_dir / contents[0]
            address = client_fp.read_text()
            guid = client_fp.name
            return Node(guid, address)

    def get_node_by_guid(self, guid: [GUID, int, str]) -> Node:
        node_fp = self.pool_dir / str(guid)
        if node_fp.exists():
            address = node_fp.read_text()
            return Node(guid, address)
        return Node(guid, None)

    def get_max_guid(self) -> GUID:
        if node_files := os.listdir(self.pool_dir):
            max_guid = max(int(fn) for fn in node_files)
            return GUID(max_guid)
        return GUID(0)

    def get_max_guid_node(self) -> Node:
        guid = self.get_max_guid()
        node_fp = self.pool_dir / str(guid)
        address = node_fp.read_text()
        return Node(guid, address)

    def get_max_message_id(self) -> int:
        if message_files := os.listdir(self.messages_dir):
            return max(int(fn) for fn in message_files)
        return 0

    def save_message(self, message: Message) -> None:
        msg_fp = self.messages_dir / str(message.id)
        if not msg_fp.exists():
            with open(msg_fp, 'w') as f:
                json.dump(message.as_json(), f)

    def set_client(self, address: str, guid: Union[GUID, int, str]) -> None:
        client_fp = self.client_dir / str(guid)
        client_fp.write_text(address)
        (self.pool_dir / str(guid)).symlink_to(client_fp)
