from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.models import ActionType, DeviceActionRequest, NotificationType, VolumeRequest
from app.utils import get_cast_service, get_history_service, get_notif_service

router = APIRouter(prefix="/api/control", tags=["control"])


@router.post("/volume")
def set_volume(req: VolumeRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.set_volume(req.device_id, req.level)
    hist.log(req.device_id, ActionType.VOLUME, details={"level": req.level}, success=ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao ajustar volume")
    return {"status": "ok"}


@router.post("/mute")
def mute(req: DeviceActionRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.set_mute(req.device_id, muted=True)
    hist.log(req.device_id, ActionType.MUTE, success=ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao mutar")
    return {"status": "ok"}


@router.post("/unmute")
def unmute(req: DeviceActionRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.set_mute(req.device_id, muted=False)
    hist.log(req.device_id, ActionType.UNMUTE, success=ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao desmutar")
    return {"status": "ok"}
