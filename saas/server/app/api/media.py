from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.db import Device, HistoryEntry, User
from app.models.schemas import (
    DeviceActionRequest,
    PlayMediaRequest,
    PlayYouTubeRequest,
    SeekRequest,
)
from app.ws.manager import manager

router = APIRouter(prefix="/api/media", tags=["media"])


@router.post("/play-youtube")
async def play_youtube(
    req: PlayYouTubeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _cmd(db, user, req.device_uuid, "play_youtube", {"video_id": req.video_id})


@router.post("/play-url")
async def play_url(
    req: PlayMediaRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _cmd(db, user, req.device_uuid, "play_media", {
        "url": req.url, "content_type": req.content_type,
        "title": req.title, "thumb": req.thumb,
    })


@router.post("/play")
async def play(req: DeviceActionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _cmd(db, user, req.device_uuid, "play", {})


@router.post("/pause")
async def pause(req: DeviceActionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _cmd(db, user, req.device_uuid, "pause", {})


@router.post("/stop")
async def stop(req: DeviceActionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _cmd(db, user, req.device_uuid, "stop", {})


@router.post("/seek")
async def seek(req: SeekRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _cmd(db, user, req.device_uuid, "seek", {"seconds": req.seconds})


# ── Shared helper ─────────────────────────────────────────────────────────────

async def _cmd(db: AsyncSession, user: User, device_uuid: str, action: str, payload: dict):
    result = await db.execute(
        select(Device).where(Device.device_uuid == device_uuid, Device.org_id == user.org_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device não encontrado")

    cmd_result = await manager.send_command(device.agent_id, action, device_uuid, payload)

    entry = HistoryEntry(
        org_id      = user.org_id,
        device_uuid = device_uuid,
        device_name = device.friendly_name,
        action      = action,
        details_json = str(payload),
        success     = cmd_result["success"],
        error       = cmd_result.get("error"),
    )
    db.add(entry)
    await db.commit()

    if not cmd_result["success"]:
        raise HTTPException(500, cmd_result.get("error", "Falha ao executar"))
    return {"status": "ok"}
