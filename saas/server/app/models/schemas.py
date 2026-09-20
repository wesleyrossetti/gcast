from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "member"]


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


# ── Organization ──────────────────────────────────────────────────────────────

class OrgOut(BaseModel):
    id:         str
    name:       str
    slug:       str
    created_at: datetime

    model_config = {"from_attributes": True}

class OrgUpdate(BaseModel):
    name: str = Field(min_length=1)


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id:         str
    name:       str | None = None
    email:      str
    role:       str
    created_at: datetime

    model_config = {"from_attributes": True}

class UserRoleUpdate(BaseModel):
    role: Role


# ── Invite ────────────────────────────────────────────────────────────────────

class InviteCreate(BaseModel):
    email: EmailStr
    role:  Role = "member"

class InviteOut(BaseModel):
    id:         str
    email:      str
    role:       str
    invited_by: str | None = None
    expires_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}

class AcceptInviteRequest(BaseModel):
    token:    str
    name:     str
    password: str = Field(min_length=8)


# ── Login audit ───────────────────────────────────────────────────────────────

class LoginAuditOut(BaseModel):
    id:              str
    email_attempted: str
    success:         bool
    reason:          str | None = None
    ip_address:      str | None = None
    created_at:      datetime

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
