import pickle
from typing import Dict, Union

import redis


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
    def guid(self) -> Union[int, None]:
        _guid = self._redis.get("guid")
        return int(_guid) if _guid is not None else _guid

    @guid.setter
    def guid(self, value: int):
        self._redis.set("guid", int(value))

    @property
    def guid_address_map(self) -> Dict[int, str]:
        if data := self._redis.get("guid_address_map"):
            retval = pickle.loads(data)
        else:
            retval = {}
        return retval

    @guid_address_map.setter
    def guid_address_map(self, value: Dict[int, str]) -> None:
        self._redis.set("guid_address_map", pickle.dumps(value))

    @property
    def network_guid(self) -> int:
        count = self._redis.get("network_guid")
        return int(count) if count is not None else -1

    @network_guid.setter
    def network_guid(self, value: int) -> None:
        self._redis.set("network_guid", value)


cache = _Cache()
