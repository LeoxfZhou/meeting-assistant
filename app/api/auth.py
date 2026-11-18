from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.security import CurrentUser, DUMMY_HASH, create_token, hasher, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import Register, Login, Token, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])
DB = Annotated[Session, Depends(get_session)]


@router.post("/register", response_model=UserRead, status_code=201)
def register(payload: Register, session: DB) -> User:
    user = User(email=str(payload.email).casefold(), display_name=payload.display_name,
                password_hash=hasher.hash(payload.password.get_secret_value()))
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "Email already registered") from exc
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(payload: Login, request: Request, session: DB) -> Token:
    user = session.scalar(select(User).where(User.email == str(payload.email).casefold()))
    valid = verify_password(user.password_hash if user else DUMMY_HASH, payload.password.get_secret_value())
    if not valid or user is None or not user.is_active:
        raise HTTPException(401, "Invalid credentials", headers={"WWW-Authenticate": "Bearer"})
    if hasher.check_needs_rehash(user.password_hash):
        user.password_hash = hasher.hash(payload.password.get_secret_value())
        session.commit()
    return Token(access_token=create_token(user, request))


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user
