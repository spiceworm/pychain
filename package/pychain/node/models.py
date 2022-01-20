from __future__ import annotations
import functools
import logging
import socket
from typing import List, Union

from aiohttp import ClientResponse, ClientSession
import requests

from .exceptions import GUIDNotInNetwork, NetworkJoinException
from .storage.redis_dict import RedisDict


__all__ = (
    "GUID",
    "Message",
    "Peer",
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
        :param start_guid: Peer GUID where the next value in the network array is the
            first backup GUID if it does not equal stop_guid.
        :param stop_guid: Peer GUID where the prior value in the network array is the
            last backup GUID if it does not equal start_guid.
        :param guid_max: Highest GUID in use by the network.
        :return: List of GUID integers for peers of the node with GUID `n`.

        Example network:
                0
            9       1
          8           2
          7           3
           6         4
                5

        # If current peer.guid == 6, compute the backup GUIDs that fall between
        # peer 2 and 8 where 9 is the highest GUID in the network.
        >>> GUID(6).get_backup_peers(GUID(2), GUID(8), GUID(9))
        [GUID(id=1), GUID(id=0), GUID(id=9)]

        # If current peer.guid == 9, compute the backup GUIDs that fall between
        # peer 7 and 5 where 9 is the highest GUID in the network.
        >>> GUID(9).get_backup_peers(GUID(7), GUID(5), GUID(9))
        [GUID(id=6)]

        # If current peer.guid == 9, compute the backup GUIDs that fall between
        # peer 1 and 9 where 9 is the highest GUID in the network.
        >>> GUID(9).get_backup_peers(GUID(1), GUID(9), GUID(9))
        [GUID(id=0)]
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
                0
            9       1
          8           2
          7           3
           6         4
                5

        # If current peer.guid == 5, compute the GUID network.
        >>> GUID(5)._get_network(GUID(9))
        [GUID(id=5),
         GUID(id=4),
         GUID(id=3),
         GUID(id=2),
         GUID(id=1),
         GUID(id=0),
         GUID(id=9),
         GUID(id=8),
         GUID(id=7),
         GUID(id=6)]

        # If current peer.guid == 0, compute the GUID network.
        >>> GUID(0)._get_network(GUID(9))
        [GUID(id=0),
         GUID(id=9),
         GUID(id=8),
         GUID(id=7),
         GUID(id=6),
         GUID(id=5),
         GUID(id=4),
         GUID(id=3),
         GUID(id=2),
         GUID(id=1)]
        """
        seq = [*range(int(guid_max) + 1)][::-1]
        offset = int(guid_max) - self.id
        ids = seq[offset::] + seq[:offset:]
        return [GUID(_id) for _id in ids]

    def get_primary_peers(self, guid_max: GUID) -> List[GUID]:
        """
        :param guid_max: Highest GUID in use by the network.
        :return: List of GUID integers for peers of the node with GUID `n`.

        Example network:
                0
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
        [GUID(id=4), GUID(id=3), GUID(id=1), GUID(id=7)]
        """
        network = self._get_network(guid_max)
        distance = 1
        peer_guids = []
        while distance <= guid_max.id:
            peer_guids.append(network[distance])
            distance *= 2
        return peer_guids


class Message:
    def __init__(self, body: int, id: int, originator: Peer, broadcast_timestamp: None = None):
        self.body = body
        self.broadcast_timestamp = broadcast_timestamp
        self.id = id
        self.originator = originator

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"body={self.body}, "
            f"id={self.id}, "
            f"originator={repr(self.originator)}, "
            f"broadcast_timestamp={self.broadcast_timestamp})"
        )

    def as_dict(self) -> dict:
        return {
            "body": self.body,
            "broadcast_timestamp": self.broadcast_timestamp,
            "id": self.id,
            "originator": self.originator.as_dict(),
        }


@functools.total_ordering
class Peer:
    def __init__(self, guid: Union[GUID, None], address: Union[str, None]):
        self.address = socket.gethostbyname(address) if address else address
        self.guid = guid
        self._is_boot_node = None

    def __eq__(self, other: Peer) -> bool:
        return self.guid == other.guid

    def __hash__(self) -> int:
        return hash(self.guid)

    def __lt__(self, other: Peer) -> bool:
        return self.guid < other.guid

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(guid={repr(self.guid)}, address={self.address})"

    def __str__(self) -> str:
        return repr(self)

    def as_dict(self) -> dict:
        return {
            "address": self.address,
            "guid": self.guid,  # TODO: convert this to an int?
        }

    async def broadcast(self, message: Message, session: ClientSession) -> ClientResponse:
        url = f"http://{self.address}/api/v1/broadcast"
        return await session.put(url, json=message.as_dict())

    def get_peers(self, guid_map: RedisDict, guid_max: GUID, boot_node: Peer) -> List[Peer]:
        """
        This method has a side-effect of adding new entries to `peer_map`.
        """
        peers = []
        unaddressed_peers = []
        unaddressed_backup_peers = []

        peer_guids = self.guid.get_primary_peers(guid_max)
        total_peer_guids = len(peer_guids)
        log.info("Searching for peers in %s", peer_guids)

        while peer_guids:
            guid = peer_guids.pop(0)
            address = guid_map.get(guid)
            peer = Peer(guid, address)
            if peer.address:
                if peer.is_unresponsive():
                    log.info("%s: Unresponsive", peer)
                    next_guid = peer_guids[0] if peer_guids else self.guid
                    backup_guids = self.guid.get_backup_peers(guid, next_guid, guid_max)
                    log.info("Finding backup peer in %s", peer, backup_guids)

                    for backup_guid in backup_guids:
                        backup_address = guid_map.get(backup_guid)
                        backup_peer = Peer(backup_guid, backup_address)
                        if backup_peer.address:
                            if backup_peer.is_alive():
                                log.info("%s: Responsive backup", backup_peer)
                                peers.append(backup_peer)
                                break
                            else:
                                log.info("%s: Unresponsive backup", backup_peer)
                        else:
                            log.info("%s: Unknown address for backup", backup_peer)
                            unaddressed_backup_peers.append(backup_peer)
                    else:
                        log.info("%s: No backup GUIDs found", peer)
                else:
                    log.info("%s: Responsive", peer)
                    peers.append(peer)
            else:
                log.info("%s: Unknown address", peer)
                unaddressed_peers.append(peer)

        while unaddressed_peers:
            if len(peers) < total_peer_guids:
                peer = unaddressed_peers.pop(0)
                if address := boot_node.get_peer_address(peer.guid):
                    guid_map[peer.guid] = peer.address = address
                    if peer.is_alive():
                        log.info("%s: Responsive peer found after boot node lookup", peer)
                        peers.append(peer)
                    else:
                        log.info(
                            "%s: Unresponsive peer detected after boot node lookup",
                            peer,
                        )
                else:
                    log.error(
                        "Could not lookup address for GUID %s using boot node. This "
                        "should never happen because we should never be touching GUIDs "
                        "that the boot node did not hand out and is therefore knows "
                        "the associated address for.",
                        peer.guid,
                    )

        while unaddressed_backup_peers:
            if len(peers) < total_peer_guids:
                peer = unaddressed_backup_peers.pop(0)
                if address := boot_node.get_peer_address(peer.guid):
                    guid_map[peer.guid] = peer.address = address
                    if peer.is_alive():
                        log.info("%s: Responsive backup found after boot node lookup", peer)
                        peers.append(peer)
                    else:
                        log.info(
                            "%s: Unresponsive backup detected after boot node lookup",
                            peer,
                        )
                else:
                    log.error(
                        "Could not lookup address for GUID %s using boot node. This "
                        "should never happen because we should never be touching GUIDs "
                        "that the boot node did not hand out and is therefore knows "
                        "the associated address for.",
                        peer.guid,
                    )

        return peers

    def get_peer_address(self, guid: GUID) -> str:
        return self._send(requests.get, f"/api/v1/peers/{guid}")

    def is_alive(self) -> bool:
        try:
            self._send(requests.get, "/api/v1/status")
        # except requests.RequestException:
        except Exception:
            # log.exception("Error thrown during liveliness check for %s", self)
            return False
        return True

    def is_boot_node(self) -> bool:
        return self._send(requests.get, "/api/v1/status")["is_boot_node"]

    def is_unresponsive(self) -> bool:
        return not self.is_alive()

    def join_network(self, guid: Union[GUID, None] = None) -> Peer:
        data = {"guid": int(guid)} if guid is not None else {}
        if response := self._send(requests.put, "/api/v1/network/join", json=data):
            guid_id, address = response["guid"], response["address"]
            guid = GUID(guid_id)
            return Peer(guid, address)
        raise NetworkJoinException(f"Sent join request to non-boot node: {self}")

    def _send(self, request, path, *args, **kwargs) -> Union[bool, dict, int, str]:
        resp = request(f"http://{self.address}{path}", *args, **kwargs, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def sync(self, guid: GUID) -> GUID:
        guid_id = self._send(requests.post, "/api/v1/sync", json={"guid": int(guid)})
        return GUID(guid_id)
