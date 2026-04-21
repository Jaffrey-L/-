import asyncio
import aiomysql
from app.config import Config


class AsyncMySQL:
    def __init__(self, host=Config.MYSQL_HOST, port=Config.MYSQL_PORT, user=Config.MYSQL_USER,
                 password=Config.MYSQL_PASSWORD, db=Config.MYSQL_DB):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db
        self.conn = None

    async def __aenter__(self):
        self.conn = await aiomysql.connect(host=self.host, port=self.port, user=self.user, password=self.password,
                                           db=self.db, loop=asyncio.get_running_loop())
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()
        await self.conn.ensure_closed()
