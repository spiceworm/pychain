import logging
import time
from typing import Union

import aiohttp
import asyncio
from fastapi import Request

from pychain.node.config import settings
from pychain.node.models import GUID, Message, Peer
from pychain.node.storage.cache import cache

from . import router


__all__ = (
    "_broadcast",
    "_is_boot_node",
    "_network_join",
    "_peers",
    "_status",
    "_sync",
)


log = logging.getLogger(__name__)


@router.put("/broadcast")
async def _broadcast(request: Request):
    msg_dct = await request.json()
    guid_id = msg_dct["originator"]["guid"]
    address = msg_dct["originator"]["address"]
    guid = GUID(guid_id)
    msg_dct["originator"] = Peer(guid, address)
    message = Message(**msg_dct)

    client = Peer(cache.guid, cache.address)

    if all(
        [
            message.originator == client,
            message.broadcast_timestamp is None,
            message.id is None,
        ]
    ):
        cache.message_id_count += 1
        message.id = cache.message_id_count
        message.broadcast_timestamp = time.time()
        log.info("Client of origin broadcasting %s", message)
        should_broadcast = True
    elif message.id > cache.message_id_count:
        cache.message_id_count = message.id
        log.info("Received new %s", message)
        should_broadcast = True
    else:
        log.debug("%s ignored. ID indicates it is old or a duplicate", message)
        should_broadcast = False

    session = aiohttp.ClientSession()
    if should_broadcast:
        coroutines = [
            p.broadcast(message, session)
            for p in client.get_peers(cache.guid_map, cache.network_guid, settings.boot_node)
        ]
        await asyncio.gather(*coroutines)
    if not session.closed:
        await session.close()
    return should_broadcast


@router.get("/is-boot-node")
async def _is_boot_node() -> bool:
    """
    Returns a response that indicates whether this is a boot node or not.
    """
    return settings.is_boot_node


@router.put("/network/join")
async def _network_join(request: Request) -> dict:
    """
    Client will send requests to a boot node to join the network. The boot node will
    assign the sender a GUID, associate that GUID with the sender's address in storage,
    and return the GUID and the sender's address to the sender. Subsequent calls to
    this endpoint by a client that has already joined will return the same values as
    when the sender initially joined. An empty response is returned if this endpoint is
    invoked on a non-boot node to ensure that GUIDs are assigned correctly.
    """
    retval = {}
    sender_address = request.client.host

    if settings.is_boot_node:
        address_map = {addr: guid for guid, addr in cache.guid_map.items()}

        data = await request.json()

        if "guid" in data:
            # Sender is attempting to re-join the network using a GUID
            # included in their request
            guid_id = int(data["guid"])
            guid = GUID(guid_id)

            if guid in cache.guid_map:
                sender = Peer(guid, sender_address)
                cache.guid_map[sender.guid] = sender.address
                log.info(
                    "%s re-joined the network using previously allocated %s",
                    sender,
                    sender.guid,
                )
            else:
                log.error(
                    "%(address)s attempting to re-join network as %s, "
                    "but %(guid)s was never allocated",
                    {"address": sender_address, "guid": guid},
                )
                return retval
        elif sender_address not in address_map:
            # Sender is joining the network for the first time
            if cache.network_guid is None:
                # This is the first client to join the network
                cache.network_guid = GUID(0)
            else:
                cache.network_guid = GUID(int(cache.network_guid) + 1)

            sender = Peer(cache.network_guid, sender_address)
            cache.guid_map[sender.guid] = sender.address
            log.info("%s joined the network", sender)
        else:
            # Sender already joined the network and invoked this endpoint for no reason
            guid = address_map[sender_address]
            sender = Peer(guid, sender_address)
            log.error("%s has already joined the network", sender)

        retval = {"address": sender.address, "guid": int(sender.guid)}
    else:
        log.error("Join request from %s but this client is not a boot node", sender_address)

    return retval


@router.get("/peers/{guid_id}")
def _peers(guid_id: int) -> Union[str, None]:
    """
    Lookup the address of a client by it's GUID using the receiver's storage.
    Return the address if it is known or None if it is not.
    """
    guid = GUID(guid_id)
    return cache.guid_map.get(guid)


@router.get("/status")
async def _status():
    """
    Returns a response code of 200 with information about the receiving node.
    """
    return {
        "is_boot_node": settings.is_boot_node,
    }


@router.post("/sync")
async def _sync(request: Request) -> int:
    """
    Incoming request includes the sender's highest known GUID for the network.
    Update the receiver's network GUID to the highest GUID known to the sender
    and receiver before returning that value.
    """
    sender = await request.json()

    if cache.network_guid is None:
        # Client may have shut down after already joining the network previously.
        # If a peer invokes this endpoint before network_sync.py runs, then
        # `cache.network_guid` will be None. At this point, the sender invoking
        # this endpoint would be the highest GUID known to this client.
        cache.network_guid = GUID(sender["guid"])
    else:
        cache.network_guid = max(GUID(sender["guid"]), cache.network_guid)

    return int(cache.network_guid)
