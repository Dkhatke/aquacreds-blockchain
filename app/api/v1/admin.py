from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import Any, Dict, List, Optional
from datetime import datetime
from bson import ObjectId

from app.db.mongo import get_db
from app.services.project_service import get_project, list_projects, update_project
from app.services.upload_service import get_upload_by_upload_id
from app.services.user_service import get_user_by_id
from app.api.deps import require_role

router = APIRouter()

# =========================================================
# HELPERS
# =========================================================

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(doc, dict):
        return doc
    out = dict(doc)
    if out.get("_id") is not None:
        out["id"] = str(out["_id"])
        out.pop("_id", None)
    return out


# =========================================================
# USERS LIST (ADMIN ONLY)
# =========================================================
@router.get("/users")
async def list_users(q: Optional[str] = None, current_user=Depends(require_role("admin"))):
    db = get_db()
    query = {}

    if q:
        query = {
            "$or": [
                {"email": {"$regex": q, "$options": "i"}},
                {"full_name": {"$regex": q, "$options": "i"}},
            ]
        }

    cursor = db["users"].find(query).sort("created_at", -1)

    out = []
    async for u in cursor:
        u = _to_str_id(u)
        u.pop("password_hash", None)
        out.append(u)

    return {"success": True, "count": len(out), "users": out}


# =========================================================
# VERIFIERS LIST
# =========================================================
@router.get("/verifiers")
async def list_verifiers(current_user=Depends(require_role("admin"))):
    db = get_db()
    cursor = db["users"].find({"role": "verifier"}).sort("created_at", -1)

    out = []
    async for v in cursor:
        v = _to_str_id(v)
        v.pop("password_hash", None)
        out.append(v)

    return {"success": True, "count": len(out), "verifiers": out}


# =========================================================
# PROJECT LIST (ADMIN + VERIFIER)
# =========================================================
@router.get("/projects")
async def admin_list_projects(
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user=Depends(require_role("admin", "verifier")),
):
    q = {}
    if status:
        q["status"] = status
    if owner_id:
        q["owner.owner_id"] = owner_id

    projects = await list_projects(q, limit=limit, skip=skip)
    cleaned = [_to_str_id(p) for p in projects]

    return {"success": True, "count": len(cleaned), "projects": cleaned}


# =========================================================
# SINGLE PROJECT WITH FULL MRV EXPANSION
# =========================================================
@router.get("/projects/{project_id}")
async def admin_get_project(project_id: str, current_user=Depends(require_role("admin", "verifier"))):

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    proj = _to_str_id(proj)

    # -----------------------------------------------
    # EXPAND MRVs (Dummy MRV + ML MRV)
    # -----------------------------------------------
    mrv_ids = proj.get("mrv_ids", [])
    expanded = []

    if mrv_ids:
        db = get_db()

        for mid in mrv_ids:
            try:
                rec = await db["mrv_records"].find_one({"_id": ObjectId(mid)})
            except:
                rec = await db["mrv_records"].find_one({"_id": mid})

            if not rec:
                continue

            r = _to_str_id(rec)

            # ---------------------------------------------------
            # 1) Dummy MRV
            # ---------------------------------------------------
            if "ndvi" in rec:
                r["ndvi"] = rec.get("ndvi")
                r["ndwi"] = rec.get("ndwi")
                r["canopy_cover"] = rec.get("canopy_cover")
                r["biomass_ton"] = rec.get("biomass_ton")
                r["carbon_stock_tCO2e"] = rec.get("carbon_stock_tCO2e")

            # ---------------------------------------------------
            # 2) ML Model MRV
            # ---------------------------------------------------
            ml = rec.get("ml_result")
            if ml:
                indices = ml.get("indices", {}) or {}
                biomass = ml.get("biomass", {}) or {}

                # normalize MRV fields so frontend always gets consistent names
                r["ndvi"] = rec.get("ndvi") or rec.get("NDVI")
                r["ndwi"] = rec.get("ndwi") or rec.get("NDWI")
                r["canopy_cover"] = rec.get("canopy_cover") or rec.get("canopy")
                r["biomass_ton"] = rec.get("biomass_ton") or rec.get("biomass")
                r["carbon_stock_tCO2e"] = rec.get("carbon_stock_tCO2e") or rec.get("carbon_stock")
                r["timestamp"] = rec.get("timestamp") or rec.get("created_at")
                r["status"] = rec.get("status", "verified")
                r["mrv_hash"] = rec.get("mrv_hash")


            expanded.append(r)

    proj["mrv_details"] = expanded
    return proj


# =========================================================
# VERIFY PROJECT (VERIFIER + ADMIN)
# =========================================================
@router.post("/projects/{project_id}/verify")
async def admin_verify_project(
    project_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_role("verifier", "admin")),
):

    action = payload.get("action", "").lower()
    notes = payload.get("notes", "")

    if action not in ("approve", "reject"):
        raise HTTPException(400, "action must be approve/reject")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    entry = {
        "verifier_id": str(current_user.get("id")),
        "verifier_name": current_user.get("full_name"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat(),
    }

    history = proj.get("verifier_history", [])
    history.append(entry)

    updates = {
        "status": "approved" if action == "approve" else "rejected",
        "verifier_history": history,
        "updated_at": datetime.utcnow(),
    }

    updated = await update_project(project_id, updates)
    return {"success": True, "project": _to_str_id(updated)}


# =========================================================
# ISSUE CREDITS (ADMIN ONLY)
# =========================================================
@router.post("/projects/{project_id}/issue")
async def admin_issue_credits(
    project_id: str,
    payload: dict = Body(...),
    current_user=Depends(require_role("admin")),
):

    action = payload.get("action", "").lower()
    notes = payload.get("notes", "")

    if action not in ("issue", "reject"):
        raise HTTPException(400, "action must be issue/reject")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    new_status = "issued" if action == "issue" else "rejected"

    entry = {
        "admin_id": str(current_user.get("id")),
        "admin_name": current_user.get("full_name"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat(),
    }

    history = proj.get("issuance_history", [])
    history.append(entry)

    updates = {
        "status": new_status,
        "listed": action == "issue",
        "issuance_history": history,
        "updated_at": datetime.utcnow(),
    }

    updated = await update_project(project_id, updates)
    return {"success": True, "project": _to_str_id(updated)}


# =========================================================
# ISSUANCE HISTORY LIST
# =========================================================
@router.get("/issuance-history")
async def issuance_history(current_user=Depends(require_role("admin"))):
    db = get_db()

    recs = await db["projects"].aggregate([
        {"$match": {"issuance_history": {"$exists": True, "$ne": []}}},
        {"$unwind": "$issuance_history"},
        {
            "$project": {
                "project_id": {"$toString": "$_id"},
                "project_title": "$plantation.project_title",
                "admin_name": "$issuance_history.admin_name",
                "notes": "$issuance_history.notes",
                "timestamp": "$issuance_history.timestamp",
            }
        },
        {"$sort": {"timestamp": -1}},
    ]).to_list(200)

    return {"success": True, "history": recs}
