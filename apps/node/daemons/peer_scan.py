import logging
import random
import time
from typing import List, Set

from apscheduler.schedulers.blocking import BlockingScheduler

from pychain.node.config import settings
from pychain.node.models import Peer
from pychain.node.storage import cache


logging.basicConfig(
    datefmt="%H:%M:%S",
    format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("/var/log/pychain/peer_scan.log"),
    ],
)
# Suppress apscheduler log messages
logging.getLogger("apscheduler").setLevel(logging.WARNING)

log = logging.getLogger(__file__)


def apply_peer_limit(randomized_peers: List[Peer], max_peers: int) -> Set[Peer]:
    """
    If we are tracking too many peers, we need to remove some until only `max_peers` are being tracked.
    First remove boot nodes, then remove client nodes.
    Return a set of `Peer` objects that has a max length of `max_peers`
    """
    dedicated_peers = []
    boot_peers = []
    client_peers = []

    for peer in randomized_peers:
        if peer.is_dedicated_peer():
            dedicated_peers.append(peer)
        elif peer.is_boot_node():
            boot_peers.append(peer)
        else:
            client_peers.append(peer)

    peers = dedicated_peers + client_peers + boot_peers

    # `peers` is ordered such that dedicated peers are first, other clients follow, and boot nodes are last.
    # This is intentional so that if our peer limit is exceeded, we can pop nodes off the back until the peer
    # limit is met and we'll keep dedicated peers around followed by other clients. We do not want to clients
    # to rely on boot nodes.
    while len(peers) > max_peers:
        peer = peers.pop()
        log.info("Max peer limit exceeded. Removing %s", peer)

    return set(peers)


def perform_peer_discovery(
    randomized_peers: List[Peer],
    ignored_peers: Set[Peer],
    max_peers: int,
    max_boot_nodes: int,
    client_address: str,
) -> Set[Peer]:
    new_peers = set()

    boot_peer_count = len([p for p in randomized_peers if p.is_boot_node()])

    # Populate `existing_peers` so that dedicated peers appear first in the list
    existing_peers = []
    for peer in randomized_peers:
        if peer.is_dedicated_peer():
            existing_peers.insert(0, peer)
        else:
            existing_peers.append(peer)

    def max_peer_limit_met():
        return len(existing_peers) + len(new_peers) >= max_peers

    for existing_peer in existing_peers:
        for found_peer in existing_peer.get_peers():
            if found_peer in ignored_peers:
                if found_peer.address == client_address:
                    log.debug("Skipping peer. Found self: %s", found_peer)
                else:
                    log.debug("Skipping peer. Is ignored peer: %s", found_peer)
            elif found_peer.is_boot_node() and boot_peer_count == max_boot_nodes:
                log.debug("Skipping boot peer. MAX_BOOT_NODES exist: %s", found_peer)
            elif found_peer in existing_peers:
                log.debug("Skipping peer. Existing peer found: %s", found_peer)
            elif not found_peer.is_alive():
                log.debug("Skipping peer. It is unresponsive: %s", found_peer)
            else:
                log.debug("New peer found: %s", found_peer)
                new_peers.add(found_peer)

            if max_peer_limit_met():
                log.debug("Max peer limit has been reached")
                break

        if max_peer_limit_met():
            break

    for peer in sorted(new_peers):
        log.info("    Discovered %s", peer)

    return set(existing_peers) | new_peers


def main() -> None:
    """ """
    while not Peer("127.0.0.1").is_alive():
        log.info("Waiting for local node API service to be responsive")
        time.sleep(1)

    # Remove unresponsive peers
    cache.peers = {p for p in cache.peers if p.is_alive()}

    if settings.is_boot_node:
        log.info("Boot nodes do not perform peer discovery")
        return
    else:
        cache.peer_scan_execution_count += 1
        log.info("Starting peer scan (execution %s)", cache.peer_scan_execution_count)

    if cache.peers:
        log.info("Starting scan - %s peers:", len(cache.peers))
        for peer in sorted(cache.peers):
            log.info("    %s", peer)
    else:
        log.info("No peers exist, falling back to boot nodes")
        cache.peers = settings.boot_nodes

        log.info("Bootstrapping with %s boot nodes:", len(cache.peers))
        for peer in sorted(cache.peers):
            log.info("    %s", peer)

    should_reset_ip = (
        cache.peer_scan_execution_count == settings.address_check_frequency
    )

    if cache.peers:
        if not cache.address or should_reset_ip:
            cache.address = cache.randomized_peers[0].my_ip()
            log.info("Address set to %s", cache.address)

            # Ignore current node so it does not try to peer with itself.
            cache.ignored_peers = cache.ignored_peers | {Peer(cache.address)}

            # Reset execution counter that is used to determine if we should
            # ask a peer what this client's IP address is.
            cache.peer_scan_execution_count = 0
    else:
        log.error("No peers exist and cannot connect to any boot nodes")
        log.error("Unable to join network")
        return

    cache.peers = perform_peer_discovery(
        cache.randomized_peers,
        cache.ignored_peers,
        settings.max_peers,
        settings.max_boot_nodes,
        cache.address,
    )

    if len(cache.peers) > settings.max_peers:
        cache.peers = apply_peer_limit(cache.randomized_peers, settings.max_peers)

    log.info("Ending scan - %s peers:", len(cache.peers))
    for peer in sorted(cache.peers):
        log.info("    %s", peer)


if __name__ == "__main__":
    jitter = random.randint(1, 30)
    peer_scan_interval = settings.peer_scan_interval + jitter
    scheduler = BlockingScheduler()
    scheduler.add_job(main, trigger="interval", seconds=peer_scan_interval)
    scheduler.start()
