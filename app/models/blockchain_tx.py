# app/models/blockchain_tx.py
from datetime import datetime

def blockchain_tx_doc(project_id, action, tx_hash, wallet, status="success"):
    return {
        "project_id": project_id,
        "action": action,     # register, submit_mrv, approve, mint
        "tx_hash": tx_hash,
        "wallet": wallet,
        "status": status,
        "timestamp": datetime.utcnow()
    }
