from datetime import datetime
from app.db.mongo import get_db

async def save_tx(project_id: str, action: str, tx_hash: str, wallet: str, extra: dict = None):
    db = get_db()
    record = {
        "project_id": project_id,
        "action": action,
        "tx_hash": tx_hash,
        "wallet": wallet,
        "extra": extra or {},
        "timestamp": datetime.utcnow(),
    }
    await db["blockchain_tx"].insert_one(record)
