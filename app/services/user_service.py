# app/services/user_service.py
from app.db.mongo import get_db
from app.utils.security import hash_password, verify_password
from bson import ObjectId
from datetime import datetime

USERS_COLL = "users"

async def create_user(user_in: dict) -> dict:
    db = get_db()
    user = user_in.copy()
    # Hash password (argon2) — plain password must be provided by caller
    raw_pw = user.pop("password", "")
    user["password_hash"] = hash_password(raw_pw)
    user["email"] = user["email"].lower()
    user["created_at"] = datetime.utcnow()
    res = await db[USERS_COLL].insert_one(user)
    user_db = await db[USERS_COLL].find_one({"_id": res.inserted_id})
    if user_db:
        user_db["id"] = str(user_db["_id"])
    return user_db

async def get_user_by_email(email: str):
    db = get_db()
    return await db[USERS_COLL].find_one({"email": email.lower()})

async def get_user_by_id(user_id: str):
    db = get_db()
    try:
        obj = ObjectId(user_id)
    except Exception:
        return None
    return await db[USERS_COLL].find_one({"_id": obj})

async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    user["id"] = str(user["_id"])
    return user
