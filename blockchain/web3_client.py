import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------
# Load RPC URL from .env
# -------------------------------------------------
RPC_URL = os.getenv("AMOY_RPC_URL")
if not RPC_URL:
    raise Exception("Missing AMOY_RPC_URL in .env")

print(f"🔍 Loading ENV from: {os.getcwd()}")
print(f"➡️ Loaded RPC from .env: {RPC_URL}")

# Initialize connection
w3 = Web3(Web3.HTTPProvider(RPC_URL))

if not w3.is_connected():
    raise Exception(f"Failed to connect to RPC: {RPC_URL}")

print("✅ Connected to Polygon RPC successfully")

# -------------------------------------------------
# Load admin private key for sending admin transactions
# -------------------------------------------------
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY")
if not ADMIN_PRIVATE_KEY:
    raise Exception("Missing ADMIN_PRIVATE_KEY in .env")

# Get checksum admin address
ADMIN_ADDRESS = w3.eth.account.from_key(ADMIN_PRIVATE_KEY).address
ADMIN_ADDRESS = Web3.to_checksum_address(ADMIN_ADDRESS)

print(f"🟦 Admin Address Loaded: {ADMIN_ADDRESS}")
