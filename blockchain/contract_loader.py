import json
import os
from web3 import Web3
from .web3_client import w3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ABI_DIR = os.path.join(BASE_DIR, "abis")

CONTRACT_ADDRESSES = {
    "ProjectRegistry": "0x8B490286f95ffFBED0Eb66a52b6dA508cECD07CC",
    "Verification": "0xcd69AB04Ae9Dc58025052e9fC4E20BDf7Ea837aa",
    "CarbonCreditToken": "0x3FF4eBD81C36C4eB4C4748841F750542e0392fe9",
    "Marketplace": "0x2D7651aDB253e1E145167241fa367a230ccE3bd8"
}

def load_contract(name: str):
    """Load contract from ABI and address."""
    abi_path = os.path.join(ABI_DIR, f"{name}.json")

    with open(abi_path, 'r') as f:
        abi = json.load(f)

    address = Web3.to_checksum_address(CONTRACT_ADDRESSES[name])

    return w3.eth.contract(address=address, abi=abi)
