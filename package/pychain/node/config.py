import logging
import os
from typing import Set

from pychain.node.models import Peer, Peers


__all__ = ("settings",)


log = logging.getLogger(__file__)


class _Settings:
    @property
    def address_check_frequency(self) -> int:
        return int(os.getenv("ADDRESS_CHECK_FREQUENCY", "25"))

    @property
    def boot_nodes(self) -> Set[Peer]:
        peers = set()
        for peer in Peers.from_env("BOOT_NODES"):
            if peer.is_alive():
                peers.add(peer)
                if len(peers) == self.max_boot_nodes:
                    break
            else:
                log.warning("BOOT_NODES contains %s but it is not responsive", peer)
        return peers

    @property
    def dedicated_peers(self) -> Set[Peer]:
        peers = set()
        for peer in Peers.from_env("DEDICATED_PEERS"):
            peer.dedicated_peer = True
            peers.add(peer)
        return peers

    @property
    def ignored_peers(self) -> Set[Peer]:
        return {p for p in Peers.from_env("IGNORED_PEERS")}

    @property
    def is_boot_node(self) -> bool:
        return not os.getenv("BOOT_NODES", "")

    @property
    def max_boot_nodes(self) -> int:
        return int(os.getenv("MAX_BOOT_NODES", "5"))

    @property
    def max_peers(self) -> int:
        return int(os.getenv("MAX_PEERS", "10"))

    @property
    def peer_scan_interval(self) -> int:
        return int(os.getenv("PEER_SCAN_INTERVAL", "60"))


settings = _Settings()
