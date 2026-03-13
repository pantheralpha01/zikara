from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import os

import bcrypt
from jose import ExpiredSignatureError, JWTError, jwt

from app.core.config import settings

_BCRYPT_ROUNDS = int(os.environ.get("BCRYPT_ROUNDS", "12"))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {"sub": subject, "role": role, "exp": expire, "type": "access"}
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    data = {"sub": subject, "role": role, "exp": expire, "type": "refresh"}
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_token_with_error(token: str) -> Tuple[Optional[dict], Optional[str]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload, None
    except ExpiredSignatureError:
        return None, "token_expired"
    except JWTError:
        return None, "token_invalid"


def create_password_reset_token(user_id: str, password_hash: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    # Bake a slice of the current hash into the token so it auto-invalidates after use
    data = {"sub": user_id, "type": "password_reset", "pwh": password_hash[:8], "exp": expire}
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_password_reset_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset":
            return None
        return payload
    except JWTError:
        return None
