from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str
    email:    EmailStr
    password: str = Field(min_length=8)
    org_name: str

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── Agent ─────────────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str

class AgentOut(BaseModel):
    id:         str
    name:       str
    org_id:     str
    is_online:  bool = False
    last_seen:  datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

class AgentCreated(AgentOut):
    token: str   # shown only once on creation


# ── Device ────────────────────────────────────────────────────────────────────

class DeviceOut(BaseModel):
    device_uuid:   str
    friendly_name: str | None = None
    host:          str | None = None
    model_name:    str | None = None
    agent_id:      str
    is_online:     bool = False

    model_config = {"from_attributes": True}

class DeviceStatus(BaseModel):
    device_uuid:   str
    friendly_name: str | None = None
    host:          str | None = None
    model_name:    str | None = None
    agent_id:      str
    is_online:     bool = False
    volume_level:  float | None = None
    volume_muted:  bool = False
    app_id:        str | None = None
    display_name:  str | None = None
    player_state:  str | None = None
    title:         str | None = None
    artist:        str | None = None
    current_time:  float | None = None
    duration:      float | None = None
    thumbnail:     str | None = None


# ── Commands ──────────────────────────────────────────────────────────────────

class DeviceActionRequest(BaseModel):
    device_uuid: str

class PlayMediaRequest(BaseModel):
    device_uuid:  str
    url:          str
    content_type: str = "video/mp4"
    title:        str | None = None
    thumb:        str | None = None

class PlayYouTubeRequest(BaseModel):
    device_uuid: str
    video_id:    str

class SeekRequest(BaseModel):
    device_uuid: str
    seconds:     float

class VolumeRequest(BaseModel):
    device_uuid: str
    level:       float = Field(ge=0.0, le=1.0)


# ── History ───────────────────────────────────────────────────────────────────

class HistoryEntryOut(BaseModel):
    id:          str
    device_uuid: str | None = None
    device_name: str | None = None
    action:      str
    details:     dict[str, Any] = {}
    success:     bool
    error:       str | None = None
    timestamp:   datetime

    model_config = {"from_attributes": True}


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    device_uuid: str
    action:      str
    run_at:      datetime
    recurrence:  str = "once"
    details:     dict[str, Any] = {}

class ScheduleOut(BaseModel):
    id:          str
    device_uuid: str
    action:      str
    run_at:      datetime
    recurrence:  str
    details:     dict[str, Any] = {}
    enabled:     bool
    created_at:  datetime
    last_run:    datetime | None = None

    model_config = {"from_attributes": True}
