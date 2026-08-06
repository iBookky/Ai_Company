from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


# ─── Enums ───────────────────────────────────────────────────────────────────

class ModelChoice(str, Enum):
    GEMINI_PRO = "gemini-1.5-pro"
    GEMINI_FLASH = "gemini-1.5-flash"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_HAIKU = "claude-3-haiku-20240307"


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"
    DEBUG = "DEBUG"


class DraftCategory(str, Enum):
    PROPOSALS = "proposals"
    ACCOUNTING = "accounting"
    CONTRACTS = "contracts"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    AWAITING_OWNER = "awaiting_owner"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    FORWARDED = "forwarded"


# ─── Agent Schemas ────────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="ชื่อตำแหน่ง Agent")
    department: str = Field(..., min_length=1, description="สังกัดแผนก เช่น 03_sales")
    parent_department: Optional[str] = Field(None, description="สังกัดหัวหน้าทีม")
    model: str = Field("gemini-1.5-flash", description="โมเดล LLM ที่ใช้")
    temperature: float = Field(0.5, ge=0.0, le=1.0, description="ค่า Temperature")
    identity: str = Field(..., min_length=10, description="System Identity/Role")
    skill: str = Field(..., min_length=10, description="Skills และ Instructions")
    role: Optional[str] = Field(None, description="Role identifier")
    ops_chat_id: Optional[str] = Field("", description="Telegram Ops Chat ID ประจำแผนก")


class AgentRead(BaseModel):
    id: str
    name: str
    role: str
    model: str
    temperature: float
    department: str
    ops_chat_id: str = ""
    has_identity: bool
    has_skill: bool
    identity_preview: str
    skill_preview: str
    created_at: str
    path: str


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=1.0)
    identity: Optional[str] = None
    skill: Optional[str] = None
    ops_chat_id: Optional[str] = None


class AgentDetail(AgentRead):
    identity: str
    skill: str


# ─── Log Schemas ──────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    agent_id: str
    agent_name: str
    level: LogLevel
    message: str
    details: Optional[dict] = None
    thought_process: Optional[str] = None


class LogCreate(BaseModel):
    agent_id: str
    agent_name: str
    level: LogLevel
    message: str
    details: Optional[dict] = None
    thought_process: Optional[str] = None


class LogFilter(BaseModel):
    agent_id: Optional[str] = None
    level: Optional[LogLevel] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    search: Optional[str] = None
    limit: int = Field(100, ge=1, le=1000)


# ─── Draft Schemas ────────────────────────────────────────────────────────────

class DraftFile(BaseModel):
    id: str
    name: str
    category: str
    size_bytes: int
    content_type: str
    uploaded_at: datetime
    path: str
    description: Optional[str] = None


class DraftPrintRequest(BaseModel):
    draft_id: str
    copies: int = Field(1, ge=1, le=10)
    paper_size: str = Field("A4")


# ─── Skype Schemas ────────────────────────────────────────────────────────────

class SkypeMessage(BaseModel):
    type: str
    id: str
    timestamp: str
    channelId: str
    from_: Optional[dict] = Field(None, alias="from")
    conversation: Optional[dict] = None
    recipient: Optional[dict] = None
    text: Optional[str] = None
    attachments: Optional[list] = None

    class Config:
        populate_by_name = True


class VerificationRequest(BaseModel):
    original_message: str
    summary: str
    agent_id: str
    room_id: str
    status: VerificationStatus = VerificationStatus.PENDING


class SkypeWebhookPayload(BaseModel):
    type: str
    id: Optional[str] = None
    timestamp: Optional[str] = None
    channelId: Optional[str] = None
    text: Optional[str] = None
    from_data: Optional[dict] = None
    conversation: Optional[dict] = None


# ─── Telegram Room Schemas ───────────────────────────────────────────────────

class DepartmentRoomCreate(BaseModel):
    id: Optional[str] = Field(None, description="รหัสแผนก เช่น 08_hr (สร้างให้อัตโนมัติถ้าเว้นว่าง)")
    name: str = Field(..., min_length=1, max_length=100, description="ชื่อแผนก เช่น ทีมการตลาด AI")
    pm_name: Optional[str] = Field("", description="ชื่อ PM หัวหน้าแผนก เช่น PM ลิซ่า")
    bot_token: Optional[str] = Field("", description="Telegram Bot Token ของ PM หัวหน้าทีมประจำแผนกนี้สำหรับคุยตรง 1-on-1")




# ─── Settings Schemas ─────────────────────────────────────────────────────────

class AppSettings(BaseModel):
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_owner_id: str = ""
    telegram_owner_direct_chat_id: str = ""
    telegram_exec_chat_id: str = ""
    telegram_admin_chat_id: str = ""
    telegram_ops_chat_id: str = ""
    telegram_ops_chat_ids: dict[str, str] = {}
    default_model: str = "gemini-1.5-flash"
    gemini_fallback_models: str = ""
    available_models: str = ""
    gemini_configured: bool = False
    anthropic_configured: bool = False
    telegram_configured: bool = False


class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_owner_id: Optional[str] = None
    telegram_owner_direct_chat_id: Optional[str] = None
    telegram_exec_chat_id: Optional[str] = None
    telegram_admin_chat_id: Optional[str] = None
    telegram_ops_chat_id: Optional[str] = None
    telegram_ops_chat_ids: Optional[dict[str, str]] = None
    default_model: Optional[str] = None
    gemini_fallback_models: Optional[str] = None
    available_models: Optional[str] = None




# ─── Generic Response ─────────────────────────────────────────────────────────

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None
