import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user
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

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    def model_post_init(self, __context: object) -> None:
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")


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
