from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

_client: AsyncIOMotorClient | None = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        if not settings.MONGODB_URI:
            raise RuntimeError("MONGODB_URI not configured in .env")
        _client = AsyncIOMotorClient(settings.MONGODB_URI)
    return _client

def get_db():
    client = get_client()
    return client[settings.MONGO_DB_NAME]
