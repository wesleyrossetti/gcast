from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.db import HistoryEntry, User
from app.models.schemas import HistoryEntryOut

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=list[HistoryEntryOut])
async def get_history(
    device_uuid: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(HistoryEntry).where(HistoryEntry.org_id == user.org_id)
    if device_uuid:
        q = q.where(HistoryEntry.device_uuid == device_uuid)
    q = q.order_by(HistoryEntry.timestamp.desc()).limit(min(limit, 200))
    result = await db.execute(q)
    entries = result.scalars().all()

    out = []
    for e in entries:
        try:
            details = json.loads(e.details_json or "{}")
        except Exception:
            details = {}
        out.append(HistoryEntryOut(
            id=e.id, device_uuid=e.device_uuid, device_name=e.device_name,
            action=e.action, details=details, success=e.success,
            error=e.error, timestamp=e.timestamp,
        ))
    return out
