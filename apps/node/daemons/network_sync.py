import logging
import random

from apscheduler.schedulers.blocking import BlockingScheduler

from pychain.node.config import settings
from pychain.node.models import Peer
from pychain.node.storage.cache import cache


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


def main() -> None:
    """ """
    if not settings.is_boot_node:
        if not cache.address:
            if cache.guid is None:
                log.debug("Sending join request to %s", settings.boot_node.address)
            else:
                log.debug(
                    "Sending re-join request to %s using %s",
                    settings.boot_node.address,
                    cache.guid,
                )

            client = settings.boot_node.join_network(cache.guid)
            cache.guid_map[client.guid] = cache.address = client.address
            cache.network_guid = cache.guid = client.guid
            log.debug("Joined network as %s", client)

        client = Peer(cache.guid, cache.address)
        log.debug("Connected to network as %s", client)
        peers = client.get_peers(cache.guid_map, cache.network_guid, settings.boot_node)

        for peer in peers:
            highest_guid_known_to_client = max(cache.guid, cache.network_guid)
            cache.network_guid = peer.sync(highest_guid_known_to_client)

        log.info("SYNC RESULTS")
        log.info("  client: %s", client)
        log.info("  network_guid: %s", cache.network_guid)
        log.info("  peers:")
        for peer in peers:
            log.info("    %s", peer)
        log.info("  guid_map:")
        for guid, address in cache.guid_map.items():
            log.info("    %s:%s", guid, address)
    else:
        log.debug("Boot nodes do not perform peer discovery")


if __name__ == "__main__":
    jitter = random.randint(1, 30)
    network_sync_interval = settings.network_sync_interval + jitter
    scheduler = BlockingScheduler()
    scheduler.add_job(main, trigger="interval", seconds=network_sync_interval)
    scheduler.start()
