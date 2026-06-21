import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Response
from jose import JWTError, jwt
from passlib.context import CryptContext

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({"sub": subject, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


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
