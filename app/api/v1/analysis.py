# app/api/v1/analysis.py
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.db.mongo import get_db
from app.services.mrv_service import build_mrv_record, compute_mrv_hash
import asyncio
import uuid
from bson import ObjectId

router = APIRouter()

async def mock_ml_worker(upload_doc: dict) -> dict:
    await asyncio.sleep(1)
    fname = (upload_doc.get("filename") or "").lower()
    if "mangrove" in fname:
        ecos = "mangrove"; canopy = 70.0; ndvi = 0.65
    elif "seagrass" in fname:
        ecos = "seagrass"; canopy = 55.0; ndvi = 0.45
    else:
        ecos = "unknown"; canopy = 30.0; ndvi = 0.30
    mask_ipfs = "Qm" + uuid.uuid4().hex[:44]
    # Return a payload shaped like your ML worker would
    return {"Tile_ID": "DUMMY", "class": ecos, "canopy_percent": canopy, "ndvi_field": ndvi, "mask_ipfs": mask_ipfs,
            "biomass": {"AGB_t_per_ha": 0, "BGB_t_per_ha": 0, "Carbon_t_per_ha": 0, "CO2eq_t_per_ha": 0,
                        "credit_suggestion": {"area_ha": 1, "gross_CO2eq_t": 0, "suggested_credits_tCO2e": 0, "buffer_fraction": 0}}}

async def run_full_analysis(upload_id: str):
    db = get_db()
    # Try finding upload by string _id or ObjectId
    upload_doc = await db["field_uploads"].find_one({"_id": upload_id})
    if upload_doc is None:
        try:
            upload_doc = await db["field_uploads"].find_one({"_id": ObjectId(upload_id)})
        except Exception:
            upload_doc = None
    if not upload_doc:
        return

    ml = await mock_ml_worker(upload_doc)
    await asyncio.sleep(0.5)
    sat_result = {"ndvi_satellite": ml.get("ndvi_field"), "satellite_score": 0.9}

    # Build MRV record (no hash yet)
    mrv_doc = build_mrv_record(upload_id, ml, sat_result)

    # Try to fetch project plantation_hash if upload_doc links to a project
    plantation_hash = ""
    project_id = upload_doc.get("project_id") or upload_doc.get("project")
    if project_id:
        try:
            proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
        except Exception:
            proj = await db["projects"].find_one({"_id": project_id})
        if proj:
            plantation_hash = (proj.get("plantation") or {}).get("plantation_hash") or ""

    # compute MRV hash combining canonical MRV data and plantation_hash
    mrv_hash = compute_mrv_hash(mrv_doc, plantation_hash)
    mrv_doc["mrv_hash"] = mrv_hash

    # For analysis run (not dummy) set is_dummy False
    mrv_doc["is_dummy"] = False

    # Insert and update upload doc to point to MRV
    res = await db["mrv_records"].insert_one(mrv_doc)
    try:
        # set mrv_id on upload (string)
        await db["field_uploads"].update_one({"_id": upload_doc.get("_id")}, {"$set": {"status": "analyzed", "mrv_id": str(res.inserted_id)}})
    except Exception:
        pass

    # return new mrv id string
    return str(res.inserted_id)


@router.post("/run-analysis/{upload_id}")
async def run_analysis(upload_id: str, background_tasks: BackgroundTasks):
    db = get_db()
    # validate upload exists
    upload_doc = await db["field_uploads"].find_one({"_id": upload_id})
    if upload_doc is None:
        try:
            upload_doc = await db["field_uploads"].find_one({"_id": ObjectId(upload_id)})
        except Exception:
            upload_doc = None
    if upload_doc is None:
        raise HTTPException(status_code=404, detail="upload_id not found")
    background_tasks.add_task(run_full_analysis, upload_id)
    return {"status": "scheduled", "upload_id": upload_id}


@router.get("/mrv/{mrv_id}")
async def get_mrv(mrv_id: str):
    db = get_db()
    # try string id first
    doc = await db["mrv_records"].find_one({"_id": mrv_id})
    if not doc:
        try:
            doc = await db["mrv_records"].find_one({"_id": ObjectId(mrv_id)})
        except Exception:
            doc = None
    if not doc:
        raise HTTPException(status_code=404, detail="mrv not found")

    # normalize created_at to iso if datetime
    created = doc.get("created_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat()

    return {
        "mrv_id": str(doc.get("_id")),
        "upload_id": doc.get("upload_id"),
        "project_id": doc.get("project_id"),
        "ml_result": doc.get("ml_result"),
        "ndvi_satellite": doc.get("ndvi_satellite"),
        "satellite_score": doc.get("satellite_score"),
        "carbon_stock_tCO2e": doc.get("carbon_stock_tCO2e"),
        "created_at": created,
        "verifier_status": doc.get("verifier_status", "pending"),
        "mrv_hash": doc.get("mrv_hash"),
        "is_dummy": bool(doc.get("is_dummy", False)),
    }
