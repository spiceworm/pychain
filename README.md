## Node Configuration
* `BOOT_NODE` (required)
  * Node to use for bootstrapping to the network.
  * Example config: `BOOT_NODE=<URL or IP-address>`

* `LOG_DIR` (optional, default: /var/log/pychain)
  * Filesystem directory where logs will be written

* `LOG_LEVEL` (optional, default: INFO)
  * Choices: DEBUG, INFO, WARNING, ERROR, CRITICAL

* `NETWORK_SYNC_INTERVAL` (optional, default: 60)
  * How many seconds should elapse between executions of network_scan.py.

* `NETWORK_SYNC_JITTER` (optional, default: 30)
  * Maximum number of seconds of jitter to add to NETWORK_SYNC_INTERVAL.

* `STORAGE_DIR` (optional, default: /usr/local/etc/pychain)
  * Filesystem directory where data will be written

## Development Environment
```bash
# Start 1 boot node and 4 client nodes with some environment variable tweaks suitable
# for a development environment.
$ ./run.py 70 -e NETWORK_SYNC_INTERVAL=15 -e NETWORK_SYNC_JITTER=5 -e LOG_LEVEL=DEBUG

# Tail logs to observe node behavior
$ docker exec -it pychain_client_1_1 tail -f /var/log/pychain/{api,network_sync}.log
$ docker exec -it pychain_boot_1_1 tail -f /var/log/pychain/{api,network_sync}.log
```

## Tests
```bash
$ docker-compose -f test.yml up --build
```

## Architecture
```
Each node is running
- nginx: reverse proxy to API
- uvicorn: Serving API written in FastAPI
- python: Long running `network_sync` process that causes has client join the network
    and synchronize with peers
- postgres: Running in sidecar container alongside each node container and is used
    to store node state.

nginx, uvicorn, and python processes are managed by supervisor in the client container.
```

## Development notes
```
TODO:
Add a some sort of identifier to the response from /api/v1/status that
  tells the caller that the callee is actually a node on the pychain
  network. Otherwise any server that responds to requests on that
  endpoint will be seen as a valid peer.

Each node should determine if their peers are running a compatible version of
the software as their own before keeping them as a peer. Maybe there should be
a "capabilities" endpoint whose response gets added as an attribute to Peer
objects and those capabilities can be used to enable/disable certain features
when interacting with peer nodes.

For testing purposes, create a "beacon" node that all nodes alert when a message
  is broadcast. All nodes would tell the beacon that they received this message,
  Checking the beacon logs would allow us to confirm whether the broadcast was
  propogated to the entire network and how long it took for all nodes to see it.

Configure logrotate

Broadcast message when a peer is leaving the network
- Handle special message types (events)

Nodes should associate a timestamp with peer GUIDs. That timestamp should get
  updated each time the corresponding peer is responsive. If a client has not
  heard from a peer with a certain GUID after some time, it should delete all
  saved records associated with that GUID (such as peer IP address)

Authenticate requests between clients so that a malicious node is not able to
  call endpoints such as /network/join and provide a GUID that is in use by an
  existing client.

Mitigate sybil attack where attacker could have several client join and then leave.
  The existing nodes will still attempt to contact those nodes until their GUID
  timeout interval was hit. A valid client would waste a ton of time waiting for
  the requests to timeout to these malicious nodes.

Handle case where boot node goes down. It will need to remember the GUIDs it has
  allocated previously. All nodes should mount their databases

Make adding nodes to the database better. It's ugly to call `ensure_node` all over the
  place.

Fix ensure_address so that it is less cludgy and does not ONLY use the boot node

Add a counter to node entries that increments if the node is unresponsive. Ignore
  nodes that have not been responsive after N attempts.

TODO: Figure out how to prevent flooding the message with duplicate messages as it happens ALOT
```

### Message Broadcasting
```python
# Run this from within a client container.
# Make sure network_sync.py has run at least once by tailing the logs.
# Otherwise the client will not know any peers to sent the message to.
# If it has not ran a single time yet, the client will not even know
# it's own GUID and address.

import aiohttp, asyncio
from pychain.node.config import settings
from pychain.node.db import Database
from pychain.node.models import Message, Node

async def main():
    db = Database(host=settings.db_host, password=settings.db_password)
    Node.db = await db.init()
    client = await db.get_client()

    async with aiohttp.ClientSession() as session:
        msg = Message({"event": "something", "args": [1], "kwargs": {2: 3}})
        await client.broadcast(msg, session)


asyncio.run(main())
```
