import uuid
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from pydantic import BaseModel
from app.core.database import get_db
from app.core.config import settings
from app.core.security import verify_password, create_access_token, hash_password
from app.core.logging import get_logger
from app.models.user import User
from app.schemas.user import LoginRequest, Token

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email, User.is_active == True).first()
    if not user or not verify_password(data.password, user.hashed_password):
        # Log de falha de login (segurança) — não revela se o usuário existe
        logger.warning("Falha de login para identificador '%s'", data.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    logger.info("Login bem-sucedido: %s (gestor=%s)", user.email, user.is_manager)
    token = create_access_token(subject=user.id)
    return Token(access_token=token)


# ---------------------------------------------------------------------------
# Integração NEO (SSO) — login delegado
# ---------------------------------------------------------------------------
# Fluxo:
#   1. O NEO autentica o servidor (já tem o controle de acesso).
#   2. Ao abrir esta aplicação, o NEO gera um "token de handoff" — um JWT
#      assinado com o segredo compartilhado (NEO_SSO_SECRET, algoritmo HS256)
#      contendo, no mínimo: { "matricula": "...", "email": "...", "name": "...", "exp": <unix> }
#   3. A aplicação valida a assinatura, identifica (ou cria) o usuário pela
#      matrícula e devolve o token de sessão próprio desta aplicação.
# Enquanto NEO_SSO_SECRET estiver vazio, o endpoint fica desativado (403).

class SSORequest(BaseModel):
    token: str


@router.post("/sso", response_model=Token)
def sso_login(data: SSORequest, db: Session = Depends(get_db)):
    if not settings.NEO_SSO_SECRET:
        raise HTTPException(status_code=403, detail="Integração NEO (SSO) não está habilitada.")

    try:
        claims = jwt.decode(
            data.token,
            settings.NEO_SSO_SECRET,
            algorithms=["HS256"],
            options={"require": ["exp"]},
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token do NEO inválido ou expirado: {e}")

    matricula = str(claims.get("matricula") or "").strip()
    email = str(claims.get("email") or "").strip().lower()
    name = str(claims.get("name") or "").strip()

    if not matricula and not email:
        raise HTTPException(status_code=400, detail="Token do NEO sem matrícula nem e-mail.")

    # Identifica por matrícula (preferencial), depois por e-mail
    user = None
    if matricula:
        user = db.query(User).filter(User.matricula == matricula).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if not user:
        if not settings.NEO_SSO_AUTO_PROVISION:
            raise HTTPException(status_code=404, detail="Servidor não cadastrado nesta aplicação.")
        user = User(
            id=str(uuid.uuid4()),
            name=name or email or matricula,
            email=email or f"{matricula}@neo.local",
            matricula=matricula or None,
            # Senha aleatória: o acesso é sempre via NEO; não há login local para ele
            hashed_password=hash_password(secrets.token_urlsafe(24)),
            is_manager=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Mantém matrícula/e-mail/nome sincronizados com o NEO
        changed = False
        if matricula and user.matricula != matricula:
            user.matricula = matricula; changed = True
        if email and user.email != email:
            user.email = email; changed = True
        if name and user.name != name:
            user.name = name; changed = True
        if changed:
            db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Usuário inativo.")

    return Token(access_token=create_access_token(subject=user.id))
