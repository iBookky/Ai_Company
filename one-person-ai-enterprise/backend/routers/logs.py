"""
logs.py — Router สำหรับ Log API + WebSocket real-time streaming
"""

import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from backend.models.schemas import LogCreate, LogEntry, LogLevel
from backend.services import log_service

router = APIRouter(prefix="/api/logs", tags=["Logs"])


@router.get("", response_model=list[LogEntry])
async def get_logs(
    agent_id: Optional[str] = Query(None),
    level: Optional[LogLevel] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    """ดึง logs พร้อม filter"""
    return log_service.get_logs(
        agent_id=agent_id,
        level=level,
        search=search,
        limit=limit,
    )


@router.post("", response_model=LogEntry, status_code=201)
async def create_log(data: LogCreate):
    """บันทึก log entry ใหม่"""
    return log_service.write_log(data)


@router.websocket("/ws")
async def logs_websocket(websocket: WebSocket):
    """
    WebSocket endpoint สำหรับ real-time log streaming
    Client เชื่อมต่อได้ที่ ws://localhost:8000/api/logs/ws
    """
    await websocket.accept()

    async def send_to_client(entry: LogEntry):
        try:
            await websocket.send_text(entry.model_dump_json())
        except Exception:
            pass

    log_service.subscribe_logs(send_to_client)

    # ส่ง logs ล่าสุด 50 รายการให้ client ตอน connect
    recent_logs = log_service.get_logs(limit=50)
    for log_entry in reversed(recent_logs):
        await websocket.send_text(log_entry.model_dump_json())

    try:
        while True:
            # รอข้อความจาก client (keep-alive ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        log_service.unsubscribe_logs(send_to_client)
