from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages live WebSocket connections from local agents."""

    def __init__(self) -> None:
        # agent_id → WebSocket
        self._connections: dict[str, WebSocket] = {}
        # agent_id → org_id
        self._agent_org: dict[str, str] = {}
        # command_id → asyncio.Future[dict]
        self._pending: dict[str, asyncio.Future] = {}
        # org_id → { device_uuid → status_dict }
        self._status: dict[str, dict[str, dict]] = {}

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def connect(self, agent_id: str, org_id: str, ws: WebSocket) -> None:
        self._connections[agent_id] = ws
        self._agent_org[agent_id] = org_id
        logger.info("Agent %s connected (org=%s)", agent_id, org_id)

    def disconnect(self, agent_id: str) -> str | None:
        org_id = self._agent_org.pop(agent_id, None)
        self._connections.pop(agent_id, None)
        if org_id:
            logger.info("Agent %s disconnected (org=%s)", agent_id, org_id)
        return org_id

    def is_online(self, agent_id: str) -> bool:
        return agent_id in self._connections

    def online_agents_for_org(self, org_id: str) -> list[str]:
        return [aid for aid, oid in self._agent_org.items() if oid == org_id]

    # ── Status cache ──────────────────────────────────────────────────────────

    def update_status(self, org_id: str, devices: list[dict]) -> None:
        bucket = self._status.setdefault(org_id, {})
        for d in devices:
            uid = d.get("device_uuid")
            if uid:
                bucket[uid] = d

    def get_all_statuses(self, org_id: str) -> list[dict]:
        return list(self._status.get(org_id, {}).values())

    def get_device_status(self, org_id: str, device_uuid: str) -> dict | None:
        return self._status.get(org_id, {}).get(device_uuid)

    # ── Command dispatch ──────────────────────────────────────────────────────

    async def send_command(
        self,
        agent_id: str,
        action: str,
        device_uuid: str,
        payload: dict,
        timeout: float = 15.0,
    ) -> dict:
        ws = self._connections.get(agent_id)
        if ws is None:
            return {"success": False, "error": "Agente offline"}

        command_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending[command_id] = future

        try:
            await ws.send_json({
                "type":       "command",
                "command_id": command_id,
                "action":     action,
                "device_id":  device_uuid,
                "payload":    payload,
            })
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout: agente não respondeu"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
        finally:
            self._pending.pop(command_id, None)

    def resolve_command(self, command_id: str, success: bool, error: str | None = None) -> None:
        future = self._pending.get(command_id)
        if future and not future.done():
            future.set_result({"success": success, "error": error})


# Singleton shared across the app
manager = ConnectionManager()
