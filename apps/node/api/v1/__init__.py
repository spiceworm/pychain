import logging

from fastapi import APIRouter


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
    log.info("Starting client API")


from .endpoints import *
