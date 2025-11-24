from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

# Create Mongo client (no type hints here – avoids Pylance errors)
client = AsyncIOMotorClient(settings.MONGODB_URI)

# Select database
database = client["aquacreds"]


def get_db():
    """Return MongoDB database instance."""
    return database
