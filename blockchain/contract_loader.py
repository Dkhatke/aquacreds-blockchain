# blockchain/contract_loader.py

import json
import os
from web3 import Web3
from .web3_client import w3   # <-- FIXED: remove is_rpc_connected

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "abis")


def load_contract(contract_name: str):
    try:
        json_path = os.path.join(ARTIFACTS_DIR, f"{contract_name}.json")

        if not os.path.exists(json_path):
            raise Exception(f"Contract artifact not found: {json_path}")

        with open(json_path, "r") as f:
            artifact = json.load(f)

        address = artifact["address"]
        abi = artifact["abi"]

        return w3.eth.contract(
            address=Web3.to_checksum_address(address),
            abi=abi
        )
    except Exception as e:
        raise Exception(f"Failed to load contract {contract_name}: {e}")
