from fastapi import APIRouter
from pydantic import BaseModel
from blockchain.contract_loader import load_contract
from blockchain.transaction_service import TxService

router = APIRouter()

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
    contract = load_contract("ProjectRegistry")

    receipt = TxService.send_user_tx(
        contract.functions.registerProject(data.project_id, data.plantation_hash),
        data.private_key,
        data.wallet
    )

    return {
        "status": "success",
        "tx_hash": receipt.transactionHash.hex()
    }


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
    contract = load_contract("Verification")

    receipt = TxService.send_user_tx(
        contract.functions.submitMRV(data.project_id, data.mrv_hash),
        data.private_key,
        data.wallet
    )

    return {"tx_hash": receipt.transactionHash.hex()}


# ---------------------------------------------------------
# C) Approve MRV (Admin)
# ---------------------------------------------------------

class ApproveMRV(BaseModel):
    project_id: str

@router.post("/approve-mrv")
async def approve_mrv(data: ApproveMRV):
    contract = load_contract("Verification")

    receipt = TxService.send_admin_tx(
        contract.functions.approveMRV(data.project_id)
    )

    return {"tx_hash": receipt.transactionHash.hex()}


# ---------------------------------------------------------
# D) Mint Credits (Admin)
# ---------------------------------------------------------

class MintCredits(BaseModel):
    project_id: str
    ngo_address: str
    amount: int

@router.post("/mint-credits")
async def mint_credits(data: MintCredits):
    contract = load_contract("CarbonCreditToken")

    receipt = TxService.send_admin_tx(
        contract.functions.mintCredits(data.project_id, data.ngo_address, data.amount)
    )

    return {"tx_hash": receipt.transactionHash.hex()}


# ---------------------------------------------------------
# E) Get Balance (Any user)
# ---------------------------------------------------------

@router.get("/balance/{address}")
async def balance(address: str):
    contract = load_contract("CarbonCreditToken")
    bal = contract.functions.balanceOf(address).call()
    return {"address": address, "balance": bal}
