import logging

import aiohttp
import fastapi
import redis
import rq

from v1 import router as v1_router

from pychain.node.config import settings
from pychain.node.db import Database


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
    api = fastapi.FastAPI()
    db = Database()
    mempool = rq.Queue('mempool', connection=redis.Redis())
    session = aiohttp.ClientSession()
    api.include_router(v1_router, prefix="/api/v1")

    @api.middleware("http")
    async def db_session_middleware(request: fastapi.Request, call_next):
        request.state.db = db
        request.state.mempool = mempool
        request.state.session = session
        return await call_next(request)

    @api.on_event("startup")
    async def startup() -> None:
        log.info("Starting client API")

        log.info("Creating database schema")
        db.create_schema()

        log.info("Initializing async database connection")
        await db.init()

        log.info("Initializing message row")
        await db.ensure_message()

    @api.on_event("shutdown")
    async def shutdown() -> None:
        log.info("Stopping client API")

        if not session.closed:
            await session.close()

    return api


app = create_app()
