from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import require_admin
from core.security import hash_password
from models.models import User

router = APIRouter(prefix="/users", tags=["users"])


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    org_id: uuid.UUID

    model_config = {"from_attributes": True}


class InviteRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "analyst"

    def model_post_init(self, __context: object) -> None:
        if self.role not in ("admin", "analyst", "viewer"):
            raise ValueError("role must be admin, analyst, or viewer")
        if len(self.password) < 8:
            raise ValueError("password must be at least 8 characters")


class RolePatch(BaseModel):
    role: str

    def model_post_init(self, __context: object) -> None:
        if self.role not in ("admin", "analyst", "viewer"):
            raise ValueError("role must be admin, analyst, or viewer")


@router.get("", response_model=list[UserResponse])
async def list_users(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[User]:
    result = await db.execute(select(User).where(User.org_id == current_user.org_id))
    return list(result.scalars().all())


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_role(
    user_id: uuid.UUID,
    body: RolePatch,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role")
    user.role = body.role
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == current_user.org_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself")
    await db.delete(user)
    await db.commit()
