from web3 import Web3
from blockchain.contract_loader import load_contract
from blockchain.web3_client import w3, ADMIN_ADDRESS

token = load_contract("CarbonCreditToken")
project_id = "project-123"   # EXACT value you used
ngo_addr = Web3.to_checksum_address("0x6C980c4daAfF5F549fCF594f139b1B77D0053407")

# Do a call (dry-run) from admin to see revert reason
try:
    token.functions.mintCredits(project_id, ngo_addr, 50).call({"from": ADMIN_ADDRESS})
    print("Call succeeded (would mint).")
except Exception as e:
    print("Revert / error from call():", e)
