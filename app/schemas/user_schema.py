from pydantic import BaseModel, EmailStr, Field
from pydantic import model_validator
from typing import Optional
from datetime import datetime

VALID_ROLES = {"user", "verifier", "admin"}

class UserCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    email: EmailStr
    role: str = Field(..., description="user|verifier|admin")
    wallet_address: Optional[str] = None
    password: str = Field(..., min_length=8, max_length=72)

    @model_validator(mode="after")
    def check_role_wallet(self):
        role = self.role
        wallet = self.wallet_address
        if role not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        if role in {"user"} and (not wallet or wallet.strip() == ""):
            raise ValueError("wallet_address required for user")
        return self

class UserOut(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    wallet_address: Optional[str] = None
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
