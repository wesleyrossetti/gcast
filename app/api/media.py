from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models import (
    ActionType,
    CastWebRequest,
    DeviceActionRequest,
    NotificationType,
    PlayMediaRequest,
    PlayYouTubeRequest,
    SeekRequest,
)
from app.utils import get_cast_service, get_history_service, get_notif_service

router = APIRouter(prefix="/api/media", tags=["media"])
logger = logging.getLogger(__name__)


@router.post("/play-youtube")
def play_youtube(req: PlayYouTubeRequest, request: Request):
    logger.debug("[API] play-youtube device=%s video_id=%s", req.device_id, req.video_id)
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)

    ok = svc.play_youtube(req.device_id, req.video_id)
    logger.debug("[API] play-youtube result=%s", ok)
    _record(hist, notif, req.device_id, ActionType.PLAY, ok, {"video_id": req.video_id, "platform": "youtube"})
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao reproduzir YouTube")
    return {"status": "ok"}


@router.post("/cast-web")
def cast_web(req: CastWebRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)

    ok = svc.cast_webpage(req.device_id, req.url, force=req.force, reload_seconds=req.reload_seconds)
    _record(hist, notif, req.device_id, ActionType.PLAY, ok, {"url": req.url, "type": "webpage"})
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao exibir página web")
    return {"status": "ok"}


@router.post("/play-url")
def play_url(req: PlayMediaRequest, request: Request):
    logger.debug("[API] play-url device=%s url=%s type=%s", req.device_id, req.url, req.content_type)
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)

    ok = svc.play_media(
        device_id=req.device_id,
        url=req.url,
        content_type=req.content_type,
        title=req.title,
        thumb=req.thumb,
        subtitles_url=req.subtitles_url,
        subtitles_lang=req.subtitles_lang,
    )
    logger.debug("[API] play-url result=%s", ok)
    _record(hist, notif, req.device_id, ActionType.PLAY, ok, {"url": req.url, "title": req.title})
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao reproduzir mídia")
    return {"status": "ok"}


@router.post("/play")
def play(req: DeviceActionRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.play(req.device_id)
    _record(hist, notif, req.device_id, ActionType.PLAY, ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao retomar reprodução")
    return {"status": "ok"}


@router.post("/pause")
def pause(req: DeviceActionRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.pause(req.device_id)
    _record(hist, notif, req.device_id, ActionType.PAUSE, ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao pausar")
    return {"status": "ok"}


@router.post("/stop")
def stop(req: DeviceActionRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.stop(req.device_id)
    _record(hist, notif, req.device_id, ActionType.STOP, ok)
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao parar")
    return {"status": "ok"}


@router.post("/seek")
def seek(req: SeekRequest, request: Request):
    svc = get_cast_service(request)
    hist = get_history_service(request)
    notif = get_notif_service(request)
    ok = svc.seek(req.device_id, req.seconds)
    _record(hist, notif, req.device_id, ActionType.SEEK, ok, {"seconds": req.seconds})
    if not ok:
        raise HTTPException(status_code=500, detail="Falha ao fazer seek")
    return {"status": "ok"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _record(hist, notif, device_id, action, success, details=None):
    hist.log(device_id, action, details=details or {}, success=success)
    if not success:
        notif.add(
            f"Erro ao executar {action.value} no device {device_id}",
            type=NotificationType.ERROR,
            device_id=device_id,
        )
