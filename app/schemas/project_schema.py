# app/schemas/project_schema.py
import hashlib
import json
from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional, List
from datetime import datetime

# Submodels for clearer structure

class Address(BaseModel):
    state: str = Field(..., min_length=2)
    district: str = Field(..., min_length=2)
    full_address: str = Field(..., min_length=5)
    pincode: str = Field(..., min_length=3)

class ContactPerson(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    mobile_no: str = Field(..., min_length=6)
    designation: Optional[str] = None

class OrganizationDetails(BaseModel):
    name: str = Field(..., min_length=2)
    reg_no: Optional[str] = None
    year_established: Optional[int] = None

class PlantationDetails(BaseModel):
    project_title: str = Field(..., min_length=2)
    plantation_date: datetime
    location: "Address"  # forward ref (Address is declared earlier)
    area_restored_hectares: float = Field(..., ge=0)
    species: Optional[List[str]] = None
    number_of_saplings: Optional[int] = Field(None, ge=0)
    seed_source: Optional[str] = None

    # computed field (stored on model instance); included in model_dump()
    plantation_hash: Optional[str] = None

    @model_validator(mode="after")
    def compute_hash(self) -> "PlantationDetails":
        """
        Compute a deterministic SHA256 hex digest from the canonical
        representation of the plantation-relevant fields.
        """
        # Build canonical object
        canonical = {
            "project_title": self.project_title or "",
            # ISO format ensures deterministic string for datetimes
            "plantation_date": self.plantation_date.isoformat() if isinstance(self.plantation_date, datetime) else str(self.plantation_date),
            # location must be Address model; convert to plain dict (assumes Address.model_dump exists)
            "location": (
                self.location.model_dump()
                if hasattr(self.location, "model_dump")
                else dict(self.location)
            ),
            "area_restored_hectares": float(self.area_restored_hectares) if self.area_restored_hectares is not None else 0.0,
            # sort species list for deterministic order
            "species": sorted(self.species) if self.species else [],
            "number_of_saplings": int(self.number_of_saplings) if self.number_of_saplings is not None else None,
            "seed_source": self.seed_source or "",
        }

        # canonicalize using JSON with sorted keys
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

        h = hashlib.sha256()
        h.update(canonical_json.encode("utf-8"))
        self.plantation_hash = h.hexdigest()
        return self

# Resolve forward refs so 'location: "Address"' works
PlantationDetails.model_rebuild()  # pydantic v2 helper to refresh model (safe to call)

# Main create schema used by the endpoint
class ProjectCreate(BaseModel):
    organization: OrganizationDetails
    contact_person: ContactPerson
    address: Address
    plantation: PlantationDetails

    # avoid any extra top-level fields silently
    model_config = {
        "extra": "forbid",
    }

# ProjectOut: shape returned to client - adjust fields if your DB stores different names
class ProjectOut(BaseModel):
    id: str
    organization_id: str
    organization: OrganizationDetails
    contact_person: ContactPerson
    address: Address
    plantation: PlantationDetails
    owner: dict  # e.g. {"owner_id": "<user id>"}
    created_at: datetime
    status: str
    listed: bool

    model_config = {
        "from_attributes": True,  # pydantic v2 equivalent of orm_mode
    }
