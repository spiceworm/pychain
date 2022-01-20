## Node Configuration
* `ADDRESS_CHECK_FREQUENCY` (optional, default: 25)
  * How many executions of peer_scan.py should occur before this node asks a peer what
    it's IP address is. This feature exists to handle the case where a client's IP
    address changes.

* `BOOT_NODES` (required)
  * Comma delimited list of nodes to use for bootstrapping to the network. Of the nodes
    provided, a randomly selected subset of `MAX_BOOT_NODES` will be used.
  * Example config: `BOOT_NODES=<URL or IP-address>,[<URL or IP-address>]`

* `NETWORK_SYNC_INTERVAL` (optional, default: 60)
  * How many seconds should elapse between executions of network_scan.py.

* `STORAGE_DIR` (optional, default: /usr/local/etc/pychain)
  * Filesystem directory where data will be written

## Development Environment
```bash
$ docker-compose up --build

# Tail logs to observe node behavior
$ docker exec -it pychain_client_1_1 tail -f /var/log/pychain/{api,network_sync}.log
$ docker exec -it pychain_boot_1_1 tail -f /var/log/pychain/{api,network_sync}.log
```

## Architecture
```
Each node is running
- nginx: reverse proxy to API
- uvicorn: Serving API written in FastAPI
- redis: Stores node settings
- python: Long running `network_sync` process that causes has client join the network
    and synchronize with peers

All of these processes are managed by supervisor.
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

Add support for basic message broadcasting between peers

For testing purposes, create a "beacon" node that all nodes alert when a message
  is broadcast. All nodes would tell the beacon that they received this message,
  Checking the beacon logs would allow us to confirm whether the broadcast was
  propogated to the entire network and how long it took for all nodes to see it.

Configure logrotate

Broadcast message when a peer is leaving the network
- Handle special message types (events)

Come up with a better GUID storage solution. If a node shuts down and starts up
  again it should reuse it's old GUID.

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
  allocated previously.
```

### Message Broadcasting
```python
import aiohttp, asyncio
from pychain.node.models import Message, Peer
from pychain.node.storage import cache

async def main():
    cache.message_id_count += 1

    async with aiohttp.ClientSession() as session:
        client = Peer(cache.guid, cache.address)
        msg = Message(
            body="test",
            id=cache.message_id_count,
            originator=client,
        )
        await client.broadcast(msg, session)

asyncio.run(main())
```
