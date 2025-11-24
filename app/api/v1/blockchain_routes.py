# app/api/v1/blockchain.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from blockchain.contract_loader import load_contract
from blockchain.transaction_service import TxService
from app.services.blockchain_tx_service import save_tx
from app.db.mongo import get_db
from web3 import Web3
import os

router = APIRouter()

# ENV values
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
ADMIN_ADDRESS = Web3.to_checksum_address(os.getenv("ADMIN_ADDRESS"))


def extract_tx_hash(receipt):
    try:
        return receipt["transactionHash"].hex()
    except:
        return receipt.transactionHash.hex()


# ===========================================================
# MODEL: Mint Credits
# ===========================================================
class MintCredits(BaseModel):
    project_id: str
    ngo_address: str
    amount: int


@router.post("/mint-credits")
async def mint_credits(data: MintCredits):
    """
    DEMO MODE:
    - Try blockchain mint
    - Regardless of success/failure, store demo balance locally
    """
    try:
        contract = load_contract("CarbonCreditToken")

        try:
            # Try real blockchain mint (may fail silently)
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
            # Blockchain failed → we still continue with demo balance
            tx_hash = f"DEMO_TX_{data.project_id}"
            print("Blockchain mint failed, switching to DEMO mode:", chain_err)

        # --------------------------------------------------------
        # 🔥 DEMO MODE: Store credit locally in MongoDB
        # --------------------------------------------------------
        db = get_db()

        await db["demo_balances"].update_one(
            {"wallet": data.ngo_address.lower()},
            {"$inc": {"balance": data.amount}},
            upsert=True
        )

        # Save TX (optional)
        await save_tx(
            project_id=data.project_id,
            action="mint_credits",
            tx_hash=tx_hash,
            wallet=data.ngo_address,
            extra={"amount": data.amount},
        )

        return {
            "status": "success",
            "tx_hash": tx_hash,
            "demo_mode": True
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ===========================================================
# GET BALANCE  (DEMO + REAL)
# ===========================================================
@router.get("/balance/{address}")
async def balance(address: str):
    try:
        contract = load_contract("CarbonCreditToken")

        checksum = Web3.to_checksum_address(address.strip())
        real_balance = contract.functions.balanceOf(checksum).call()

        # Fetch DEMO balance from MongoDB
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
        raise HTTPException(status_code=400, detail=str(e))
