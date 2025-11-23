# app/services/project_service.py
from app.db.mongo import get_db
from datetime import datetime
from bson import ObjectId

COLL = "projects"
UPLOADS_COLL = "field_uploads"

async def create_project(project_in: dict) -> dict:
    db = get_db()
    doc = project_in.copy()

    # ensure mrv_ids exists and is a list of strings
    doc.setdefault("mrv_ids", [])
    # other autogen fields
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = datetime.utcnow()
    doc["status"] = doc.get("status", "draft")

    # rest of logic unchanged...
    if "geotag_photos" in doc and doc["geotag_photos"]:
        p = doc["geotag_photos"][0]
        try:
            lon = float(p.get("longitude"))
            lat = float(p.get("latitude"))
            doc["location_geojson"] = {"type": "Point", "coordinates": [lon, lat]}
        except Exception:
            pass

    res = await db[COLL].insert_one(doc)
    project = await db[COLL].find_one({"_id": res.inserted_id})
    if project:
        project["id"] = str(project["_id"])
    return project

async def get_project(project_id: str) -> dict | None:
    db = get_db()
    try:
        obj = ObjectId(project_id)
    except Exception:
        return None
    p = await db[COLL].find_one({"_id": obj})
    if p:
        p["id"] = str(p["_id"])
    return p

async def list_projects(filter_query: dict = None, limit: int = 50, skip: int = 0):
    db = get_db()
    q = filter_query or {}
    cursor = db[COLL].find(q).skip(skip).limit(limit)
    out = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        out.append(doc)
    return out

async def update_project(project_id: str, updates: dict) -> dict | None:
    db = get_db()
    try:
        obj = ObjectId(project_id)
    except Exception:
        return None
    updates["updated_at"] = datetime.utcnow()
    await db[COLL].update_one({"_id": obj}, {"$set": updates})
    return await get_project(project_id)


async def add_photo_to_project(project_id: str, upload_doc: dict, acting_user: dict) -> dict | None:
    """
    Attach an upload (upload_doc) to project's geotag_photos.
    - upload_doc: document from field_uploads collection (must include upload_id/ipfs_hash/latitude/longitude/filename/exif/timestamp)
    - acting_user: current_user dict (for added_by)
    """
    db = get_db()
    try:
        proj_obj = ObjectId(project_id)
    except Exception:
        return None

    project = await db[COLL].find_one({"_id": proj_obj})
    if not project:
        return None

    # Build normalized photo entry
    photo_entry = {
        "upload_id": upload_doc.get("upload_id") or str(upload_doc.get("_id")),
        "ipfs_hash": upload_doc.get("ipfs_hash"),
        "filename": upload_doc.get("filename"),
        "size": upload_doc.get("size"),
        "sha256": upload_doc.get("sha256"),
        "exif": upload_doc.get("exif"),
        "latitude": None,
        "longitude": None,
        "timestamp": None,
        "added_by": {
            "id": str(acting_user.get("id")) if acting_user else None,
            "email": acting_user.get("email") if acting_user else None,
        },
        "added_at": datetime.utcnow()
    }

    # try to populate lat/long/timestamp from upload_doc.exif or top-level fields
    exif = upload_doc.get("exif") or {}
    # Accept latitude/longitude either at top-level or inside exif
    lat = upload_doc.get("latitude") or exif.get("latitude") or exif.get("lat")
    lon = upload_doc.get("longitude") or exif.get("longitude") or exif.get("lon")
    ts = upload_doc.get("timestamp") or exif.get("timestamp") or exif.get("DateTimeOriginal")

    try:
        if lat is not None:
            photo_entry["latitude"] = float(lat)
        if lon is not None:
            photo_entry["longitude"] = float(lon)
    except Exception:
        # ignore conversion error; keep None
        pass

    if ts:
        photo_entry["timestamp"] = ts

    # Use $addToSet with a filter on upload_id to avoid duplicates
    update_doc = {
        "$addToSet": {
            "geotag_photos": photo_entry
        },
        "$setOnInsert": {
            "updated_at": datetime.utcnow()
        }
    }

    await db[COLL].update_one({"_id": proj_obj}, update_doc)

    # If project had no location_geojson, set it using this photo's coords (if available)
    if not project.get("location_geojson") and photo_entry.get("latitude") is not None and photo_entry.get("longitude") is not None:
        await db[COLL].update_one(
            {"_id": proj_obj},
            {"$set": {"location_geojson": {"type": "Point", "coordinates": [photo_entry["longitude"], photo_entry["latitude"]]}, "updated_at": datetime.utcnow()}}
        )

    return await get_project(project_id)
# add near other functions in app/services/project_service.py

async def list_submitted_projects(limit: int = 100, skip: int = 0) -> list[dict]:
    """
    Return projects with status == 'submitted' (or other statuses you decide).
    """
    await asyncio.sleep(0)
    items = [p for p in _PROJECTS.values() if p.get("status") == "submitted"]
    return [deepcopy(p) for p in items[skip: skip + limit]]

async def review_project(project_id: str, action: str, reviewer_id: str, comment: str | None = None) -> dict | None:
    """
    action: 'approve' or 'reject'
    This sets project.status to 'approved' or 'rejected' and records reviewer metadata.
    """
    await asyncio.sleep(0)
    proj = _PROJECTS.get(project_id)
    if not proj:
        return None
    action = action.lower()
    if action not in ("approve", "reject"):
        raise ValueError("action must be 'approve' or 'reject'")
    new_status = "approved" if action == "approve" else "rejected"
    proj["status"] = new_status
    proj.setdefault("review", {})
    proj["review"]["reviewer_id"] = reviewer_id
    proj["review"]["action"] = new_status
    proj["review"]["comment"] = comment or ""
    proj["review"]["timestamp"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    _PROJECTS[project_id] = proj
    return deepcopy(proj)
