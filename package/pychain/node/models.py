from __future__ import annotations
import functools
from ipaddress import (
    AddressValueError,
    IPv4Address,
)
import logging
import socket
from typing import (
    List,
    Union,
)

from aiohttp import ClientSession
import requests

from .exceptions import (
    GUIDNotInNetwork,
    NetworkJoinException,
)
from .config import settings


__all__ = (
    "DeadPeer",
    "GUID",
    "Message",
    "Node",
)


log = logging.getLogger(__file__)


@functools.total_ordering
class GUID:
    def __init__(self, id: int):
        self.id = id

    def __eq__(self, other: GUID) -> bool:
        return self.id == other.id

    def __hash__(self) -> int:
        return self.id

    def __int__(self):
        return self.id

    def __lt__(self, other: GUID) -> bool:
        return self.id < other.id

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id})"

    def __str__(self):
        return str(self.id)

    def get_backup_peers(self, start_guid: GUID, stop_guid: GUID, guid_max: GUID) -> List[GUID]:
        """
        :param start_guid: Node GUID where the next value in the network array is the
            first backup GUID if it does not equal stop_guid.
        :param stop_guid: Node GUID where the prior value in the network array is the
            last backup GUID if it does not equal start_guid.
        :param guid_max: Highest GUID in use by the network.
        :return: List of GUID integers for peers of the node with GUID `n`.

        Example network:
                10
            9       1
          8           2
          7           3
           6         4
                5

        # If current peer.guid == 6, compute the backup GUIDs that fall between
        # peer 2 and 8 where 9 is the highest GUID in the network.
        >>> GUID(6).get_backup_peers(GUID(2), GUID(8), GUID(9))
        [GUID(id=1), GUID(id=9)]

        # If current peer.guid == 9, compute the backup GUIDs that fall between
        # peer 7 and 5 where 9 is the highest GUID in the network.
        >>> GUID(9).get_backup_peers(GUID(7), GUID(5), GUID(9))
        [GUID(id=6)]

        # If current peer.guid == 9, compute the backup GUIDs that fall between
        # peer 1 and 9 where 9 is the highest GUID in the network.
        >>> GUID(9).get_backup_peers(GUID(1), GUID(9), GUID(9))
        []
        """
        network = self._get_network(guid_max)

        try:
            start_idx = network.index(start_guid)
        except ValueError:
            raise GUIDNotInNetwork(start_guid)

        try:
            stop_idx = network.index(stop_guid)
        except ValueError:
            raise GUIDNotInNetwork(stop_guid)

        if stop_idx > start_idx:
            return network[start_idx + 1 : stop_idx]
        return network[start_idx + 1 :]

    def _get_network(self, guid_max: GUID) -> List[GUID]:
        """
        :param guid_max: Highest GUID in use by the network.
        :return: List of integers rotated such that `self.guid` is the first GUID in
            the list of GUIDs.

        Example network:
                10
            9       1
          8           2
          7           3
           6         4
                5

        # If current peer.guid == 5, compute the GUID network.
        >>> GUID(5)._get_network(GUID(10))
        [GUID(id=5),
         GUID(id=4),
         GUID(id=3),
         GUID(id=2),
         GUID(id=1),
         GUID(id=10),
         GUID(id=9),
         GUID(id=8),
         GUID(id=7),
         GUID(id=6)]

        # If current peer.guid == 0, compute the GUID network.
        >>> GUID(1)._get_network(GUID(10))
        [GUID(id=1)
         GUID(id=10),
         GUID(id=9),
         GUID(id=8),
         GUID(id=7),
         GUID(id=6),
         GUID(id=5),
         GUID(id=4),
         GUID(id=3),
         GUID(id=2)]
        """
        seq = [*range(1, int(guid_max) + 1)][::-1]
        offset = int(guid_max) - self.id
        ids = seq[offset::] + seq[:offset:]
        return [GUID(_id) for _id in ids]

    def get_primary_peers(self, guid_max: GUID) -> List[GUID]:
        """
        :param guid_max: Highest GUID in use by the network.
        :return: List of GUID integers for peers of the node with GUID `n`.

        Example network:
                10
            9       1
          8           2
          7           3
           6         4
                5

        # If current peer.guid == 9, compute the peers where 9 is the highest GUID.
        >>> GUID(9).get_primary_peers(GUID(9))
        [GUID(id=8), GUID(id=7), GUID(id=5), GUID(id=1)]

        # If current peer.guid == 5, compute the peers where 9 is the highest GUID.
        >>> GUID(5).get_primary_peers(GUID(9))
        [GUID(id=4), GUID(id=3), GUID(id=1), GUID(id=6)]
        """
        network = self._get_network(guid_max)
        distance = 1
        peer_guids = []
        while distance < guid_max.id:
            peer_guids.append(network[distance])
            distance *= 2
        return peer_guids


@functools.total_ordering
class Node:
    def __init__(self, guid: GUID, address: Union[IPv4Address, str, None]):
        try:
            address = IPv4Address(address)
        except AddressValueError:
            # A url or None was passed in for the address value
            address = socket.gethostbyname(address) if address else address
        else:
            address = str(address)

        self.address = address
        self.guid = guid

    def __eq__(self, other: Node) -> bool:
        return self.guid == other.guid

    def __hash__(self) -> int:
        return hash(self.guid)

    def __lt__(self, other: Node) -> bool:
        return self.guid < other.guid

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(guid={repr(self.guid)}, address={self.address})"

    def __str__(self) -> str:
        return repr(self)

    def as_json(self) -> dict:
        return {
            "address": self.address,
            "guid": int(self.guid),
        }

    def broadcast(self, message: Message):
        message.originator = message.originator or self
        url = f"http://{self.address}/api/v1/broadcast"
        return requests.put(url, json=message.as_json())

    async def _ensure_address(self, session: ClientSession) -> None:
        if self.address is None:
            log.info("Retrieving %s address from boot node", self.guid)
            boot_node = Node(GUID(0), settings.boot_node_address)
            self.address = await boot_node.get_node_address(self.guid, session)

    async def get_peers(self, db, session: ClientSession) -> List[Node]:
        """
        This method has a side-effect of adding new entries to `peer_map`.
        """
        peers = []

        max_guid = await db.get_max_guid()
        peer_guids = self.guid.get_primary_peers(max_guid)
        log.debug("Searching for peers in %s", peer_guids)

        while peer_guids:
            guid = peer_guids.pop(0)
            peer = await db.get_node(guid)
            if await peer.is_alive(session):
                peers.append(peer)
            else:
                log.info("%s: Unresponsive/unknown", peer)
                next_guid = peer_guids[0] if peer_guids else self.guid
                backup_guids = self.guid.get_backup_peers(guid, next_guid, max_guid)
                log.info("Finding backup peer in %s", peer, backup_guids)

                for backup_guid in backup_guids:
                    backup_peer = await db.get_node(backup_guid)
                    if backup_peer is not None and await backup_peer.is_alive(session):
                        log.info("%s: Responsive backup", backup_peer)
                        peers.append(backup_peer)
                        break

        return peers

    async def get_node_address(self, guid: GUID, session: ClientSession) -> str:
        return await self._send("get", f"/api/v1/nodes/{guid}", session)

    async def is_alive(self, session: ClientSession) -> bool:
        try:
            await self._send("get", "/api/v1/status", session)
        except Message:
            return False
        return True

    async def join_network(self, session: ClientSession) -> Node:
        if resp := await self._send("put", "/api/v1/network/join", session):
            guid_id, address = resp["guid"], resp["address"]
            guid = GUID(guid_id)
            return Node(guid, address)
        raise NetworkJoinException(f"Sent join request to non-boot node: {self}")

    async def _send(self, request_type: str, path: str, session: ClientSession, *args, **kwargs):
        await self._ensure_address(session)
        url = f"http://{self.address}{path}"
        async with getattr(session, request_type)(url, *args, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def sync(self, sender_guid: GUID, max_guid_node: Node, session: ClientSession) -> Node:
        resp = await self._send(
            "post",
            "/api/v1/sync",
            session,
            json={
                "guid": int(sender_guid),
                "max_guid_node": {
                    "address": max_guid_node.address,
                    "guid": int(max_guid_node.guid),
                },
            },
        )
        max_guid_node_address, max_guid_node_guid = resp["address"], resp["guid"]
        return Node(GUID(max_guid_node_guid), max_guid_node_address)


class Message:
    def __init__(
        self,
        data: dict,
        id: Union[int, None] = None,
        originator: Union[Node, None] = None,
        broadcast_timestamp: Union[float, None] = None,
    ):
        self.data = data
        self.broadcast_timestamp = broadcast_timestamp
        self.id = id
        self.originator = originator

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"data={self.data}, "
            f"id={self.id}, "
            f"originator={repr(self.originator)}, "
            f"broadcast_timestamp={self.broadcast_timestamp})"
        )

    def as_json(self) -> dict:
        return {
            "data": self.data,
            "broadcast_timestamp": self.broadcast_timestamp,
            "id": self.id,
            "originator": self.originator.as_json(),
        }


class DeadPeer(Message):
    def __init__(
        self,
        guid: GUID,
        id: Union[int, None] = None,
        originator: Union[Node, None] = None,
        broadcast_timestamp: Union[float, None] = None,
    ):
        data = {
            "event": {
                "name": "DEAD_PEER",
                "guid": int(guid),
            },
        }
        super().__init__(data, id, originator, broadcast_timestamp)
