from __future__ import annotations

import ipaddress
import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Callable

import pychromecast
import zeroconf as zc
from pychromecast.controllers.youtube import YouTubeController

from app.models import (
    DeviceInfo,
    DeviceStatus,
    MediaStatus,
    PlayerState,
)

logger = logging.getLogger(__name__)


class CastService:
    """Thread-safe wrapper around PyChromecast for device discovery and control."""

    def __init__(self, discovery_timeout: int = 10):
        self._discovery_timeout = discovery_timeout
        self._devices: dict[str, pychromecast.Chromecast] = {}
        self._device_infos: dict[str, DeviceInfo] = {}
        self._lock = threading.Lock()
        self._browser: pychromecast.CastBrowser | None = None
        self._zconf: zc.Zeroconf | None = None
        self._scan_zconfs: list[zc.Zeroconf] = []  # zconfs from one-shot scans
        self._known_hosts_file: str | None = None
        self._hosts_lock = threading.Lock()

    # ── Host persistence ─────────────────────────────────────────────────────

    def set_persistence(self, filepath: str) -> None:
        """Enable host persistence. Loads saved hosts and re-scans them in the background."""
        self._known_hosts_file = filepath
        hosts = self._load_persisted_hosts()
        if hosts:
            logger.info("Restoring %d persisted host(s) on startup: %s", len(hosts), hosts)
            threading.Thread(
                target=self.discover,
                kwargs={"known_hosts": hosts},
                daemon=True,
                name="cast-restore",
            ).start()

    def _load_persisted_hosts(self) -> list[str]:
        if not self._known_hosts_file:
            return []
        try:
            with open(self._known_hosts_file) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_host(self, host: str) -> None:
        if not self._known_hosts_file or not host:
            return
        with self._hosts_lock:
            hosts = self._load_persisted_hosts()
            if host in hosts:
                return
            hosts.append(host)
            try:
                os.makedirs(
                    os.path.dirname(os.path.abspath(self._known_hosts_file)),
                    exist_ok=True,
                )
                with open(self._known_hosts_file, "w") as f:
                    json.dump(hosts, f, indent=2)
                logger.info("Persisted new host: %s", host)
            except Exception as exc:
                logger.error("Failed to persist host %s: %s", host, exc)

    # ── Discovery ────────────────────────────────────────────────────────────

    def start_discovery(
        self,
        on_added: "Callable[[DeviceInfo], None] | None" = None,
        on_removed: "Callable[[DeviceInfo], None] | None" = None,
    ) -> None:
        """Start continuous background mDNS discovery of Chromecast devices."""
        if self._browser is not None:
            logger.debug("Background discovery already running")
            return

        def _add_cast(uuid, name):
            try:
                cast_info = self._browser.devices.get(uuid)
                if cast_info is None:
                    return
                cast = pychromecast.get_chromecast_from_cast_info(
                    cast_info, self._zconf
                )
                cast.start()
                uid = str(uuid)
                info = DeviceInfo(
                    device_id=uid,
                    friendly_name=cast_info.friendly_name,
                    host=cast_info.host,
                    port=cast_info.port,
                    model_name=cast_info.model_name,
                    cast_type=cast_info.cast_type,
                    is_connected=True,
                )
                with self._lock:
                    self._devices[uid] = cast
                    self._device_infos[uid] = info
                logger.info(
                    "Device added via mDNS: %s (%s)",
                    cast_info.friendly_name,
                    uid,
                )
                self._save_host(cast_info.host)
                if on_added:
                    on_added(info)
            except Exception as exc:
                logger.error("Error processing discovered device %s: %s", uuid, exc)

        def _remove_cast(uuid, name, cast_info):
            uid = str(uuid)
            with self._lock:
                cast = self._devices.pop(uid, None)
                info = self._device_infos.pop(uid, None)
            if cast:
                try:
                    cast.disconnect(blocking=False)
                except Exception:
                    pass
            logger.info("Device removed via mDNS: %s", uid)
            if on_removed and info:
                on_removed(info)

        self._zconf = zc.Zeroconf()
        listener = pychromecast.discovery.SimpleCastListener(
            add_callback=_add_cast,
            remove_callback=_remove_cast,
        )
        self._browser = pychromecast.CastBrowser(listener, self._zconf)
        self._browser.start_discovery()
        logger.info("Background Chromecast discovery started via mDNS/zeroconf")

    def stop_discovery(self) -> None:
        """Stop background mDNS discovery."""
        if self._browser:
            try:
                self._browser.stop_discovery()
            except Exception:
                pass
            self._browser = None
        if self._zconf:
            try:
                self._zconf.close()
            except Exception:
                pass
            self._zconf = None
        logger.info("Background Chromecast discovery stopped")

    # ── Host expansion helper ───────────────────────────────────────────────────

    @staticmethod
    def _expand_hosts(hosts: list[str]) -> list[str]:
        """Expand CIDR ranges (e.g. 10.0.0.0/24) to individual IPs; pass through hostnames."""
        result: list[str] = []
        for h in hosts:
            h = h.strip()
            if not h:
                continue
            try:
                net = ipaddress.ip_network(h, strict=False)
                if net.num_addresses == 1:
                    result.append(str(net.network_address))
                else:
                    result.extend(str(ip) for ip in net.hosts())
            except ValueError:
                result.append(h)  # plain hostname / IP
        return result

    def _one_shot_scan(self, known_hosts: list[str] | None = None) -> None:
        """Blocking scan using CastBrowser directly (no deprecated get_chromecasts)."""
        found: dict = {}
        zconf = zc.Zeroconf()
        ref: list = []

        def _add(uuid, name):
            if ref:
                ci = ref[0].devices.get(uuid)
                if ci:
                    found[uuid] = ci

        listener = pychromecast.discovery.SimpleCastListener(add_callback=_add)
        browser = pychromecast.CastBrowser(listener, zconf, known_hosts=known_hosts or [])
        ref.append(browser)
        browser.start_discovery()
        time.sleep(self._discovery_timeout)
        browser.stop_discovery()

        new_devices: list[tuple] = []
        for uuid, cast_info in found.items():
            try:
                cast = pychromecast.get_chromecast_from_cast_info(cast_info, zconf)
                cast.start()
                uid = str(uuid)
                new_devices.append((uid, cast, cast_info))
            except Exception as exc:
                logger.error("Failed to connect to %s: %s", uuid, exc)

        # Keep zconf alive as long as the cast objects use it
        self._scan_zconfs.append(zconf)

        with self._lock:
            for uid, cast, cast_info in new_devices:
                self._devices[uid] = cast
                self._device_infos[uid] = DeviceInfo(
                    device_id=uid,
                    friendly_name=cast_info.friendly_name,
                    host=cast_info.host,
                    port=cast_info.port,
                    model_name=cast_info.model_name,
                    cast_type=cast_info.cast_type,
                    is_connected=True,
                )
                logger.info("Found device: %s (%s)", cast_info.friendly_name, uid)
                self._save_host(cast_info.host)

    def discover(self, known_hosts: list[str] | None = None) -> list[DeviceInfo]:
        """
        If known_hosts given → always do a direct IP scan (supports CIDR, cross-subnet).
        If background discovery active → return cached devices.
        Otherwise → one-shot mDNS scan.
        """
        if known_hosts:
            expanded = self._expand_hosts(known_hosts)
            logger.info("Direct host scan: %d IP(s) expanded from input", len(expanded))
            try:
                self._one_shot_scan(known_hosts=expanded)
            except Exception as exc:
                logger.error("Direct host scan failed: %s", exc)
            return list(self._device_infos.values())

        if self._browser is not None:
            logger.info(
                "Background discovery active – returning %d cached device(s)",
                len(self._device_infos),
            )
            return list(self._device_infos.values())

        logger.info("Starting one-shot mDNS discovery (timeout=%ss)", self._discovery_timeout)
        try:
            self._one_shot_scan()
        except Exception as exc:
            logger.error("Discovery failed: %s", exc)
        return list(self._device_infos.values())

    def list_devices(self) -> list[DeviceInfo]:
        with self._lock:
            return list(self._device_infos.values())

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self, device_id: str) -> DeviceStatus | None:
        cast = self._get_cast(device_id)
        if cast is None:
            return None
        try:
            cast.wait(timeout=5)
            cs = cast.status  # CastStatus
            ms = cast.media_controller.status  # MediaStatus

            # If connected (cs valid) but no active media, report IDLE not UNKNOWN
            player_state_str = ms.player_state if ms else None
            if player_state_str:
                player_state = self._map_player_state(player_state_str)
            elif cs is not None:
                player_state = PlayerState.IDLE
            else:
                player_state = PlayerState.UNKNOWN

            media = MediaStatus(
                player_state=player_state,
                title=ms.title if ms else None,
                artist=ms.artist if ms else None,
                album=ms.album_name if ms else None,
                content_url=ms.content_id if ms else None,
                content_type=ms.content_type if ms else None,
                current_time=ms.current_time if ms else None,
                duration=ms.duration if ms else None,
                thumbnail=ms.images[0].url if (ms and ms.images) else None,
            )

            return DeviceStatus(
                device_id=device_id,
                friendly_name=cast.cast_info.friendly_name,
                is_active_input=cs.is_active_input if cs else None,
                is_stand_by=cs.is_stand_by if cs else None,
                volume_level=cs.volume_level if cs else None,
                volume_muted=cs.volume_muted if cs else False,
                display_name=cs.display_name if cs else None,
                app_id=cs.app_id if cs else None,
                media=media,
                last_updated=datetime.now(),
            )
        except Exception as exc:
            logger.warning("Could not get status for %s: %s", device_id, exc)
            info = self._device_infos.get(device_id)
            return DeviceStatus(
                device_id=device_id,
                friendly_name=info.friendly_name if info else device_id,
                media=MediaStatus(player_state=PlayerState.UNKNOWN),
                last_updated=datetime.now(),
            )

    # ── Media Control ─────────────────────────────────────────────────────────

    def play_media(
        self,
        device_id: str,
        url: str,
        content_type: str = "video/mp4",
        title: str | None = None,
        thumb: str | None = None,
        subtitles_url: str | None = None,
        subtitles_lang: str = "pt-BR",
    ) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            return False
        try:
            cast.wait(timeout=5)
            mc = cast.media_controller
            kwargs: dict[str, Any] = {
                "url": url,
                "content_type": content_type,
            }
            if title:
                kwargs["title"] = title
            if thumb:
                kwargs["thumb"] = thumb
            if subtitles_url:
                kwargs["subtitles"] = subtitles_url
                kwargs["subtitles_lang"] = subtitles_lang
                kwargs["subtitles_mime"] = "text/vtt"
            mc.play_media(**kwargs)
            mc.block_until_active(timeout=10)
            return True
        except Exception as exc:
            logger.error("play_media failed for %s: %s", device_id, exc)
            return False

    def pause(self, device_id: str) -> bool:
        return self._media_cmd(device_id, "pause")

    def play(self, device_id: str) -> bool:
        return self._media_cmd(device_id, "play")

    def stop(self, device_id: str) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            logger.error("[CMD] stop -> device_id=%s NOT in cache", device_id)
            return False
        try:
            # A generic MediaController.stop() often isn't enough for apps like
            # YouTube (MDX session), which can just re-buffer the same queue
            # instead of going idle. Quitting the running receiver app is the
            # reliable way to fully stop playback for any content type.
            try:
                cast.media_controller.stop()
            except Exception as exc:
                logger.debug("[CMD] stop -> media_controller.stop() failed (continuing): %s", exc)
            cast.quit_app()
            logger.debug("[CMD] stop -> quit_app() sent OK device=%s", device_id)
            return True
        except Exception as exc:
            logger.error("[CMD] stop FAILED device=%s: %s", device_id, exc, exc_info=True)
            return False

    def seek(self, device_id: str, seconds: float) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            return False
        try:
            cast.media_controller.seek(seconds)
            return True
        except Exception as exc:
            logger.error("seek failed for %s: %s", device_id, exc)
            return False

    # ── YouTube ───────────────────────────────────────────────────────────────

    def play_youtube(self, device_id: str, video_id: str) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            logger.error("[YT] device_id=%s NOT in cache", device_id)
            return False
        try:
            logger.debug(
                "[YT] device=%s video=%s | cast.is_idle=%s socket_connected=%s",
                device_id, video_id,
                getattr(cast, 'is_idle', '?'),
                getattr(getattr(cast, 'socket_client', None), 'is_connected', '?'),
            )

            logger.debug("[YT] calling cast.wait(timeout=10)...")
            connected = cast.wait(timeout=10)
            logger.debug("[YT] cast.wait returned: %s | cast.status=%s", connected, cast.status)

            if not cast.status:
                logger.error("[YT] cast.status is None — device not reachable")
                return False

            logger.debug("[YT] current app_id=%s display_name=%s",
                         cast.status.app_id, cast.status.display_name)

            # Reuse existing handler if already registered
            yt = cast.media_controller
            if not isinstance(yt, YouTubeController):
                logger.debug("[YT] registering new YouTubeController")
                yt = YouTubeController()
                cast.register_handler(yt)
            else:
                logger.debug("[YT] reusing existing YouTubeController")

            logger.debug("[YT] calling yt.play_video(%s)...", video_id)
            yt.play_video(video_id)
            logger.info("[YT] play_video sent OK: device=%s video=%s", device_id, video_id)
            return True
        except Exception as exc:
            logger.error("[YT] play_youtube FAILED for %s: %s", device_id, exc, exc_info=True)
            return False

    # ── Web Page (DashCast) ─────────────────────────────────────────────────

    def cast_webpage(self, device_id: str, url: str, force: bool = False, reload_seconds: int = 0) -> bool:
        """Display a web page on the Chromecast using DashCast."""
        from pychromecast.controllers.dashcast import DashCastController
        cast = self._get_cast(device_id)
        if cast is None:
            return False
        try:
            cast.wait(timeout=5)
            dc = DashCastController()
            cast.register_handler(dc)

            sent = threading.Event()

            def _on_sent():
                sent.set()

            dc.load_url(url, force=force, reload_seconds=reload_seconds, callback_function=_on_sent)

            # Wait for DashCast to launch AND the URL message to be delivered (max 15s)
            if not sent.wait(timeout=15):
                logger.warning(
                    "cast_webpage timed out for %s — DashCast app may be unavailable on this device",
                    device_id,
                )
                return False

            logger.info("cast_webpage %s -> %s (OK)", device_id, url)
            return True
        except Exception as exc:
            logger.error("cast_webpage failed for %s: %s", device_id, exc)
            return False

    # ── Volume Control ────────────────────────────────────────────────────────

    def set_volume(self, device_id: str, level: float) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            return False
        try:
            cast.set_volume(max(0.0, min(1.0, level)))
            return True
        except Exception as exc:
            logger.error("set_volume failed for %s: %s", device_id, exc)
            return False

    def set_mute(self, device_id: str, muted: bool) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            return False
        try:
            cast.set_volume_muted(muted)
            return True
        except Exception as exc:
            logger.error("set_mute failed for %s: %s", device_id, exc)
            return False

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_cast(self, device_id: str) -> pychromecast.Chromecast | None:
        with self._lock:
            cast = self._devices.get(device_id)
        if cast is None:
            logger.warning("Device %s not found in cache", device_id)
        return cast

    def _media_cmd(self, device_id: str, cmd: str) -> bool:
        cast = self._get_cast(device_id)
        if cast is None:
            logger.error("[CMD] device_id=%s NOT in cache (cmd=%s)", device_id, cmd)
            return False
        try:
            logger.debug("[CMD] %s -> device=%s | mc.status=%s",
                         cmd, device_id, cast.media_controller.status)
            getattr(cast.media_controller, cmd)()
            logger.debug("[CMD] %s sent OK device=%s", cmd, device_id)
            return True
        except Exception as exc:
            logger.error("[CMD] %s FAILED device=%s: %s", cmd, device_id, exc, exc_info=True)
            return False

    @staticmethod
    def _map_player_state(state: str | None) -> PlayerState:
        mapping = {
            "PLAYING": PlayerState.PLAYING,
            "PAUSED": PlayerState.PAUSED,
            "BUFFERING": PlayerState.BUFFERING,
            "IDLE": PlayerState.IDLE,
        }
        return mapping.get(state or "", PlayerState.UNKNOWN)

    def shutdown(self) -> None:
        self.stop_discovery()
        with self._lock:
            for cast in self._devices.values():
                try:
                    cast.disconnect(timeout=2, blocking=False)
                except Exception:
                    pass
        for zconf in self._scan_zconfs:
            try:
                zconf.close()
            except Exception:
                pass
        self._scan_zconfs.clear()
        logger.info("CastService shutdown complete")
