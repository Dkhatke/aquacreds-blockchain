import os
import uuid
from typing import Tuple, Optional

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_file_local(filename: str, data: bytes) -> str:
    """
    Save bytes to uploads/<uuid>_<filename>
    Return absolute filepath.
    """
    uid = uuid.uuid4().hex
    safe_name = f"{uid}_{os.path.basename(filename)}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(data)
    return path

def upload_to_ipfs_stub(filepath: str) -> Optional[str]:
    """
    Dev stub — returns a fake IPFS hash. Replace with real IPFS pinning call later.
    """
    # You will replace this with an API call to Pinata/Infura or a local IPFS daemon.
    fake_hash = "Qm" + uuid_hex_stub(filepath := filepath)  # intentionally playful
    return fake_hash

def uuid_hex_stub(s: str) -> str:
    # deterministic-ish short stub from path (not cryptographically meaningful)
    import hashlib
    return hashlib.sha1(s.encode()).hexdigest()[:40]
