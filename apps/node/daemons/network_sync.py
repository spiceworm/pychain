import logging
import random
import time

from apscheduler.schedulers.blocking import BlockingScheduler

from pychain.node.config import settings
from pychain.node.models import Peer
from pychain.node.storage import cache


logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("/var/log/pychain/network_sync.log"),
    ],
)
# Suppress apscheduler log messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)

log = logging.getLogger(__file__)


def main() -> None:
    """ """
    while not Peer(cache.guid, "127.0.0.1").is_alive():
        log.info("Waiting for local API service to be responsive")
        time.sleep(1)

    if not settings.is_boot_node:
        boot_node = settings.boot_node

        if cache.guid is None:
            if boot_node:
                log.debug("Sending request to %s to join network", boot_node)
                client = boot_node.join_network()
                cache.address, cache.guid = client.address, client.guid
                cache.network_guid = cache.guid
                log.info(
                    "NETWORK JOIN: %s peers=%s",
                    client,
                    client.get_peer_guids(),
                )
            else:
                log.error("No boot node is configured for client")
        else:
            log.debug("Client is connected to the network")

            client = Peer(cache.guid, cache.address)

            for guid in client.get_peer_guids(cache.network_guid):
                guid_address_map = cache.guid_address_map
                address = guid_address_map.get(guid)

                if address is None:
                    # TODO: attempt to resolve address from peers before using boot node
                    address = boot_node.get_peer_address(guid)
                    log.debug("Boot node resolved guid %s to %s", guid, address)
                    guid_address_map[guid] = address
                    cache.guid_address_map = guid_address_map
                else:
                    log.debug("Storage resolved guid %s to %s", guid, address)

                cache.network_guid = Peer(guid, address).sync(
                    max(cache.guid, cache.network_guid)
                )

            log.info(
                "%s: network_guid=%s, peers=%s, guid_address_map=%s",
                client,
                cache.network_guid,
                client.get_peer_guids(cache.network_guid),
                [*cache.guid_address_map.keys()]
            )
    else:
        log.info("Boot nodes do not perform peer discovery")


if __name__ == "__main__":
    jitter = random.randint(1, 30)
    network_sync_interval = settings.network_sync_interval + jitter
    scheduler = BlockingScheduler()
    scheduler.add_job(main, trigger="interval", seconds=network_sync_interval)
    scheduler.start()
