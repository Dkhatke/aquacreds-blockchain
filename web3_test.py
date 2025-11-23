# web3_test.py
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()   # reads .env in cwd

RPC = os.getenv("AMOY_RPC_URL")
print("Loaded RPC from .env (repr):", repr(RPC))

if not RPC:
    print("ERROR: AMOY_RPC_URL is missing")
    raise SystemExit(1)

w3 = Web3(Web3.HTTPProvider(RPC))

print("web3.py version:", Web3.__version__)
print("Is connected (w3.is_connected()):", w3.is_connected())

# optional: simple rpc call
try:
    print("chain id (eth_chainId):", w3.eth.chain_id)
except Exception as e:
    print("Exception calling chain_id:", type(e), e)
