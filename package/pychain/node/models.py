from __future__ import annotations
import functools
import logging
import socket
from typing import Generator, List, Union

import requests

from .exceptions import NetworkJoinException


__all__ = (
    "Peer",
)


log = logging.getLogger(__file__)


@functools.total_ordering
class Peer:
    def __init__(self, guid: Union[int, None], address: str = None):
        self.address = socket.gethostbyname(address)
        self.guid = guid
        self._is_boot_node = None
        self._version = None

    def __eq__(self, other: Peer) -> bool:
        return self.guid == other.guid

    def __hash__(self) -> int:
        return self.guid

    def __lt__(self, other: Peer) -> bool:
        return self.guid < other.guid

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(guid={self.guid}, address={self.address})"

    def __str__(self) -> str:
        if self.is_boot_node():
            return f"{repr(self)} (BOOT)"
        else:
            return f"{repr(self)} (CLIENT)"

    def as_dict(self) -> dict:
        return {
            'address': self.address,
        }

    def compute_peer_guids(self, network_size: int = None) -> List[int]:
        """
        :param network_size: Total number of nodes in the network. If not provided, assume
            that `n` is the highest GUID in the network and represents network size.
        :return: List of GUID integers for peers of the node with GUID `n`.

        Example network:
                0
            9       1
          8           2
          7           3
           6         4
                5

        # Compute the peers of node 9 in a 9 node network.
        list(computer_peers(9)) == [8, 7, 5, 1]

        # Compute the peers of node 5 in a 9 node network
        list(computer_peers(5, 9)) == [4, 3, 1, 7]
        """
        network_size = network_size or self.guid
        seq = [*range(network_size + 1)][::-1]
        offset = network_size - self.guid
        network = seq[offset::] + seq[:offset:]
        distance = 1
        peer_guids = []
        while distance <= network_size:
            peer_guids.append(network[distance])
            distance *= 2
        return peer_guids

    def get_peer_address(self, guid: int) -> str:
        return self._send(requests.get, f"/api/v1/peers/{guid}")

    def is_alive(self) -> bool:
        try:
            self._send(requests.get, "/api/v1/status")
        except requests.RequestException:
            log.exception("Error thrown during liveliness check for %s", self)
            return False
        return True

    def is_boot_node(self) -> bool:
        return self._send(requests.get, "/api/v1/status")["is_boot_node"]

    def join_network(self) -> Peer:
        if response := self._send(requests.put, "/api/v1/network/join"):
            guid, address = response["guid"], response["address"]
            return Peer(guid, address)
        raise NetworkJoinException(f"Sent join request to non-boot node: {self}")

    def _send(self, request, path, *args, **kwargs) -> Union[bool, dict, int, str]:
        resp = request(f"http://{self.address}{path}", *args, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def sync(self, guid: int) -> int:
        return self._send(requests.post, "/api/v1/sync", json={"guid": guid})

    @property
    def version(self) -> str:
        return self._send(requests.get, "/api/v1/status")["version"]
