"""
skype_service.py — Dual-Verification Loop & Room Integration
ระบบคัดกรองและทวนคำสั่งผ่าน Skype
"""

import os
import json
import httpx
import asyncio
from typing import Optional
from datetime import datetime
from pathlib import Path

from backend.models.schemas import VerificationStatus
from backend.services import log_service
from backend.models.schemas import LogCreate, LogLevel

SKYPE_APP_ID = os.getenv("SKYPE_APP_ID", "")
SKYPE_APP_PASSWORD = os.getenv("SKYPE_APP_PASSWORD", "")
SKYPE_ADMIN_ROOM_ID = os.getenv("SKYPE_ADMIN_ROOM_ID", "")
SKYPE_OPS_ROOM_ID = os.getenv("SKYPE_OPS_ROOM_ID", "")
SKYPE_OWNER_ID = os.getenv("SKYPE_OWNER_ID", "")

# Token cache
_bot_token: Optional[str] = None
_token_expires_at: Optional[datetime] = None

# Pending verifications ที่รอ Owner ยืนยัน
_pending_verifications: dict[str, dict] = {}


# ─── Bot Token Management ─────────────────────────────────────────────────────

async def _get_bot_token() -> Optional[str]:
    """ดึง Bot Access Token จาก Microsoft"""
    global _bot_token, _token_expires_at

    if _bot_token and _token_expires_at and datetime.now() < _token_expires_at:
        return _bot_token

    if not SKYPE_APP_ID or not SKYPE_APP_PASSWORD:
        return None

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": SKYPE_APP_ID,
                    "client_secret": SKYPE_APP_PASSWORD,
                    "scope": "https://api.botframework.com/.default",
                },
            )
            resp.raise_for_status()
            token_data = resp.json()
            _bot_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            from datetime import timedelta
            _token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)
            return _bot_token
        except Exception as e:
            _log("system", "Skype Bot", LogLevel.ERROR, f"ไม่สามารถดึง Bot Token: {e}")
            return None


async def send_message(room_id: str, text: str) -> bool:
    """ส่งข้อความไปยังห้อง Skype"""
    token = await _get_bot_token()
    if not token:
        _log("system", "Skype Bot", LogLevel.WARNING,
             f"ข้ามการส่งข้อความ (ไม่มี token): {text[:50]}")
        return False

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"https://smba.trafficmanager.net/apis/v3/conversations/{room_id}/activities",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"type": "message", "text": text},
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            _log("system", "Skype Bot", LogLevel.ERROR, f"ส่งข้อความไม่สำเร็จ: {e}")
            return False


# ─── Dual-Verification Loop ───────────────────────────────────────────────────

async def secretary_intercept(owner_message: str, conversation_id: str) -> dict:
    """
    เลขา AI ดักจับข้อความจาก Owner → สรุป → ทวนกลับเพื่อยืนยัน
    """
    from backend.services.llm_service import get_llm_for_agent

    _log("01_secretary", "เลขา AI", LogLevel.INFO,
         f"รับข้อความจาก Owner: {owner_message[:100]}")

    # เรียก LLM เพื่อสรุปคำสั่ง
    llm, system_instruction = await get_llm_for_agent("01_secretary")

    summarize_prompt = f"""
Owner ส่งข้อความต่อไปนี้มา:
"{owner_message}"

กรุณาสรุปและทวนคำสั่งในรูปแบบ:
📋 สรุปคำสั่งที่ได้รับ:
• เป้าหมาย: [สรุปเป้าหมายหลัก]
• สิ่งที่ต้องทำ: [รายการงาน]
• Deadline: [ถ้ามี หรือ "ไม่ระบุ"]
• ทรัพยากร/งบประมาณ: [ถ้ามี]

✅ ยืนยันถูกต้องไหมครับ? (พิมพ์ "ใช่" เพื่อดำเนินการต่อ)
"""

    summary = await llm.generate(system_instruction, summarize_prompt)

    # เก็บ pending verification
    verification_id = f"verify_{conversation_id}_{int(datetime.now().timestamp())}"
    _pending_verifications[verification_id] = {
        "original_message": owner_message,
        "summary": summary,
        "status": VerificationStatus.AWAITING_OWNER,
        "created_at": datetime.now().isoformat(),
        "conversation_id": conversation_id,
    }

    # ส่งทวนกลับไปใน Admin Room
    await send_message(SKYPE_ADMIN_ROOM_ID, summary)

    _log("01_secretary", "เลขา AI", LogLevel.INFO,
         f"ส่งสรุปทวนคำสั่งแล้ว รอการยืนยันจาก Owner (ID: {verification_id})")

    return {
        "verification_id": verification_id,
        "summary": summary,
        "status": VerificationStatus.AWAITING_OWNER,
    }


async def owner_confirm(verification_id: str, confirmed: bool) -> dict:
    """
    เมื่อ Owner พิมพ์ยืนยัน → ส่งต่องานให้ PM หรือยกเลิก
    """
    if verification_id not in _pending_verifications:
        return {"error": "ไม่พบ verification นี้"}

    verification = _pending_verifications[verification_id]

    if not confirmed:
        verification["status"] = VerificationStatus.REJECTED
        _log("01_secretary", "เลขา AI", LogLevel.INFO, "Owner ยกเลิกคำสั่งแล้ว")
        await send_message(SKYPE_ADMIN_ROOM_ID, "⚠️ คำสั่งถูกยกเลิกโดย Owner")
        return {"status": "cancelled"}

    verification["status"] = VerificationStatus.CONFIRMED
    _log("01_secretary", "เลขา AI", LogLevel.SUCCESS,
         "Owner ยืนยันแล้ว กำลังส่งต่อให้ PM")

    # ส่งต่อให้ PM
    result = await pm_receive_task(verification["original_message"], verification["summary"])
    verification["status"] = VerificationStatus.FORWARDED

    return {"status": "forwarded", "pm_plan": result}


async def pm_receive_task(original_task: str, secretary_summary: str) -> dict:
    """
    PM AI รับงาน → คำนวณงบประมาณ/เวลา → ทวนแผนงานให้ Owner อนุมัติ
    """
    from backend.services.llm_service import LLMService

    _log("pm_agent", "Project Manager AI", LogLevel.INFO,
         "รับงานจากเลขา กำลังวางแผน...")

    # ใช้ Gemini Pro สำหรับ PM
    llm = LLMService(model="gemini-1.5-pro", temperature=0.4)

    pm_prompt = f"""
คุณคือ Project Manager AI ที่เพิ่งได้รับงานจากเลขา ดังนี้:

สรุปจากเลขา:
{secretary_summary}

งานต้นฉบับ:
{original_task}

กรุณาสร้าง Project Plan ดังนี้:

📊 แผนงานโครงการ
━━━━━━━━━━━━━━━━━━━━━━━━━
📌 ภาพรวมงาน: [สรุปงาน 1-2 ประโยค]

📅 Timeline:
• วันที่เริ่มต้น: [วันนี้]
• ขั้นตอน: [รายการขั้นตอนพร้อมระยะเวลา]
• วันที่เสร็จสิ้น (ประมาณ): [วันที่]

💰 ประมาณการค่าใช้จ่าย (Token Cost):
• จำนวน LLM Calls: [ประมาณ]
• Token ที่ใช้ (ประมาณ): [จำนวน]
• ค่าใช้จ่ายโดยประมาณ: [USD]

👥 การมอบหมายงาน:
• [ชื่อ Agent]: [งานที่ได้รับ]

✅ รอการอนุมัติจาก Owner เพื่อเริ่มดำเนินการ (พิมพ์ "อนุมัติ")
"""

    plan = await llm.generate(
        "คุณคือ Project Manager AI ที่มีความเชี่ยวชาญในการวางแผนโครงการ",
        pm_prompt
    )

    # ส่งแผนงานไปในห้องบริหาร
    await send_message(SKYPE_ADMIN_ROOM_ID, plan)

    _log("pm_agent", "Project Manager AI", LogLevel.INFO,
         "ส่งแผนงานให้ Owner อนุมัติแล้ว")

    return {"plan": plan, "status": "awaiting_approval"}


async def pm_dispatch_to_ops(plan: str) -> bool:
    """
    เมื่อ Owner อนุมัติแล้ว → PM กระจายงานลงห้องปฏิบัติการ
    """
    dispatch_message = f"🚀 เริ่มดำเนินงานตามแผน:\n\n{plan}"
    success = await send_message(SKYPE_OPS_ROOM_ID, dispatch_message)

    _log("pm_agent", "Project Manager AI",
         LogLevel.SUCCESS if success else LogLevel.ERROR,
         "กระจายงานลงห้องปฏิบัติการ" if success else "ไม่สามารถกระจายงานได้")

    return success


# ─── Webhook Handler ──────────────────────────────────────────────────────────

async def handle_webhook(payload: dict) -> dict:
    """
    รับ Webhook จาก Skype Bot Framework แล้วส่งต่อให้ Logic ที่เหมาะสม
    """
    msg_type = payload.get("type", "")
    text = payload.get("text", "").strip()
    from_data = payload.get("from", {})
    sender_id = from_data.get("id", "")
    conversation = payload.get("conversation", {})
    conv_id = conversation.get("id", "")

    if msg_type != "message" or not text:
        return {"status": "ignored"}

    is_owner = sender_id == SKYPE_OWNER_ID or SKYPE_OWNER_ID == ""

    # ตรวจสอบว่าเป็นการยืนยัน
    confirm_keywords = ["ใช่", "yes", "ยืนยัน", "confirm", "ok", "โอเค"]
    reject_keywords = ["ไม่", "no", "ยกเลิก", "cancel"]
    approve_keywords = ["อนุมัติ", "approve", "approved"]

    # ตรวจสอบ pending verifications
    if is_owner and _pending_verifications:
        latest_verification_id = list(_pending_verifications.keys())[-1]
        latest = _pending_verifications[latest_verification_id]

        if latest["status"] == VerificationStatus.AWAITING_OWNER:
            if any(kw in text.lower() for kw in confirm_keywords):
                result = await owner_confirm(latest_verification_id, True)
                return {"status": "confirmed", "result": result}
            elif any(kw in text.lower() for kw in reject_keywords):
                result = await owner_confirm(latest_verification_id, False)
                return {"status": "rejected"}
            elif any(kw in text.lower() for kw in approve_keywords):
                # Owner อนุมัติแผน PM
                await pm_dispatch_to_ops(latest.get("summary", ""))
                return {"status": "approved_and_dispatched"}

    # ถ้าเป็นข้อความใหม่จาก Owner → Secretary intercept
    if is_owner:
        result = await secretary_intercept(text, conv_id)
        return {"status": "intercepted", "verification_id": result["verification_id"]}

    return {"status": "no_action"}


def get_pending_verifications() -> list[dict]:
    """ดึงรายการ verification ที่รออยู่"""
    return [
        {"id": vid, **data}
        for vid, data in _pending_verifications.items()
    ]


# ─── Helper ───────────────────────────────────────────────────────────────────

def _log(agent_id: str, agent_name: str, level: LogLevel, message: str):
    """บันทึก log สำหรับ Skype operations"""
    try:
        log_service.write_log(LogCreate(
            agent_id=agent_id,
            agent_name=agent_name,
            level=level,
            message=message,
        ))
    except Exception:
        pass
