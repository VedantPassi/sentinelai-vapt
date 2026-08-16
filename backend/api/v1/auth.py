import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.db import get_db
from core.deps import get_current_user
from core.oidc import build_authorization_url, exchange_code, fetch_userinfo
from core.security import create_access_token, hash_password, verify_password
from models.models import Organization, User

router = APIRouter(prefix="/auth", tags=["auth"])


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    org_id: uuid.UUID

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    org_name: str = "Default Organization"

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    org = Organization(id=uuid.uuid4(), name=body.org_name)
    db.add(org)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        org_id=org.id,
        email=body.email,
        password_hash=hash_password(body.password),
        role="admin",
    )
    db.add(user)
    await db.commit()

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"org_id": str(org.id), "role": user.role},
    )
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"org_id": str(user.org_id), "role": user.role},
    )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/oidc/login")
async def oidc_login(request: Request) -> RedirectResponse:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")
    state = secrets.token_urlsafe(16)
    # Store state in session cookie for CSRF validation — use a signed value
    # In prod this should be stored server-side; here we embed it in the redirect
    # and validate it on callback via the same state value echoed by the provider.
    url = await build_authorization_url(state=state)
    response = RedirectResponse(url=url)
    response.set_cookie("oidc_state", state, httponly=True, samesite="lax", max_age=300)
    return response


@router.get("/oidc/callback")
async def oidc_callback(
    code: str = Query(...),
    state: str = Query(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    if not settings.oidc_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not enabled")

    # Validate state to prevent CSRF
    cookie_state = request.cookies.get("oidc_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OIDC state")

    try:
        tokens = await exchange_code(code)
        userinfo = await fetch_userinfo(tokens["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OIDC exchange failed: {exc}") from exc

    email: str | None = userinfo.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OIDC provider did not return email")

    # Find existing user or provision a new org + admin user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        org_name = userinfo.get("hd") or email.split("@")[-1]
        org = Organization(id=uuid.uuid4(), name=org_name)
        db.add(org)
        await db.flush()
        user = User(
            id=uuid.uuid4(),
            org_id=org.id,
            email=email,
            password_hash="",  # OIDC users have no local password
            role="admin",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"org_id": str(user.org_id), "role": user.role},
    )

    frontend_url = settings.cors_origins[0] if settings.cors_origins else "http://localhost:3000"
    response = RedirectResponse(url=f"{frontend_url}/auth/callback?token={token}")
    response.delete_cookie("oidc_state")
    return response
