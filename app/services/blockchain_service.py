from datetime import datetime
from app.db.mongo import get_db

class BlockchainService:

    @staticmethod
    async def approve_mrv(project_id: str, tx_hash: str):
        db = get_db()
        await db["blockchain_mrv"].update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "approved": True,
                    "approved_tx": tx_hash,
                    "approved_at": datetime.utcnow()
                }
            },
            upsert=True
        )

    @staticmethod
    async def save_project(project_id: str, wallet: str, plantation_hash: str, tx_hash: str):
        db = get_db()
        await db["blockchain_projects"].insert_one({
            "project_id": project_id,
            "wallet": wallet,
            "plantation_hash": plantation_hash,
            "tx_hash": tx_hash,
            "timestamp": datetime.utcnow(),
        })

    @staticmethod
    async def save_mrv(project_id: str, mrv_hash: str, wallet: str, tx_hash: str):
        db = get_db()
        await db["blockchain_mrv"].insert_one({
            "project_id": project_id,
            "mrv_hash": mrv_hash,
            "wallet": wallet,
            "tx_hash": tx_hash,
            "timestamp": datetime.utcnow(),
            "approved": False
        })

    @staticmethod
    async def save_mint(project_id: str, ngo_address: str, amount: int, tx_hash: str):
        db = get_db()
        await db["mint_history"].insert_one({
            "project_id": project_id,
            "ngo_address": ngo_address,
            "amount": amount,
            "tx_hash": tx_hash,
            "timestamp": datetime.utcnow()
        })
