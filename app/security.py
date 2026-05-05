from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

# Monkeypatch for passlib + bcrypt 4.0.0+ incompatibility
import bcrypt
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = type("About", (object,), {"__version__": bcrypt.__version__})

from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str, company_id: str | None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "role": role, "company_id": company_id, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
