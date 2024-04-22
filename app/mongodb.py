import motor.motor_asyncio

mongo_client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://vayi:vayi12aBde@192.168.1.223:27017/')
db = mongo_client.lingxing
