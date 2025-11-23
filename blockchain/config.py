import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BASE_DIR / ".env"

load_dotenv(ENV_PATH, override=True)

class Settings:
    AMOY_RPC_URL: str = os.getenv("AMOY_RPC_URL")
    ADMIN_PRIVATE_KEY: str = os.getenv("ADMIN_PRIVATE_KEY")
    VERIFIER_ADDRESS: str = os.getenv("VERIFIER_ADDRESS")
    PROJECT_REGISTRY_ADDRESS: str = os.getenv("PROJECT_REGISTRY_ADDRESS")
    VERIFICATION_ADDRESS: str = os.getenv("VERIFICATION_ADDRESS")
    CARBON_CREDIT_TOKEN_ADDRESS: str = os.getenv("CARBON_CREDIT_TOKEN_ADDRESS")
    MARKETPLACE_ADDRESS: str = os.getenv("MARKETPLACE_ADDRESS")

settings = Settings()
