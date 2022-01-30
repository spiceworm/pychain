from __future__ import annotations

import functools
from ipaddress import (
    AddressValueError,
    IPv4Address,
)
import logging
import socket
from typing import (
    Callable,
    List,
    Union,
)

from aiohttp import ClientSession
import requests

from .exceptions import (
    GUIDNotInNetwork,
    NetworkJoinException,
)


__all__ = (
    "DeadPeer",
    "GUID",
    "Message",
    "Node",
)


log = logging.getLogger(__file__)


@functools.total_ordering
class GUID:
    def __init__(self, id_: int):
        self.id = id_

    def __eq__(self, other: Union[GUID, int]) -> bool:
        return int(self) == int(other)

    def __hash__(self) -> int:
        return self.id

    def __int__(self):
        return self.id

    def __lt__(self, other: Union[GUID, int]) -> bool:
        return int(self) < int(other)

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

    def _get_network(self, guid_max: Union[GUID, int]) -> List[GUID]:
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

    def get_primary_peers(self, guid_max: Union[GUID, int]) -> List[GUID]:
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
        while distance < int(guid_max):
            peer_guids.append(network[distance])
            distance *= 2
        return peer_guids


@functools.total_ordering
class Node:
    boot_node: Node = None
    db = None

    def __init__(self, guid: Union[GUID, int], address: Union[IPv4Address, str, None]):
        try:
            address = IPv4Address(address)
        except AddressValueError:
            # A url or None was passed in for the address value
            address = socket.gethostbyname(address) if address else address
        else:
            address = str(address)

        self.address = address
        self.guid = GUID(int(guid))

    def __eq__(self, other: Node) -> bool:
        return self.guid == other.guid

    def __hash__(self) -> int:
        return hash(self.guid)

    def __lt__(self, other: Union[Node, int]) -> bool:
        if isinstance(other, int):
            return int(self.guid) < other
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
        resp = requests.put(f"http://{self.address}/api/v1/broadcast", json=message.as_json())
        resp.raise_for_status()
        return resp.json()

    async def get_peers(self, session: ClientSession) -> List[Node]:
        """ """
        peers = []

        max_guid = await self.db.get_max_guid()
        peer_guids = self.guid.get_primary_peers(max_guid)
        log.debug("Searching for peers in %s", peer_guids)

        while peer_guids:
            guid = peer_guids.pop(0)
            peer = await self.db.get_node(guid)
            if await peer.is_alive(session):
                peers.append(peer)
                await self.db.ensure_node(peer.address, peer.guid)
            else:
                log.info("%s: Unresponsive/unknown", peer)
                next_guid = peer_guids[0] if peer_guids else self.guid
                backup_guids = self.guid.get_backup_peers(guid, next_guid, max_guid)
                log.info("Finding backup peer in %s", peer, backup_guids)

                for backup_guid in backup_guids:
                    backup_peer = await self.db.get_node(backup_guid)
                    if backup_peer is not None and await backup_peer.is_alive(session):
                        log.info("%s: Responsive backup", backup_peer)
                        peers.append(backup_peer)
                        await self.db.ensure_node(backup_peer.address, backup_peer.guid)
                        break

        return peers

    async def get_node_address(self, guid: GUID, session: ClientSession) -> Union[str, None]:
        """
        Returns the IP address of the `Node` where `Node.guid` == `guid` if an entry for `guid`
        exists in the database of the client represented by this `Node`. If the client does not
        have a database entry for `guid`, returns `None`.
        """
        return await self._send(session.get, f"/api/v1/nodes/{guid}", session)

    async def is_alive(self, session: ClientSession) -> bool:
        """
        Returns True if the API of the client represented by this `Node` is responsive.
        """
        try:
            await self._send(session.get, "/api/v1/status", session)
        except Exception:
            return False
        return True

    async def join_network(self, session: ClientSession) -> Node:
        if resp := await self._send(session.put, "/api/v1/network/join", session):
            guid_id, address = resp["guid"], resp["address"]
            return Node(guid_id, address)
        raise NetworkJoinException(f"Sent join request to non-boot node: {self}")

    async def _send(self, request: Callable, path: str, session: ClientSession, *args, **kwargs):
        """
        Asynchronously send a request to the API of the client represented by this `Node`.
        """
        if self.address is None:
            log.info("Retrieving %s address from boot node", self.guid)
            self.address = await self.boot_node.get_node_address(self.guid, session)

        async with request(f"http://{self.address}{path}", *args, **kwargs) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def sync(self, sender_guid: GUID, max_guid_node: Node, session: ClientSession) -> Node:
        """
        Returns a `Node` instance representing the node on the network with the highest
        GUID known to the client represented by this `Node`.
        """
        resp = await self._send(
            session.post,
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
        return Node(max_guid_node_guid, max_guid_node_address)


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
