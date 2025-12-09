# app/core/config.py
from dotenv import load_dotenv
import os

# Load .env file (if present)
load_dotenv()

class Settings:
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "aquacreds_dev")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret")
    IPFS_API: str = os.getenv("IPFS_API", "")

settings = Settings()

