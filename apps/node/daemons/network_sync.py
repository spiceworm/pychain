import asyncio
import logging
import random

from aiohttp import ClientSession
from apscheduler.schedulers.blocking import BlockingScheduler

from pychain.node.config import settings
from pychain.node.db import Database
from pychain.node.models import (
    GUID,
    Node,
)


logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(settings.log_dir / "network_sync.log"),
    ],
)
# Suppress apscheduler log messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)


log = logging.getLogger(__file__)


async def network_sync() -> None:
    db = Database()
    await db.init()

    async with ClientSession() as session:
        if not (client := await db.get_client()):
            boot_node = Node(GUID(0), settings.boot_node_address)
            log.info("Sending join request to %s", boot_node.address)
            client = await boot_node.join_network(session)
            await db.set_client(client.address, client.guid)
            log.debug("Joined network as %s", client)

        log.debug("Connected to network as %s", client)

        for peer in (peers := await client.get_peers(db, session)):
            await db.ensure_node(peer.address, peer.guid)
            old_max_guid_node = await db.get_max_guid_node()
            new_max_guid_peer = await peer.sync(client.guid, old_max_guid_node, session)
            await db.ensure_node(new_max_guid_peer.address, new_max_guid_peer.guid)

    log.info("client: %s", client)
    log.info("max guid: %s", await db.get_max_guid())
    log.info("peers: %s", [int(p.guid) for p in peers])
    log.info("-" * 10)


def main() -> None:
    """ """
    if settings.is_boot_node:
        log.debug("Boot nodes do not perform network sync")
    else:
        asyncio.run(network_sync())


if __name__ == "__main__":
    jitter = random.randint(1, 30)
    network_sync_interval = settings.network_sync_interval + jitter
    scheduler = BlockingScheduler()
    scheduler.add_job(main, trigger="interval", seconds=network_sync_interval)
    scheduler.start()
