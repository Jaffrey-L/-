import motor.motor_asyncio
from app.config import Config

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGO_URI)
db = mongo_client[Config.MONGO_DB]
