from __future__ import annotations

from ipaddress import IPv4Address
import logging
from typing import (
    List,
    Union,
)

import asyncpg
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from .models import (
    GUID,
    Node,
)


__all__ = ("Database",)


log = logging.getLogger(__name__)


class Database:
    metadata = sa.MetaData()

    def __init__(
        self,
        *,
        host: str,
        password: str,
        port: int = 5432,
        user: str = "postgres",
        database: str = "postgres",
    ):
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.database = database

    async def add_node(self, address: str) -> Node:
        # Only boot nodes should invoke this method
        async with self.pool.acquire() as conn:
            guid_id = await conn.fetchval(
                "INSERT INTO nodes (address) VALUES ($1) RETURNING guid",
                address,
            )
            return Node(guid_id, address)

    def create_schema(self):
        dsn = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        engine = sa.create_engine(dsn, echo=log.level <= logging.DEBUG)
        self.metadata.create_all(engine)

    async def ensure_message(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (id, counter) VALUES (1, 0) ON CONFLICT DO NOTHING"
            )

    async def ensure_node(self, address: str, guid: Union[GUID, int]) -> None:
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO nodes (address, guid) 
                VALUES ($1, $2) 
                ON CONFLICT DO NOTHING
            """
            await conn.execute(query, address, int(guid))

    async def get_client(self) -> Union[Node, None]:
        async with self.pool.acquire() as conn:
            if node := await conn.fetchrow("SELECT * FROM nodes WHERE is_client IS TRUE"):
                guid_id = node["guid"]
                address = node["address"]
                return Node(guid_id, address)

    async def get_node_by_address(self, address: [IPv4Address, str]) -> Union[Node, None]:
        async with self.pool.acquire() as conn:
            if node := await conn.fetchrow("SELECT guid FROM nodes WHERE address=$1", str(address)):
                guid_id = node["guid"]
                return Node(guid_id, address)
            return None

    async def get_node_by_guid(self, guid: [GUID, int]) -> Node:
        async with self.pool.acquire() as conn:
            if node := await conn.fetchrow("SELECT address FROM nodes WHERE guid=$1", int(guid)):
                address = node["address"]
                return Node(guid, address)
            return Node(guid, None)

    async def get_nodes(self) -> List[Node]:
        async with self.pool.acquire() as conn:
            nodes = await conn.fetch("SELECT guid, address FROM nodes ORDER BY guid")
            return [Node(n["guid"], n["address"]) for n in nodes]

    async def get_max_guid(self) -> GUID:
        async with self.pool.acquire() as conn:
            guid_id = await conn.fetchval("SELECT MAX(guid) FROM nodes")
            return GUID(guid_id)

    async def get_max_guid_node(self) -> Node:
        async with self.pool.acquire() as conn:
            node = await conn.fetchrow(
                "SELECT address, guid FROM nodes WHERE guid = (SELECT MAX(guid) FROM nodes)"
            )
            address = node["address"]
            guid_id = node["guid"]
            return Node(guid_id, address)

    async def increment_message_count(self) -> None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE messages SET counter = counter + 1 WHERE id=1 RETURNING counter"
            )

    async def init(self) -> Database:
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=5,
            max_size=10,
        )
        return self

    async def set_client(self, address: str, guid: Union[GUID, int]) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO nodes (address, guid, is_client) VALUES ($1, $2, true)",
                address,
                int(guid),
            )

    async def update_message_count_if_less_than(self, count: int) -> bool:
        """
        Returns true if and update was performed otherwise false
        """
        async with self.pool.acquire() as conn:
            output = await conn.execute(
                "UPDATE messages SET counter = $1 WHERE id=1 AND $1 > (SELECT counter FROM messages WHERE id=1)",
                count,
            )
            return output != "UPDATE 0"


Message = sa.Table(
    "messages",
    Database.metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("counter", sa.Integer, nullable=False, default=0),
)

Nodes = sa.Table(
    "nodes",
    Database.metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("address", postgresql.INET, unique=True),
    sa.Column("guid", sa.Integer, sa.Identity(start=1, cycle=False), unique=True),
    sa.Column("is_client", sa.Boolean, default=False),
)
