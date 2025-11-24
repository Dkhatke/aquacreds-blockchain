from web3 import Web3
import json
from pathlib import Path

RPC = "https://rpc-amoy.polygon.technology"

w3 = Web3(Web3.HTTPProvider(RPC))

print("\n======================")
print("🔍 Web3 Connected:", w3.is_connected())
print("======================\n")

# ----------------------------------------
# Load ABI helper (FIXED PATH)
# ----------------------------------------
def load_abi(name):
    path = Path("blockchain/abis") / f"{name}.json"
    with open(path, "r") as f:
        artifact = json.load(f)
    return artifact["address"], artifact["abi"]


# ----------------------------------------
# Test A — Verification.isEligible(projectId)
# ----------------------------------------
def test_A(project_id):
    print("\n--- TEST A: Check isEligible(projectId) ---")

    addr, abi = load_abi("Verification")
    verif = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)

    try:
        print("Verification contract:", addr)
        mrv = verif.functions.getMRV(project_id).call()
        print("MRV:", mrv)
        eligible = verif.functions.isEligible(project_id).call()
        print("isEligible:", eligible)
    except Exception as e:
        print("Error:", e)



# ----------------------------------------
# Test B — Token verificationContract address
# ----------------------------------------
def test_B():
    print("\n--- TEST B: Token linked verificationContract ---")

    addr, abi = load_abi("CarbonCreditToken")
    token = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)

    try:
        v_addr = token.functions.verificationContract().call()
        print("Token address:", addr)
        print("Token's verificationContract:", v_addr)
    except Exception as e:
        print("Error:", e)


# ----------------------------------------
# Test C — Project exists in ProjectRegistry
# ----------------------------------------
def test_C(project_id):
    print("\n--- TEST C: ProjectRegistry.projectExists(projectId) ---")

    addr, abi = load_abi("ProjectRegistry")
    reg = w3.eth.contract(address=Web3.to_checksum_address(addr), abi=abi)

    try:
        exists = reg.functions.projectExists(project_id).call()
        print("Registry address:", addr)
        print("project_id:", project_id)
        print("Exists:", exists)
    except Exception as e:
        print("Error:", e)


# ----------------------------------------
# RUN TESTS
# ----------------------------------------
project_id = "6924119fd46fc1fa3b77cbfb"   # Replace with your actual project_id

test_A(project_id)
test_B()
test_C(project_id)
