# app/api/v1/projects.py
import hashlib
import json
import os
from fastapi import (
    APIRouter, Depends, HTTPException, status, Body,
    Request, File, UploadFile, Form, Query
)
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from bson import ObjectId

from app.db.mongo import get_db
from app.schemas.project_schema import ProjectCreate, ProjectOut
from app.services.project_service import (
    create_project, get_project, list_projects, update_project, add_photo_to_project
)
from app.services.upload_service import get_upload_by_upload_id
from app.api.deps import get_current_user
# add imports at top of file if not present
import os
from web3 import Web3
from fastapi import BackgroundTasks

from blockchain.contract_loader import load_contract
from blockchain.transaction_service import TxService
from app.services.blockchain_tx_service import save_tx  # ensure exists
from app.db.mongo import get_db

ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ADMIN_ADDRESS = os.getenv("ADMIN_ADDRESS")  # store checksum later

def _checksum(addr: str) -> str | None:
    try:
        return Web3.to_checksum_address(addr)
    except Exception:
        return None

def calculate_credits(mrv, plantation):
    try:
        area = float(plantation.get("area_restored_hectares", 1)) or 1
    except:
        area = 1

    # 1 — Dummy MRV carbon stock
    if mrv.get("carbon_stock_tCO2e"):
        return max(1, round(float(mrv["carbon_stock_tCO2e"]) * area))

    # 2 — ML MRV carbon stock
    ml = mrv.get("ml_result", {})
    biomass = ml.get("biomass", {})
    if biomass.get("CO2eq_t_per_ha"):
        return max(1, round(float(biomass["CO2eq_t_per_ha"]) * area))

    # 3 — Last fallback: saplings
    saplings = plantation.get("number_of_saplings", 0)
    return max(1, round(int(saplings) / 10))

router = APIRouter()

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------
def _safe_id(v): return str(v) if isinstance(v, ObjectId) else v

def _clean_ts(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v

def _clean(obj):
    """ Recursively convert ObjectId → str, datetime → iso, remove bytes """
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if isinstance(v, (bytes, bytearray)):
                continue
            new[k] = _clean(v)
        return new
    if isinstance(obj, list):
        return [_clean(x) for x in obj]
    return _clean_ts(_safe_id(obj))


# -------------------------------------------------------------
# STEP 1 — CREATE PROJECT DRAFT
# -------------------------------------------------------------
@router.post("/projects/create-step1")
async def create_step1(payload: dict = Body(...), current_user=Depends(get_current_user)):
    """
    Accepts only basic organization + contact + address (NO plantation)
    """
    db = get_db()

    doc = {
        "organization": payload.get("organization"),
        "contact_person": payload.get("contact_person"),
        "address": payload.get("address"),
        "owner": {
            "owner_id": str(current_user["id"]),
            "owner_name": current_user.get("full_name"),
            "owner_email": current_user.get("email"),
        },
        "status": "draft",
        "listed": False,
        "mrv_ids": [],
        "created_at": datetime.utcnow(),
    }

    res = await db["projects"].insert_one(doc)
    return {"success": True, "id": str(res.inserted_id)}


# -------------------------------------------------------------
# STEP 2 — ADD PLANTATION DETAILS
# -------------------------------------------------------------
@router.put("/projects/{project_id}/step2-plantation")
async def update_step2(project_id: str, payload: dict = Body(...), current_user=Depends(get_current_user)):
    db = get_db()
    proj = await get_project(project_id)

    if not proj:
        raise HTTPException(404, "Project not found")

    if str(proj["owner"]["owner_id"]) != str(current_user["id"]):
        raise HTTPException(403, "Not allowed")

    updates = {
        "plantation": payload.get("plantation"),
        "updated_at": datetime.utcnow(),
    }

    updated = await update_project(project_id, updates)
    return _clean(updated)


# -------------------------------------------------------------
# STEP 3 — FINAL SUBMISSION
# -------------------------------------------------------------
@router.put("/projects/{project_id}/submit")
async def submit_project(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()

    proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(404, "Project not found")

    # Only owner can submit
    if str(proj["owner"]["owner_id"]) != str(current_user["id"]):
        raise HTTPException(403, "Not allowed")

    # 🔵 AUTO GENERATE MRV IF NONE EXISTS
    existing_mrvs = proj.get("mrv_ids", [])
    if not existing_mrvs:

        dummy_mrv = {
            "project_id": project_id,
            "ndvi": round(random.uniform(0.45, 0.85), 3),
            "ndwi": round(random.uniform(0.10, 0.45), 3),
            "canopy_cover": random.randint(40, 90),
            "biomass_ton": round(random.uniform(12, 60), 2),
            "carbon_stock_tCO2e": round(random.uniform(20, 120), 2),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "verified"
        }

        # Generate MRV hash
        mrv_hash = hashlib.sha256(str(dummy_mrv).encode()).hexdigest()
        dummy_mrv["mrv_hash"] = mrv_hash

        # Save MRV
        saved = await db["mrv_records"].insert_one(dummy_mrv)
        mrv_id = str(saved.inserted_id)

        # Attach to project
        await db["projects"].update_one(
            {"_id": ObjectId(project_id)},
            {"$addToSet": {"mrv_ids": mrv_id}}
        )

    # 🔵 Update project status → submitted
    await db["projects"].update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"status": "submitted"}}
    )

    return {"success": True, "message": "Project submitted successfully"}

# -------------------------------------------------------------
# GET PROJECT BY ID
# -------------------------------------------------------------
@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project_endpoint(project_id: str, current_user=Depends(get_current_user)):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")
    return _clean(proj)


# -------------------------------------------------------------
# USER LIST OWN PROJECTS
# -------------------------------------------------------------
@router.get("/projects")
async def list_user_projects(
    owner_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    db = get_db()
    q = {}

    if owner_id:
        q["owner.owner_id"] = owner_id

    cursor = db["projects"].find(q).sort("created_at", -1)

    out = []
    async for p in cursor:
        p["id"] = str(p["_id"])
        out.append(_clean(p))

    return out


# -------------------------------------------------------------
# ADMIN & VERIFIER: LIST PROJECTS
# -------------------------------------------------------------
@router.get("/projects/admin-list")
async def admin_list(
    status: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    if current_user["role"] not in ("admin", "verifier"):
        raise HTTPException(403, "Not allowed")

    db = get_db()
    q = {}
    if status:
        q["status"] = status

    cursor = db["projects"].find(q)

    out = []
    async for p in cursor:
        p["id"] = str(p["_id"])
        out.append(_clean(p))

    return {"success": True, "projects": out}


# -------------------------------------------------------------
# ADD PHOTO (GEOTAG)
# -------------------------------------------------------------
@router.post("/projects/{project_id}/add-photo")
async def add_photo(
    project_id: str,
    request: Request,
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    timestamp: str = Form(...),
    current_user=Depends(get_current_user),
):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    if str(proj["owner"]["owner_id"]) != str(current_user["id"]):
        raise HTTPException(403, "Not allowed")

    file_bytes = await file.read()

    upload_doc = {
        "file_bytes": file_bytes,
        "filename": file.filename,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
    }

    updated = await add_photo_to_project(project_id, upload_doc, current_user)
    return _clean(updated)


# -------------------------------------------------------------
# GENERATE MRV (dummy)
# -------------------------------------------------------------
import random
def sha256(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

@router.post("/projects/{project_id}/generate-mrv")
async def generate_mrv(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()

    if current_user["role"] not in ("user", "verifier", "admin"):
        raise HTTPException(403, "Not allowed")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    # dummy metrics
    metrics = {
        "ndvi": round(random.uniform(0.3, 0.9), 3),
        "ndwi": round(random.uniform(0.1, 0.7), 3),
        "canopy_cover": random.randint(40, 95),
        "biomass_ton": round(random.uniform(5, 60), 2),
        "carbon_stock_tCO2e": round(random.uniform(10, 120), 2),
    }

    mrv_record = {
        "project_id": project_id,
        "metrics": metrics,
        "timestamp": datetime.utcnow().isoformat(),
    }

    mrv_hash = sha256(mrv_record)
    mrv_record["mrv_hash"] = mrv_hash

    res = await db["mrv_records"].insert_one(mrv_record)
    mrv_id = str(res.inserted_id)

    await db["projects"].update_one(
        {"_id": ObjectId(project_id)},
        {"$addToSet": {"mrv_ids": mrv_id}}
    )

    return {"success": True, "mrv_id": mrv_id, "mrv_hash": mrv_hash, "metrics": metrics}


# -------------------------------------------------------------
# VERIFIER/Admin APPROVE/REJECT
# -------------------------------------------------------------
@router.post("/projects/{project_id}/verify")
async def verify_project(project_id: str, payload: dict = Body(...), current_user=Depends(get_current_user)):
    action = payload.get("action")
    notes = payload.get("notes", "")

    if current_user["role"] not in ("verifier", "admin"):
        raise HTTPException(403, "Not allowed")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Project not found")

    new_status = "approved" if action == "approve" else "rejected"

    entry = {
        "verifier_id": str(current_user["id"]),
        "verifier_name": current_user.get("full_name"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat(),
    }

    history = proj.get("verifier_history") or []
    history.append(entry)

    updated = await update_project(project_id, {
        "status": new_status,
        "verifier_history": history,
        "updated_at": datetime.utcnow(),
    })

    return _clean(updated)


# -------------------------------------------------------------
# ADMIN ISSUE CREDITS
# -------------------------------------------------------------
@router.post("/projects/{project_id}/issue")
async def issue_credits(project_id: str, payload: dict = Body(...), current_user=Depends(get_current_user)):

    if current_user["role"] != "admin":
        raise HTTPException(403, "Admins only")

    action = payload.get("action")
    notes = payload.get("notes", "")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(404, "Not found")

    new_status = "issued" if action == "issue" else "rejected"

    entry = {
        "admin_id": str(current_user["id"]),
        "admin_name": current_user.get("full_name"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat(),
    }

    history = proj.get("issuance_history") or []
    history.append(entry)

    updated = await update_project(project_id, {
        "status": new_status,
        "issuance_history": history,
        "listed": (action == "issue"),
        "updated_at": datetime.utcnow(),
    })

    return _clean(updated)

@router.post("/projects/{project_id}/attach-upload", summary="Geotag upload disabled")
async def user_attach_geotag(project_id: str, payload: dict = Body(...), current_user=Depends(get_current_user)):
    """
    Geotag uploads are disabled.
    Frontend can still call this, but it will not save anything.
    """
    return {
        "success": True,
        "message": "Geotag skipped — upload not required",
        "project_id": project_id
    }

# blockchain
@router.post("/projects/{project_id}/register")
async def register_project_onchain(project_id: str, current_user=Depends(get_current_user)):
    """
    Compute plantation hash if missing and call registerProject(projectId, plantationHash).
    Admin/private-key owner will send tx (ADMIN_PRIVATE_KEY).
    """
    db = get_db()
    proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # compute plantation hash deterministically (you can reuse your schema helper)
    # e.g. use json.dumps on plantation fields
    import json, hashlib
    plantation = proj.get("plantation") or {}
    plantation_json = json.dumps(plantation, sort_keys=True, default=str, separators=(",", ":"), ensure_ascii=False)
    plantation_hash = hashlib.sha256(plantation_json.encode("utf-8")).hexdigest()

    # if already registered, return existing tx
    if proj.get("register_tx"):
        return {"success": True, "message": "Already registered", "tx_hash": proj.get("register_tx")}

    tx_hash = None
    try:
        contract = load_contract("ProjectRegistry")
        admin_addr = _checksum(ADMIN_ADDRESS)
        if not (ADMIN_PRIVATE_KEY and admin_addr):
            raise Exception("Blockchain admin credentials not configured")

        # synchronous send (TxService should return receipt)
        receipt = TxService.send_user_tx(
            contract.functions.registerProject(project_id, plantation_hash),
            ADMIN_PRIVATE_KEY,
            admin_addr
        )
        # if TxService returns web3 receipt object:
        tx_hash = getattr(receipt, "transactionHash", None)
        if tx_hash:
            tx_hash = tx_hash.hex()
        else:
            # maybe it's dict
            tx_hash = receipt.get("transactionHash").hex() if isinstance(receipt, dict) and receipt.get("transactionHash") else str(receipt)

        await db["projects"].update_one({"_id": ObjectId(project_id)}, {"$set": {"plantation_hash": plantation_hash, "register_tx": tx_hash}})
        await save_tx(project_id, "register_project", tx_hash)

    except Exception as e:
        # save failed log for retry; don't block caller
        err_msg = str(e)
        await db["blockchain_logs"].insert_one({
            "project_id": project_id,
            "operation": "register_project",
            "status": "error",
            "error": err_msg,
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"success": False, "detail": "Blockchain register failed", "error": err_msg}

    return {"success": True, "plantation_hash": plantation_hash, "tx_hash": tx_hash}

@router.post("/projects/{project_id}/submit-mrv")
async def submit_mrv_onchain(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()
    proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # project should contain mrv_ids / mrv_hash - pick latest
    mrv_ids = proj.get("mrv_ids", [])
    if not mrv_ids:
        raise HTTPException(status_code=400, detail="No MRV found for project")

    latest_mrv_id = mrv_ids[-1] if isinstance(mrv_ids, list) else mrv_ids
    # fetch MRV doc
    mrv_doc = await db["mrv_records"].find_one({"_id": ObjectId(latest_mrv_id)}) if ObjectId.is_valid(latest_mrv_id) else await db["mrv_records"].find_one({"_id": latest_mrv_id})
    if not mrv_doc:
        raise HTTPException(status_code=404, detail="MRV not found")

    mrv_hash = mrv_doc.get("mrv_hash")
    if not mrv_hash:
        raise HTTPException(status_code=400, detail="MRV missing hash")

    # idempotency: if already submitted
    if proj.get("mrv_submit_tx"):
        return {"success": True, "message": "MRV already submitted", "tx_hash": proj.get("mrv_submit_tx")}

    try:
        contract = load_contract("ProjectRegistry")
        admin_addr = _checksum(ADMIN_ADDRESS)
        if not (ADMIN_PRIVATE_KEY and admin_addr):
            raise Exception("Blockchain admin credentials not configured")

        receipt = TxService.send_user_tx(
            contract.functions.submitMRV(project_id, mrv_hash),
            ADMIN_PRIVATE_KEY,
            admin_addr
        )
        tx_hash = getattr(receipt, "transactionHash", None)
        if tx_hash:
            tx_hash = tx_hash.hex()
        else:
            tx_hash = receipt.get("transactionHash").hex() if isinstance(receipt, dict) and receipt.get("transactionHash") else str(receipt)

        await db["projects"].update_one({"_id": ObjectId(project_id)}, {"$set": {"mrv_submit_tx": tx_hash, "mrv_status": "submitted"}})
        await save_tx(project_id, "submit_mrv", tx_hash)

    except Exception as e:
        await db["blockchain_logs"].insert_one({
            "project_id": project_id,
            "operation": "submit_mrv",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })
        return {"success": False, "detail": "Blockchain MRV submit failed", "error": str(e)}

    return {"success": True, "tx_hash": tx_hash}


# -----------------------------
#   SUBMIT MRV TO BLOCKCHAIN
# -----------------------------
@router.post("/projects/{project_id}/submit-mrv")
async def submit_mrv_onchain(project_id: str, current_user=Depends(get_current_user)):
    db = get_db()

    # Fetch project
    proj = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Expect MRV saved in project.mrv_details[]
    mrv_list = proj.get("mrv_details", [])
    if not mrv_list:
        raise HTTPException(status_code=400, detail="No MRV found for project")

    latest_mrv = mrv_list[-1]
    mrv_hash = latest_mrv.get("mrv_hash")
    if not mrv_hash:
        raise HTTPException(status_code=400, detail="MRV missing hash")

    # Idempotency
    if proj.get("mrv_submit_tx"):
        return {
            "success": True,
            "message": "MRV already submitted",
            "tx_hash": proj["mrv_submit_tx"]
        }

    try:
        contract = load_contract("ProjectRegistry")

        receipt = TxService.send_user_tx(
            contract.functions.submitMRV(project_id, mrv_hash),
            ADMIN_PRIVATE_KEY,
            _checksum(ADMIN_ADDRESS)
        )

        # Extract hash safely
        tx_hash = None
        if hasattr(receipt, "transactionHash"):
            tx_hash = receipt.transactionHash.hex()
        elif isinstance(receipt, dict) and receipt.get("transactionHash"):
            tx_hash = receipt["transactionHash"].hex()
        else:
            tx_hash = str(receipt)

        # Save in DB
        await db["projects"].update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "mrv_submit_tx": tx_hash,
                    "mrv_status": "submitted"
                }
            }
        )

        await save_tx(project_id, "submit_mrv", tx_hash)

        return {"success": True, "tx_hash": tx_hash}

    except Exception as e:
        await db["blockchain_logs"].insert_one({
            "project_id": project_id,
            "operation": "submit_mrv",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        })

        return {
            "success": False,
            "detail": "Blockchain MRV submit failed",
            "error": str(e)
        }


@router.post("/projects/{project_id}/mint-credits")
async def mint_credits(project_id: str, payload: dict = Body(...), current_user=Depends(get_current_user)):

    from datetime import datetime
    import hashlib
    db = get_db()

    # Only admin allowed
    if current_user.get("role") != "admin":
        raise HTTPException(403, "Admins only")

    amount = payload.get("amount")
    ngo_address = payload.get("ngo_address")

    if not amount or amount <= 0:
        raise HTTPException(400, "Amount missing")

    if not ngo_address:
        raise HTTPException(400, "NGO address missing")

    project = await db["projects"].find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(404, "Project not found")

    # DEMO FIX: auto-submit MRV if missing
    if not project.get("mrv_submit_tx"):
        fake_submit_hash = hashlib.sha256(
            f"submit-{project_id}".encode()
        ).hexdigest()

        await db["projects"].update_one(
            {"_id": ObjectId(project_id)},
            {
                "$set": {
                    "mrv_submit_tx": fake_submit_hash,
                    "mrv_status": "submitted"
                }
            }
        )

    # DEMO mint hash
    fake_mint_hash = hashlib.sha256(
        f"mint-{project_id}-{datetime.utcnow()}".encode()
    ).hexdigest()

    # Save mint record
    await db["projects"].update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "mint_tx": fake_mint_hash,
                "credits_issued": amount,
                "status": "issued",
                "mint_timestamp": datetime.utcnow().isoformat()
            }
        }
    )

    return {
        "success": True,
        "message": "Credits minted successfully (DEMO MODE)",
        "tx_hash": fake_mint_hash,
        "credits": amount
    }

@router.get("/blockchain/status")
async def blockchain_status(current_user=Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "verifier"):
        raise HTTPException(status_code=403, detail="Not allowed")
    db = get_db()
    recs = await db["blockchain_logs"].find({}).sort("timestamp", -1).to_list(200)
    for r in recs:
        r["id"] = str(r["_id"])
    return {"records": recs}

@router.post("/blockchain/retry")
async def blockchain_retry(payload: dict = Body(...), current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Only admin allowed")

    project_id = payload.get("project_id")
    operation = payload.get("operation")
    if not project_id or not operation:
        raise HTTPException(status_code=400, detail="project_id and operation required")

    if operation == "register_project":
        return await register_project_onchain(project_id, current_user)

    if operation == "submit_mrv":
        return await submit_mrv_onchain(project_id, current_user)

    if operation == "mint_credits":
        return await mint_credits(project_id, payload, current_user)


    raise HTTPException(status_code=400, detail="Unknown operation")
