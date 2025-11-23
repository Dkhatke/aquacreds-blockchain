from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
from typing import Optional, Dict, Any

def _convert_to_degrees(value):
    # value is a tuple like ((deg,1),(min,1),(sec,100))
    try:
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

def extract_exif(filepath: str) -> Dict[str, Any]:
    """
    Returns dict: {'latitude': float|None, 'longitude': float|None, 'timestamp': datetime|None, 'raw': {...}}
    """
    out = {"latitude": None, "longitude": None, "timestamp": None, "raw": {}}
    try:
        img = Image.open(filepath)
        exif_data = img._getexif() or {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            out["raw"][str(tag)] = value

        # GPS extraction
        gps_info = {}
        gps_tag = None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                gps_tag = value
                break
        if gps_tag:
            gps_parsed = {}
            for key in gps_tag.keys():
                name = GPSTAGS.get(key, key)
                gps_parsed[name] = gps_tag[key]
            lat = None
            lon = None
            if "GPSLatitude" in gps_parsed and "GPSLatitudeRef" in gps_parsed:
                lat = _convert_to_degrees(gps_parsed["GPSLatitude"])
                if gps_parsed.get("GPSLatitudeRef", "N") != "N":
                    lat = -lat
            if "GPSLongitude" in gps_parsed and "GPSLongitudeRef" in gps_parsed:
                lon = _convert_to_degrees(gps_parsed["GPSLongitude"])
                if gps_parsed.get("GPSLongitudeRef", "E") != "E":
                    lon = -lon
            out["latitude"] = lat
            out["longitude"] = lon

        # DateTime original
        dt = None
        for candidate in ("DateTimeOriginal", "DateTime", "DateTimeDigitized"):
            if candidate in out["raw"]:
                try:
                    val = out["raw"][candidate]
                    if isinstance(val, bytes):
                        val = val.decode(errors="ignore")
                    # common format: "YYYY:MM:DD HH:MM:SS"
                    dt = datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                    out["timestamp"] = dt
                    break
                except Exception:
                    continue
    except Exception:
        # swallow and return None-filled structure
        pass
    return out
