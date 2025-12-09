import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(
    settings.MONGODB_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

database = client[settings.MONGO_DB_NAME]

def get_db():
    return database
