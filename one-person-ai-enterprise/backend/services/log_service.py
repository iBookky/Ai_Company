"""
log_service.py — Central Logging Service
บันทึก Thought Process ของ Agents ทุกตัวลง JSONL file + in-memory cache
"""

import json
import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
from collections import deque

from backend.models.schemas import LogEntry, LogCreate, LogLevel

BASE_DIR = Path(__file__).parent.parent.parent
LOG_FILE = BASE_DIR / "logs" / "system.jsonl"
MAX_MEMORY_ENTRIES = 500

# In-memory log store สำหรับ real-time streaming
_log_cache: deque[LogEntry] = deque(maxlen=MAX_MEMORY_ENTRIES)
_ws_subscribers: list[Callable] = []


def _ensure_log_file():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.touch()


def write_log(data: LogCreate) -> LogEntry:
    """บันทึก log entry"""
    _ensure_log_file()

    entry = LogEntry(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        agent_id=data.agent_id,
        agent_name=data.agent_name,
        level=data.level,
        message=data.message,
        details=data.details,
        thought_process=data.thought_process,
    )

    # เขียนลงไฟล์
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")

    # เก็บใน memory
    _log_cache.append(entry)

    # broadcast ไปยัง WebSocket subscribers
    asyncio.create_task(_broadcast_log(entry))

    return entry


async def _broadcast_log(entry: LogEntry):
    """ส่ง log entry ไปยัง WebSocket clients ทุกคน"""
    disconnected = []
    for callback in _ws_subscribers:
        try:
            await callback(entry)
        except Exception:
            disconnected.append(callback)
    for cb in disconnected:
        _ws_subscribers.remove(cb)


def subscribe_logs(callback: Callable):
    """ลงทะเบียน WebSocket callback"""
    _ws_subscribers.append(callback)


def unsubscribe_logs(callback: Callable):
    """ยกเลิกการลงทะเบียน"""
    if callback in _ws_subscribers:
        _ws_subscribers.remove(callback)


def get_logs(
    agent_id: Optional[str] = None,
    level: Optional[LogLevel] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> list[LogEntry]:
    """ดึง logs จาก memory cache พร้อม filter"""
    logs = list(_log_cache)

    # โหลดจากไฟล์ถ้า cache ว่าง
    if not logs:
        logs = _load_from_file(limit * 2)

    # Apply filters
    if agent_id:
        logs = [l for l in logs if l.agent_id == agent_id]
    if level:
        logs = [l for l in logs if l.level == level]
    if search:
        search_lower = search.lower()
        logs = [l for l in logs if search_lower in l.message.lower()]

    # เรียงจากใหม่ไปเก่า
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    return logs[:limit]


def _load_from_file(limit: int = 200) -> list[LogEntry]:
    """โหลด logs จากไฟล์"""
    _ensure_log_file()
    entries = []
    try:
        lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
        for line in lines[-limit:]:
            if line.strip():
                try:
                    entries.append(LogEntry.model_validate_json(line))
                except Exception:
                    pass
    except Exception:
        pass
    return entries


def load_logs_to_cache():
    """โหลด logs จากไฟล์เข้า cache ตอนเริ่มต้น"""
    entries = _load_from_file(MAX_MEMORY_ENTRIES)
    for entry in entries:
        _log_cache.append(entry)
