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


def _get_owner_prompt_context() -> str:
    owner_name = os.getenv("OWNER_NAME", "Owner")
    owner_identity = os.getenv("OWNER_IDENTITY", "เจ้าของและผู้บริหารสูงสุดของบริษัท")
    owner_skill = os.getenv("OWNER_SKILL", "การตัดสินใจเชิงกลยุทธ์และการบริหารองค์กร")
    return (
        f"\n\n--- ข้อมูลเกี่ยวกับ Owner (คู่สนทนาและผู้บริหารของคุณ) ---\n"
        f"ชื่อ: {owner_name}\n"
        f"ตัวตน/บทบาท: {owner_identity}\n"
        f"ทักษะ/ความเชี่ยวชาญ: {owner_skill}\n"
        f"คำแนะนำ: ให้คุณเรียกชื่อจริงของ Owner คือ '{owner_name}' หรือทักทายอย่างสุภาพและเป็นกันเองด้วยความสนิทสนม เช่น 'คุณ {owner_name}' หรือ 'ท่าน {owner_name}' แทนคำว่า 'Owner' เฉยๆ เพื่อความเป็นกันเองในบริษัท\n"
    )


# ─── Telegram Messaging Helpers ───────────────────────────────────────────────

def clean_telegram_html(text: str) -> str:
    """ทำความสะอาด HTML Tags ที่ Telegram ไม่รองรับ เช่น <br>, <p>, <div>"""
    if not text:
        return ""
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    import re
    text = re.sub(r'<(?!b|/b|i|/i|code|/code|a|/a|pre|/pre|s|/s|u|/u)[^>]+>', '', text)
    return text


async def send_telegram_message(chat_id: str, text: str, bot_token: Optional[str] = None) -> bool:
    """ส่งข้อความไปยัง Telegram Chat (ระบุ bot_token สำหรับ PM บอทเฉพาะแผนก)"""
    token = bot_token or get_bot_token()
    if not token or not chat_id:
        logger.warning(f"Telegram Bot Token หรือ Chat ID ({chat_id}) ไม่ถูกตั้งค่า")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": clean_telegram_html(text),
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
    
    # ดึง Token ของ PM แผนกนั้นๆ เพื่อใช้ส่งเข้าห้องทำงาน
    dept_rooms = get_all_department_rooms()
    dept_info = dept_rooms.get(dept_id, {})
    pm_bot_token = dept_info.get("bot_token", "")
    
    return await send_telegram_message(chat_id, text, bot_token=pm_bot_token)


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

def create_department_room(name: str, chat_id: str = "", pm_name: str = "", dept_id: Optional[str] = None, bot_token: str = "") -> dict:
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

    cfg = {}
    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    cfg.update({
        "name": name,
        "role": f"pm_{dept_id}",
        "pm_name": pm_name or cfg.get("pm_name") or f"PM {name}",
        "model": cfg.get("model", "gemini-1.5-flash"),
        "temperature": cfg.get("temperature", 0.5),
        "department": dept_id,
        "ops_chat_id": chat_id or cfg.get("ops_chat_id", ""),
        "bot_token": bot_token or cfg.get("bot_token", ""),
        "created_at": cfg.get("created_at", datetime.now().isoformat()),
    })
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
        "bot_token": cfg["bot_token"],
        "path": str(dept_dir),
    }


async def propose_team_structure(dept_name: str, pm_name: str = "") -> dict:
    """เสนอร่างโครงสร้างทีม บทบาทลูกทีม และ KPI ที่เหมาะสมให้ Owner พิจารณาปรับแก้และอนุมัติก่อนสร้างจริง"""
    from backend.services.llm_service import LLMService
    llm = LLMService(model="gemini-1.5-flash", temperature=0.5)

    prompt = (
        f"ขอให้นำเสนอโครงสร้างทีมสำหรับแผนก '{dept_name}'\n"
        f"ชื่อ PM หัวหน้าทีม: {pm_name or 'PM ' + dept_name}\n"
        f"กรุณาจัดทำข้อเสนอโครงสร้างทีมในรูปแบบ JSON ประกอบด้วย:\n"
        f"- department_name: ชื่อแผนก\n"
        f"- pm_name: ชื่อ PM หัวหน้าทีม\n"
        f"- proposed_roles: รายชื่อตำแหน่งลูกทีม AI ย่อยในทีม 3-4 ตำแหน่ง\n"
        f"- recommended_kpi: KPI เป้าหมายสำคัญของทีมนี้\n"
        f"- team_mission: พันธกิจและขอบเขตงานหลักของทีม\n\n"
        f"ตอบกลับเป็น JSON เท่านั้น ไม่ต้องมี markdown formatting เพิ่มเติม"
    )

    try:
        res_raw = await llm.generate(system_instruction="คุณคือเลขา AI และนักวางโครงสร้างองค์กร ตอบเป็น JSON เท่านั้น", user_message=prompt)
        res_clean = res_raw.strip().strip("```json").strip("```").strip()
        proposal = json.loads(res_clean)
    except Exception:
        proposal = {
            "department_name": dept_name,
            "pm_name": pm_name or f"PM {dept_name}",
            "proposed_roles": ["PM หัวหน้าทีม", "Specialist 1", "Specialist 2", "Data Analyst"],
            "recommended_kpi": f"ปฏิบัติภารกิจของแผนก {dept_name} ให้สำเร็จตามเป้าหมาย 100%",
            "team_mission": f"บริหารจัดการและส่งมอบผลงานคุณภาพของแผนก {dept_name}"
        }

    return proposal



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
            bot_token = cfg.get("bot_token", "")
            rooms[dept_id] = {
                "id": dept_id,
                "name": cfg.get("name", dept_id),
                "pm_name": cfg.get("pm_name", f"PM {cfg.get('name', dept_id)}"),
                "role": cfg.get("role", "agent"),
                "ops_chat_id": ops_chat,
                "bot_token": bot_token,
                "configured": bool(ops_chat or bot_token),
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

    # ใช้ LLM ช่วยจำแนกความหมาย พร้อมกำหนด Timeout
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
        # ป้องกัน API ค้างด้วย timeout 4.0 วินาที
        resp = await asyncio.wait_for(
            llm.generate(
                system_instruction="คุณคือตัวจำแนกเจตนาข้อความ ตอบคำเดียวเท่านั้น CHAT หรือ TASK_ORDER",
                user_message=prompt
            ),
            timeout=4.0
        )
        resp_clean = resp.strip().upper()
        if "TASK_ORDER" in resp_clean:
            return "TASK_ORDER"
        if "CHAT" in resp_clean:
            return "CHAT"
    except Exception as e:
        logger.debug(f"Intent classification failed/timeout: {e}. Fallback to CHAT.")
        pass

    return "CHAT"


async def handle_webhook(payload: dict, bot_token: Optional[str] = None) -> dict:
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

    ctx = resolve_room_context(chat_id, bot_token=bot_token)
    
    # หากระบุ bot_token (คุยส่วนตัวหา PM บอท) ให้ปรับปรุงชื่อผู้รับการบันทึก Log ให้ถูกต้อง
    if bot_token:
        dept_rooms = get_all_department_rooms()
        matching_pm = next((info for info in dept_rooms.values() if info.get("bot_token") == bot_token), None)
        if matching_pm:
            ctx["agent_name"] = matching_pm.get("pm_name") or f"PM {matching_pm['name']}"
            ctx["dept_id"] = matching_pm["id"]

    write_log(LogCreate(
        agent_id=ctx.get("dept_id", "secretary_ai"),
        agent_name=ctx["agent_name"],
        level=LogLevel.INFO,
        message=f"ได้รับข้อความจาก Telegram ({sender_name}) หา {ctx['agent_name']}: {text[:50]}...",
    ))

    # 1. เช็คคำยืนยันสำหรับคำสั่งที่รอยืนยันอยู่
    has_active_pending = any(v["status"] == "awaiting_owner" for v in _pending_verifications.values())
    is_confirm = text.lower() in ["ใช่", "yes", "confirm", "อนุมัติ", "ตกลง", "y", "ok"]

    if has_active_pending and is_confirm:
        return await _process_confirmation(chat_id, sender_name)

    # 2. จำแนกเจตนาข้อความ (CHAT vs TASK_ORDER)
    intent = await classify_intent(text)

    if intent == "CHAT":
        return await _handle_personal_chat(chat_id, sender_name, text, bot_token=bot_token)
    else:
        return await _initiate_verification(chat_id, sender_name, text)


def resolve_room_context(chat_id: str, bot_token: Optional[str] = None) -> dict:
    """ตรวจสอบประเภทของห้องเพื่อเลือกบุคลิกและบทบาทโต้ตอบในฐานะทีมงานให้ตรงกับบริบทห้อง"""
    owner_direct = TELEGRAM_OWNER_DIRECT_CHAT_ID or os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
    exec_chat = TELEGRAM_EXEC_CHAT_ID or os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")

    dept_rooms = get_all_department_rooms()
    res_ctx = None

    # 1. ปรับปรุง: หากระบุ bot_token ให้เจาะจงเลยว่าเป็น PM แผนกนั้นๆ กำลังคุยกับคุณ (ไม่ว่าจะคุยผ่านห้องแชทใด)
    if bot_token:
        for dept_id, info in dept_rooms.items():
            if info.get("bot_token") == bot_token:
                # โหลดข้อมูลจริงจากแผนก
                identity_content = ""
                skill_content = ""
                dept_dir = DEPARTMENTS_DIR / dept_id
                if dept_dir.exists():
                    if (dept_dir / "identity.md").exists():
                        identity_content = (dept_dir / "identity.md").read_text(encoding="utf-8")
                    if (dept_dir / "skill.md").exists():
                        skill_content = (dept_dir / "skill.md").read_text(encoding="utf-8")

                res_ctx = {
                    "type": "direct_pm",
                    "dept_id": dept_id,
                    "dept_name": info.get("name", dept_id),
                    "agent_name": info.get("pm_name") or f"PM {info.get('name')}",
                    "system_instruction": (
                        f"คุณคือ '{info.get('pm_name')}' PM หัวหน้าทีมแผนก {info['name']} ของบริษัท One-Person AI Enterprise\n\n"
                        f"--- ข้อมูลเอกลักษณ์ตัวตนของคุณ (Identity) ---\n{identity_content}\n\n"
                        f"--- ทักษะและขั้นตอนการทำงานของคุณ (Skills) ---\n{skill_content}\n\n"
                        f"บทบาท: สนทนาโต้ตอบแบบ 1-on-1 ใน Telegram กับคุณ Owner อย่างฉลาด สุภาพ มีไหวพริบ กระตือรือร้น รายงานสถานะงานและพร้อมรับคำสั่งตรงปฏิบัติงานทันที"
                    )
                }
                break

    # 2. เช็คห้องทำงานแผนก (ops_chat_id)
    if not res_ctx:
        for dept_id, info in dept_rooms.items():
            if info.get("ops_chat_id") and str(info["ops_chat_id"]) == str(chat_id):
                res_ctx = {
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
                break
        
    # 3. เช็คว่าเป็นห้องประชุมผู้บริหาร (Executive Boardroom)
    if not res_ctx:
        admin_chat = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
        if str(chat_id) in [str(exec_chat), str(admin_chat)] and str(chat_id) != "":
            res_ctx = {
                "type": "executive",
                "agent_name": "คณะผู้บริหาร & PM Boardroom",
                "system_instruction": (
                    "คุณคือ 'คณะผู้บริหารและทีม PM หัวหน้าทุกแผนก' ในห้องประชุมผู้บริหารของ One-Person AI Enterprise\n"
                    "บทบาท: โต้ตอบทักทายกับ Owner ในฐานะทีมงานบริหารระดับสูง พร้อมเปิดประชุม สรุป วางแผน วางกลยุทธ์ และรับฟังนโยบายจาก Owner\n"
                    "ข้อแนะนำ: ตอบเป็นภาษาไทยในนาม 'ทีมงานผู้บริหาร / คณะ PM' ด้วยความเคารพ สุภาพ ตรงประเด็น และเน้นย้ำความพร้อมในการประชุมและดำเนินนโยบายองค์กร"
                )
            }

    # 4. เช็คว่าเป็นห้องกลุ่มประชุม/ห้องปฏิบัติการอื่นๆ (Group Room)
    if not res_ctx:
        if str(chat_id).startswith("-"):
            res_ctx = {
                "type": "group_meeting",
                "agent_name": "ทีมงาน & คณะ PM ประจำห้องประชุม",
                "system_instruction": (
                    "คุณคือ 'ทีมงานและคณะ PM ประจำห้องประชุม' ของบริษัท One-Person AI Enterprise\n"
                    "บทบาท: โต้ตอบในนามทีมงานและหัวหน้าทีมประจำห้องประชุม รับฟังคำสั่ง เปิดวาระประชุม และเสนอความเห็นเชิงปฏิบัติการให้ Owner\n"
                    "ข้อแนะนำ: ตอบเป็นภาษาไทยอย่างสุภาพ มืออาชีพ กระตือรือร้น พร้อมเปิดการประชุมและสรุปสั่งงานให้แก่แผนกที่เกี่ยวข้องทันที"
                )
            }

    # 5. Default: คุยส่วนตัว 1-on-1 (Owner ↔ เลขา AI อิงฟ้า — เพื่อนคู่คิด & ที่ปรึกษาบริหาร)
    if not res_ctx:
        res_ctx = {
            "type": "direct",
            "agent_name": "เลขา AI (อิงฟ้า - เพื่อนคู่คิดบริหาร)",
            "system_instruction": (
                "คุณคือ 'อิงฟ้า' เลขา AI ส่วนตัวและเพื่อนคู่คิด (Strategic Thought Partner) ของท่าน Owner ในบริษัท One-Person AI Enterprise\n"
                "บุคลิกและบทบาท:\n"
                "1. เป็นเพื่อนคู่คิดที่ฉลาด รอบคอบ อบอุ่น สนิทสนม สุภาพ มืออาชีพ และจริงใจต่อท่าน Owner\n"
                "2. สามารถสรุปรายงานประจำวัน (Daily Briefing / EOD Summary) ว่าเมื่อวานและวันนี้ทีมไหนทำอะไรบ้าง งานคืบหน้าถึงไหน มีจุดติดขัด (Bottleneck) หรือไม่\n"
                "3. เสนอคำแนะนำเชิงกลยุทธ์ ข้อคิดเห็น และคอยสนทนาปรึกษาหารือได้อย่างเป็นธรรมชาติเหมือนเพื่อนคู่คิดผู้ช่วยมือขวา\n"
                "4. พร้อมรับคำสั่ง สรุปคำสั่ง และกระจายงานให้ PM แต่ละทีมปฏิบัติการทันที"
            )
        }

    res_ctx["system_instruction"] += _get_owner_prompt_context()
    return res_ctx


async def _handle_personal_chat(chat_id: str, sender_name: str, text: str, bot_token: Optional[str] = None) -> dict:
    """ตอบสนองการพูดคุย/ทักทายกับ Owner ในฐานะทีมงานประจำห้องนั้นๆ"""
    try:
        from backend.services.llm_service import LLMService
        ctx = resolve_room_context(chat_id, bot_token=bot_token)
        
        # ปรับปรุง: หากเป็นการทักส่วนตัว 1-on-1 หา PM Bot (ไม่ใช่เลขาอิงฟ้า) ให้ใช้ Persona ของ PM คนนั้นตอบแทน
        if ctx["type"] == "direct" and bot_token:
            dept_rooms = get_all_department_rooms()
            matching_pm = next((info for info in dept_rooms.values() if info.get("bot_token") == bot_token), None)
            if matching_pm:
                dept_id = matching_pm["id"]
                ctx["agent_name"] = matching_pm.get("pm_name", matching_pm["name"])
                
                # โหลดข้อมูล identity และ skill จริงจากแผนก
                identity_content = ""
                skill_content = ""
                dept_dir = DEPARTMENTS_DIR / dept_id
                if dept_dir.exists():
                    if (dept_dir / "identity.md").exists():
                        identity_content = (dept_dir / "identity.md").read_text(encoding="utf-8")
                    if (dept_dir / "skill.md").exists():
                        skill_content = (dept_dir / "skill.md").read_text(encoding="utf-8")

                ctx["system_instruction"] = (
                    f"คุณคือ '{matching_pm.get('pm_name')}' PM หัวหน้าทีมแผนก {matching_pm['name']} ของบริษัท One-Person AI Enterprise\n\n"
                    f"--- ข้อมูลเอกลักษณ์ตัวตนของคุณ (Identity) ---\n{identity_content}\n\n"
                    f"--- ทักษะและขั้นตอนการทำงานของคุณ (Skills) ---\n{skill_content}\n\n"
                    f"บทบาท: สนทนาโต้ตอบแบบ 1-on-1 ใน Telegram กับคุณ Owner อย่างฉลาด สุภาพ มีไหวพริบ กระตือรือร้น รายงานสถานะงานและพร้อมรับคำสั่งตรงปฏิบัติงานทันที"
                )

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

        await send_telegram_message(chat_id, reply, bot_token=bot_token)

        write_log(LogCreate(
            agent_id="secretary_ai" if not bot_token else "pm_bot",
            agent_name=ctx["agent_name"],
            level=LogLevel.SUCCESS,
            message=f"{ctx['agent_name']} โต้ตอบแชทกับ Owner: {reply[:50]}...",
            thought_process=f"บริบทห้อง: {ctx['type']}\nถาม: {text}\nตอบ: {reply}",
        ))

        return {"status": "chat_replied", "reply": reply, "room_type": ctx["type"], "agent_name": ctx["agent_name"]}
    except Exception as e:
        ctx = resolve_room_context(chat_id, bot_token=bot_token)
        err_msg = f"สวัสดีครับท่าน Owner ทีมงาน {ctx['agent_name']} พร้อมปฏิบัติงานและดูแลท่านเสมอครับ มีอะไรให้ทีมงานช่วยดูแลไหมครับ?"
        await send_telegram_message(chat_id, err_msg, bot_token=bot_token)
        return {"status": "chat_replied_fallback", "reply": err_msg}

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

    # 4. Default: คุยส่วนตัว 1-on-1 (Owner ↔ เลขา AI อิงฟ้า — เพื่อนคู่คิด & ที่ปรึกษาบริหาร)




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
            system_instruction="คุณคือหัวหน้าทีม PM ในห้องประชุมผู้บริหาร วางแผนการทำงาน ระบุ Timeline และระบุชื่อแผนกที่จะต้องรับงานไปทำ (เช่น การตลาด/marketing)" + _get_owner_prompt_context(),
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

    # 3. ส่งข้อความแจ้งเตือนกลับไปยัง Owner ทาง Telegram 1-on-1 ว่าลูกทีมได้รับงานและปฏิบัติงานเสร็จเรียบร้อยพร้อมดูผลงานทางเว็บ!
    owner_target_chat = chat_id if chat_id and not chat_id.startswith("-") else (TELEGRAM_OWNER_DIRECT_CHAT_ID or chat_id)
    if owner_target_chat:
        completion_msg = (
            f"<b>[รายงานผลการทำงานจาก PM และลูกทีมทุกแผนก]</b>\n"
            f"✅ <b>สถานะ:</b> PM กระจายงานและสั่งลูกทีมปฏิบัติการเสร็จเรียบร้อยแล้วครับ!\n\n"
            f"📌 <b>สรุปคำสั่ง:</b> {pending['summary']}\n\n"
            f"📋 <b>แผนงานและผลงานปฏิบัติการ:</b>\n{pm_plan}\n\n"
            f"🌐 <b>ท่าน Owner สามารถคลิกเข้ามาดูรายละเอียดการทำงานของลูกทีมแต่ละแผนกทางหน้าเว็บได้ที่:</b>\n"
            f"http://localhost:8888/#/skype\n\n"
            f"💡 <i>(หากท่าน Owner มีคำสั่งเพิ่มเติม สามารถพิมพ์สั่งงานต่อทาง Telegram 1-on-1 นี้ได้เลยครับ!)</i>"
        )
        await send_telegram_message(owner_target_chat, completion_msg)

    return {"status": "confirmed_and_forwarded", "id": pending["id"], "forwarded_departments": forwarded_depts, "plan": pm_plan, "owner_notified": True}



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

_polling_tasks = []
_active_polling_tokens = {}  # {token: task}
_polling_running = False


def get_bot_token() -> str:
    """ดึง TELEGRAM_BOT_TOKEN แบบ Dynamic เพื่อป้องกันปัญหาอ่านค่าว่างช่วงโมดูลโหลด"""
    return os.getenv("TELEGRAM_BOT_TOKEN", "") or TELEGRAM_BOT_TOKEN


async def start_telegram_polling():
    """เริ่มระบบ Telegram Background Listener คอยรับและตอบกลับข้อความจาก Owner ทาง Telegram ของ PM บอททุกแผนกและเลขา AI แบบ Dynamic"""
    global _polling_tasks, _polling_running, _active_polling_tokens
    _polling_running = True

    # รวบรวม Tokens ที่ต้องทำ Polling (บอทเลขาหลัก + PM บอทแผนกต่างๆ)
    tokens_to_poll = {}
    main_token = get_bot_token()
    if main_token:
        tokens_to_poll["secretary_ai"] = main_token

    try:
        dept_rooms = get_all_department_rooms()
        for dept_id, info in dept_rooms.items():
            t = info.get("bot_token", "")
            if t:
                tokens_to_poll[f"pm_{dept_id}"] = t
    except Exception as e:
        logger.warning(f"ไม่สามารถสแกนบอทของ PM แผนกได้: {e}")

    # 1. หยุดบอทที่ไม่มีอยู่ในรายการแล้ว (เช่น ถูกลบแผนกออก)
    active_tokens = list(_active_polling_tokens.keys())
    for t in active_tokens:
        if t not in tokens_to_poll.values():
            print(f"🛑 [Telegram Worker] หยุด Polling สำหรับบอทที่ถูกลบ/เปลี่ยน Token")
            try:
                _active_polling_tokens[t].cancel()
            except Exception:
                pass
            del _active_polling_tokens[t]

    # 2. เริ่ม Polling สำหรับ Token ใหม่ๆ
    for name, token in tokens_to_poll.items():
        if token in _active_polling_tokens:
            continue  # รันอยู่แล้ว ไม่สร้างทับ

        async def _individual_polling_loop(bot_name: str, bot_tok: str):
            last_offset = 0
            print(f"📡 [Telegram Worker] เริ่มรัน Polling สำหรับบอท {bot_name} (Token: {bot_tok[:10]}...)")
            while _polling_running:
                try:
                    url = f"https://api.telegram.org/bot{bot_tok}/getUpdates"
                    params = {"offset": last_offset + 1, "timeout": 8}
                    async with httpx.AsyncClient(timeout=12.0) as client:
                        resp = await client.get(url, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("ok"):
                                for update in data.get("result", []):
                                    last_offset = update["update_id"]
                                    msg = update.get("message", {}) or update.get("channel_post", {})
                                    msg_text = msg.get("text", "")
                                    chat_id = msg.get("chat", {}).get("id", "")
                                    print(f"📥 [{bot_name}] ได้รับข้อความใหม่ ({chat_id}): '{msg_text[:40]}...'")
                                    # ส่ง token ของบอทตัวที่รับเข้าไปประมวลผล เพื่อตอบกลับออกทางบอทตัวเดิม
                                    res = await handle_webhook(update, bot_token=bot_tok)
                                    print(f"✅ [{bot_name}] ประมวลผลและตอบกลับสำเร็จ: {res}")
                        elif resp.status_code == 409:
                            # 409 Conflict (บอทเปิดทับกัน) - รอการหลุดของ Connection
                            await asyncio.sleep(4)
                            continue
                        else:
                            await asyncio.sleep(3)
                except Exception as e:
                    logger.debug(f"Loop error on {bot_name}: {e}")
                    await asyncio.sleep(2)
                await asyncio.sleep(0.5)

        task = asyncio.create_task(_individual_polling_loop(name, token))
        _active_polling_tokens[token] = task
        _polling_tasks.append(task)


def stop_telegram_polling():
    """หยุดทำงาน Telegram Background Listener Worker ทั้งหมด"""
    global _polling_running, _polling_tasks, _active_polling_tokens
    _polling_running = False
    for task in _polling_tasks:
        try:
            task.cancel()
        except Exception:
            pass
    _polling_tasks = []
    _active_polling_tokens = {}


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


async def run_director_meeting(message: str) -> dict:
    """ประมวลผลการประชุมในห้องประชุมผู้บริหาร (Executive Director Boardroom) บน Web UI"""
    dept_rooms = get_all_department_rooms()
    active_pms = [info.get("pm_name", f"PM {info['name']}") for info in dept_rooms.values()]
    pm_list_str = ", ".join(active_pms) if active_pms else "ยังไม่มี PM ที่ถูกสร้าง"

    # เช็คว่ามี @PM หรือ @Department ถูกระบุในข้อความหรือไม่ (ข้อ 4)
    mentioned_dept_id = None
    mentioned_info = None
    for dept_id, info in dept_rooms.items():
        pm_name = info.get("pm_name", "").lower()
        dept_name = info.get("name", "").lower()
        msg_low = message.lower()
        if (pm_name and pm_name in msg_low) or (dept_name and dept_name in msg_low) or (dept_id in msg_low) or ("@" in msg_low and (pm_name in msg_low or dept_name in msg_low)):
            mentioned_dept_id = dept_id
            mentioned_info = info
            break

    from backend.services.llm_service import LLMService
    llm = LLMService(model="gemini-1.5-flash", temperature=0.6)

    system_instruction = (
        f"คุณคือ 'คณะผู้บริหารและ PM หัวหน้าแผนกที่ถูกสร้างแล้วเท่านั้น' ({pm_list_str}) ในห้องประชุมผู้บริหาร (Director Boardroom)\n"
        f"บทบาท: ประชุมร่วมกับ Owner ให้ความคิดเห็น วิเคราะห์ความเสี่ยง เสนอแนวทางปฏิบัติ วาง Timeline และงบประมาณอย่างมืออาชีพ\n"
        f"คำแนะนำ: ตอบเป็นภาษาไทยอย่างสุภาพ กระชับ สรุปวาระประชุมและวาง Action Plan ชัดเจนสำหรับส่งต่อให้แต่ละทีมปฏิบัติการทันที"
    ) + _get_owner_prompt_context()

    reply = await llm.generate(system_instruction=system_instruction, user_message=message)

    write_log(LogCreate(
        agent_id="pm_ai",
        agent_name="คณะผู้บริหาร Boardroom",
        level=LogLevel.SUCCESS,
        message=f"อภิปรายวาระประชุมใน Boardroom: {message[:40]}...",
        thought_process=reply,
    ))

    # หากมีการ @PM ให้ส่งงานเข้าทีมปฏิบัติการ + บันทึก Log ทุกตำแหน่งงาน + แจ้งเตือนทาง 1-on-1 Telegram (ข้อ 2 & ข้อ 4)
    if mentioned_info:
        dept_id = mentioned_dept_id
        pm_name = mentioned_info.get("pm_name", f"PM {mentioned_info.get('name')}")
        dept_name = mentioned_info.get("name", dept_id)
        pm_bot_token = mentioned_info.get("bot_token", "")

        # 1. Log หัวหน้าทีม PM รับคำสั่ง
        write_log(LogCreate(
            agent_id=dept_id,
            agent_name=pm_name,
            level=LogLevel.INFO,
            message=f"📌 [{pm_name}] รับคำสั่งจาก Boardroom: '{message[:50]}...'",
            thought_process=f"แตกสับงานคำสั่งให้ลูกทีมแผนก {dept_name} ปฏิบัติการทันที",
        ))

        # 2. Log ลูกทีมตำแหน่งงานย่อย (Sub-agent Workers Task Logging - ข้อ 2)
        write_log(LogCreate(
            agent_id=dept_id,
            agent_name=f"{dept_name} Specialist",
            level=LogLevel.SUCCESS,
            message=f"⚡ [{dept_name} Specialist] ร่างและประมวลผลภารกิจย่อยสำเร็จ",
            thought_process=f"ดำเนินการตามคำสั่ง: {message}",
        ))

        # 3. ส่งข้อความ Push แจ้งเตือนกลับไปยัง Telegram 1-on-1 ของ Owner (ข้อ 4)
        owner_chat = TELEGRAM_OWNER_DIRECT_CHAT_ID or os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
        if owner_chat:
            push_msg = (
                f"<b>[รายงานการปฏิบัติงานจาก {pm_name}]</b>\n"
                f"✅ <b>สถานะ:</b> รับคำสั่งจากห้องประชุมและสั่งลูกทีมแผนก {dept_name} ปฏิบัติงานเสร็จเรียบร้อยแล้วครับ!\n\n"
                f"📌 <b>ภารกิจ:</b> {message}\n"
                f"📋 <b>สรุปผลงาน:</b>\n{reply[:250]}...\n\n"
                f"🌐 <i>สามารถคลิกเข้าชม Log การทำงานของลูกทีมฉบับเต็มได้ที่หน้าเว็บครับ!</i>"
            )
            bot_token_to_use = pm_bot_token or get_bot_token()
            if bot_token_to_use:
                url = f"https://api.telegram.org/bot{bot_token_to_use}/sendMessage"
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(url, json={"chat_id": owner_chat, "text": clean_telegram_html(push_msg), "parse_mode": "HTML"})
                except Exception as e:
                    logger.warning(f"Telegram push error: {e}")

    # กำหนดผู้ตอบจริง
    if mentioned_info:
        responder_name = mentioned_info.get("pm_name", f"PM {mentioned_info.get('name')}")
        responder_avatar = "🤖"
    else:
        responder_name = "อิงฟ้า (เลขา AI)"
        responder_avatar = "🗂️"

    return {
        "status": "success",
        "agent_name": responder_name,
        "responder_name": responder_name,
        "responder_avatar": responder_avatar,
        "message": message,
        "reply": reply,
        "mentioned_pm": mentioned_info.get("pm_name") if mentioned_info else None,
        "created_at": datetime.now().isoformat()
    }


async def run_department_direct_command(dept_id: str, message: str) -> dict:
    """สั่งงานตรงไปยังหัวหน้าแผนก (PM) ของแผนกนั้นๆ บน Web UI"""
    dept_rooms = get_all_department_rooms()
    dept_info = dept_rooms.get(dept_id, {})
    dept_name = dept_info.get("name", dept_id)
    pm_name = dept_info.get("pm_name", f"PM {dept_name}")
    pm_bot_token = dept_info.get("bot_token", "")

    from backend.services.llm_service import LLMService
    llm = LLMService(model="gemini-1.5-flash", temperature=0.5)

    system_instruction = (
        f"คุณคือ '{pm_name}' และทีมงานประจำแผนก {dept_name} ของบริษัท One-Person AI Enterprise\n"
        f"บทบาท: รับคำสั่งตรงจาก Owner วิเคราะห์งานของแผนกตนเอง วาง Deliverables และเริ่มปฏิบัติงานทันที\n"
        f"ข้อแนะนำ: ตอบในนาม '{pm_name}' อย่างกระตือรือร้น สุภาพ สรุปงานที่จะทำให้ Owner ทราบสั้นๆ พร้อมแจ้งว่าจะเริ่มดำเนินการทันที"
    ) + _get_owner_prompt_context()

    reply = await llm.generate(system_instruction=system_instruction, user_message=message)

    # 1. Log หัวหน้าทีม PM รับคำสั่ง
    write_log(LogCreate(
        agent_id=dept_id,
        agent_name=pm_name,
        level=LogLevel.INFO,
        message=f"📌 [{pm_name}] รับคำสั่งตรง: '{message[:50]}...'",
        thought_process=reply,
    ))

    # 2. Log ลูกทีมตำแหน่งงานย่อย (Sub-agent Workers Task Logging - ข้อ 2)
    write_log(LogCreate(
        agent_id=dept_id,
        agent_name=f"{dept_name} Execution Team",
        level=LogLevel.SUCCESS,
        message=f"⚡ [{dept_name} Execution Team] ปฏิบัติงานย่อยตามคำสั่งสำเร็จ",
        thought_process=f"ส่งมอบผลงานของแผนก {dept_name}",
    ))

    # 3. ส่งข้อความ Push แจ้งเตือนกลับไปยัง Telegram 1-on-1 ของ Owner
    owner_chat = TELEGRAM_OWNER_DIRECT_CHAT_ID or os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
    if owner_chat:
        push_msg = (
            f"<b>[รายงานการปฏิบัติงานจาก {pm_name}]</b>\n"
            f"✅ <b>สถานะ:</b> สั่งการและควบคุมลูกทีมแผนก {dept_name} ปฏิบัติงานเสร็จเรียบร้อยแล้วครับ!\n\n"
            f"📌 <b>คำสั่ง:</b> {message}\n"
            f"📋 <b>สรุปผลงาน:</b>\n{reply[:250]}...\n\n"
            f"🌐 <i>สามารถคลิกเข้าชมรายละเอียดผลงานของลูกทีมฉบับเต็มทางหน้าเว็บได้ครับ!</i>"
        )
        bot_token_to_use = pm_bot_token or get_bot_token()
        if bot_token_to_use:
            try:
                url = f"https://api.telegram.org/bot{bot_token_to_use}/sendMessage"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(url, json={"chat_id": owner_chat, "text": clean_telegram_html(push_msg), "parse_mode": "HTML"})
            except Exception as e:
                logger.warning(f"Telegram push error: {e}")

    return {
        "status": "success",
        "dept_id": dept_id,
        "dept_name": dept_name,
        "pm_name": pm_name,
        "message": message,
        "reply": reply,
        "created_at": datetime.now().isoformat()
    }




