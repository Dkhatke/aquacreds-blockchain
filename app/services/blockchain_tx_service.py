from datetime import datetime
from app.db.mongo import get_db


async def save_tx(project_id: str, operation: str, tx_hash: str | None, wallet: str, error: str | None = None):
    """
    Save blockchain transaction logs.
    Works for:
    - register_project
    - submit_mrv
    - mint_credits
    """
    db = get_db()

    doc = {
        "project_id": project_id,
        "operation": operation,
        "tx_hash": tx_hash,
        "wallet": wallet,
        "status": "error" if error else "success",
        "error": error,
        "timestamp": datetime.utcnow()
    }

    await db["tx_logs"].insert_one(doc)
