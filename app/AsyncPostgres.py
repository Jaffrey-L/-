import asyncio
import asyncpg
from app.config import Config


class AsyncPostgres:
    def __init__(self, host=Config.PG_HOST, port=Config.PG_PORT, user=Config.PG_USER, password=Config.PG_PASSWORD,
                 database=Config.PG_DATABASE, schema=Config.PG_SCHEMA):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.schema = schema
        self.conn = None

    async def __aenter__(self):
        # 创建一个到 PostgreSQL 的连接
        self.conn = await asyncpg.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database
        )
        await self.conn.execute(f'SET search_path TO {self.schema}')
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 关闭连接
        await self.conn.close()
