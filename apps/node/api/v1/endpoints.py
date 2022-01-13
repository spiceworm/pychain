import logging

from fastapi import Request

from pychain.__version__ import __version__
from pychain.node.config import settings
from pychain.node.models import Peer
from pychain.node.storage import cache

from . import router


__all__ = (
    "_broadcast",
    "_is_boot_node",
    "_my_ip",
    "_peers",
    "_status",
    "_version",
)


log = logging.getLogger(__name__)


@router.put("/broadcast")
async def _broadcast(request: Request):
    msg = await request.json()
    log.info("Received message: %s", msg)

    for peer in cache.randomized_peers:
        peer.broadcast(msg)

    return True


@router.get("/is-boot-node")
async def _is_boot_node():
    """
    Returns a response that indicates whether this is a boot node or not.
    """
    return {"is_boot_node": settings.is_boot_node}


@router.get("/my-ip")
async def _my_ip(request: Request):
    """
    Returns the ip-address of the calling node.
    """
    return {"address": request.client.host}


@router.get("/peers")
async def _peers(request: Request):
    """
    Returns a list of 2-tuples where each tuple corresponds to ("<ip-address>", <port>) for all
    peers tracked by the current node. Shuffle the peers before iterating over them as an attempt
    to increase even node tracking distribution across network. We do not want all calls to this
    endpoint to iterate over the response in the same order each time.
    """
    peer = Peer(request.client.host)

    if settings.is_boot_node and peer not in cache.peers:
        log.info("Adding new peer at %s", peer)
        cache.peers = cache.peers | {peer}

    peers_lst = cache.randomized_peers
    log.info("%s known peers:", len(peers_lst))
    for peer in sorted(peers_lst):
        log.info("    %s", peer)

    return [(p.address, p.port) for p in peers_lst]


@router.get("/status")
async def _status():
    """
    Returns an empty response with a response code of 200.
    """
    return {}


@router.get("/version")
async def _version():
    """
    Returns the version of the pychain package in use by this node.
    """
    return {"version": __version__}
