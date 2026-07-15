from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

# Política de senha: mínimo de 8 caracteres.
# Máximo de 72 — o bcrypt só considera os primeiros 72 BYTES e truncaria o resto
# silenciosamente; limitar aqui evita esse comportamento confuso.
# Atenção: o limite do bcrypt é em bytes, não em caracteres. Uma senha com
# acentos/emoji pode ter ≤ 72 caracteres e ainda assim passar de 72 bytes em
# UTF-8 — por isso a checagem final é feita sobre o tamanho codificado.
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72


def validate_password_strength(password: str) -> str:
    """Valida tamanho (em bytes, p/ bcrypt) e complexidade da senha.

    Política (decidida na fase de testes): mínimo de 8 caracteres, ao menos um
    caractere especial, máximo 72 bytes (limite do bcrypt). Sem exigência de
    maiúscula/dígito — regras demais geram senhas anotadas em post-it.
    Levanta ValueError (vira 422 no FastAPI) com mensagem clara.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"A senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"A senha é longa demais (máx. {MAX_PASSWORD_BYTES} bytes; "
            "acentos e emoji contam mais de 1 byte cada)."
        )
    if all(c.isalnum() for c in password):
        raise ValueError("A senha deve conter ao menos um caractere especial (ex.: !#-.,*).")
    return password


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    password: str
    is_manager: bool = False
    profile_id: str | None = None
    matricula: str | None = None

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


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
    # True = precisa trocar a senha antes de usar o sistema (1º login)
    must_change_password: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPasswordChange(BaseModel):
    current_password: str
    # Mesma política da criação (tamanho + complexidade).
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    csrf_token: str | None = None


class LoginRequest(BaseModel):
    email: str  # aceita qualquer identificador (email ou username simples)
    password: str
