from __future__ import annotations
from collections.abc import MutableMapping
import pickle

from redis import Redis


__all__ = ("RedisDict",)


class RedisDict(MutableMapping):
    def __init__(self, key: str, d: dict = None, connection: Redis = None):
        super().__init__()
        self._initial = d or {}
        self._key = key
        self._redis = connection or Redis()

    def __contains__(self, k) -> bool:
        return k in self._get()

    def __delitem__(self, k) -> None:
        d = self._get()
        del d[k]
        self._set(d)

    def __getitem__(self, k):
        return self._get()[k]

    def __iter__(self):
        return iter(self._get())

    def __len__(self) -> int:
        return len(self._get())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(key={self._key}, {self._get()})"

    def __setitem__(self, k, v) -> None:
        d = self._get()
        d[k] = v
        self._set(d)

    def _get(self) -> dict:
        if data := self._redis.get(self._key):
            d = pickle.loads(data)
        else:
            d = self._initial
        return d

    def keys(self):
        return self._get().keys()

    def _set(self, d: dict) -> None:
        self._redis.set(self._key, pickle.dumps(d))

    def update(self, _d: dict, **kwargs) -> None:
        d = self._get()
        d.update(_d, **kwargs)
        self._set(d)

    def values(self):
        return self._get().values()
