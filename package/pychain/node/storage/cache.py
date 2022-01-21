from __future__ import annotations
import logging
import pickle
from typing import Union

from redis import Redis

from .redis_dict import RedisDict
from ..config import settings
from ..models import GUID


__all__ = ("cache",)


log = logging.getLogger(__file__)


class Cache:
    def __init__(self):
        self._redis = Redis()

    @property
    def address(self) -> str:
        """
        The IP address of this client.
        """
        return (self._redis.get("address") or b"").decode()

    @address.setter
    def address(self, value: str):
        self._redis.set("address", value)

    @property
    def guid(self) -> Union[GUID, None]:
        """
        The globally unique ID (GUID) of this client.
        """
        if data := self._redis.get("guid"):
            return pickle.loads(data)
        elif (guid_path := settings.storage_dir / "guid").is_file():
            log.debug("Reading GUID from %s", guid_path)
            data = guid_path.read_text()
            self.guid = GUID(int(data))
            log.debug("Loaded %s from %s", self.guid, guid_path)
            return self.guid

    @guid.setter
    def guid(self, value: GUID):
        if not (guid_path := settings.storage_dir / "guid").is_file():
            log.debug("Writing %s to %s", value, guid_path)
            guid_path.parent.mkdir(parents=True, exist_ok=True)
            guid_path.write_text(str(value))

        self._redis.set("guid", pickle.dumps(value))

    @property
    def guid_map(self) -> RedisDict[GUID, str]:
        """
        GUID to IP address mapping.
        """
        return RedisDict("guid_map", connection=self._redis)

    @property
    def message_id_count(self) -> int:
        """
        Integer that tracks the last seen message ID that was broadcast to the network.
        """
        if count := self._redis.get("message_id_count"):
            return int(count)
        return 0

    @message_id_count.setter
    def message_id_count(self, value: int) -> None:
        self._redis.set("message_id_count", int(value))

    @property
    def network_guid(self) -> Union[GUID, None]:
        """
        Integer used to track the highest known GUID on the network.
        """
        if data := self._redis.get("network_guid"):
            return pickle.loads(data)
        return data

    @network_guid.setter
    def network_guid(self, value: GUID) -> None:
        self._redis.set("network_guid", pickle.dumps(value))


cache = Cache()
