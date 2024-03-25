import motor.motor_asyncio

mongo_client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://vayi:vayi12aBde@192.168.1.223:27017/')
db = mongo_client.lingxing
collection = db['products']


# 关闭MongoDB连接的函数应该也是异步的
async def close_mongo_connection():
    mongo_client.close()
