#  app/core/init_db.py
import asyncio
from app.db.mongo import get_db
from app.models.collections import USERS_COLL, PROJECTS_COLL, UPLOADS_COLL, MRV_COLL
from pymongo import ASCENDING, GEOSPHERE

# Basic JSON schema validator for projects (optional)
PROJECTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "owner_org_id"],
        "properties": {
            "name": {"bsonType": "string"},
            "owner_org_id": {"bsonType": "string"},
            "status": {"enum": ["active", "inactive", "archived"], "bsonType": "string"}
        }
    }
}

async def create_indexes_and_validators():
    db = get_db()
    # Users: unique email
    try:
        await db[USERS_COLL].create_index([("email", ASCENDING)], unique=True, name="email_unique")
    except Exception:
        pass

    # Projects: index owner_org_id + name
    try:
        await db[PROJECTS_COLL].create_index([("owner_org_id", ASCENDING)], name="owner_idx")
        await db[PROJECTS_COLL].create_index([("name", ASCENDING)], name="name_idx")
    except Exception:
        pass

    # Field uploads: index on uploader_id, created_at and geospatial index on coordinates if present
    try:
        await db[UPLOADS_COLL].create_index([("uploader_id", ASCENDING)], name="uploader_idx")
        await db[UPLOADS_COLL].create_index([("created_at", ASCENDING)], name="uploads_created_idx")
        # assume coordinates stored as GeoJSON {"type":"Point","coordinates":[lon,lat]}
        await db[UPLOADS_COLL].create_index([("coordinates", GEOSPHERE)], name="coords_2dsphere")
    except Exception:
        # ignore geospatial index creation errors (collection missing or permissions)
        pass

    # MRV records: index created_at, project_id
    try:
        await db[MRV_COLL].create_index([("created_at", ASCENDING)], name="mrv_created_idx")
        await db[MRV_COLL].create_index([("project_id", ASCENDING)], name="mrv_project_idx")
    except Exception:
        pass

    # Optionally create validators (requires privileges) - safe try/except
    try:
        existing = await db.list_collection_names()
        if PROJECTS_COLL not in existing:
            await db.create_collection(PROJECTS_COLL, validator=PROJECTS_VALIDATOR)
    except Exception:
        # skip if not allowed
        pass

    return True
