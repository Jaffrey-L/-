import asyncio
import asyncpg


class AsyncPostgres:
    def __init__(self, host='192.168.1.223', port=5432, user='postgres', password='ab3E3k3j4DDEEabc',
                 database='postgres', schema='vayidw'):
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
