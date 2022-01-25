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
from .config import settings


class Database:
    metadata = sa.MetaData()

    def __init__(self):
        self.user = "postgres"
        self.password = settings.db_password
        self.host = settings.db_host
        self.port = 5432
        self.database = "postgres"

    def create_schema(self):
        dsn = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        engine = sa.create_engine(dsn, echo=True)
        self.metadata.create_all(engine)

    async def ensure_message(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO messages (id, counter) VALUES (1, 0) ON CONFLICT DO NOTHING"
            )

    async def ensure_node(self, address: str, guid: Union[GUID, int, None] = None) -> Node:
        async with self.pool.acquire() as conn:
            if guid is not None:
                query = """
                    INSERT INTO nodes (address, guid) 
                    VALUES ($1, $2) 
                    ON CONFLICT DO NOTHING
                """
                args = (address, int(guid))
            else:
                # Only boot nodes should invoke this method without a guid argument
                # It will create a new entry and
                query = "INSERT INTO nodes (address) VALUES ($1)"
                args = (address,)
            await conn.execute(query, *args)

            guid_id = await conn.fetchval("SELECT guid FROM nodes WHERE address=$1", address)
            guid = GUID(guid_id)
            return Node(guid, address)

    async def get_client(self) -> Union[Node, None]:
        async with self.pool.acquire() as conn:
            if node := await conn.fetchrow("SELECT * FROM nodes WHERE is_client IS TRUE"):
                guid = GUID(node["guid"])
                address = node["address"]
                return Node(guid, address)

    async def get_node(self, guid: [GUID, int]) -> Node:
        async with self.pool.acquire() as conn:
            if node := await conn.fetchrow("SELECT address FROM nodes WHERE guid=$1", int(guid)):
                address = node["address"]
            else:
                address = None
            return Node(GUID(int(guid)), address)

    async def get_nodes(self) -> List[Node]:
        async with self.pool.acquire() as conn:
            nodes = await conn.fetch("SELECT guid, address FROM nodes ORDER BY guid")
            return [Node(GUID(n["guid"]), n["address"]) for n in nodes]

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
            return Node(GUID(guid_id), address)

    async def increment_message_count(self) -> None:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE messages SET counter = counter + 1 WHERE id=1 RETURNING counter"
            )

    async def init(self) -> None:
        self.pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=5,
            max_size=10,
        )

    async def set_client(self, address: str, guid: GUID) -> None:
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
