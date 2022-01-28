import logging
import time
from typing import Union

from fastapi import Request

from pychain.node.config import settings
from pychain.node.models import (
    GUID,
    Message,
    Node,
)

from . import router


__all__ = (
    "_broadcast",
    "_network_join",
    "_node_address",
    "_status",
    "_sync",
)


log = logging.getLogger(__name__)


@router.put("/broadcast")
async def _broadcast(request: Request) -> bool:
    msg_dct = await request.json()
    guid_id = msg_dct["originator"]["guid"]
    address = msg_dct["originator"]["address"]
    guid = GUID(guid_id)
    msg_dct["originator"] = Node(guid, address)
    message = Message(**msg_dct)

    db = request.state.db
    client = await db.get_client()

    if all(
        [
            message.originator == client,
            message.broadcast_timestamp is None,
            message.id is None,
        ]
    ):
        message.id = await db.increment_message_count()
        message.broadcast_timestamp = time.time()
        log.info("Client of origin broadcasting %s", message)
        should_broadcast = True
    elif await db.update_message_count_if_less_than(message.id):
        log.info("Received new %s", message)
        should_broadcast = True
    else:
        log.debug("%s ignored. ID indicates it is old or a duplicate", message)
        should_broadcast = False

    if should_broadcast:
        for peer in await client.get_peers(db, request.state.session):
            request.state.mempool.enqueue(peer.broadcast, message)
    return should_broadcast


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
        sender = await request.state.db.ensure_node(sender_address)
        log.info("%s joined the network", sender)
        retval = {"address": sender.address, "guid": int(sender.guid)}
    else:
        log.error("Join request from %s but this client is not a boot node", sender_address)

    return retval


@router.get("/nodes/{guid_id}")
async def _node_address(guid_id: int, request: Request) -> Union[str, None]:
    """
    Lookup the address of a client by it's GUID using the receiver's storage.
    Return the address if it is known or None if it is not.
    """
    if node := await request.state.db.get_node(guid_id):
        log.info("Resolve %s to %s", guid_id, node)
        return node.address


@router.get("/status")
async def _status() -> dict:
    """
    Returns a response code of 200 with information about the receiving node.
    """
    return {}


@router.post("/sync")
async def _sync(request: Request) -> dict:
    """
    Incoming request includes the sender's highest known GUID for the network.
    Update the receiver's network GUID to the highest GUID known to the sender
    and receiver before returning that value.
    """
    data = await request.json()
    db = request.state.db
    sender_address = request.client.host

    sender_guid = data["guid"]
    await db.ensure_node(sender_address, sender_guid)
    await db.ensure_node(data["max_guid_node"]["address"], data["max_guid_node"]["guid"])

    max_guid_node = await db.get_max_guid_node()
    return {
        "address": max_guid_node.address,
        "guid": int(max_guid_node.guid),
    }
