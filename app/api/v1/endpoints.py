# app/api/v1/endpoints.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.utils.hashing import sha256_bytes
from app.utils.exif_utils import extract_exif
from app.services.storage_service import save_file_local, upload_to_ipfs_stub
from app.db.mongo import get_db
from bson import ObjectId
from app.schemas.upload_schema import UploadResponse, EXIFData
import datetime

router = APIRouter()

@router.post("/upload/photo", response_model=UploadResponse)
async def upload_photo(file: UploadFile = File(...)):
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")

    # 1) save local
    saved_path = save_file_local(file.filename, contents)

    # 2) compute sha256
    sha = sha256_bytes(contents)

    # 3) extract exif
    exif = extract_exif(saved_path)
    exif_payload = {}
    if exif.get("latitude") is not None and exif.get("longitude") is not None:
        exif_payload["latitude"] = exif["latitude"]
        exif_payload["longitude"] = exif["longitude"]
    if exif.get("timestamp") is not None:
        exif_payload["timestamp"] = exif["timestamp"]

    # 4) upload to IPFS (stub) - non-blocking in real system
    ipfs_hash = upload_to_ipfs_stub(saved_path)

    # 5) store record in MongoDB
    db = get_db()
    record = {
        "filename": file.filename,
        "saved_path": saved_path,
        "sha256": sha,
        "ipfs_hash": ipfs_hash,
        "size": len(contents),
        "exif": exif_payload,
        "created_at": datetime.datetime.utcnow(),
        "status": "uploaded"  # later: processed, validated, approved
    }
    res = await db["field_uploads"].insert_one(record)
    upload_id = str(res.inserted_id)

    # Prepare response
    exif_obj = None
    if exif_payload:
        exif_obj = EXIFData(
            latitude=exif_payload.get("latitude"),
            longitude=exif_payload.get("longitude"),
            timestamp=exif_payload.get("timestamp"),
        )
    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        size=len(contents),
        sha256=sha,
        ipfs_hash=ipfs_hash,
        exif=exif_obj,
    )

@router.get("/health")
async def health():
    return {"status": "ok", "component": "api_v1"}
