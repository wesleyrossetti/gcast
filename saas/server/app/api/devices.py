from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.db import Device, User
from app.models.schemas import DeviceOut, DeviceStatus
from app.ws.manager import manager

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceStatus])
async def list_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.org_id == user.org_id))
    devices = result.scalars().all()
    out = []
    for d in devices:
        live = manager.get_device_status(user.org_id, d.device_uuid) or {}
        out.append(_merge(d, live))
    return out


@router.get("/{device_uuid}/status", response_model=DeviceStatus)
async def device_status(
    device_uuid: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Device).where(Device.device_uuid == device_uuid, Device.org_id == user.org_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(404, "Device não encontrado")
    live = manager.get_device_status(user.org_id, device_uuid) or {}
    return _merge(device, live)


@router.post("/discover")
async def request_discover(
    user: User = Depends(get_current_user),
):
    """Ask all online agents to re-discover Chromecasts."""
    agents = manager.online_agents_for_org(user.org_id)
    if not agents:
        raise HTTPException(503, "Nenhum agente online")
    results = []
    for aid in agents:
        r = await manager.send_command(aid, "discover", "", {})
        results.append({"agent_id": aid, **r})
    return {"results": results}


def _merge(device: Device, live: dict) -> DeviceStatus:
    return DeviceStatus(
        device_uuid   = device.device_uuid,
        friendly_name = device.friendly_name,
        host          = device.host,
        model_name    = device.model_name,
        agent_id      = device.agent_id,
        is_online     = manager.is_online(device.agent_id),
        volume_level  = live.get("volume_level"),
        volume_muted  = live.get("volume_muted", False),
        app_id        = live.get("app_id"),
        display_name  = live.get("display_name"),
        player_state  = live.get("player_state"),
        title         = live.get("title"),
        artist        = live.get("artist"),
        current_time  = live.get("current_time"),
        duration      = live.get("duration"),
        thumbnail     = live.get("thumbnail"),
    )
