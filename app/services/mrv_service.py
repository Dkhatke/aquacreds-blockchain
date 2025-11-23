# app/services/mrv_service.py
import datetime
import hashlib
import json
from typing import Dict, Any, Optional, Tuple

def estimate_carbon_from_canopy(canopy_percent: float, area_ha: float = 1.0) -> float:
    max_carbon_per_ha = 50.0
    carbon = (canopy_percent / 100.0) * max_carbon_per_ha * area_ha
    return round(carbon, 3)


def _extract_biomass_and_area(ml_result: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    try:
        biomass = ml_result.get("biomass") or ml_result.get("Biomass") or {}
        co2eq = biomass.get("CO2eq_t_per_ha") or biomass.get("co2eq_t_per_ha")
        credit_suggestion = biomass.get("credit_suggestion") or {}
        area = credit_suggestion.get("area_ha") or credit_suggestion.get("area")
        return float(co2eq) if co2eq is not None else None, float(area) if area is not None else None
    except Exception:
        return None, None


def _ndvi_to_canopy_percent(ndvi_val: Optional[float]) -> float:
    if ndvi_val is None:
        return 0.0
    try:
        nd = float(ndvi_val)
        if nd < 0:
            nd = 0.0
        if 1 < nd <= 100:
            return nd
        return max(0.0, min(nd, 1.0)) * 100.0
    except Exception:
        return 0.0


def normalize_ml_result(raw_ml: Dict[str, Any]) -> Dict[str, Any]:
    ml = dict(raw_ml) if isinstance(raw_ml, dict) else {}

    tile = ml.get("Tile_ID") or ml.get("tile_id")
    if tile:
        ml["tile_id"] = tile

    cls = ml.get("class") or ml.get("ecosystem_class")
    if cls:
        ml["ecosystem_class"] = cls

    ml["indices"] = ml.get("indices") or {}
    ml["biomass"] = ml.get("biomass") or {}

    if ml.get("canopy_percent") is None:
        ndvi = ml["indices"].get("NDVI") or ml.get("ndvi")
        ml["canopy_percent"] = _ndvi_to_canopy_percent(ndvi)

    return ml


def _canonicalize(obj: Any) -> Any:
    # stable canonicalization for nested structures
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _canonicalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [_canonicalize(x) for x in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def compute_mrv_hash(record: Dict[str, Any], plantation_hash: Optional[str] = None) -> str:
    """
    Build canonical representation of MRV record + plantation_hash and return sha256 hex digest.
    """
    canonical = {
        "upload_id": record.get("upload_id", "") or "",
        "project_id": record.get("project_id", "") or "",
        "ml_result": record.get("ml_result") or {},
        "ndvi_satellite": record.get("ndvi_satellite"),
        "satellite_score": record.get("satellite_score"),
        "carbon_stock_tCO2e": record.get("carbon_stock_tCO2e"),
        "created_at": (
            record.get("created_at").isoformat()
            if hasattr(record.get("created_at"), "isoformat")
            else str(record.get("created_at") or "")
        ),
        "plantation_hash": plantation_hash or "",
    }

    canonical = _canonicalize(canonical)
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_mrv_record(upload_id: str, ml_result: Dict[str, Any], sat_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    sat = sat_result or {}

    ml = normalize_ml_result(ml_result)

    co2eq_per_ha, area_ha = _extract_biomass_and_area(ml.get("biomass", {}))
    if co2eq_per_ha is not None and area_ha is not None:
        carbon = round(co2eq_per_ha * area_ha, 3)
    else:
        canopy = ml.get("canopy_percent", 0.0) or 0.0
        area = ml.get("biomass", {}).get("credit_suggestion", {}).get("area_ha", 1.0) or 1.0
        carbon = estimate_carbon_from_canopy(canopy, area)

    record = {
        "upload_id": upload_id,
        "project_id": ml.get("project_id"),
        "ml_result": ml,
        "ndvi_satellite": sat.get("ndvi_satellite"),
        "satellite_score": sat.get("satellite_score"),
        "carbon_stock_tCO2e": carbon,
        "verifier_status": "pending",
        "created_at": now,
    }
    return record
