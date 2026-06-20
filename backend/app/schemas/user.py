from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# Tamanho mínimo de senha aplicado na criação e na troca de senha.
MIN_PASSWORD_LENGTH = 8


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)
    is_manager: bool = False
    profile_id: str | None = None
    matricula: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    email: EmailStr | None = None
    is_manager: bool | None = None
    is_active: bool | None = None
    profile_id: str | None = None
    matricula: str | None = None


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    matricula: str | None = None
    is_manager: bool
    is_active: bool
    profile_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPasswordChange(BaseModel):
    current_password: str
    # Política de senha: mínimo de 8 caracteres (igual à criação).
    new_password: str = Field(..., min_length=MIN_PASSWORD_LENGTH)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str  # aceita qualquer identificador (email ou username simples)
    password: str
