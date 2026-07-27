"""Authentication — JWT-based login gate."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

router = APIRouter()

JWT_SECRET = "optimus-trustlayer-jwt-secret-2026"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# Hardcoded credentials — production would use a proper user store
VALID_USERNAME = "sujansonu07"
VALID_PASSWORD_HASH = hashlib.sha256("sujansonu07".encode()).hexdigest()

security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    expires_in: int


class MeResponse(BaseModel):
    username: str
    viewer_id: str


def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + (JWT_EXPIRY_HOURS * 3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Dependency that extracts and validates the JWT from the Authorization header."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    password_hash = hashlib.sha256(request.password.encode()).hexdigest()

    if request.username != VALID_USERNAME or not hmac.compare_digest(password_hash, VALID_PASSWORD_HASH):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(request.username)
    return LoginResponse(
        token=token,
        username=request.username,
        expires_in=JWT_EXPIRY_HOURS * 3600,
    )


@router.get("/auth/me", response_model=MeResponse)
async def get_me(user: dict = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        username=user["sub"],
        viewer_id="00000000-0000-0000-0000-000000000001",
    )
