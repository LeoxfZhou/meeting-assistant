from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_session
from app.models.user import User

hasher = PasswordHasher()
# 不存在的账户也做一次散列验证，减少明显的账户枚举时间差。
DUMMY_HASH = hasher.hash("not-a-real-user-password")
bearer = HTTPBearer(auto_error=False)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def create_token(user: User, request: Request) -> str:
    settings = request.app.state.settings
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
                       "iss": "meeting-assistant", "aud": "meeting-assistant-api"},
                      settings.jwt_secret.get_secret_value(), algorithm="HS256")


def current_user(request: Request, session: Annotated[Session, Depends(get_session)],
                 credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    unauthorized = HTTPException(401, "Invalid or missing credentials", headers={"WWW-Authenticate": "Bearer"})
    if credentials is None:
        raise unauthorized
    try:
        claims = jwt.decode(credentials.credentials, request.app.state.settings.jwt_secret.get_secret_value(),
                            algorithms=["HS256"], issuer="meeting-assistant", audience="meeting-assistant-api",
                            options={"require": ["sub", "exp", "iat", "iss", "aud"]})
        uid = UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise unauthorized from exc
    user = session.get(User, uid)
    if user is None or not user.is_active:
        raise unauthorized
    request.state.user_id = str(user.id)
    return user


CurrentUser = Annotated[User, Depends(current_user)]
