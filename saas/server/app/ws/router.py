from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.db import Agent, Device, Organization
from app.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/agent")
async def agent_ws(ws: WebSocket, db: AsyncSession = Depends(get_db)):
    await ws.accept()
    agent_id: str | None = None
    org_id:   str | None = None

    try:
        # ── Step 1: Authenticate ──────────────────────────────────────────────
        try:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=10.0)
        except asyncio.TimeoutError:
            await ws.close(code=4000)
            return

        if msg.get("type") != "auth":
            await ws.send_json({"type": "auth_error", "message": "Esperado tipo 'auth'"})
            await ws.close(code=4001)
            return

        token = msg.get("token", "")
        token_hash = Agent.hash_token(token)

        result = await db.execute(select(Agent).where(Agent.token_hash == token_hash))
        agent = result.scalar_one_or_none()
        if not agent:
            await ws.send_json({"type": "auth_error", "message": "Token inválido"})
            await ws.close(code=4001)
            return

        agent_id = agent.id
        org_id   = agent.org_id
        agent.last_seen = datetime.utcnow()
        await db.commit()

        manager.connect(agent_id, org_id, ws)
        await ws.send_json({"type": "auth_ok", "agent_id": agent_id})
        logger.info("Agent %s authenticated", agent_id)

        # ── Step 2: Message loop ──────────────────────────────────────────────
        async for data in ws.iter_json():
            msg_type = data.get("type")

            if msg_type == "status_update":
                devices = data.get("devices", [])
                manager.update_status(org_id, devices)
                await _upsert_devices(db, org_id, agent_id, devices)

            elif msg_type == "command_result":
                manager.resolve_command(
                    data.get("command_id", ""),
                    data.get("success", False),
                    data.get("error"),
                )

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

            # Update last_seen periodically (every ~10 messages to reduce DB writes)
            agent.last_seen = datetime.utcnow()

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("Agent WS error (agent=%s): %s", agent_id, exc)
    finally:
        if agent_id:
            manager.disconnect(agent_id)
            # Commit last_seen
            try:
                await db.commit()
            except Exception:
                pass


async def _upsert_devices(
    db: AsyncSession,
    org_id: str,
    agent_id: str,
    devices: list[dict],
) -> None:
    for d in devices:
        uuid = d.get("device_uuid")
        if not uuid:
            continue
        result = await db.execute(
            select(Device).where(Device.device_uuid == uuid, Device.org_id == org_id)
        )
        device = result.scalar_one_or_none()
        if device:
            device.friendly_name = d.get("friendly_name") or device.friendly_name
            device.host          = d.get("host") or device.host
            device.agent_id      = agent_id  # o agente que reportou por último passa a ser o dono
            device.updated_at    = datetime.utcnow()
        else:
            device = Device(
                device_uuid   = uuid,
                friendly_name = d.get("friendly_name"),
                host          = d.get("host"),
                port          = d.get("port"),
                model_name    = d.get("model_name"),
                agent_id      = agent_id,
                org_id        = org_id,
            )
            db.add(device)
    await db.commit()
