"""Authentication — JWT-based multi-user auth with persistent storage."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import time
import uuid
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from libs.observability.logging import get_logger

logger = get_logger("auth")

router = APIRouter()

JWT_SECRET = os.getenv("JWT_SECRET", "optimus-trustlayer-jwt-secret-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer(auto_error=False)

# ── Persistent user store ──────────────────────────────────────────────

DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data"
USERS_FILE = str(DATA_DIR / "users.json")


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _load_users() -> list[dict]:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_users(users: list[dict]) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


_users: list[dict] = _load_users()

# Seed the original admin user if no users exist
if not _users:
    _users.append({
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "sujansonu07",
        "password_hash": _hash_password("sujansonu07"),
        "email": "",
        "company_domain": "",
        "role": "admin",
        "created_at": "2026-01-01T00:00:00Z",
    })
    _save_users(_users)


def _find_user(username: str) -> Optional[dict]:
    for u in _users:
        if u["username"].lower() == username.lower():
            return u
    return None


def _find_user_by_id(user_id: str) -> Optional[dict]:
    for u in _users:
        if u["id"] == user_id:
            return u
    return None


# ── Models ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    user_id: str
    role: str
    expires_in: int


class SignupRequest(BaseModel):
    username: str
    password: str
    email: str = ""


class SignupResponse(BaseModel):
    token: str
    username: str
    user_id: str
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class MeResponse(BaseModel):
    username: str
    user_id: str
    email: str
    company_domain: str
    role: str


class UpdateProfileRequest(BaseModel):
    email: str = ""
    company_domain: str = ""


# ── Token helpers ──────────────────────────────────────────────────────

def create_token(user: dict) -> str:
    payload = {
        "sub": user["username"],
        "uid": user["id"],
        "role": user.get("role", "user"),
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
    """Dependency that extracts and validates the JWT."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return payload


# ── Routes ─────────────────────────────────────────────────────────────

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    user = _find_user(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    password_hash = _hash_password(request.password)
    if not hmac.compare_digest(password_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_token(user)
    logger.info("user_login", username=user["username"])
    return LoginResponse(
        token=token,
        username=user["username"],
        user_id=user["id"],
        role=user.get("role", "user"),
        expires_in=JWT_EXPIRY_HOURS * 3600,
    )


@router.post("/auth/signup", response_model=SignupResponse)
async def signup(request: SignupRequest) -> SignupResponse:
    if len(request.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(request.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    existing = _find_user(request.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Detect company domain from email
    company_domain = ""
    if request.email and "@" in request.email:
        domain = request.email.split("@")[1].lower()
        # Skip generic email providers
        generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "protonmail.com"}
        if domain not in generic:
            company_domain = domain

    user = {
        "id": str(uuid.uuid4()),
        "username": request.username,
        "password_hash": _hash_password(request.password),
        "email": request.email,
        "company_domain": company_domain,
        "role": "user",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _users.append(user)
    _save_users(_users)

    token = create_token(user)
    logger.info("user_signup", username=user["username"], domain=company_domain)
    return SignupResponse(
        token=token,
        username=user["username"],
        user_id=user["id"],
        message="Account created successfully",
    )


@router.post("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user = _find_user(current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    current_hash = _hash_password(request.current_password)
    if not hmac.compare_digest(current_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    user["password_hash"] = _hash_password(request.new_password)
    _save_users(_users)
    logger.info("password_changed", username=user["username"])
    return {"message": "Password changed successfully"}


@router.get("/auth/me", response_model=MeResponse)
async def get_me(user: dict = Depends(get_current_user)) -> MeResponse:
    stored = _find_user(user["sub"])
    return MeResponse(
        username=user["sub"],
        user_id=user.get("uid", "00000000-0000-0000-0000-000000000001"),
        email=stored.get("email", "") if stored else "",
        company_domain=stored.get("company_domain", "") if stored else "",
        role=user.get("role", "user"),
    )


@router.put("/auth/profile")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    user = _find_user(current_user["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.email:
        user["email"] = request.email
        if "@" in request.email:
            domain = request.email.split("@")[1].lower()
            generic = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "protonmail.com"}
            if domain not in generic:
                user["company_domain"] = domain

    if request.company_domain:
        user["company_domain"] = request.company_domain

    _save_users(_users)
    return {"message": "Profile updated"}


@router.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)) -> dict:
    """Logout — client discards the token. Server-side we just acknowledge."""
    logger.info("user_logout", username=current_user["sub"])
    return {"message": "Logged out successfully"}
