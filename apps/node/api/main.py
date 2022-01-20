import logging

from fastapi import FastAPI

from v1 import router as v1_router

from pychain.node.config import settings


logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(settings.log_dir / "api.log"),
    ],
)
log = logging.getLogger(__file__)


def create_app():
    api = FastAPI()
    api.include_router(v1_router, prefix="/api/v1")

    @api.on_event("startup")
    async def startup() -> None:
        log.info("Starting client API")

    @api.on_event("shutdown")
    async def shutdown() -> None:
        log.info("Stopping client API")

    return api


app = create_app()
