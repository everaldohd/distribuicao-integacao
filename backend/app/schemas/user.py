from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=8)
    is_manager: bool = False
    profile_id: Optional[str] = None
    matricula: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    is_manager: Optional[bool] = None
    is_active: Optional[bool] = None
    profile_id: Optional[str] = None
    matricula: Optional[str] = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    matricula: Optional[str] = None
    is_manager: bool
    is_active: bool
    profile_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str  # aceita qualquer identificador (email ou username simples)
    password: str
