import pickle
import random
from typing import List, Set

import redis

from .models import Peer


__all__ = ("cache",)


class _Cache:
    def __init__(self):
        self._redis = redis.Redis()

    @property
    def address(self) -> str:
        return (self._redis.get("address") or b"").decode()

    @address.setter
    def address(self, value: str):
        self._redis.set("address", value)

    @property
    def ignored_peers(self) -> Set[Peer]:
        if data := self._redis.get("ignored_peers"):
            retval = pickle.loads(data)
        else:
            retval = set()
        return retval

    @ignored_peers.setter
    def ignored_peers(self, value: Set[Peer]) -> None:
        self._redis.set("ignored_peers", pickle.dumps(value))

    @property
    def peers(self) -> Set[Peer]:
        if data := self._redis.get("peers"):
            retval = pickle.loads(data)
        else:
            retval = set()
        return retval

    @peers.setter
    def peers(self, value: Set[Peer]) -> None:
        self._redis.set("peers", pickle.dumps(value))

    @property
    def peer_scan_execution_count(self) -> int:
        if count := self._redis.get("peer_scan_execution_count"):
            return int(count)
        return 0

    @peer_scan_execution_count.setter
    def peer_scan_execution_count(self, value: int) -> None:
        self._redis.set("peer_scan_execution_count", int(value))

    @property
    def randomized_peers(self) -> List[Peer]:
        _peers = list(self.peers)
        random.shuffle(_peers)
        return _peers


cache = _Cache()
