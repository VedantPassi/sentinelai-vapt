import uuid
from typing import Any
from urllib.parse import urlparse

import dns.resolver
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import get_current_user, require_admin, require_analyst
from models.models import Target, User

router = APIRouter(prefix="/targets", tags=["targets"])


class TargetCreate(BaseModel):
    name: str
    type: str
    url: str
    scope_definition: dict[str, Any] | None = None
    asset_criticality: float = 0.5


class TargetUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    url: str | None = None
    scope_definition: dict[str, Any] | None = None
    asset_criticality: float | None = None


class TargetResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    name: str
    type: str
    url: str
    scope_definition: dict[str, Any] | None
    asset_criticality: float
    verified: bool

    model_config = {"from_attributes": True}


async def _get_target_or_404(target_id: uuid.UUID, org_id: uuid.UUID, db: AsyncSession) -> Target:
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.org_id == org_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return target


@router.get("", response_model=list[TargetResponse])
async def list_targets(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Target]:
    result = await db.execute(select(Target).where(Target.org_id == current_user.org_id))
    return list(result.scalars().all())


@router.post("", response_model=TargetResponse, status_code=status.HTTP_201_CREATED)
async def create_target(
    body: TargetCreate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> Target:
    target = Target(
        id=uuid.uuid4(),
        org_id=current_user.org_id,
        name=body.name,
        type=body.type,
        url=body.url,
        scope_definition=body.scope_definition,
        asset_criticality=body.asset_criticality,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Target:
    return await _get_target_or_404(target_id, current_user.org_id, db)


@router.put("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: uuid.UUID,
    body: TargetUpdate,
    current_user: User = Depends(require_analyst),
    db: AsyncSession = Depends(get_db),
) -> Target:
    target = await _get_target_or_404(target_id, current_user.org_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(target, field, value)
    await db.commit()
    await db.refresh(target)
    return target


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(
    target_id: uuid.UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    target = await _get_target_or_404(target_id, current_user.org_id, db)
    db.delete(target)
    await db.commit()


@router.post("/{target_id}/verify", response_model=TargetResponse)
async def verify_target(
    target_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Target:
    target = await _get_target_or_404(target_id, current_user.org_id, db)

    domain = urlparse(target.url).hostname or target.url
    expected_record = f"sentinelai-verify={str(target.id)}"

    try:
        answers = dns.resolver.resolve(f"_sentinelai-verify.{domain}", "TXT")
        txt_values = [rdata.to_text().strip('"') for rdata in answers]
        verified = any(expected_record in v for v in txt_values)
    except Exception:
        verified = False

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DNS TXT record '_sentinelai-verify.{domain}' with value '{expected_record}' not found",
        )

    target.verified = True
    await db.commit()
    await db.refresh(target)
    return target
