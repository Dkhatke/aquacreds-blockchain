# app/api/v1/mrv.py
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId, errors as bson_errors
from typing import Optional, List
from datetime import datetime

from app.db.mongo import get_db
from app.schemas.mrv_schema import MRVCreate, MRVOut
from app.services.mrv_service import build_mrv_record, compute_mrv_hash
from app.api.deps import get_current_user

router = APIRouter()
COLL = "mrv_records"


@router.post("/mrv", response_model=MRVOut, status_code=201)
async def create_mrv(payload: MRVCreate, current_user=Depends(get_current_user)):
    """
    Create MRV record (manual input). Computes mrv_hash and stores document.
    """
    db = get_db()

    ml_dict = payload.ml_result.model_dump(by_alias=True)
    record = build_mrv_record(
        upload_id=payload.upload_id,
        ml_result=ml_dict,
        sat_result={
            "ndvi_satellite": payload.ndvi_satellite,
            "satellite_score": payload.satellite_score,
        }
    )

    record["project_id"] = payload.project_id

    # Try to fetch plantation_hash from project (if project_id provided)
    plantation_hash = None
    if payload.project_id:
        try:
            proj = await db["projects"].find_one({"_id": ObjectId(payload.project_id)})
            if proj and isinstance(proj.get("plantation"), dict):
                plantation_hash = proj.get("plantation", {}).get("plantation_hash") or proj.get("plantation", {}).get("hash")
        except Exception:
            plantation_hash = None

    # compute deterministic hash
    try:
        record["mrv_hash"] = compute_mrv_hash(record, plantation_hash=plantation_hash)
    except Exception:
        record["mrv_hash"] = None

    # Insert
    res = await db[COLL].insert_one(record)
    saved = await db[COLL].find_one({"_id": res.inserted_id})
    if not saved:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create MRV record")

    saved["id"] = str(saved["_id"])
    return saved


@router.get("/mrv/{mrv_id}", response_model=MRVOut)
async def get_mrv(mrv_id: str, current_user=Depends(get_current_user)):
    """
    Robust retrieval:
      - try direct _id match with ObjectId
      - try direct string _id
      - fall back to document 'id' field, mrv_hash, or upload_id
    """
    db = get_db()

    # 1) try as ObjectId
    try:
        obj = ObjectId(mrv_id)
    except (bson_errors.InvalidId, Exception):
        obj = None

    doc = None
    if obj is not None:
        doc = await db[COLL].find_one({"_id": obj})
    # 2) direct string _id (some parts of app might have stored string keys)
    if not doc:
        doc = await db[COLL].find_one({"_id": mrv_id})
    # 3) fallback search by id field / mrv_hash / upload_id
    if not doc:
        doc = await db[COLL].find_one({"$or": [{"id": mrv_id}, {"mrv_hash": mrv_id}, {"upload_id": mrv_id}]})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mrv not found")

    doc["id"] = str(doc["_id"])
    return doc


@router.get("/mrv/{mrv_id}", response_model=MRVOut)
async def get_mrv(mrv_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    doc = None

    # 1) try as ObjectId
    try:
        obj = ObjectId(mrv_id)
    except (bson_errors.InvalidId, Exception):
        obj = None

    if obj is not None:
        doc = await db["mrv_records"].find_one({"_id": obj})

    # 2) try direct string _id (some code may have stored string _id)
    if not doc:
        doc = await db["mrv_records"].find_one({"_id": mrv_id})

    # 3) fallback: maybe stored an 'id' field, mrv_hash, or upload_id
    if not doc:
        doc = await db["mrv_records"].find_one({"$or": [{"id": mrv_id}, {"mrv_hash": mrv_id}, {"upload_id": mrv_id}]})

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="mrv not found")

    doc["id"] = str(doc.get("_id"))
    return doc
