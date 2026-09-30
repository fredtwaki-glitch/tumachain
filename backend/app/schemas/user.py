from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole, VerificationState


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    username: Optional[str] = Field(default=None, min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    phone_number: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: Optional[str]
    username: Optional[str]
    phone_number: Optional[str]
    profile_photo_url: Optional[str]
    preferred_settlement_method: Optional[str]
    kyc_status: str
    kyb_status: str
    aml_status: str
    role: UserRole
    verification_state: VerificationState
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class EmailVerifyRequest(BaseModel):
    token: str


class RefreshRequest(BaseModel):
    refresh_token: str
