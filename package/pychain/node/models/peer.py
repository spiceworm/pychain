from __future__ import annotations
import functools
import logging
import os
import random
import socket
from typing import Generator, Union

import requests


__all__ = ("Peer", "Peers")


log = logging.getLogger(__file__)


@functools.total_ordering
class Peer:
    def __init__(self, address: str, port: Union[int, str] = 80):
        self.address = socket.gethostbyname(address)
        self.port = int(port)
        self.dedicated_peer = False
        self._is_boot_node = None

    def __eq__(self, other) -> bool:
        return all(
            [
                self.address == other.address,
                self.port == other.port,
            ]
        )

    def __hash__(self) -> int:
        return hash((self.address, self.port))

    def __lt__(self, other) -> bool:
        return repr(self) < repr(other)

    def __repr__(self) -> str:
        return f"{self.get_alias() or self.address}:{self.port}"

    def __str__(self) -> str:
        if self.is_boot_node():
            return f"{repr(self)} (BOOT)"
        elif self.is_dedicated_peer():
            return f"{repr(self)} (DEDICATED)"
        else:
            return f"{repr(self)} (CLIENT)"

    def get_alias(self) -> str:
        try:
            resp = socket.gethostbyaddr(self.address)
        except Exception:
            return ""
        else:
            return resp[0]

    def get_peers(self) -> Generator[Peer, None, None]:
        response = self._send(requests.get, "/api/v1/peers")
        yield from (Peer(address, port) for address, port in response)

    def get_version(self) -> str:
        return self._send(requests.get, "/api/v1/version")["version"]

    def is_alive(self) -> bool:
        """Return true if peer has confirmed receipt of heartbeat before being deemed stale"""
        # TODO: check some part of response so that this method does not return True for any
        # server that allows GET requests to an /api/v1/status endpoints.
        # `Peer('1.1.1.1').is_alive()` returns True because GET http://1.1.1.1:80/api/v1/status
        # is a valid cloudflare site.
        try:
            resp = self._send(requests.get, "/api/v1/status", raw_response=True)
        except Exception:
            log.exception("Error thrown during liveliness check for %s", self)
            _is_alive = False
        else:
            _is_alive = resp.ok

        if not _is_alive:
            log.info("Unresponsive peer found: %s", self)

        return _is_alive

    def is_boot_node(self) -> bool:
        if self._is_boot_node is None:
            response = self._send(requests.get, "/api/v1/is-boot-node")
            self._is_boot_node = response["is_boot_node"]
        return self._is_boot_node

    def is_dedicated_peer(self) -> bool:
        # This could have been a class property, but having it as a method makes the
        # interface more consistent with the other `Peer.is_*()` methods.
        return self.dedicated_peer

    def my_ip(self) -> str:
        return self._send(requests.get, "/api/v1/my-ip")["address"]

    def _send(self, request, path, *args, **kwargs) -> Union[dict, requests.Response]:
        raw_response = kwargs.pop("raw_response", False)
        url = f"http://{self.address}:{self.port}{path}"
        resp = request(url, *args, **kwargs, timeout=1)
        if raw_response:
            return resp
        else:
            resp.raise_for_status()
            return resp.json()


class Peers:
    @classmethod
    def from_env(cls, env_var: str) -> Generator[Peer, None, None]:
        env_str = os.getenv(env_var, "")
        address_ports = list(filter(None, env_str.split(",")))
        random.shuffle(address_ports)
        for address_port in address_ports:
            address, port = address_port.split(":", 1)
            yield Peer(address, port)
