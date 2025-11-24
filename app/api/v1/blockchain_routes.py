from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from blockchain.contract_loader import load_contract
from blockchain.transaction_service import TxService

router = APIRouter()

# -----------------------------
# Utility: safe receipt hash
# -----------------------------
def extract_tx_hash(receipt):
    try:
        return receipt["transactionHash"].hex()
    except:
        return receipt.transactionHash.hex()


# ---------------------------------------------------------
# A) Register Project (NGO)
# ---------------------------------------------------------

class RegisterProject(BaseModel):
    project_id: str
    plantation_hash: str
    private_key: str
    wallet: str

@router.post("/register-project")
async def register_project(data: RegisterProject):

    try:
        contract = load_contract("ProjectRegistry")

        receipt = TxService.send_user_tx(
            contract.functions.registerProject(data.project_id, data.plantation_hash),
            data.private_key,
            data.wallet
        )

        return {"status": "success", "tx_hash": extract_tx_hash(receipt)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# ---------------------------------------------------------
# B) Submit MRV (Verifier)
# ---------------------------------------------------------

class SubmitMRV(BaseModel):
    project_id: str
    mrv_hash: str
    private_key: str
    wallet: str

@router.post("/submit-mrv")
async def submit_mrv(data: SubmitMRV):

    try:
        contract = load_contract("Verification")

        receipt = TxService.send_user_tx(
            contract.functions.submitMRV(data.project_id, data.mrv_hash),
            data.private_key,
            data.wallet
        )

        return {"status": "success", "tx_hash": extract_tx_hash(receipt)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# ---------------------------------------------------------
# C) Approve MRV (Admin-only)
# ---------------------------------------------------------

class ApproveMRV(BaseModel):
    project_id: str

@router.post("/approve-mrv")
async def approve_mrv(data: ApproveMRV):

    try:
        contract = load_contract("Verification")

        receipt = TxService.send_admin_tx(
            contract.functions.approveMRV(data.project_id)
        )

        return {"status": "success", "tx_hash": extract_tx_hash(receipt)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# ---------------------------------------------------------
# D) Mint Credits (Admin)
# ---------------------------------------------------------

class MintCredits(BaseModel):
    project_id: str
    ngo_address: str
    amount: int

@router.post("/mint-credits")
async def mint_credits(data: MintCredits):
    try:
        from web3 import Web3

        contract = load_contract("CarbonCreditToken")

        # FIX: Convert NGO address to checksum
        ngo_address = Web3.to_checksum_address(data.ngo_address)

        receipt = TxService.send_admin_tx(
            contract.functions.mintCredits(data.project_id, ngo_address, data.amount)
        )

        return {"status": "success", "tx_hash": extract_tx_hash(receipt)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------
# E) Get CC Token Balance
# ---------------------------------------------------------

@router.get("/balance/{address}")
async def balance(address: str):
    try:
        from web3 import Web3
        contract = load_contract("CarbonCreditToken")

        # FIX: strip hidden characters
        address = address.strip()

        # Convert to checksum
        address = Web3.to_checksum_address(address)

        balance_value = contract.functions.balanceOf(address).call()

        return {"address": address, "balance": balance_value}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
