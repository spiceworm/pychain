import logging

from fastapi import APIRouter

from pychain.node.config import settings
from pychain.node.storage import cache


logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("/var/log/pychain/api.log"),
    ],
)

log = logging.getLogger(__file__)
router = APIRouter()


@router.on_event("startup")
async def startup() -> None:
    log.info("Performing startup sequence")
    cache.peers = settings.dedicated_peers | settings.boot_nodes
    cache.ignored_peers = settings.ignored_peers


from .endpoints import *
