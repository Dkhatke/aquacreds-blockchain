# app/core/create_project_indexes.py
import asyncio
from app.db.mongo import get_client
from app.core.config import settings

async def run():
    client = get_client()
    db = client[settings.MONGO_DB_NAME]
    await db["projects"].create_index([("owner.owner_id", 1)])
    await db["projects"].create_index([("created_at", -1)])
    # 2dsphere geo index
    await db["projects"].create_index([("location_geojson", "2dsphere")])
    print("Indexes created")

if __name__ == "__main__":
    asyncio.run(run())
