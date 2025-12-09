from fastapi import APIRouter
from app.services.user_service import create_user

router = APIRouter()

@router.post("/dev/register")
async def dev_register(payload: dict):
    return await create_user(payload)
