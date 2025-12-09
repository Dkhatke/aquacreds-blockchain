from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
import random
import hashlib
from datetime import datetime

from app.db.mongo import get_db
from app.services.project_service import get_project, update_project
from app.api.deps import get_current_user

router = APIRouter()
COLL = "mrv_records"


@router.post("/mrv/dummy", summary="Generate dummy MRV report automatically")
async def create_dummy_mrv(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()

    # verify project exists
    project = await get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # ----- Dummy ML Result -----
    dummy_ml = {
        "Tile_ID": f"TILE-{random.randint(1000,9999)}",
        "canopy_cover": round(random.uniform(40, 95), 2),
        "biomass_estimate": round(random.uniform(4.5, 18.5), 2),
        "tree_health_index": round(random.uniform(0.60, 0.98), 2),
    }

    # ----- Dummy Satellite Data -----
    ndvi = round(random.uniform(0.35, 0.90), 3)
    sat_score = round(random.uniform(60, 98), 1)

    # ----- Record -----
    record = {
        "project_id": project_id,
        "upload_id": f"dummy-UP-{random.randint(1000,9999)}",
        "ml_result": dummy_ml,
        "sat_result": {
            "ndvi_satellite": ndvi,
            "satellite_score": sat_score,
        },
        "created_at": datetime.utcnow(),
    }

    # Create deterministic hash
    hash_input = f"{project_id}-{ndvi}-{sat_score}-{record['ml_result']}"
    record["mrv_hash"] = hashlib.sha256(hash_input.encode()).hexdigest()

    # Insert MRV record
    res = await db[COLL].insert_one(record)
    record["id"] = str(res.inserted_id)

    # Attach MRV reference to project
    existing = project.get("mrv_ids") or []
    existing.append(record["id"])

    await update_project(project_id, {"mrv_ids": existing})

    return {
        "success": True,
        "message": "Dummy MRV generated",
        "mrv_record": record
    }
