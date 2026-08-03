"""
skype.py — Router สำหรับ Skype Webhook + Simulation endpoint
"""

from fastapi import APIRouter, Request, HTTPException
from backend.services import skype_service
from backend.models.schemas import ApiResponse

router = APIRouter(prefix="/api/skype", tags=["Skype"])


@router.post("/webhook")
async def skype_webhook(request: Request):
    """
    รับ Webhook จาก Microsoft Bot Framework
    Microsoft จะส่ง POST ที่ URL นี้เมื่อมีข้อความใหม่ใน Skype
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    result = await skype_service.handle_webhook(payload)
    return result


@router.post("/simulate")
async def simulate_message(request: Request):
    """
    จำลองการส่งข้อความจาก Owner (สำหรับทดสอบโดยไม่ต้อง connect Skype จริง)
    Body: { "text": "คำสั่งที่ต้องการทดสอบ", "sender": "owner" }
    """
    body = await request.json()
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="กรุณาระบุ text")

    fake_payload = {
        "type": "message",
        "id": "sim_001",
        "timestamp": "2024-01-01T00:00:00Z",
        "channelId": "skype",
        "from": {"id": skype_service.SKYPE_OWNER_ID or "owner_sim", "name": "Owner"},
        "conversation": {"id": "sim_conv_001"},
        "text": text,
    }

    result = await skype_service.handle_webhook(fake_payload)
    return {"simulated": True, "result": result}


@router.get("/verifications")
async def get_pending_verifications():
    """ดึงรายการ verification ที่รอ Owner ยืนยัน"""
    return skype_service.get_pending_verifications()


@router.post("/verify/{verification_id}")
async def confirm_verification(verification_id: str, request: Request):
    """
    Owner กดยืนยัน/ปฏิเสธผ่าน Dashboard
    Body: { "confirmed": true }
    """
    body = await request.json()
    confirmed = body.get("confirmed", False)
    result = await skype_service.owner_confirm(verification_id, confirmed)
    return result


@router.get("/rooms")
async def get_rooms():
    """ดึงข้อมูลห้อง Skype ที่กำหนด"""
    import os
    return {
        "admin_room": {
            "id": os.getenv("SKYPE_ADMIN_ROOM_ID", ""),
            "name": "ห้องบริหารรวม",
            "participants": ["Owner", "เลขา AI", "PM AI"],
            "configured": bool(os.getenv("SKYPE_ADMIN_ROOM_ID")),
        },
        "ops_room": {
            "id": os.getenv("SKYPE_OPS_ROOM_ID", ""),
            "name": "ห้องปฏิบัติการ",
            "participants": ["PM AI", "ลูกน้อง AI"],
            "configured": bool(os.getenv("SKYPE_OPS_ROOM_ID")),
        },
    }
