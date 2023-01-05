import logging
import time
from typing import Union

from fastapi import Request

from pychain.node.config import settings
from pychain.node.models import (
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
log.setLevel(settings.log_level)


@router.put("/broadcast")
async def _broadcast(request: Request) -> bool:
    msg_dct = await request.json()
    guid = msg_dct["originator"]["guid"]
    address = msg_dct["originator"]["address"]
    msg_dct["originator"] = Node(guid, address)
    message = Message(**msg_dct)

    db = request.state.db
    client = db.get_client()

    log.info("Received %s", message)

    if all(
        [
            message.originator == client,
            message.broadcast_timestamp is None,
            message.id is None,
        ]
    ):
        message.id = int(db.get_max_message_id()) + 1
        message.broadcast_timestamp = time.time()
        log.info("Broadcasting message from client of origin")
        should_broadcast = True
    elif message.ttl == 0:
        log.info("Not broadcasting message as TTL is 0")
        should_broadcast = False
    elif int(client.guid) in message.seen_by:
        log.info("Not broadcasting as already seen")
        should_broadcast = False
    elif int(db.get_max_message_id()) < message.id:
        log.info("New message received")
        message.ttl -= 1
        db.ensure_node(message.originator.address, message.originator.guid)
        should_broadcast = True

        event = message.data.get("event", {})
        match event_name := event.get("name"):
            case "DEAD_PEER":
                log.info("%s event detected", event_name)
            case _:
                log.warning("Unhandled event '%s'", event_name)

    else:
        log.info("Duplicate or old message received")
        should_broadcast = False

    if should_broadcast:
        message.seen_by.append(int(client.guid))
        db.save_message(message)

        for peer in await client.get_peers(request.state.session):
            if int(peer.guid) not in message.seen_by:
                log.debug("Broadcasting message to %s", peer)
                request.state.mempool.enqueue(peer.synchronous_broadcast, message)

    return should_broadcast


@router.put("/network/join")
async def _network_join(request: Request) -> dict:
    """
    Client will send requests to a boot node to join the network. The boot node will
    add the sender to the database which will assign it a GUID. Subsequent calls to
    this endpoint by a client that has already joined will return the same values as
    when the sender initially joined. An empty response is returned if this endpoint is
    invoked on a non-boot node to ensure that GUIDs are assigned correctly.
    """
    retval = {}
    sender_address = request.client.host

    if settings.is_boot_node:
        sender = request.state.db.add_node(sender_address)
        retval = {"address": sender.address, "guid": int(sender.guid)}
    else:
        log.error("Join request from %s but this client is not a boot node", sender_address)

    return retval


@router.get("/nodes/{guid}")
async def _node_address(guid: int, request: Request) -> Union[str, None]:
    """
    Lookup the address of the Node assigned to `guid`.
    Return the address if it is known or None if it is not.
    """
    if node := request.state.db.get_node_by_guid(guid):
        log.info("Resolve %s to %s", guid, node)
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
    db.ensure_node(sender_address, sender_guid)
    db.ensure_node(data["max_guid_node"]["address"], data["max_guid_node"]["guid"])

    max_guid_node = db.get_max_guid_node()
    return {"address": max_guid_node.address, "guid": int(max_guid_node.guid)}
