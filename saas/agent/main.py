from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed

from agent.cast_service import LocalCastService
from agent.config import (
    AGENT_TOKEN,
    DISCOVERY_TIMEOUT,
    LOG_LEVEL,
    RECONNECT_DELAY,
    SERVER_WS_URL,
    STATUS_INTERVAL,
)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("agent")


async def run_agent() -> None:
    cast = LocalCastService(discovery_timeout=DISCOVERY_TIMEOUT)

    # Initial local discovery (blocking, run in executor to not block event loop)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, cast.discover)

    while True:
        try:
            await _connect_and_run(cast, loop)
        except Exception as exc:
            logger.warning("Disconnected (%s). Reconnecting in %ss...", exc, RECONNECT_DELAY)
        await asyncio.sleep(RECONNECT_DELAY)


async def _connect_and_run(cast: LocalCastService, loop: asyncio.AbstractEventLoop) -> None:
    logger.info("Connecting to %s", SERVER_WS_URL)
    async with websockets.connect(SERVER_WS_URL, ping_interval=20, ping_timeout=10) as ws:
        # ── Auth ──────────────────────────────────────────────────────────────
        await ws.send(json.dumps({"type": "auth", "token": AGENT_TOKEN}))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if resp.get("type") != "auth_ok":
            raise RuntimeError(f"Auth failed: {resp.get('message', 'unknown')}")
        logger.info("Authenticated — agent_id=%s", resp.get("agent_id"))

        # ── Background tasks ──────────────────────────────────────────────────
        stop_event = asyncio.Event()

        async def status_sender():
            while not stop_event.is_set():
                statuses = await loop.run_in_executor(None, cast.get_statuses)
                try:
                    await ws.send(json.dumps({
                        "type":      "status_update",
                        "devices":   statuses,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }))
                except ConnectionClosed:
                    stop_event.set()
                    break
                await asyncio.sleep(STATUS_INTERVAL)

        async def command_receiver():
            async for raw in ws:
                data = json.loads(raw)
                msg_type = data.get("type")

                if msg_type == "command":
                    cmd_id = data.get("command_id", "")
                    action = data.get("action", "")
                    dev_id = data.get("device_id", "")
                    payload = data.get("payload", {})
                    logger.info("Command: %s → device=%s", action, dev_id)

                    result = await loop.run_in_executor(
                        None, cast.execute, action, dev_id, payload
                    )
                    await ws.send(json.dumps({
                        "type":       "command_result",
                        "command_id": cmd_id,
                        **result,
                    }))

                elif msg_type == "ping":
                    await ws.send(json.dumps({"type": "pong"}))

        await asyncio.gather(status_sender(), command_receiver())


def main() -> None:
    if not AGENT_TOKEN:
        raise SystemExit("AGENT_TOKEN environment variable is required.")
    asyncio.run(run_agent())


if __name__ == "__main__":
    main()
