import asyncio
import aiomysql


class AsyncMySQL:
    def __init__(self, host='192.168.1.191', port=3306, user='root', password='Dk03Bt3409abc', db='api_access_token'):
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
