# app/schemas/mrv_schema.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreditSuggestion(BaseModel):
    area_ha: float
    gross_CO2eq_t: float
    suggested_credits_tCO2e: float
    buffer_fraction: float


class Biomass(BaseModel):
    AGB_t_per_ha: float
    BGB_t_per_ha: float
    Carbon_t_per_ha: float
    CO2eq_t_per_ha: float
    credit_suggestion: CreditSuggestion


class MLIndices(BaseModel):
    NDVI: float
    EVI: float
    SAVI: float
    NDWI: float
    MNDWI: float
    MSI: float
    NDMI: float


class MLResult(BaseModel):
    tile_id: str = Field(..., alias="Tile_ID")
    ecosystem_class: str = Field(..., alias="class")
    indices: MLIndices
    biomass: Biomass

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
    }


class MRVCreate(BaseModel):
    upload_id: str
    project_id: Optional[str]
    ml_result: MLResult
    ndvi_satellite: Optional[float] = None
    satellite_score: Optional[float] = None


class MRVOut(BaseModel):
    id: str
    upload_id: str
    project_id: Optional[str]
    ml_result: dict
    ndvi_satellite: Optional[float]
    satellite_score: Optional[float]
    carbon_stock_tCO2e: float
    verifier_status: str
    created_at: datetime
    mrv_hash: Optional[str] = None   # new field: SHA-256 of MRV payload + plantation_hash
