# app/services/upload_service.py
from app.db.mongo import get_db
from bson import ObjectId

COLL = "field_uploads"

async def get_upload_by_upload_id(upload_id: str) -> dict | None:
    """
    Try to find upload by a friendly upload_id field first; if not found,
    try to interpret upload_id as an ObjectId and search by _id.
    """
    db = get_db()
    doc = await db[COLL].find_one({"upload_id": upload_id})
    if doc:
        return doc
    # try as ObjectId
    try:
        obj = ObjectId(upload_id)
        doc = await db[COLL].find_one({"_id": obj})
        return doc
    except Exception:
        return None
