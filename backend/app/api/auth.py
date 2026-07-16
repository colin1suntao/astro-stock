"""API routes for auth."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import current_user, hash_pwd, make_token, verify_pwd
from app.db import get_db
from app.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    name: str
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    birth_iso: str | None = None
    birth_lat: float | None = None
    birth_lng: float | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


def _to_out(u: User) -> UserOut:
    return UserOut(
        id=u.id, email=u.email, name=u.name,
        birth_iso=u.birth_iso, birth_lat=u.birth_lat, birth_lng=u.birth_lng,
    )


@router.post("/register", response_model=TokenOut)
async def register(body: RegisterIn, db: Session = Depends(get_db)):
    exists = db.scalar(select(User).where(User.email == body.email))
    if exists:
        raise HTTPException(409, "email already registered")
    user = User(email=body.email, name=body.name, pwd_hash=hash_pwd(body.password))
    db.add(user); db.commit(); db.refresh(user)
    return TokenOut(access_token=make_token(user.id), user=_to_out(user))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_pwd(body.password, user.pwd_hash):
        raise HTTPException(401, "invalid credentials")
    return TokenOut(access_token=make_token(user.id), user=_to_out(user))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return _to_out(user)


@router.put("/me", response_model=UserOut)
async def update_me(
    body: dict,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Update birth info / name. Accepts partial keys."""
    for k in ("name", "birth_iso", "birth_lat", "birth_lng"):
        if k in body and body[k] is not None:
            setattr(user, k, body[k])
    db.commit(); db.refresh(user)
    return _to_out(user)
