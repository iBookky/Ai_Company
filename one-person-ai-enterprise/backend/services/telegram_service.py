"""
telegram_service.py — Clean Room Architecture for Telegram Integration

โครงสร้าง 3 รูปแบบหลัก:
1. Direct Chat (1-on-1): Owner ↔ เลขา AI (คุยส่วนตัวสัพเพเหระ/ปรึกษาได้ทุกเรื่อง จนกว่าจะสั่งงาน)
2. Executive Room (ห้องประชุมผู้บริหาร): Owner + เลขา AI + PM หัวหน้าทุกแผนก
3. Department Working Rooms (ห้องทำงานแต่ละแผนก): Owner + PM แต่ละทีม + ทีม AI ลูกน้อง
"""

import os
import json
import uuid
import shutil
import logging
import asyncio
from pathlib import Path

from typing import Dict, List, Optional
from datetime import datetime, timezone
import httpx

from backend.services.log_service import write_log
from backend.models.schemas import LogCreate, LogLevel

logger = logging.getLogger("telegram_service")

BASE_DIR = Path(__file__).parent.parent.parent
DEPARTMENTS_DIR = BASE_DIR / "departments"

# ─── Environment Credentials ─────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "")

# 1. Direct Chat (Owner ↔ เลขา AI)
TELEGRAM_OWNER_DIRECT_CHAT_ID = os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")

# 2. Executive Boardroom (ห้องประชุมผู้บริหาร: Owner + เลขา + PMs)
TELEGRAM_EXEC_CHAT_ID = os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

# 3. Department Working Rooms (ห้องทำงานแต่ละแผนก)
TELEGRAM_OPS_CHAT_ID = os.getenv("TELEGRAM_OPS_CHAT_ID", "")
TELEGRAM_OPS_CHAT_IDS: Dict[str, str] = {}

_env_ops_json = os.getenv("TELEGRAM_OPS_CHAT_IDS", "")
if _env_ops_json:
    try:
        TELEGRAM_OPS_CHAT_IDS = json.loads(_env_ops_json)
    except Exception:
        pass

# In-memory storage for active verifications & conversation history
_pending_verifications: Dict[str, dict] = {}
_chat_histories: Dict[str, List[dict]] = {}


# ─── Telegram Messaging Helpers ───────────────────────────────────────────────

async def send_telegram_message(chat_id: str, text: str) -> bool:
    """ส่งข้อความไปยัง Telegram Chat"""
    token = get_bot_token()
    if not token or not chat_id:

        logger.warning(f"Telegram Bot Token หรือ Chat ID ({chat_id}) ไม่ถูกตั้งค่า")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API Error: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        logger.error(f"ส่งข้อความ Telegram ไม่สำเร็จ: {e}")
        return False


async def send_direct_to_secretary(text: str) -> bool:
    """ส่งข้อความคุยส่วนตัว 1-on-1 (Owner ↔ เลขา AI)"""
    chat_id = TELEGRAM_OWNER_DIRECT_CHAT_ID or TELEGRAM_EXEC_CHAT_ID
    return await send_telegram_message(chat_id, text)


async def send_to_executive_board(text: str) -> bool:
    """ส่งข้อความเข้าห้องประชุมผู้บริหาร (Owner + เลขา + PMs)"""
    chat_id = TELEGRAM_EXEC_CHAT_ID or TELEGRAM_OWNER_DIRECT_CHAT_ID
    return await send_telegram_message(chat_id, text)


async def send_to_department_room(dept_id: str, text: str) -> bool:
    """ส่งข้อความเข้าห้องทำงานเฉพาะของแผนกนั้น (Owner + PM แผนก + ลูกน้อง AI)"""
    chat_id = get_ops_chat_id_for_department(dept_id)
    if not chat_id:
        logger.warning(f"ไม่พบ Ops Chat ID สำหรับแผนก {dept_id}")
        return False
    return await send_telegram_message(chat_id, text)


def get_ops_chat_id_for_department(dept_id: str) -> str:
    """หา Chat ID ของห้องทำงานแผนกนั้นๆ"""
    if not dept_id:
        return TELEGRAM_OPS_CHAT_ID or TELEGRAM_EXEC_CHAT_ID

    # 1. เช็คจาก config.json ในโฟลเดอร์แผนก
    dept_dir = DEPARTMENTS_DIR / dept_id
    if dept_dir.exists() and (dept_dir / "config.json").exists():
        try:
            cfg = json.loads((dept_dir / "config.json").read_text(encoding="utf-8"))
            if cfg.get("ops_chat_id"):
                return cfg["ops_chat_id"]
        except Exception:
            pass

    # 2. เช็คจาก dictionary mapping
    if dept_id in TELEGRAM_OPS_CHAT_IDS and TELEGRAM_OPS_CHAT_IDS[dept_id]:
        return TELEGRAM_OPS_CHAT_IDS[dept_id]

    # 3. Fallback
    return TELEGRAM_OPS_CHAT_ID or TELEGRAM_EXEC_CHAT_ID


# ─── Dynamic Department Room Management (สร้าง/ยุบแผนก) ─────────────────────

def create_department_room(name: str, chat_id: str = "", pm_name: str = "", dept_id: Optional[str] = None) -> dict:
    """สร้างห้องทำงานแผนกใหม่ (สร้างโฟลเดอร์ + config.json)"""
    DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)

    if not dept_id:
        existing_indices = []
        for d in DEPARTMENTS_DIR.iterdir():
            if d.is_dir() and "_" in d.name and d.name.split("_")[0].isdigit():
                existing_indices.append(int(d.name.split("_")[0]))
        next_idx = str(max(existing_indices) + 1).zfill(2) if existing_indices else "01"

        clean_name = "".join([c if c.isalnum() else "_" for c in name.lower()]).strip("_")
        dept_id = f"{next_idx}_{clean_name or 'dept'}"

    dept_dir = DEPARTMENTS_DIR / dept_id
    dept_dir.mkdir(parents=True, exist_ok=True)

    config_file = dept_dir / "config.json"
    identity_file = dept_dir / "identity.md"
    skill_file = dept_dir / "skill.md"

    cfg = {
        "name": name,
        "role": f"pm_{dept_id}",
        "pm_name": pm_name or f"PM {name}",
        "model": "gemini-1.5-flash",
        "temperature": 0.5,
        "department": dept_id,
        "ops_chat_id": chat_id or "",
        "created_at": datetime.now().isoformat(),
    }
    config_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    if not identity_file.exists():
        identity_file.write_text(f"# {name} PM Identity\nคุณคือ PM หัวหน้าทีมแผนก {name}", encoding="utf-8")
    if not skill_file.exists():
        skill_file.write_text(f"# {name} Skills\nรับผิดชอบและบริหารงานแผนก {name}", encoding="utf-8")

    if chat_id:
        TELEGRAM_OPS_CHAT_IDS[dept_id] = chat_id

    return {
        "id": dept_id,
        "name": name,
        "pm_name": cfg["pm_name"],
        "ops_chat_id": chat_id,
        "path": str(dept_dir),
    }


def delete_department_room(dept_id: str) -> bool:
    """ยุบแผนก / ลบห้องทำงานแผนก (ลบโฟลเดอร์ + ลบคอนฟิก)"""
    dept_dir = DEPARTMENTS_DIR / dept_id
    if dept_dir.exists():
        shutil.rmtree(dept_dir)

    if dept_id in TELEGRAM_OPS_CHAT_IDS:
        del TELEGRAM_OPS_CHAT_IDS[dept_id]

    return True


def get_all_department_rooms() -> Dict[str, dict]:
    """สแกนห้องทำงานแผนกทั้งหมด"""
    DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)
    rooms = {}

    for dept_dir in sorted(DEPARTMENTS_DIR.iterdir()):
        if dept_dir.is_dir() and not dept_dir.name.startswith("."):
            dept_id = dept_dir.name
            config_file = dept_dir / "config.json"
            cfg = {}
            if config_file.exists():
                try:
                    cfg = json.loads(config_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

            ops_chat = cfg.get("ops_chat_id") or TELEGRAM_OPS_CHAT_IDS.get(dept_id, "")
            rooms[dept_id] = {
                "id": dept_id,
                "name": cfg.get("name", dept_id),
                "pm_name": cfg.get("pm_name", f"PM {cfg.get('name', dept_id)}"),
                "role": cfg.get("role", "agent"),
                "ops_chat_id": ops_chat,
                "configured": bool(ops_chat),
            }

    return rooms


# ─── Smart Intent Classifier & Webhook Handler ───────────────────────────────

async def classify_intent(text: str) -> str:
    """
    จำแนกเจตนาข้อความของ Owner:
    - 'CHAT': คุยส่วนตัวสัพเพเหระ/ปรึกษา/ถามความเห็นทั่วไป
    - 'TASK_ORDER': คำสั่งงานชัดเจน/สั่งมอบหมายงานให้แผนกไปทำ
    """
    lowered = text.strip().lower()

    # เช็คคีย์เวิร์ดทักทาย คุยทั่วไป
    greetings = ["สวัสดี", "หวัดดี", "เป็นไง", "สบายดีไหม", "สบายดีมั้ย", "คิดว่าไง", "แนะนำหน่อย", "ช่วยคิด", "ปรึกษา", "ขอบคุณ", "ขอบใจ", "hello", "hi", "hey"]
    if any(g in lowered for g in greetings) and len(text) < 40 and not any(k in lowered for k in ["สั่งงาน", "ให้ทำ", "สร้าง"]):
        return "CHAT"

    # เช็คคีย์เวิร์ดสั่งงาน
    order_keywords = ["สั่งงาน", "มอบหมาย", "ทำแคมเปญ", "จัดทำ", "อนุมัติ", "จัดซื้อ", "สร้างแผนก", "ช่วยสั่งงาน", "ให้แผนก"]
    if any(k in lowered for k in order_keywords):
        return "TASK_ORDER"

    # ใช้ LLM ช่วยจำแนกความหมาย
    try:
        from backend.services.llm_service import LLMService
        llm = LLMService(model="gemini-1.5-flash", temperature=0.0)
        prompt = (
            "โปรดจำแนกเจตนาข้อความของ Owner ว่าเป็น 'CHAT' หรือ 'TASK_ORDER'\n"
            "- ตอบ 'CHAT': ถ้าเป็นการพูดคุยส่วนตัวทั่วไป, ทักทาย, ปรึกษาไอเดีย, ถามความเห็น, สนทนาเรื่องทั่วไปที่ไม่ใช่การสั่งมอบหมายงาน\n"
            "- ตอบ 'TASK_ORDER': ถ้าเป็นการสั่งงานชัดเจน, มอบหมายภารกิจ, สั่งให้แผนกไปดำเนินการทำผลงาน, หรือสั่งให้ระบบทำรายการ\n\n"
            f"ข้อความ: '{text}'\n"
            "คำตอบ (ตอบเฉพาะ CHAT หรือ TASK_ORDER เท่านั้น):"
        )
        resp = await llm.generate(
            system_instruction="คุณคือตัวจำแนกเจตนาข้อความ ตอบคำเดียวเท่านั้น CHAT หรือ TASK_ORDER",
            user_message=prompt
        )
        resp_clean = resp.strip().upper()
        if "TASK_ORDER" in resp_clean:
            return "TASK_ORDER"
        if "CHAT" in resp_clean:
            return "CHAT"
    except Exception:
        pass

    return "CHAT"


async def handle_webhook(payload: dict) -> dict:
    """ประมวลผล Incoming Webhook Update จาก Telegram"""
    message = payload.get("message", {}) or payload.get("channel_post", {})
    if not message:
        return {"status": "ignored", "reason": "no_message"}

    chat_id = str(message.get("chat", {}).get("id", ""))
    from_user = message.get("from", {})
    sender_name = from_user.get("first_name", "Owner")
    text = message.get("text", "").strip() if isinstance(message.get("text"), str) else ""

    if not text:
        return {"status": "ignored", "reason": "empty_text"}

    write_log(LogCreate(
        agent_id="secretary_ai",
        agent_name="เลขา AI",
        level=LogLevel.INFO,
        message=f"ได้รับข้อความจาก Telegram ({sender_name}): {text[:50]}...",
    ))

    # 1. เช็คคำยืนยันสำหรับคำสั่งที่รอยืนยันอยู่
    has_active_pending = any(v["status"] == "awaiting_owner" for v in _pending_verifications.values())
    is_confirm = text.lower() in ["ใช่", "yes", "confirm", "อนุมัติ", "ตกลง", "y", "ok"]

    if has_active_pending and is_confirm:
        return await _process_confirmation(chat_id, sender_name)

    # 2. จำแนกเจตนาข้อความ (CHAT vs TASK_ORDER)
    intent = await classify_intent(text)

    if intent == "CHAT":
        return await _handle_personal_chat(chat_id, sender_name, text)
    else:
        return await _initiate_verification(chat_id, sender_name, text)


def resolve_room_context(chat_id: str) -> dict:
    """ตรวจสอบประเภทของห้องเพื่อเลือกบุคลิกและบทบาทโต้ตอบในฐานะทีมงานให้ตรงกับบริบทห้อง"""
    owner_direct = TELEGRAM_OWNER_DIRECT_CHAT_ID or os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
    exec_chat = TELEGRAM_EXEC_CHAT_ID or os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    dept_rooms = get_all_department_rooms()

    # 1. เช็คว่าเป็นห้องทำงานแผนกใดหรือไม่
    for dept_id, info in dept_rooms.items():
        if info.get("ops_chat_id") and str(info["ops_chat_id"]) == str(chat_id):
            return {
                "type": "department",
                "dept_id": dept_id,
                "dept_name": info.get("name", dept_id),
                "agent_name": f"ทีมงาน {info.get('name')}",
                "system_instruction": (
                    f"คุณคือ 'ทีมงานและ {info.get('pm_name', 'PMประจำแผนก')}' ประจำแผนก {info.get('name')} ของบริษัท One-Person AI Enterprise\n"
                    f"บทบาท: โต้ตอบทักทายหรือสนทนากับ Owner ในฐานะทีมงานปฏิบัติการประจำแผนก {info.get('name')} ที่มีความพร้อม เชี่ยวชาญ สุภาพ กระตือรือร้น และพร้อมปฏิบัติงาน\n"
                    f"ข้อแนะนำ: ตอบเป็นภาษาไทยในนาม 'ทีมงาน {info.get('name')}' หรือ '{info.get('pm_name')}' รายงานความพร้อม เสนอความช่วยเหลือในส่วนงานประจำแผนกอย่างสุภาพและมืออาชีพ"
                )
            }

    # 2. เช็คว่าเป็นห้องประชุมผู้บริหาร (Executive Boardroom)
    admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    if str(chat_id) in [str(exec_chat), str(admin_chat)] and str(chat_id) != "":
        return {
            "type": "executive",
            "agent_name": "คณะผู้บริหาร & PM Boardroom",
            "system_instruction": (
                "คุณคือ 'คณะผู้บริหารและทีม PM หัวหน้าทุกแผนก' ในห้องประชุมผู้บริหารของ One-Person AI Enterprise\n"
                "บทบาท: โต้ตอบทักทายกับ Owner ในฐานะทีมงานบริหารระดับสูง พร้อมเปิดประชุม สรุป วางแผน วางกลยุทธ์ และรับฟังนโยบายจาก Owner\n"
                "ข้อแนะนำ: ตอบเป็นภาษาไทยในนาม 'ทีมงานผู้บริหาร / คณะ PM' ด้วยความเคารพ สุภาพ ตรงประเด็น และเน้นย้ำความพร้อมในการประชุมและดำเนินนโยบายองค์กร"
            )
        }

    # 3. เช็คว่าเป็นห้องกลุ่มประชุม/ห้องปฏิบัติการอื่นๆ (Group Room)
    if str(chat_id).startswith("-"):
        return {
            "type": "group_meeting",
            "agent_name": "ทีมงาน & คณะ PM ประจำห้องประชุม",
            "system_instruction": (
                "คุณคือ 'ทีมงานและคณะ PM ประจำห้องประชุม' ของบริษัท One-Person AI Enterprise\n"
                "บทบาท: โต้ตอบในนามทีมงานและหัวหน้าทีมประจำห้องประชุม รับฟังคำสั่ง เปิดวาระประชุม และเสนอความเห็นเชิงปฏิบัติการให้ Owner\n"
                "ข้อแนะนำ: ตอบเป็นภาษาไทยอย่างสุภาพ มืออาชีพ กระตือรือร้น พร้อมเปิดการประชุมและสรุปสั่งงานให้แก่แผนกที่เกี่ยวข้องทันที"
            )
        }

    # 4. Default: คุยส่วนตัว 1-on-1 (Owner ↔ เลขา AI & ทีมงานกลาง)
    return {
        "type": "direct",
        "agent_name": "เลขา AI & ทีมงาน enterprise",
        "system_instruction": (
            "คุณคือ 'เลขา AI' เลขานุการส่วนตัวและตัวแทนทีมงาน enterprise ของบริษัท One-Person AI Enterprise\n"
            "บทบาท: โต้ตอบทักทายและสนทนากับ Owner ในฐานะเลขาและทีมงานส่วนตัว ให้คำปรึกษา แลกเปลี่ยนความคิด ทักทาย ดูแลความเรียบร้อยสัพเพเหระได้อย่างสนิทสนม สุภาพ มืออาชีพ\n"
            "ข้อแนะนำ: ตอบเป็นภาษาไทยอย่างสุภาพ ในนามเลขาและทีมงาน AI ยืนยันความพร้อมในการคอยช่วยเหลือ ปรึกษา และกระจายงานให้ทุกแผนกเสมอ"
        )
    }



async def _handle_personal_chat(chat_id: str, sender_name: str, text: str) -> dict:
    """ตอบสนองการพูดคุย/ทักทายกับ Owner ในฐานะทีมงานประจำห้องนั้นๆ"""
    try:
        from backend.services.llm_service import LLMService
        ctx = resolve_room_context(chat_id)

        llm = LLMService(model="gemini-1.5-flash", temperature=0.7)

        history = _chat_histories.get(chat_id, [])
        reply = await llm.generate(
            system_instruction=ctx["system_instruction"],
            user_message=text,
            history=history
        )

        # บันทึกประวัติการสนทนา
        history.append({"role": "user", "content": text})
        history.append({"role": "model", "content": reply})
        if len(history) > 10:
            history = history[-10:]
        _chat_histories[chat_id] = history

        await send_telegram_message(chat_id, reply)

        write_log(LogCreate(
            agent_id="secretary_ai",
            agent_name=ctx["agent_name"],
            level=LogLevel.SUCCESS,
            message=f"{ctx['agent_name']} โต้ตอบแชทกับ Owner: {reply[:50]}...",
            thought_process=f"บริบทห้อง: {ctx['type']}\nถาม: {text}\nตอบ: {reply}",
        ))

        return {"status": "chat_replied", "reply": reply, "room_type": ctx["type"], "agent_name": ctx["agent_name"]}
    except Exception as e:
        ctx = resolve_room_context(chat_id)
        err_msg = f"สวัสดีครับท่าน Owner ทีมงาน {ctx['agent_name']} พร้อมปฏิบัติงานและดูแลท่านเสมอครับ มีอะไรให้ทีมงานช่วยดูแลไหมครับ?"
        await send_telegram_message(chat_id, err_msg)
        return {"status": "chat_replied_fallback", "reply": err_msg}



async def _initiate_verification(chat_id: str, sender_name: str, text: str) -> dict:
    """ขั้นตอนที่ 1 & 2: เมื่อเป็นคำสั่งงาน (TASK_ORDER) — เลขา AI สรุปทวนคำสั่งกับ Owner"""
    verification_id = str(uuid.uuid4())[:8]

    try:
        from backend.services.llm_service import LLMService
        llm = LLMService(model="gemini-1.5-flash", temperature=0.3)
        summary = await llm.generate(
            system_instruction="คุณคือเลขา AI หน้าที่ของคุณคือทวนสรุปคำสั่งงานจาก Owner อย่างกระชับ ตรงประเด็น สั้นไม่เกิน 2 ประโยค",
            user_message=f"สรุปคำสั่งนี้เพื่อส่งทวนกับ Owner: '{text}'"
        )
    except Exception as e:
        logger.warning(f"LLM Error: {e}")
        summary = text

    verif_data = {
        "id": verification_id,
        "chat_id": chat_id,
        "sender_name": sender_name,
        "original_message": text,
        "summary": summary,
        "status": "awaiting_owner",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _pending_verifications[verification_id] = verif_data

    ctx = resolve_room_context(chat_id)
    confirm_msg = (
        f"<b>[{ctx['agent_name']} — รับทราบและทวนสรุปคำสั่งงาน]</b>\n"
        f"📌 <b>สรุปคำสั่ง/วาระประชุม:</b> {summary}\n\n"
        f"พิมพ์ <b>'ใช่'</b> หรือ <b>'อนุมัติ'</b> เพื่อเริ่มการประชุมและสั่งงานให้ PM และทีมงานแต่ละแผนกปฏิบัติการทันที\n"
        f"<i>(ID: {verification_id})</i>"
    )
    await send_telegram_message(chat_id, confirm_msg)

    write_log(LogCreate(
        agent_id="secretary_ai",
        agent_name=ctx["agent_name"],
        level=LogLevel.INFO,
        message=f"ส่งสรุปทวนคำสั่งในห้อง {ctx['agent_name']} (ID: {verification_id})",
        thought_process=f"ต้นฉบับ: {text}\nสรุป: {summary}",
    ))

    return {
        "status": "verification_initiated",
        "id": verification_id,
        "summary": summary,
        "agent_name": ctx["agent_name"],
        "reply": confirm_msg
    }



async def _process_confirmation(chat_id: str, sender_name: str) -> dict:
    """ขั้นตอนที่ 3 & 4: อนุมัติ → ประชุมผู้บริหาร (Exec Room) → ส่งงานลงห้องแผนกเฉพาะ (Ops Room)"""
    pending = next((v for v in _pending_verifications.values() if v["status"] == "awaiting_owner"), None)
    if not pending:
        return {"status": "error", "reason": "no_pending"}

    pending["status"] = "confirmed"

    # 1. PMs ร่วมวางแผนใน Executive Room
    try:
        from backend.services.llm_service import LLMService
        llm = LLMService(model="gemini-1.5-flash", temperature=0.5)
        pm_plan = await llm.generate(
            system_instruction="คุณคือหัวหน้าทีม PM ในห้องประชุมผู้บริหาร วางแผนการทำงาน ระบุ Timeline และระบุชื่อแผนกที่จะต้องรับงานไปทำ (เช่น การตลาด/marketing)",
            user_message=f"คำสั่งที่ได้รับอนุมัติจาก Owner: '{pending['summary']}'"
        )
    except Exception as e:
        logger.warning(f"LLM Error in PM Plan: {e}")
        pm_plan = f"แผนการดำเนินงานสำหรับคำสั่ง: {pending['summary']}"

    # แจ้งใน Executive Room (ห้องประชุมผู้บริหาร)
    exec_msg = (
        f"<b>[ห้องประชุมผู้บริหาร — PM Boardroom]</b>\n"
        f"✅ Owner อนุมัติคำสั่งเรียบร้อย!\n\n"
        f"📋 <b>แผนการดำเนินงาน:</b>\n{pm_plan}"
    )
    await send_to_executive_board(exec_msg)

    # 2. กระจายงานเข้าห้องทำงานเฉพาะของแต่ละแผนก (Department Working Rooms)
    dept_rooms = get_all_department_rooms()
    forwarded_depts = []

    for dept_id, dept_info in dept_rooms.items():
        dept_name = dept_info.get("name", "")
        if dept_id in pm_plan or (dept_name and dept_name in pm_plan) or len(dept_rooms) == 1:
            dept_msg = (
                f"<b>[ห้องทำงานแผนก {dept_name}]</b>\n"
                f"🚀 <b>คำสั่งจาก Owner:</b> {pending['summary']}\n"
                f"👤 <b>ดูแลโดย:</b> {dept_info.get('pm_name', 'PMประจำแผนก')}\n\n"
                f"📝 <b>มอบหมายงาน:</b>\n{pm_plan}\n\n"
                f"⚡ ขอให้สมาชิกในทีมเริ่มปฏิบัติงานทันที"
            )
            await send_to_department_room(dept_id, dept_msg)
            forwarded_depts.append(dept_id)

    # Fallback
    if not forwarded_depts and TELEGRAM_OPS_CHAT_ID:
        fallback_msg = (
            f"<b>[ห้องทำงานปฏิบัติการรวม]</b>\n"
            f"🚀 <b>คำสั่งใหม่:</b> {pending['summary']}\n{pm_plan}"
        )
        await send_telegram_message(TELEGRAM_OPS_CHAT_ID, fallback_msg)

    write_log(LogCreate(
        agent_id="pm_ai",
        agent_name="PM AI Board",
        level=LogLevel.SUCCESS,
        message=f"กระจายงานเข้าห้องทำงานแผนกสำเร็จ ({', '.join(forwarded_depts) if forwarded_depts else 'Exec Board'})",
        thought_process=pm_plan,
    ))

    return {"status": "confirmed_and_forwarded", "id": pending["id"], "forwarded_departments": forwarded_depts, "plan": pm_plan}


def get_verifications() -> List[dict]:
    return list(_pending_verifications.values())


def get_room_status() -> dict:
    bot_token = TELEGRAM_BOT_TOKEN or os.getenv("TELEGRAM_BOT_TOKEN", "")
    owner_direct = TELEGRAM_OWNER_DIRECT_CHAT_ID or os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
    exec_chat = TELEGRAM_EXEC_CHAT_ID or os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    default_ops = TELEGRAM_OPS_CHAT_ID or os.getenv("TELEGRAM_OPS_CHAT_ID", "")

    dept_rooms = get_all_department_rooms()

    return {
        "bot_configured": bool(bot_token),
        "owner_id": TELEGRAM_OWNER_ID or os.getenv("TELEGRAM_OWNER_ID", ""),
        "direct_chat": {
            "id": owner_direct,
            "name": "💬 คุยส่วนตัว 1-on-1 (Owner ↔ เลขา AI)",
            "configured": bool(owner_direct),
        },
        "executive_room": {
            "id": exec_chat,
            "name": "🏛️ ห้องประชุมผู้บริหาร (Owner + เลขา + PMs ทุกแผนก)",
            "configured": bool(exec_chat),
        },
        "default_ops_room": {
            "id": default_ops,
            "configured": bool(default_ops),
        },
        "department_rooms": dept_rooms,
    }


# ─── Telegram Background Polling Service ────────────────────────────────────

_polling_task = None
_polling_running = False


def get_bot_token() -> str:
    """ดึง TELEGRAM_BOT_TOKEN แบบ Dynamic เพื่อป้องกันปัญหาอ่านค่าว่างช่วงโมดูลโหลด"""
    return os.getenv("TELEGRAM_BOT_TOKEN", "") or TELEGRAM_BOT_TOKEN


async def start_telegram_polling():
    """เริ่มระบบ Telegram Background Listener เพื่อคอยรับและตอบกลับข้อความจาก Owner บน Telegram เรียลไทม์ 24/7"""
    global _polling_task, _polling_running
    if _polling_running:
        return

    token = get_bot_token()
    if not token:
        print("⚠️ [Telegram Worker] ไม่พบ TELEGRAM_BOT_TOKEN ไม่สามารถเริ่ม Telegram Polling ได้")
        return

    _polling_running = True
    print(f"🚀 [Telegram Worker] เริ่มทำงาน Telegram Background Listener เรียลไทม์ (Token: {token[:10]}...)...")

    async def _polling_loop():
        global _polling_running
        last_offset = 0
        async with httpx.AsyncClient(timeout=25.0) as client:
            while _polling_running:
                try:
                    curr_token = get_bot_token()
                    if curr_token:
                        url = f"https://api.telegram.org/bot{curr_token}/getUpdates"
                        params = {"offset": last_offset + 1, "timeout": 10}
                        resp = await client.get(url, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("ok"):
                                for update in data.get("result", []):
                                    last_offset = update["update_id"]
                                    msg = update.get("message", {}) or update.get("channel_post", {})
                                    msg_text = msg.get("text", "")
                                    chat_id = msg.get("chat", {}).get("id", "")
                                    print(f"📥 [Telegram Worker] ได้รับข้อความใหม่ ({chat_id}): '{msg_text[:40]}...' (Update ID: {update['update_id']})")
                                    res = await handle_webhook(update)
                                    print(f"✅ [Telegram Worker] ประมวลผลสำเร็จ: {res}")
                        elif resp.status_code == 409:
                            logger.info("Telegram Polling 409 Conflict: Waiting 3s for previous polling connection to release...")
                            await asyncio.sleep(3)
                            continue
                        else:
                            logger.warning(f"Telegram Polling HTTP Error {resp.status_code}: {resp.text}")
                            await asyncio.sleep(2)
                except Exception as e:
                    logger.debug(f"Telegram Polling loop update error: {e}")
                    await asyncio.sleep(2)
                await asyncio.sleep(0.5)

    _polling_task = asyncio.create_task(_polling_loop())




def stop_telegram_polling():
    """หยุดทำงาน Telegram Background Listener Worker"""
    global _polling_running, _polling_task
    _polling_running = False
    if _polling_task:
        _polling_task.cancel()
        _polling_task = None


async def simulate_owner_message(text: str, is_private_dm: bool = True) -> dict:
    chat_id = TELEGRAM_OWNER_DIRECT_CHAT_ID or "simulated_owner_dm"
    chat_type = "private" if is_private_dm else "group"
    payload = {
        "update_id": 99999,
        "message": {
            "message_id": 8888,
            "from": {"id": 1111, "first_name": "Owner"},
            "chat": {"id": chat_id, "type": chat_type},
            "text": text,
        },
    }
    result = await handle_webhook(payload)
    return {"simulated": True, "input_text": text, "result": result}


