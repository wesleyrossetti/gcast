from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from app.models import ActionType, DeviceActionRequest, DeviceInfo, DeviceStatus
from app.utils import get_cast_service, get_history_service, get_notif_service
from app.models import NotificationType

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceInfo])
def list_devices(request: Request):
    svc = get_cast_service(request)
    return svc.list_devices()


@router.post("/discover", response_model=list[DeviceInfo])
def discover(request: Request, known_hosts: list[str] = Body(default=[])):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    devices = svc.discover(known_hosts=known_hosts)
    hist.log("system", ActionType.DISCOVER, details={"count": len(devices)})
    notif.add(
        f"Descoberta concluída: {len(devices)} device(s) encontrado(s)",
        type=NotificationType.SUCCESS,
    )
    return devices


@router.get("/{device_id}/status", response_model=DeviceStatus)
def device_status(device_id: str, request: Request):
    svc = get_cast_service(request)
    status = svc.get_status(device_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Device não encontrado")
    return status
