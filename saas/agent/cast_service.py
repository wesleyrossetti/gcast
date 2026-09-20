from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any

import pychromecast
from pychromecast.controllers.youtube import YouTubeController

logger = logging.getLogger("agent.cast")


class LocalCastService:
    """Manages Chromecast discovery and control on the local network."""

    def __init__(self, discovery_timeout: int = 10) -> None:
        self._timeout = discovery_timeout
        self._devices: dict[str, pychromecast.Chromecast] = {}
        self._lock = threading.Lock()

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover(self) -> list[dict]:
        logger.info("Starting discovery (timeout=%ss)...", self._timeout)
        casts, browser = pychromecast.get_chromecasts(timeout=self._timeout)
        with self._lock:
            for cast in casts:
                uid = str(cast.cast_info.uuid)
                self._devices[uid] = cast
                logger.info("Found: %s (%s)", cast.cast_info.friendly_name, uid)
        pychromecast.discovery.stop_discovery(browser)
        return self._snapshot_all()

    def _snapshot_all(self) -> list[dict]:
        with self._lock:
            uids = list(self._devices.keys())
        return [self._snapshot(uid) for uid in uids]

    def _snapshot(self, uid: str) -> dict:
        with self._lock:
            cast = self._devices.get(uid)
        if cast is None:
            return {"device_uuid": uid, "error": "not found"}
        try:
            cast.wait(timeout=3)
            cs = cast.status
            ms = cast.media_controller.status
            return {
                "device_uuid":  uid,
                "friendly_name": cast.cast_info.friendly_name,
                "host":         cast.cast_info.host,
                "port":         cast.cast_info.port,
                "model_name":   cast.cast_info.model_name,
                "cast_type":    cast.cast_info.cast_type,
                "volume_level": cs.volume_level if cs else None,
                "volume_muted": cs.volume_muted if cs else False,
                "app_id":       cs.app_id if cs else None,
                "display_name": cs.display_name if cs else None,
                "player_state": ms.player_state if ms else None,
                "title":        ms.title if ms else None,
                "artist":       ms.artist if ms else None,
                "album":        ms.album_name if ms else None,
                "current_time": ms.current_time if ms else None,
                "duration":     ms.duration if ms else None,
                "thumbnail":    ms.images[0].url if (ms and ms.images) else None,
            }
        except Exception as exc:
            return {
                "device_uuid":  uid,
                "friendly_name": cast.cast_info.friendly_name,
                "host":         cast.cast_info.host,
                "port":         cast.cast_info.port,
                "error":        str(exc),
            }

    # ── Commands ──────────────────────────────────────────────────────────────

    def execute(self, action: str, device_id: str, payload: dict) -> dict:
        if action == "discover":
            self.discover()
            return {"success": True}

        with self._lock:
            cast = self._devices.get(device_id)
        if cast is None:
            return {"success": False, "error": f"Device {device_id} not found"}
        try:
            cast.wait(timeout=5)
            if action == "play":
                cast.media_controller.play()
            elif action == "pause":
                cast.media_controller.pause()
            elif action == "stop":
                cast.media_controller.stop()
            elif action == "seek":
                cast.media_controller.seek(float(payload.get("seconds", 0)))
            elif action == "set_volume":
                cast.set_volume(float(payload.get("level", 0.5)))
            elif action == "mute":
                cast.set_volume_muted(True)
            elif action == "unmute":
                cast.set_volume_muted(False)
            elif action == "play_media":
                mc = cast.media_controller
                mc.play_media(
                    url          = payload["url"],
                    content_type = payload.get("content_type", "video/mp4"),
                    title        = payload.get("title"),
                    thumb        = payload.get("thumb"),
                )
                mc.block_until_active(timeout=10)
            elif action == "play_youtube":
                yt = YouTubeController()
                cast.register_handler(yt)
                yt.play_video(payload["video_id"])
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            return {"success": True}
        except Exception as exc:
            logger.error("Command %s on %s failed: %s", action, device_id, exc)
            return {"success": False, "error": str(exc)}

    def get_statuses(self) -> list[dict]:
        return self._snapshot_all()
