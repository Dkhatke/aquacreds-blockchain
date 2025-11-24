# blockchain/web3_client.py

import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

AMOY_RPC_URL = os.getenv("AMOY_RPC_URL")
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
VERIFIER_ADDRESS = os.getenv("VERIFIER_ADDRESS")
VERIFIER_PRIVATE_KEY = os.getenv("VERIFIER_PRIVATE_KEY")

if not all([AMOY_RPC_URL, ADMIN_PRIVATE_KEY, VERIFIER_ADDRESS, VERIFIER_PRIVATE_KEY]):
    raise Exception("❌ Missing Web3 environment variables")

w3 = Web3(Web3.HTTPProvider(AMOY_RPC_URL))

if not w3.is_connected():
    raise Exception("❌ Web3 connection failed")

ADMIN_ADDRESS = w3.eth.account.from_key(ADMIN_PRIVATE_KEY).address
CHAIN_ID = w3.eth.chain_id

print("✅ Connected to Polygon Amoy RPC")
print(f"🟦 Admin Address: {ADMIN_ADDRESS}")
print(f"🟪 Verifier Address: {VERIFIER_ADDRESS}")
