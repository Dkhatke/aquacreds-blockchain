# app/api/v1/projects.py
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request, File, UploadFile, Form, Query
from typing import Any, Dict, List, Optional
from datetime import datetime, date
from bson import ObjectId

from app.db.mongo import get_db
from app.schemas.project_schema import ProjectCreate, ProjectOut
from app.services.project_service import (
    create_project,
    get_project,
    list_projects,
    update_project,
    add_photo_to_project,
)
from app.services.upload_service import get_upload_by_upload_id
from app.api.deps import get_current_user

router = APIRouter()


# ---------------------------
# Utility helpers
# ---------------------------

def _is_objectid(v: Any) -> bool:
    return isinstance(v, ObjectId)


def _to_str_safe(v: Any) -> Any:
    if _is_objectid(v):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def _recursive_convert(obj: Any) -> Any:
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            # drop raw bytes fields (safety)
            if isinstance(v, (bytes, bytearray)):
                continue
            new[k] = _recursive_convert(v)
        return new

    if isinstance(obj, list):
        return [_recursive_convert(x) for x in obj]

    return _to_str_safe(obj)


# ---------------------------
# Cleaners: produce JSON-safe docs
# ---------------------------

def _clean_project_doc(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize and sanitize a raw project document from MongoDB so it matches ProjectOut
    and is safe for JSON encoding.
    Guarantees presence of required fields for ProjectOut.
    """
    if not isinstance(raw, dict):
        return {}

    p = dict(raw)  # shallow copy

    # _id -> id (string)
    if p.get("_id") is not None:
        p["id"] = str(p["_id"])
    else:
        p.setdefault("id", str(ObjectId()))

    # OWNER: ensure dict and string owner_id
    owner = p.get("owner") or {}
    if isinstance(owner, dict) and owner.get("owner_id") is not None:
        owner["owner_id"] = str(owner["owner_id"])
    p["owner"] = owner

    # ORGANIZATION: ensure exists
    organization = p.get("organization")
    if not isinstance(organization, dict):
        organization = {
            "name": owner.get("owner_org") or "Unknown Organization",
            "reg_no": None,
            "year_established": None,
        }
    p["organization"] = organization

    # ORGANIZATION_ID: ensure ALWAYS present and deterministic when missing
    org_id = p.get("organization_id")
    if not org_id:
        # if organization name exists, derive a deterministic 24-char hex string from its hash
        name = (organization.get("name") or "").strip()
        if name:
            h = hashlib.sha256(name.encode("utf-8")).hexdigest()[:24]
            org_id = h
        else:
            org_id = str(ObjectId())
    p["organization_id"] = str(org_id)

    # CONTACT PERSON: default fallback
    contact = p.get("contact_person")
    if not isinstance(contact, dict):
        contact = {
            "full_name": owner.get("owner_name") or "Contact Person",
            "email": owner.get("owner_email") or "no-reply@example.com",
            "mobile_no": "000000",
            "designation": None,
        }
    p["contact_person"] = contact

    # ADDRESS fallback
    address = p.get("address")
    if not isinstance(address, dict):
        address = {"state": "NA", "district": "NA", "full_address": "Not provided", "pincode": "000"}
    p["address"] = address

    # PLANTATION: ensure structure + iso date
    plantation = p.get("plantation")
    if not isinstance(plantation, dict):
        plantation = {
            "project_title": p.get("name") or "Untitled Project",
            "plantation_date": _to_str_safe(p.get("created_at") or datetime.utcnow()),
            "location": p["address"],
            "area_restored_hectares": p.get("area_restored_hectares", 0.0),
            "species": p.get("species", []),
            "number_of_saplings": p.get("number_of_saplings"),
            "seed_source": None,
        }
    else:
        pd = plantation.get("plantation_date")
        if pd is not None:
            if isinstance(pd, (datetime, date)):
                plantation["plantation_date"] = pd.isoformat()
            else:
                plantation["plantation_date"] = str(pd)
        # ensure location exists
        loc = plantation.get("location")
        if not isinstance(loc, dict):
            plantation["location"] = p.get("address") or {}
    p["plantation"] = plantation

    # STATUS & LISTED
    p["status"] = p.get("status", "draft")
    p["listed"] = bool(p.get("listed", False))

    # GEOTAG PHOTOS & VERIFIER HISTORY (clean recursively)
    p["geotag_photos"] = _recursive_convert(p.get("geotag_photos") or [])
    p["verifier_history"] = _recursive_convert(p.get("verifier_history") or [])

    # ensure mrv_ids is a list of strings
    mrv_ids = p.get("mrv_ids") or []
    if isinstance(mrv_ids, list):
        p["mrv_ids"] = [str(x) for x in mrv_ids if x is not None]
    else:
        p["mrv_ids"] = [str(mrv_ids)]

    # issuance_history safe
    p["issuance_history"] = _recursive_convert(p.get("issuance_history") or [])

    # sanitize top-level timestamps
    for t in ("created_at", "updated_at", "verified_at"):
        if t in p and p[t] is not None:
            if isinstance(p[t], (datetime, date)):
                p[t] = p[t].isoformat()
            else:
                p[t] = str(p[t])

    # drop binary payloads accidentally included
    for banned in ("file_bytes", "raw", "blob", "data"):
        if banned in p:
            p.pop(banned, None)

    # final recursive conversion (ObjectId -> str etc.)
    return _recursive_convert(p)


def _clean_mrv_doc(raw: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    m = dict(raw)
    if m.get("_id") is not None:
        m["id"] = str(m["_id"])
    # created_at normalization
    if m.get("created_at") is not None:
        if isinstance(m["created_at"], (datetime, date)):
            m["created_at"] = m["created_at"].isoformat()
        else:
            m["created_at"] = str(m["created_at"])
    # ml_result nested clean
    m["ml_result"] = _recursive_convert(m.get("ml_result") or {})
    # ensure carbon number is simple float if possible
    if "carbon_stock_tCO2e" in m:
        try:
            m["carbon_stock_tCO2e"] = float(m["carbon_stock_tCO2e"])
        except Exception:
            pass
    # drop binary if present
    for banned in ("file_bytes", "raw", "blob", "data"):
        if banned in m:
            m.pop(banned, None)
    return _recursive_convert(m)


# ---------------------------
# RESPONSE BUILDER
# ---------------------------

def _build_project_response_shape(raw: Dict[str, Any]) -> Dict[str, Any]:
    return _clean_project_doc(raw)


# ---------------------------
# ENDPOINTS
# ---------------------------

@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project_endpoint(payload: ProjectCreate, current_user=Depends(get_current_user)):
    if current_user.get("role") != "user":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only users can create projects")

    db = get_db()

    # ---------------------------
    # 1. Create the normal project as before
    # ---------------------------
    proj_doc = payload.model_dump()
    proj_doc["owner"] = {
        "owner_id": str(current_user["id"]),
        "owner_name": current_user.get("full_name"),
        "owner_email": current_user.get("email"),
        "owner_org": current_user.get("organization"),
    }
    proj_doc.setdefault("status", "draft")
    proj_doc.setdefault("listed", False)
    proj_doc.setdefault("mrv_ids", [])

    new_proj = await create_project(proj_doc)
    if not new_proj:
        raise HTTPException(status_code=500, detail="Failed to create project")

    project_id = str(new_proj["_id"])

    # ---------------------------
    # 2. Create NGO wallet if missing
    # ---------------------------
    # Find user by email (safer cross-runtime)
    user = await db["users"].find_one({"email": current_user.get("email")})

    # Wallet creation/import is done via blockchain.wallet_manager
    try:
        from blockchain.wallet_manager import WalletManager
    except Exception:
        WalletManager = None

    if user is None:
        # shouldn't happen — guard
        ngo_wallet = None
        ngo_private = None
    else:
        if "wallet_address" not in user or not user.get("wallet_address"):
            if WalletManager is not None:
                wallet = WalletManager.create_wallet()
                await db["users"].update_one(
                    {"_id": user["_id"]},
                    {"$set": {
                        "wallet_address": wallet["address"],
                        "wallet_private_key": wallet["private_key"]
                    }}
                )
                ngo_wallet = wallet["address"]
                ngo_private = wallet["private_key"]
            else:
                ngo_wallet = None
                ngo_private = None
        else:
            ngo_wallet = user.get("wallet_address")
            ngo_private = user.get("wallet_private_key")

    # ---------------------------
    # 3. Create SHA256 plantation hash
    # ---------------------------
    plantation_json = json.dumps(proj_doc, default=str)
    plantation_hash = hashlib.sha256(plantation_json.encode()).hexdigest()

    # ---------------------------
    # 4. Register project on blockchain (best-effort; failures do not block creation)
    # ---------------------------
    try:
        from blockchain.contract_loader import load_contract
        from blockchain.transaction_service import TxService

        if ngo_private and ngo_wallet:
            registry = load_contract("ProjectRegistry")
            receipt = TxService.send_user_tx(
                registry.functions.registerProject(project_id, plantation_hash),
                ngo_private,
                ngo_wallet
            )
            tx_hash = receipt.transactionHash.hex()
            # Store blockchain tx in DB
            await db["projects"].update_one(
                {"_id": new_proj["_id"]},
                {"$set": {
                    "plantation_hash": plantation_hash,
                    "blockchain_tx": tx_hash
                }}
            )
        else:
            # Save plantation_hash at least in DB so we keep local proof
            await db["projects"].update_one(
                {"_id": new_proj["_id"]},
                {"$set": {
                    "plantation_hash": plantation_hash
                }}
            )
    except Exception as e:
        # Log but don't raise — keep the project creation resilient.
        print("Blockchain registration failed:", e)
        # still attempt to save plantation_hash locally
        try:
            await db["projects"].update_one(
                {"_id": new_proj["_id"]},
                {"$set": {
                    "plantation_hash": plantation_hash
                }}
            )
        except Exception:
            pass

    # ---------------------------
    # OPTIONAL: Attach dummy MRV (existing logic)
    # ---------------------------
    try:
        dummy = await db["mrv_records"].find_one({"is_dummy": True})
        if dummy:
            dummy_id_str = str(dummy["_id"])
            await db["projects"].update_one(
                {"_id": new_proj["_id"]},
                {"$addToSet": {"mrv_ids": dummy_id_str}}
            )
            new_proj = await db["projects"].find_one({"_id": new_proj["_id"]})
    except Exception:
        pass

    return _build_project_response_shape(new_proj)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project_endpoint(project_id: str, current_user=Depends(get_current_user)):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return _build_project_response_shape(proj)


@router.get("/projects", response_model=List[ProjectOut])
async def list_projects_endpoint(
    projectid: str | None = Query(None),
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    limit: int = 50,
    skip: int = 0,
):
    q: Dict[str, Any] = {}

    if projectid:
        try:
            q = {"_id": ObjectId(projectid)}
        except Exception:
            q = {"id": projectid}
    else:
        if status:
            q["status"] = status
        if owner_id:
            q["owner.owner_id"] = owner_id

    projects = await list_projects(q, limit=limit, skip=skip)
    return [_build_project_response_shape(p) for p in projects]


@router.get("/projects/actions/submitted-with-mrv")
async def list_submitted_projects_with_mrvs(
    status: str | None = "submitted",
    limit: int = 100,
    skip: int = 0,
    current_user=Depends(get_current_user),
):
    """
    Verifier/admin-only endpoint returning projects with the given status
    and embedding full MRV documents (mrv_records) for each project's mrv_ids.
    """
    role = current_user.get("role")
    if role not in ("verifier", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only verifiers/admins allowed")

    db = get_db()
    q = {"status": status} if status else {}
    cursor = db["projects"].find(q).skip(skip).limit(limit)

    projects_raw = []
    all_mrv_hexes = []

    async for p in cursor:
        # ensure id string
        p["id"] = str(p.get("_id") or p.get("id") or ObjectId())
        raw = p.get("mrv_ids") or []
        if isinstance(raw, list):
            hexes = [str(x) for x in raw if x]
        else:
            hexes = [str(raw)]
        p["_mrv_hexes"] = hexes
        all_mrv_hexes.extend([h for h in hexes if h])
        projects_raw.append(p)

    # Batch fetch MRV docs
    mrv_map: Dict[str, Dict[str, Any]] = {}
    if all_mrv_hexes:
        obj_ids = []
        string_ids = []
        for h in set(all_mrv_hexes):
            try:
                obj_ids.append(ObjectId(h))
            except Exception:
                string_ids.append(h)

        queries = []
        if obj_ids:
            queries.append({"_id": {"$in": obj_ids}})
        if string_ids:
            queries.append({"$or": [{"_id": {"$in": string_ids}}, {"id": {"$in": string_ids}}, {"mrv_hash": {"$in": string_ids}}, {"upload_id": {"$in": string_ids}}]})

        if queries:
            q_final = {"$or": queries} if len(queries) > 1 else queries[0]
            async for m in db["mrv_records"].find(q_final):
                key = str(m.get("_id"))
                mrv_map[key] = _clean_mrv_doc(m)
                if m.get("mrv_hash"):
                    mrv_map[str(m["mrv_hash"])] = _clean_mrv_doc(m)
                if m.get("upload_id"):
                    mrv_map[str(m["upload_id"])] = _clean_mrv_doc(m)

    # Attach MRV docs to each project and clean project
    final_projects: List[Dict[str, Any]] = []
    for p in projects_raw:
        hexes = p.pop("_mrv_hexes", [])
        p["mrv_details"] = [mrv_map.get(h) for h in hexes if mrv_map.get(h)]
        p_clean = _clean_project_doc(p)
        final_projects.append(p_clean)

    return {"count": len(final_projects), "projects": final_projects}


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project_endpoint(project_id: str, updates: dict = Body(...), current_user=Depends(get_current_user)):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user["role"] != "admin" and str(proj["owner"]["owner_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Not allowed")

    updated = await update_project(project_id, updates)
    if not updated:
        raise HTTPException(status_code=500, detail="Update failed")

    return _build_project_response_shape(updated)


@router.post("/projects/{project_id}/add-photo", response_model=ProjectOut)
async def add_photo_endpoint(
    project_id: str,
    request: Request,
    file: UploadFile | None = File(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    timestamp: str | None = Form(None),
    filename: str | None = Form(None),
    current_user=Depends(get_current_user),
):
    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user["role"] != "admin" and str(proj["owner"]["owner_id"]) != str(current_user["id"]):
        raise HTTPException(status_code=403, detail="Not allowed")

    content_type = request.headers.get("content-type", "")
    is_json = "application/json" in content_type.lower()

    upload_doc: Optional[Dict[str, Any]] = None

    if is_json:
        payload = await request.json()
        upload_id = payload.get("upload_id")
        if not upload_id:
            raise HTTPException(status_code=400, detail="upload_id is required")
        upload_doc = await get_upload_by_upload_id(upload_id)
        if not upload_doc:
            raise HTTPException(status_code=404, detail="Upload not found")
    else:
        if file is None:
            form = await request.form()
            file = form.get("file")
            latitude = latitude or form.get("latitude")
            longitude = longitude or form.get("longitude")
            timestamp = timestamp or form.get("timestamp")
            filename = filename or form.get("filename")

        if file is None:
            raise HTTPException(status_code=400, detail="file is required")

        try:
            file_bytes = await file.read()
        except Exception:
            raise HTTPException(status_code=400, detail="Failed to read uploaded file")

        upload_doc = {
            "file_bytes": file_bytes,
            "filename": filename or file.filename,
            "original_filename": file.filename,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "timestamp": timestamp,
            "size_bytes": len(file_bytes),
        }

    updated_proj = await add_photo_to_project(project_id, upload_doc, current_user)
    if not updated_proj:
        raise HTTPException(status_code=500, detail="Failed to attach photo")

    return _build_project_response_shape(updated_proj)


@router.post("/projects/{project_id}/verify", response_model=ProjectOut)
async def verify_project_endpoint(
    project_id: str,
    payload: dict = Body(...),
    current_user=Depends(get_current_user),
):
    action = (payload.get("action") or "").lower()
    notes = payload.get("notes") or ""

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve or reject")

    if current_user["role"] not in ("verifier", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    new_status = "approved" if action == "approve" else "rejected"

    entry = {
        "verifier_id": str(current_user["id"]),
        "verifier_name": current_user.get("full_name") or current_user.get("email"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    history = proj.get("verifier_history") or []
    history.append(entry)

    updates = {
        "status": new_status,
        "verifier_history": history,
        "updated_at": datetime.utcnow(),
    }

    updated = await update_project(project_id, updates)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update")

    return _build_project_response_shape(updated)


@router.post("/projects/{project_id}/issue", response_model=ProjectOut)
async def issue_credits_endpoint(
    project_id: str,
    payload: dict = Body(...),  # {"action": "issue" | "reject", "notes": "optional"}
    current_user=Depends(get_current_user),
):
    """
    Admin-only: mark credits as issued or rejected for a project.
    - action: "issue" -> status="issued", listed=True
              "reject" -> status="rejected", listed=False
    - notes: optional explanatory text
    Adds an `issuance_history` entry (admin id/name/action/notes/timestamp).
    Returns the updated project.
    """
    action = (payload.get("action") or "").strip().lower()
    notes = payload.get("notes") or ""

    if action not in ("issue", "reject"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="action must be 'issue' or 'reject'")

    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can issue credits")

    proj = await get_project(project_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    new_status = "issued" if action == "issue" else "rejected"
    new_listed = True if action == "issue" else False

    issuance_entry = {
        "admin_id": str(current_user.get("id")),
        "admin_name": current_user.get("full_name") or current_user.get("email"),
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    existing = proj.get("issuance_history") or []
    if not isinstance(existing, list):
        existing = []
    existing.append(issuance_entry)

    updates = {
        "status": new_status,
        "listed": new_listed,
        "issuance_history": existing,
        "updated_at": datetime.utcnow(),
    }

    updated = await update_project(project_id, updates)
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update project")

    return _build_project_response_shape(updated)
