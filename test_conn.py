import os, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# read from .env
MONGO = "mongodb+srv://db_user:db_user@aquacreds.wsmwvcu.mongodb.net/?appName=Aquacreds"

if not MONGO:
    print("MONGODB_URL not set.")
    raise SystemExit(1)

print("Using certifi CA file:", certifi.where())

client = AsyncIOMotorClient(
    MONGO,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000
)

async def main():
    try:
        print("Trying connection...")
        dbs = await client.list_database_names()
        print("Connected! Databases:", dbs)
    except Exception as e:
        print("Connection failed:", type(e).__name__, e)

asyncio.run(main())
