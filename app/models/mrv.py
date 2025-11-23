# app/api/v1/mrv.py

from fastapi import APIRouter, Depends, HTTPException, status, Body
from bson import ObjectId
from datetime import datetime
from typing import Optional

from app.db.mongo import get_db
from app.schemas.mrv_schema import MRVCreate, MRVOut
from app.services.mrv_service import build_mrv_record, compute_mrv_hash
from app.services.project_service import get_project
from app.api.deps import get_current_user

router = APIRouter()
COLL = "mrv_records"


@router.post("/mrv", response_model=MRVOut, status_code=201)
async def create_mrv(payload: MRVCreate, current_user=Depends(get_current_user)):
    db = get_db()

    # normalize ML dict for service; Pydantic model_dump(by_alias=True) ensures Tile_ID alias handled
    ml_dict = payload.ml_result.model_dump(by_alias=True)

    record = build_mrv_record(
        upload_id=payload.upload_id,
        ml_result=ml_dict,
        sat_result={
            "ndvi_satellite": payload.ndvi_satellite,
            "satellite_score": payload.satellite_score,
        }
    )

    # attach project_id from payload
    record["project_id"] = payload.project_id

    # fetch project plantation_hash if available
    plantation_hash: Optional[str] = None
    if payload.project_id:
        proj = await get_project(payload.project_id)
        if proj and isinstance(proj.get("plantation"), dict):
            # expecting plantation.plantation_hash saved on project
            plantation_hash = proj.get("plantation", {}).get("plantation_hash") or proj.get("plantation", {}).get("hash")

    # compute mrv_hash and persist it in record
    try:
        record["mrv_hash"] = compute_mrv_hash(record, plantation_hash=plantation_hash)
    except Exception:
        # don't block creation if hashing somehow fails; set None
        record["mrv_hash"] = None

    # insert into MongoDB
    res = await db[COLL].insert_one(record)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    if not saved:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create MRV record")

    saved["id"] = str(saved["_id"])
    # Ensure created_at is a datetime for Pydantic MRVOut
    return saved


@router.get("/mrv/{mrv_id}", response_model=MRVOut)
async def get_mrv(mrv_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    try:
        obj = ObjectId(mrv_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid MRV id")
    rec = await db[COLL].find_one({"_id": obj})
    if not rec:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    rec["id"] = str(rec["_id"])
    return rec
