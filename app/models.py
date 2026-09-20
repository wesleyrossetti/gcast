from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────


class PlayerState(str, Enum):
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    BUFFERING = "BUFFERING"
    IDLE = "IDLE"
    UNKNOWN = "UNKNOWN"


class ActionType(str, Enum):
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    SEEK = "seek"
    VOLUME = "volume"
    MUTE = "mute"
    UNMUTE = "unmute"
    DISCOVER = "discover"
    CONNECT = "connect"
    DISCONNECT = "disconnect"


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class RecurrenceType(str, Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


# ── Device Models ─────────────────────────────────────────────────────────────


class DeviceInfo(BaseModel):
    device_id: str
    friendly_name: str
    host: str
    port: int
    model_name: str | None = None
    cast_type: str | None = None
    is_connected: bool = False


class MediaStatus(BaseModel):
    player_state: PlayerState = PlayerState.UNKNOWN
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    content_url: str | None = None
    content_type: str | None = None
    current_time: float | None = None
    duration: float | None = None
    thumbnail: str | None = None


class DeviceStatus(BaseModel):
    device_id: str
    friendly_name: str
    is_active_input: bool | None = None
    is_stand_by: bool | None = None
    volume_level: float | None = None
    volume_muted: bool = False
    display_name: str | None = None
    app_id: str | None = None
    media: MediaStatus | None = None
    last_updated: datetime = Field(default_factory=datetime.now)


# ── Request/Response Models ───────────────────────────────────────────────────


class PlayYouTubeRequest(BaseModel):
    device_id: str
    video_id: str  # e.g. "G_8uG1Ot0yo"


class CastWebRequest(BaseModel):
    device_id: str
    url: str
    force: bool = False
    reload_seconds: int = 0


class PlayMediaRequest(BaseModel):
    device_id: str
    url: str
    content_type: str = "video/mp4"
    title: str | None = None
    thumb: str | None = None
    subtitles_url: str | None = None
    subtitles_lang: str = "pt-BR"


class SeekRequest(BaseModel):
    device_id: str
    seconds: float


class VolumeRequest(BaseModel):
    device_id: str
    level: float = Field(ge=0.0, le=1.0)


class DeviceActionRequest(BaseModel):
    device_id: str


# ── History Models ────────────────────────────────────────────────────────────


class HistoryEntry(BaseModel):
    id: str
    device_id: str
    device_name: str | None = None
    action: ActionType
    details: dict[str, Any] = {}
    success: bool = True
    error: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


# ── Notification Models ───────────────────────────────────────────────────────


class Notification(BaseModel):
    id: str
    type: NotificationType = NotificationType.INFO
    message: str
    device_id: str | None = None
    read: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)


# ── Schedule Models ───────────────────────────────────────────────────────────


class ScheduleRequest(BaseModel):
    device_id: str
    action: ActionType
    run_at: datetime
    recurrence: RecurrenceType = RecurrenceType.ONCE
    details: dict[str, Any] = {}


class ScheduleEntry(BaseModel):
    id: str
    device_id: str
    action: ActionType
    run_at: datetime
    recurrence: RecurrenceType = RecurrenceType.ONCE
    details: dict[str, Any] = {}
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_run: datetime | None = None
