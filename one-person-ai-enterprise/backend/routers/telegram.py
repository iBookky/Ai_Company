"""
telegram.py — Router สำหรับ Telegram Webhook, Simulation & Room Management
"""

from fastapi import APIRouter, Request, HTTPException
from typing import List, Dict, Optional
from pydantic import BaseModel

from backend.services import telegram_service
from backend.models.schemas import DepartmentRoomCreate

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


class SimulateRequest(BaseModel):
    text: str


class VerifyConfirmRequest(BaseModel):
    confirmed: bool


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Webhook สำหรับรับข้อความจาก Telegram Bot API"""
    try:
        payload = await request.json()
        result = await telegram_service.handle_webhook(payload)
        return {"status": "ok", "detail": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/rooms")
async def get_telegram_rooms():
    """ดูสถานะการตั้งค่า Telegram Rooms (Direct, Exec Board & Department Rooms)"""
    return telegram_service.get_room_status()


@router.post("/rooms")
async def create_department_room(req: DepartmentRoomCreate):
    """สร้างห้องทำงานแผนกใหม่ (สร้างโฟลเดอร์แผนก + คอนฟิก)"""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุชื่อแผนก")

    room = telegram_service.create_department_room(
        name=req.name.strip(),
        chat_id=req.chat_id.strip() if req.chat_id else "",
        pm_name=req.pm_name.strip() if req.pm_name else "",
        dept_id=req.id.strip() if req.id else None
    )
    return {"status": "success", "message": f"สร้างห้องทำงานแผนก '{req.name}' เรียบร้อย", "room": room}


@router.delete("/rooms/{dept_id}")
async def delete_department_room(dept_id: str):
    """ยุบแผนก / ลบห้องทำงานแผนก"""
    success = telegram_service.delete_department_room(dept_id)
    if not success:
        raise HTTPException(status_code=404, detail="ไม่พบห้องแผนกนี้")
    return {"status": "success", "message": f"ยุบแผนก {dept_id} และลบห้องทำงานเรียบร้อย"}


@router.get("/verifications")
async def get_verifications():
    """ดูรายการคำสั่งรอยืนยันทั้งหมด"""
    return telegram_service.get_verifications()


@router.post("/verify/{verification_id}")
async def confirm_verification(verification_id: str, req: VerifyConfirmRequest):
    """อนุมัติหรือปฏิเสธคำสั่งจาก Dashboard UI"""
    pending = telegram_service._pending_verifications.get(verification_id)
    if not pending:
        raise HTTPException(status_code=404, detail="ไม่พบรายการรอยืนยันนี้")

    if req.confirmed:
        chat_id = pending.get("chat_id", "")
        sender_name = pending.get("sender_name", "Owner")
        result = await telegram_service._process_confirmation(chat_id, sender_name)
        return {"status": "confirmed", "result": result}
    else:
        pending["status"] = "rejected"
        return {"status": "rejected", "id": verification_id}


@router.post("/simulate")
async def simulate_message(req: SimulateRequest):
    """ส่งคำสั่งจำลองจาก Owner"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุข้อความ")
    result = await telegram_service.simulate_owner_message(req.text)
    return result
