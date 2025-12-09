# app/api/v1/auth.py
from fastapi import APIRouter, HTTPException, Depends, status
from app.schemas.user_schema import UserCreate, UserOut, Token
from app.services.user_service import create_user, authenticate_user, get_user_by_id, get_user_by_email
from app.utils.security import create_access_token, decode_access_token
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/auth/register", response_model=UserOut)
async def register(user_in: UserCreate):
    existing = await get_user_by_email(user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(user_in.dict())
    return UserOut(
        id=str(user["_id"]),
        full_name=user["full_name"],
        email=user["email"],
        role=user["role"],
        wallet_address=user.get("wallet_address"),
        created_at=user["created_at"],
    )

@router.post("/auth/login", response_model=Token)
async def login(body: dict):
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password required")
    user = await authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    user["id"] = str(user["_id"])
    return user

@router.get("/users")
async def list_users():
    db = get_db()
    cursor = db["users"].find({})
    users = []
    async for u in cursor:
        u["id"] = str(u["_id"])
        users.append(u)
    return users

@router.get("/auth/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return UserOut(
        id=str(current_user["_id"]),
        full_name=current_user["full_name"],
        email=current_user["email"],
        role=current_user["role"],
        wallet_address=current_user.get("wallet_address"),
        created_at=current_user["created_at"],
    )
