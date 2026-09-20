from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models import HistoryEntry, Notification, ScheduleEntry, ScheduleRequest
from app.utils import get_cast_service, get_history_service, get_notif_service, get_scheduler_service

router = APIRouter(prefix="/api", tags=["history & notifications & schedules"])


# ── Debug ─────────────────────────────────────────────────────────────────────

@router.get("/debug/cast/{device_id}", tags=["debug"])
def debug_cast(device_id: str, request: Request):
    """Return raw connection info for a cast device (for troubleshooting)."""
    svc = get_cast_service(request)
    cast = svc._devices.get(device_id)
    if cast is None:
        return JSONResponse({"error": "device not in cache", "device_id": device_id}, status_code=404)

    sc = getattr(cast, "socket_client", None)
    try:
        connected = cast.wait(timeout=5)
        cs = cast.status
        ms = cast.media_controller.status
    except Exception as exc:
        return JSONResponse({"error": str(exc), "device_id": device_id}, status_code=500)

    return {
        "device_id": device_id,
        "host": cast.cast_info.host,
        "port": cast.cast_info.port,
        "friendly_name": cast.cast_info.friendly_name,
        "wait_returned": connected,
        "socket_connected": getattr(sc, "is_connected", None),
        "cast_status": {
            "app_id": cs.app_id if cs else None,
            "display_name": cs.display_name if cs else None,
            "is_stand_by": cs.is_stand_by if cs else None,
            "volume_level": cs.volume_level if cs else None,
        } if cs else None,
        "media_player_state": ms.player_state if ms else None,
        "media_title": ms.title if ms else None,
    }


# ── History ───────────────────────────────────────────────────────────────────


@router.get("/history", response_model=list[HistoryEntry])
def get_history(request: Request, device_id: str | None = None, limit: int = 50):
    svc = get_history_service(request)
    return svc.get_history(device_id=device_id, limit=min(limit, 200))


# ── Notifications ─────────────────────────────────────────────────────────────


@router.get("/notifications", response_model=list[Notification])
def get_notifications(request: Request, unread_only: bool = False):
    svc = get_notif_service(request)
    return svc.get_all(unread_only=unread_only)


@router.get("/notifications/count")
def notification_count(request: Request):
    svc = get_notif_service(request)
    return {"count": svc.unread_count()}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, request: Request):
    svc = get_notif_service(request)
    svc.mark_read(notification_id)
    return {"status": "ok"}


@router.post("/notifications/read-all")
def mark_all_read(request: Request):
    svc = get_notif_service(request)
    svc.mark_all_read()
    return {"status": "ok"}


# ── Schedules ─────────────────────────────────────────────────────────────────


@router.get("/schedule", response_model=list[ScheduleEntry])
def list_schedules(request: Request):
    svc = get_scheduler_service(request)
    return svc.list_schedules()


@router.post("/schedule", response_model=ScheduleEntry)
def create_schedule(req: ScheduleRequest, request: Request):
    svc = get_scheduler_service(request)
    return svc.create(req)


@router.delete("/schedule/{schedule_id}")
def delete_schedule(schedule_id: str, request: Request):
    svc = get_scheduler_service(request)
    ok = svc.delete(schedule_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agendamento não encontrado")
    return {"status": "ok"}
