from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from blockchain.contract_loader import load_contract
from blockchain.transaction_service import TxService
from app.services.blockchain_tx_service import save_tx
from app.db.mongo import get_db
from web3 import Web3
from bson import ObjectId
import os
import json
import hashlib
from app.api.deps import get_current_user
from datetime import datetime

router = APIRouter()

# ENV values
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ADMIN_ADDRESS = Web3.to_checksum_address(os.getenv("ADMIN_ADDRESS"))

def extract_tx_hash(receipt):
    try:
        return receipt["transactionHash"].hex()
    except:
        return getattr(receipt, "transactionHash", None) and receipt.transactionHash.hex()

# ------------------------------
# Models
# ------------------------------
class RegisterProjectPayload(BaseModel):
    project_id: str

class SubmitMRVPayload(BaseModel):
    project_id: str
    mrv_hash: str

class ApproveMRVPayload(BaseModel):
    project_id: str
    verifier_id: str | None = None
    comment: str | None = None

class MintCredits(BaseModel):
    project_id: str
    ngo_address: str
    amount: int


# ===========================================================
# MINT CREDITS (DEMO + CHAIN)
# ===========================================================
@router.post("/mint-credits")
async def mint_credits(data: MintCredits):
    try:
        contract = load_contract("CarbonCreditToken")

        try:
            receipt = TxService.send_user_tx(
                contract.functions.mintCredits(
                    data.project_id,
                    data.ngo_address,
                    data.amount
                ),
                ADMIN_PRIVATE_KEY,
                ADMIN_ADDRESS
            )
            tx_hash = extract_tx_hash(receipt)
        except Exception as chain_err:
            tx_hash = f"DEMO_TX_{data.project_id}"
            print("Mint failed, DEMO mode:", chain_err)

        # DEMO balance
        db = get_db()
        await db["demo_balances"].update_one(
            {"wallet": data.ngo_address.lower()},
            {"$inc": {"balance": data.amount}},
            upsert=True
        )

        await save_tx(
            project_id=data.project_id,
            operation="mint_credits",
            tx_hash=tx_hash,
            wallet=data.ngo_address,
            extra={"amount": data.amount}
        )

        return {"status": "success", "tx_hash": tx_hash}

    except Exception as e:
        raise HTTPException(400, str(e))

# ===========================================================
# REGISTER PROJECT ON-CHAIN
# ===========================================================
@router.post("/register-project")
async def register_project(payload: RegisterProjectPayload, current_user=Depends(get_current_user)):
    try:
        db = get_db()
        proj = await db["projects"].find_one({"_id": ObjectId(payload.project_id)})
        if not proj:
            raise HTTPException(404, "Project not found")

        # Build deterministic hash
        plantation = proj.get("plantation") or proj.get("plantation_info") or {}
        plantation_json = json.dumps(plantation, sort_keys=True, default=str)
        plantation_hash = hashlib.sha256(plantation_json.encode()).hexdigest()

        tx_hash = None

        try:
            contract = load_contract("CarbonRegistry")
            receipt = TxService.send_user_tx(
                contract.functions.registerProject(
                    payload.project_id,
                    plantation_hash
                ),
                ADMIN_PRIVATE_KEY,
                ADMIN_ADDRESS
            )
            tx_hash = extract_tx_hash(receipt)

        except Exception as e:
            tx_hash = f"DEMO_REGISTER_{payload.project_id}"
            print("register-project failed, using DEMO:", e)

        await db["projects"].update_one(
            {"_id": ObjectId(payload.project_id)},
            {"$set": {
                "plantation_hash": plantation_hash,
                "blockchain_registration_tx": tx_hash,
                "plantation_hash_generated_at": datetime.utcnow().isoformat()
            }}
        )

        await save_tx(
            project_id=payload.project_id,
            operation="register_project",
            tx_hash=tx_hash,
            wallet=current_user.get("wallet", "unknown"),
        )

        return {"status": "success", "plantation_hash": plantation_hash, "tx_hash": tx_hash}

    except Exception as e:
        raise HTTPException(400, str(e))



# ===========================================================
# SUBMIT MRV HASH ON-CHAIN
# ===========================================================
@router.post("/submit-mrv")
async def submit_mrv(payload: SubmitMRVPayload, current_user=Depends(get_current_user)):

    try:
        db = get_db()
        proj = await db["projects"].find_one({"_id": ObjectId(payload.project_id)})
        if not proj:
            raise HTTPException(404, "Project not found")

        tx_hash = None

        try:
            contract = load_contract("CarbonRegistry")
            receipt = TxService.send_user_tx(
                contract.functions.submitMRV(
                    payload.project_id,
                    payload.mrv_hash
                ),
                ADMIN_PRIVATE_KEY,
                ADMIN_ADDRESS
            )
            tx_hash = extract_tx_hash(receipt)

        except Exception as e:
            tx_hash = f"DEMO_SUBMIT_MRV_{payload.project_id}"
            print("submit-mrv failed, DEMO mode:", e)

        await db["projects"].update_one(
            {"_id": ObjectId(payload.project_id)},
            {"$set": {
                "mrv_hash": payload.mrv_hash,
                "mrv_submission_tx": tx_hash,
                "mrv_submitted_at": datetime.utcnow().isoformat()
            }}
        )

        await save_tx(
            project_id=payload.project_id,
            operation="submit_mrv",
            tx_hash=tx_hash,
            wallet=current_user.get("wallet", "unknown")
        )

        return {"status": "success", "tx_hash": tx_hash}

    except Exception as e:
        raise HTTPException(400, str(e))



# ===========================================================
# APPROVE MRV
# ===========================================================
@router.post("/approve-mrv")
async def approve_mrv(payload: ApproveMRVPayload, current_user=Depends(get_current_user)):

    try:
        db = get_db()
        proj = await db["projects"].find_one({"_id": ObjectId(payload.project_id)})
        if not proj:
            raise HTTPException(404, "Project not found")

        tx_hash = None

        try:
            contract = load_contract("CarbonRegistry")
            receipt = TxService.send_user_tx(
                contract.functions.approveMRV(
                    payload.project_id,
                    payload.verifier_id or ""
                ),
                ADMIN_PRIVATE_KEY,
                ADMIN_ADDRESS
            )
            tx_hash = extract_tx_hash(receipt)

        except Exception as e:
            tx_hash = f"DEMO_APPROVE_MRV_{payload.project_id}"
            print("approve-mrv failed, DEMO mode:", e)

        await db["projects"].update_one(
            {"_id": ObjectId(payload.project_id)},
            {"$set": {
                "mrv_approval_tx": tx_hash,
                "mrv_approved_at": datetime.utcnow().isoformat(),
                "status": "approved",
                "verifier_comment": payload.comment or ""
            }}
        )

        await save_tx(
            project_id=payload.project_id,
            operation="approve_mrv",
            tx_hash=tx_hash,
            wallet=current_user.get("wallet", "unknown")
        )

        return {"status": "success", "tx_hash": tx_hash}

    except Exception as e:
        raise HTTPException(400, str(e))



# ===========================================================
# GET BALANCE
# ===========================================================
@router.get("/balance/{address}")
async def balance(address: str):
    try:
        contract = load_contract("CarbonCreditToken")

        checksum = Web3.to_checksum_address(address.strip())
        real_balance = contract.functions.balanceOf(checksum).call()

        db = get_db()
        demo = await db["demo_balances"].find_one({"wallet": address.lower()})
        demo_balance = demo["balance"] if demo else 0

        return {
            "address": checksum,
            "real_blockchain_balance": real_balance,
            "demo_balance": demo_balance,
            "final_display_balance": real_balance + demo_balance
        }

    except Exception as e:
        raise HTTPException(400, str(e))
