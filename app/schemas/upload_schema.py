from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class EXIFData(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None

class UploadResponse(BaseModel):
    upload_id: str = Field(..., description="MongoDB _id as string")
    filename: str
    size: int
    sha256: str
    ipfs_hash: Optional[str] = None
    exif: Optional[EXIFData] = None
class UploadCreate(BaseModel):
    uploader_id: str
    project_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None