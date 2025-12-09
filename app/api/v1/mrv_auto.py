# app/api/v1/mrv_auto.py
from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from datetime import datetime
import hashlib
import random

from app.db.mongo import get_db
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/projects/{project_id}/generate-mrv")
async def generate_dummy_mrv(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()

    proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    dummy_mrv = {
        "project_id": project_id,
        "ndvi": round(random.uniform(0.45, 0.85), 3),
        "ndwi": round(random.uniform(0.10, 0.45), 3),
        "canopy_cover": random.randint(40, 90),
        "biomass_ton": round(random.uniform(12, 60), 2),
        "carbon_stock_tCO2e": round(random.uniform(20, 120), 2),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "verified",  # ✅ NEW FLAG
    }

    mrv_string = str(dummy_mrv).encode()
    mrv_hash = hashlib.sha256(mrv_string).hexdigest()
    dummy_mrv["mrv_hash"] = mrv_hash

    saved = await db["mrv_records"].insert_one(dummy_mrv)
    mrv_id = str(saved.inserted_id)

    await db["projects"].update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {"status": "submitted"},    # still submitted until verifier approves
            "$addToSet": {"mrv_ids": mrv_id}
        }
    )

    return {
        "success": True,
        "message": "MRV Generated",
        "mrv_id": mrv_id,
        "mrv_hash": mrv_hash,
        "dummy_mrv": dummy_mrv,
    }

