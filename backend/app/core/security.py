import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Response

from .config import settings
from .token_denylist import denylist

# bcrypt direto (sem passlib): a lib é mantida ativamente e os hashes $2b$
# gerados pelo passlib continuam verificáveis — migração transparente.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # hash malformado no banco → trata como credencial inválida
        return False


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "exp": expire,
        # jti: identifica o token individualmente → permite revogá-lo no logout
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    """Valida assinatura/expiração e recusa tokens revogados (logout)."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    jti = payload.get("jti")
    if jti and denylist.contains(jti):
        return None
    return payload.get("sub")


def revoke_token(token: str) -> None:
    """Revoga um token válido (logout): denylist pelo jti até o exp original.

    Tokens inválidos/expirados são ignorados em silêncio — não há o que revogar.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return  # token antigo (sem jti) — expira naturalmente pelo exp
    ttl = int(exp - datetime.now(UTC).timestamp())
    if ttl > 0:
        denylist.add(jti, ttl)


def set_auth_cookies(response: Response, token: str) -> str:
    """Grava o JWT em cookie HttpOnly e emite o cookie CSRF (double-submit).

    Retorna o token CSRF gerado (o front também o recebe no corpo, opcional).
    """
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    csrf_token = secrets.token_urlsafe(32)
    # Cookie de sessão: HttpOnly (JS não lê → mitiga roubo por XSS)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    # Cookie CSRF: legível pelo front, que o reflete no header X-CSRF-Token
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Remove os cookies de sessão e CSRF (logout)."""
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")
