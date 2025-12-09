# app/schemas/project_schema.py
import hashlib
import json
from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import Optional, List
from datetime import datetime


# ---------------------------------------------------------
# ADDRESS
# ---------------------------------------------------------
class Address(BaseModel):
    state: str = Field(..., min_length=2)
    district: str = Field(..., min_length=2)
    full_address: str = Field(..., min_length=5)
    pincode: str = Field(..., min_length=3)


# ---------------------------------------------------------
# CONTACT PERSON
# ---------------------------------------------------------
class ContactPerson(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    mobile_no: str = Field(..., min_length=6)
    designation: Optional[str] = None


# ---------------------------------------------------------
# ORGANIZATION
# ---------------------------------------------------------
class OrganizationDetails(BaseModel):
    name: str = Field(..., min_length=2)
    reg_no: Optional[str] = None
    year_established: Optional[int] = None


# ---------------------------------------------------------
# PLANTATION — FIXED (NO location field)
# ---------------------------------------------------------
class PlantationDetails(BaseModel):
    project_title: str = Field(..., min_length=2)
    plantation_date: datetime
    area_restored_hectares: float = Field(..., ge=0)
    species: Optional[List[str]] = None
    number_of_saplings: Optional[int] = Field(None, ge=0)
    seed_source: Optional[str] = None

    # computed hash
    plantation_hash: Optional[str] = None

    @model_validator(mode="after")
    def compute_hash(self):
        canonical = {
            "project_title": self.project_title or "",
            "plantation_date": self.plantation_date.isoformat(),
            "area_restored_hectares": self.area_restored_hectares,
            "species": sorted(self.species) if self.species else [],
            "number_of_saplings": self.number_of_saplings,
            "seed_source": self.seed_source or "",
        }

        canonical_json = json.dumps(
            canonical, sort_keys=True, separators=(",", ":")
        )

        h = hashlib.sha256()
        h.update(canonical_json.encode("utf-8"))
        self.plantation_hash = h.hexdigest()
        return self


# ---------------------------------------------------------
# CREATE PROJECT — FIXED (plantation optional)
# ---------------------------------------------------------
class ProjectCreate(BaseModel):
    organization: OrganizationDetails
    contact_person: ContactPerson
    address: Address
    plantation: Optional[PlantationDetails] = None  # <-- FIXED

    model_config = {
        "extra": "ignore",  # <-- FIXED (prevents 422)
    }


# ---------------------------------------------------------
# OUTPUT SCHEMA
# ---------------------------------------------------------
class ProjectOut(BaseModel):
    id: str
    organization: OrganizationDetails
    contact_person: ContactPerson
    address: Address
    plantation: Optional[PlantationDetails] = None
    owner: dict
    created_at: datetime
    status: str
    listed: bool

    model_config = {
        "from_attributes": True,
    }
