from __future__ import annotations

import logging
import os
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.control import router as control_router
from app.api.devices import router as devices_router
from app.api.extras import router as extras_router
from app.api.media import router as media_router
from app.cast_service import CastService
from app.config import API_PORT, DISCOVERY_TIMEOUT, KNOWN_HOSTS_FILE, LOG_LEVEL
from app.history_service import HistoryService
from app.models import ActionType, NotificationType
from app.notification_service import NotificationService
from app.scheduler_service import SchedulerService

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)
# Enable pychromecast socket/protocol debug when LOG_LEVEL=DEBUG
if LOG_LEVEL.upper() == "DEBUG":
    logging.getLogger("pychromecast").setLevel(logging.DEBUG)
    logging.getLogger("pychromecast.socket_client").setLevel(logging.DEBUG)
    logging.getLogger("pychromecast.controllers").setLevel(logging.DEBUG)

# ── Jinja2 templates ──────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
templates.env.globals["static_v"] = str(int(time.time()))

# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    cast_svc = CastService(discovery_timeout=DISCOVERY_TIMEOUT)
    hist_svc = HistoryService()
    notif_svc = NotificationService()
    sched_svc = SchedulerService()

    app.state.cast_service = cast_svc
    app.state.history_service = hist_svc
    app.state.notif_service = notif_svc
    app.state.scheduler_service = sched_svc

    def scheduled_action_callback(entry):
        """Execute a scheduled action via CastService."""
        action = entry.action
        device_id = entry.device_id
        ok = False
        try:
            if action == ActionType.PLAY:
                ok = cast_svc.play(device_id)
            elif action == ActionType.PAUSE:
                ok = cast_svc.pause(device_id)
            elif action == ActionType.STOP:
                ok = cast_svc.stop(device_id)
            elif action == ActionType.VOLUME:
                level = entry.details.get("level", 0.5)
                ok = cast_svc.set_volume(device_id, float(level))
            elif action == ActionType.MUTE:
                ok = cast_svc.set_mute(device_id, muted=True)
            elif action == ActionType.UNMUTE:
                ok = cast_svc.set_mute(device_id, muted=False)
        except Exception as exc:
            logger.error("Scheduled action failed: %s", exc)
            ok = False

        hist_svc.log(
            device_id=device_id,
            action=action,
            details=entry.details,
            success=ok,
            error=None if ok else "Scheduled action failed",
        )
        notif_svc.add(
            message=f"Ação agendada '{action.value}' {'executada' if ok else 'falhou'} no device {device_id}",
            type=NotificationType.SUCCESS if ok else NotificationType.ERROR,
            device_id=device_id,
        )

    sched_svc.start(action_callback=scheduled_action_callback)

    def _on_device_added(info):
        hist_svc.log(
            device_id="system",
            action=ActionType.DISCOVER,
            details={"device": info.friendly_name, "host": info.host},
        )
        notif_svc.add(
            message=f"Dispositivo encontrado: {info.friendly_name} ({info.host})",
            type=NotificationType.SUCCESS,
        )

    def _on_device_removed(info):
        notif_svc.add(
            message=f"Dispositivo saiu da rede: {info.friendly_name}",
            type=NotificationType.WARNING,
        )

    cast_svc.start_discovery(on_added=_on_device_added, on_removed=_on_device_removed)
    cast_svc.set_persistence(KNOWN_HOSTS_FILE)
    logger.info("Application started. Access http://localhost:%s", API_PORT)

    yield

    sched_svc.stop()
    cast_svc.shutdown()
    logger.info("Application shutdown complete.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Chromecast Manager",
    description="Sistema de monitoramento e gerenciamento de Chromecasts na rede local.",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)

# Routers
app.include_router(devices_router)
app.include_router(media_router)
app.include_router(control_router)
app.include_router(extras_router)


# ── Page routes ───────────────────────────────────────────────────────────────
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse(url="/static/favicon.svg")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "active_page": "dashboard"},
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "active_page": "history"},
    )


@app.get("/schedule", response_class=HTMLResponse)
def schedule_page(request: Request):
    return templates.TemplateResponse(
        "schedule.html",
        {"request": request, "active_page": "schedule"},
    )
