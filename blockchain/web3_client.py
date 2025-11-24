import os
from web3 import Web3
from dotenv import load_dotenv

# --------------------------------------------
# FORCE LOAD .env FROM PROJECT ROOT
# --------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, ".env")

# Debug: Print which file is being used
print("📌 Using .env file at:", ENV_PATH)

# Load env file explicitly
load_dotenv(ENV_PATH)

# Debug: Print RAW bytes of the actual file
print("------ RAW .env FILE CONTENTS (DEBUG) ------")
try:
    with open(ENV_PATH, "rb") as f:
        raw_bytes = f.read()
        print(raw_bytes)
except Exception as e:
    print("Error reading .env file:", e)
print("--------------------------------------------")

# --------------------------------------------
# Load RPC URL safely
# --------------------------------------------
RPC_URL = os.getenv("AMOY_RPC_URL", "").strip()

if not RPC_URL:
    raise Exception("❌ Missing AMOY_RPC_URL in .env")

print(f"🔍 Current Working Directory: {os.getcwd()}")
print(f"➡️ Loaded AMOY RPC from .env: {RPC_URL}")

# Show sanitized value
print("------ DEBUG ENV VALUES ------")
print("RAW AMOY_RPC_URL =", repr(RPC_URL))
print("AVAILABLE ENV KEYS:", list(os.environ.keys()))
print("--------------------------------")

# Create Web3 provider (no crash on slow RPC)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

def is_rpc_connected():
    """Safe connection test — does NOT crash backend."""
    try:
        return w3.is_connected()
    except:
        return False

# Polygon Amoy Testnet Chain ID
CHAIN_ID = 80002

# --------------------------------------------
# Load ADMIN Private Key Safely
# --------------------------------------------
ADMIN_PRIVATE_KEY = os.getenv("ADMIN_PRIVATE_KEY", "").strip()

if not ADMIN_PRIVATE_KEY:
    raise Exception("❌ Missing ADMIN_PRIVATE_KEY in .env")

# Validate key format (must start with 0x)
if not ADMIN_PRIVATE_KEY.startswith("0x"):
    raise Exception("❌ ADMIN_PRIVATE_KEY must start with 0x (0x + 64 hex chars)")

# Validate hex string length (66 chars)
if len(ADMIN_PRIVATE_KEY) != 66:
    raise Exception("❌ ADMIN_PRIVATE_KEY must be 66 characters long (0x + 64 hex chars)")

try:
    ADMIN_ADDRESS = w3.eth.account.from_key(ADMIN_PRIVATE_KEY).address
    ADMIN_ADDRESS = Web3.to_checksum_address(ADMIN_ADDRESS)
except Exception as e:
    raise Exception(f"❌ Invalid ADMIN_PRIVATE_KEY format: {e}")

print(f"🟦 Admin Address Loaded: {ADMIN_ADDRESS}")

# --------------------------------------------
# Final RPC status print
# --------------------------------------------
if is_rpc_connected():
    print("✅ Connected to Polygon Amoy RPC Successfully")
else:
    print("⚠️ Warning: RPC NOT connected (will retry during tx calls)")
