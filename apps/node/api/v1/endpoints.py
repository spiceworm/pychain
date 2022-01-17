import logging
from typing import Union

from fastapi import Request

from pychain.__version__ import __version__
from pychain.node.config import settings
from pychain.node.models import Peer
from pychain.node.storage import cache

from . import router


__all__ = (
    "_is_boot_node",
    "_network_join",
    "_peers",
    "_status",
    "_sync",
)


log = logging.getLogger(__name__)


@router.get("/is-boot-node")
async def _is_boot_node() -> bool:
    """
    Returns a response that indicates whether this is a boot node or not.
    """
    return settings.is_boot_node


@router.put("/network/join")
async def _network_join(request: Request) -> dict:
    """
    Client will send requests to a boot node to join the network. The boot node will assign
    the sender a GUID, associate that GUID with the sender's address in storage, and return
    the GUID and the sender's address to the sender. Subsequent calls to this endpoint by a
    client that has already joined will return the same values as when the sender initially
    joined. An empty response is returned if this endpoint is invoked on a non-boot node to
    ensure that GUIDs are assigned correctly.
    """
    sender = Peer(None, request.client.host)
    retval = {}

    if settings.is_boot_node:
        guid_address_map = cache.guid_address_map
        address_guid_map = {addr: guid for guid, addr in guid_address_map.items()}
        sender.guid = address_guid_map.get(sender.address)

        if sender.guid is None:
            cache.network_guid += 1
            sender.guid = cache.network_guid
            guid_address_map[sender.guid] = sender.address
            cache.guid_address_map = guid_address_map
            log.info("%s joined the network", sender)
        else:
            log.error("%s has already joined the network", sender)

        retval = {"address": sender.address, "guid": sender.guid}
    else:
        log.error("Join request from %s but not a boot node", sender)

    return retval


@router.get("/peers/{guid}")
def _peers(guid: int) -> Union[str, None]:
    """
    Lookup the address of a client by it's GUID using the receiver's storage.
    Return the address if it is known or None if it is not.
    """
    return cache.guid_address_map.get(guid)


@router.get("/status")
async def _status():
    """
    Returns a response code of 200 with information about the receiving node.
    """
    return {
        "is_boot_node": settings.is_boot_node,
        "network_guid": cache.network_guid,
        "version": __version__,
    }


@router.post("/sync")
async def _sync(request: Request) -> int:
    """
    Incoming request includes the sender's highest known GUID for the network.
    Update the receiver's network GUID to the highest GUID known to the sender
    and receiver before returning that value.
    """
    sender = await request.json()
    cache.network_guid = max(sender["guid"], cache.network_guid)
    return cache.network_guid
