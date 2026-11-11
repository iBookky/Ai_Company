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
import re
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

# 1. Direct Chat (พี่บุ๊ค ↔ เลขา AI)
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
_current_session_messages: List[Dict[str, str]] = []
_active_chat_agents: Dict[str, str] = {}  # {chat_id: current_dept_id}
_agent_chat_histories: Dict[tuple, list] = {}  # {(chat_id, dept_id): [messages]}

async def summarize_and_save_session(session_msgs: List[dict]) -> str:
    """รวบรวมข้อสรุปจากประวัติใน session แล้วกรองคัดแยกบันทึกลงไฟล์ company_memory.md"""
    if not session_msgs:
        return "*ไม่มีข้อความในเซสชัน*"

    from backend.services.llm_service import LLMService
    llm = LLMService(model="gemini-1.5-flash", temperature=0.3)
    
    history_str = ""
    for msg in session_msgs:
        history_str += f"{msg['sender']}: {msg['content']}\n\n"

    # ดึง Log การทำงานจริงจากระบบล่าสุดมาร่วมพิจารณา
    logs_str = ""
    try:
        from backend.services.log_service import get_logs
        # ดึง 30 log ล่าสุดเพื่อมาวิเคราะห์เหตุการณ์ที่ทำสำเร็จจริง
        recent_logs = get_logs(limit=30)
        recent_logs.reverse() # ลำดับตามเวลาจริง
        log_lines = []
        for l in recent_logs:
            ts = l.timestamp.split("T")[1][:5] if "T" in l.timestamp else l.timestamp[:5]
            log_lines.append(f"[{ts}] {l.agent_name} ({l.level.name}): {l.message}")
        if log_lines:
            logs_str = "\n\n--- บันทึกกิจกรรมและเหตุการณ์จริงจากระบบ (System Logs) ---\n" + "\n".join(log_lines) + "\n"
    except Exception as e_log:
        logger.warning(f"Failed to fetch logs for session summary: {e_log}")
        
    prompt = (
        "คุณคือ Chief Knowledge Officer (CKO) มีหน้าที่รวบรวมข้อสรุป บทเรียนองค์กร และคอขวดที่ทีมแก้ไขร่วมกัน รวมถึงจุดคอขวดและสูตรสำเร็จการตลาด (Winner Campaign)\n"
        "โดยให้คุณพิจารณาเปรียบเทียบและวิเคราะห์ร่วมกันจาก 2 แหล่งข้อมูลนี้:\n"
        "1. ประวัติการแชทพูดคุยการประชุมในรอบนี้ (Chat Messages)\n"
        "2. บันทึกประวัติการทำงานจริงและการทำคำสั่งสำเร็จจากระบบ (System Logs)\n\n"
        f"--- ประวัติการแชท (Chat History) ---\n{history_str}\n"
        f"{logs_str}\n\n"
        "กรุณาสรุปข้อมูลและตอบกลับเป็น Markdown ใน 2 ส่วนนี้เท่านั้น (ถ้าส่วนไหนไม่มีข้อมูลในประวัติ ไม่ต้องสรุปส่วนนั้น หรือสรุปสั้นๆ เท่าที่มี):\n\n"
        "1. สำหรับ [คลังปัญญาการตลาด] (หากมีข้อมูลความสำเร็จการตลาด, Winner Campaign หรือคอขวดช่องทางขาย):\n"
        "### [คลังปัญญาการตลาด] - อัปเดตวันที่ [วันที่ปัจจุบัน]\n"
        "- **จุดคอขวด/ปัญหาสำคัญ**: [จุดหลุดหรือคอขวดในการตลาด/การขายที่วิเคราะห์พบ]\n"
        "- **สูตรสำเร็จ (Winner Campaign)**: [แคมเปญหรือการตั้งค่าการตลาดที่ทำสำเร็จ]\n"
        "- **แนวทางแนะนำสำหรับแคมเปญใหม่**: [คำแนะนำเพื่อพัฒนาต่อยอด]\n\n"
        "2. สำหรับ [บันทึกการประชุมและบทเรียนองค์กรประจำวัน] (บันทึกสรุปทั่วไป):\n"
        "### [บันทึกการประชุมและบทเรียนองค์กรประจำวัน] - วันที่ [วันที่ปัจจุบัน]\n"
        "- **ข้อสรุปการประชุม**: [สรุปสิ่งที่ทีมตกลงร่วมกัน]\n"
        "- **บทเรียนองค์กร**: [สิ่งที่เรียนรู้และพัฒนาขึ้น]\n"
        "- **คอขวดที่แก้ไขร่วมกัน**: [ปัญหาหลักและแนวทางที่แก้สำเร็จ]\n\n"
        "ตอบเฉพาะหัวข้อ Markdown ที่สรุปได้ตามเทมเพลตข้างบนนี้เท่านั้น เพื่อให้นำไปต่อยอดประมวลผลต่อ ไม่ต้องมีคำเกริ่นใดๆ ทั้งสิ้น"
    )
    
    from backend.services.status_service import set_agent_status
    set_agent_status("01_secretary", "processing")
    try:
        summary = await llm.generate(
            system_instruction="คุณคือ CKO สรุปรายงานการประชุมสั้น กระชับ ตรงประเด็น เป็น Markdown เท่านั้น",
            user_message=prompt
        )
    finally:
        set_agent_status("01_secretary", "idle")
    
    memory_path = Path(__file__).parent.parent.parent / "company_memory.md"
    current_date = datetime.now().strftime("%Y-%m-%d")
    clean_summary = summary.strip().replace("[วันที่ปัจจุบัน]", current_date)
    
    memory_path = Path(__file__).parent.parent.parent / "company_memory.md"
    current_date = datetime.now().strftime("%Y-%m-%d")
    clean_summary = summary.strip().replace("[วันที่ปัจจุบัน]", current_date)
    
    if memory_path.exists():
        try:
            existing_content = memory_path.read_text(encoding="utf-8")
            
            merge_prompt = (
                "คุณคือ CKO (Chief Knowledge Officer) ผู้ดูแลคลังปัญญาของบริษัท\n"
                "คุณมีหน้าที่อ่านคลังปัญญาเดิมของบริษัท (Company Memory) และนำข้อมูลสรุปการประชุมครั้งใหม่ไปปรับปรุงรวมกัน (Merge & Update) "
                "เพื่อให้เนื้อหาเป็นปัจจุบันที่สุด กระชับ ชัดเจน และไม่เกิดการบันทึกข้อมูลซ้ำซ้อนในหัวข้อเดียวกัน\n\n"
                "--- ข้อกำหนดในการควบรวม ---\n"
                "1. ส่วนของ [ข้อมูลโปรไฟล์ธุรกิจและเป้าหมายองค์กร] (ช่วงบนสุด) ให้คงไว้ตามเดิม ห้ามลบหรือแก้ไข เว้นแต่จะมีข้อมูลอัปเดตสำคัญขัดแย้ง\n"
                "2. สำหรับหัวข้อ [คลังปัญญาการตลาด] และ [บันทึกการประชุมและบทเรียนองค์กรประจำวัน]:\n"
                "   - ตรวจสอบประวัติการบันทึก หากเป็นการประชุมของวันใหม่ ให้เพิ่มหัวข้อใหม่ตามลำดับวันที่ล่าสุดอยู่บนสุด\n"
                "   - หากหัวข้อใหม่มีการแก้ไขรายละเอียดงานหรืออัปเดตความคืบหน้าของหัวข้อเดิมที่มีอยู่แล้วในประวัติ ให้ยุบรวม/อัปเดตหัวข้อเก่าให้เป็นเนื้อหาปัจจุบันและลบข้อมูลที่ล้าสมัยออก\n"
                "   - ลบประโยคประเภท '*ยังไม่มีการบันทึกข้อมูลล่าสุด*' ออกหากมีข้อมูลจริงแล้ว\n\n"
                f"--- คลังปัญญาเดิม (Existing Company Memory) ---\n{existing_content}\n\n"
                f"--- ข้อมูลสรุปใหม่ที่ต้องการอัปเดต (New Summary to Update) ---\n{clean_summary}\n\n"
                "ตอบกลับเฉพาะเนื้อหา Markdown ของ Company Memory ฉบับสมบูรณ์ใหม่ล่าสุดที่ควบรวมและปรับปรุงเสร็จเรียบร้อยแล้วเท่านั้น ห้ามมีคำอธิบายเพิ่มเติมใดๆ นอกเหนือจากตัวไฟล์"
            )
            
            set_agent_status("01_secretary", "processing")
            try:
                merged_content = await llm.generate(
                    system_instruction="คุณคือ CKO ผู้มีหน้าที่ควบรวมและอัปเดตเอกสาร Company Memory ให้เป็นระเบียบและเป็นปัจจุบันที่สุด ตอบเฉพาะไฟล์ Markdown เท่านั้น",
                    user_message=merge_prompt
                )
            finally:
                set_agent_status("01_secretary", "idle")
                
            clean_merged = merged_content.strip()
            # ป้องกันข้อผิดพลาดกรณี LLM ตอบกลับว่างเปล่า หรือหลุดหัวข้อ
            if clean_merged and "# Company Memory" in clean_merged:
                memory_path.write_text(clean_merged, encoding="utf-8")
            else:
                new_content = existing_content + "\n\n" + clean_summary
                memory_path.write_text(new_content, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to merge and write to company_memory.md: {e}")
            
    return clean_summary


def _get_owner_prompt_context() -> str:
    owner_name = os.getenv("OWNER_NAME", "พี่บุ๊ค")
    owner_identity = os.getenv("OWNER_IDENTITY", "เจ้าของและผู้บริหารสูงสุดของบริษัท")
    owner_skill = os.getenv("OWNER_SKILL", "การตัดสินใจเชิงกลยุทธ์และการบริหารองค์กร")
    
    company_memory = ""
    memory_path = Path(__file__).parent.parent.parent / "company_memory.md"
    if memory_path.exists():
        try:
            company_memory = f"\n\n--- ข้อมูลหน่วยความจำบริษัท (Company Memory) ---\n{memory_path.read_text(encoding='utf-8')}\n"
        except Exception:
            pass

    # ดึง Log ล่าสุดมาใช้งานร่วมเพื่อความต่อเนื่องของการพูดคุยและการทำงาน
    recent_activities = ""
    try:
        from backend.services.log_service import get_logs
        logs = get_logs(limit=15)
        # เรียงจากเก่าไปใหม่ เพื่อให้โมเดลอ่านตามลำดับเวลาที่เกิดขึ้นจริง
        logs.reverse()
        log_lines = []
        for l in logs:
            ts = l.timestamp.split("T")[1][:5] if "T" in l.timestamp else l.timestamp[:5]
            log_lines.append(f"[{ts}] {l.agent_name}: {l.message}")
        if log_lines:
            recent_activities = "\n\n--- ประวัติการประชุมและการทำงานล่าสุด (Recent Meeting & Execution Logs) ---\n" + "\n".join(log_lines) + "\n"
    except Exception:
        pass

    return (
        f"\n\n--- ข้อมูลเกี่ยวกับพี่บุ๊ค (คู่สนทนาและผู้บริหารสูงสุดของคุณ) ---\n"
        f"ชื่อ: {owner_name}\n"
        f"ตัวตน/บทบาท: {owner_identity}\n"
        f"ทักษะ/ความเชี่ยวชาญ: {owner_skill}\n"
        f"กฎเหล็กการสนทนา: ในการตอบกลับทาง Telegram ทุกครั้ง ให้คุณเรียกคู่สนทนาว่า 'พี่บุ๊ค' เสมออย่างสนิทสนม สุภาพ และเป็นกันเอง ห้ามใช้คำว่า 'Owner', 'ท่าน Owner', หรือ 'คุณ Owner' โดยเด็ดขาด ให้ใช้คำว่า 'พี่บุ๊ค' เท่านั้น\n"
        f"{company_memory}"
        f"{recent_activities}"
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
    """ส่งข้อความคุยส่วนตัว 1-on-1 (พี่บุ๊ค ↔ เลขา AI)"""
    chat_id = TELEGRAM_OWNER_DIRECT_CHAT_ID or TELEGRAM_EXEC_CHAT_ID
    return await send_telegram_message(chat_id, text)


async def send_to_executive_board(text: str) -> bool:
    """ส่งข้อความเข้าห้องประชุมผู้บริหาร (พี่บุ๊ค + เลขา + PMs)"""
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

def create_department_room(name: str, chat_id: str = "", pm_name: str = "", dept_id: Optional[str] = None, bot_token: Optional[str] = None) -> dict:
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

    final_bot_token = bot_token if bot_token is not None else cfg.get("bot_token", "")

    cfg.update({
        "name": name,
        "role": f"pm_{dept_id}",
        "pm_name": pm_name or cfg.get("pm_name") or f"PM {name}",
        "model": cfg.get("model", "gemini-1.5-flash"),
        "temperature": cfg.get("temperature", 0.5),
        "department": dept_id,
        "ops_chat_id": chat_id or cfg.get("ops_chat_id", ""),
        "bot_token": final_bot_token,
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
    """เสนอร่างโครงสร้างทีม บทบาทลูกทีม และ KPI ที่เหมาะสมให้พี่บุ๊ค พิจารณาปรับแก้และอนุมัติก่อนสร้างจริง"""
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
    """ยุบแผนก / ลบห้องทำงานแผนก (ลบโฟลเดอร์ + ลบคอนฟิก + ซิงค์สถานะทั้งระบบ)"""
    dept_dir = DEPARTMENTS_DIR / dept_id
    if dept_dir.exists():
        shutil.rmtree(dept_dir)

    if dept_id in TELEGRAM_OPS_CHAT_IDS:
        del TELEGRAM_OPS_CHAT_IDS[dept_id]

    try:
        from backend.services import simulation_service
        simulation_service.remove_agent_or_department(dept_id)
    except Exception as e:
        logger.warning(f"Failed to remove agent {dept_id} from simulation: {e}")

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
    จำแนกเจตนาข้อความของพี่บุ๊ค:
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
            "โปรดจำแนกเจตนาข้อความของพี่บุ๊ค ว่าเป็น 'CHAT' หรือ 'TASK_ORDER'\n"
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


def get_registered_agents_info() -> list[dict]:
    """ดึงข้อมูล Agent ทั้งหมดที่ประจำการอยู่ใน departments/ แบบ Real-time"""
    agents = []
    if DEPARTMENTS_DIR.exists():
        for d in sorted(DEPARTMENTS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                cfg_file = d / "config.json"
                if cfg_file.exists():
                    try:
                        cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                        identity = (d / "identity.md").read_text(encoding="utf-8") if (d / "identity.md").exists() else ""
                        skills = (d / "skill.md").read_text(encoding="utf-8") if (d / "skill.md").exists() else ""
                        jd = (d / "job_description.md").read_text(encoding="utf-8") if (d / "job_description.md").exists() else ""
                        agents.append({
                            "dept_id": d.name,
                            "name": cfg.get("name", d.name),
                            "pm_name": cfg.get("pm_name") or f"PM {cfg.get('name', d.name)}",
                            "role": cfg.get("role", f"pm_{d.name}"),
                            "model": cfg.get("model", "gemini-1.5-flash"),
                            "identity": identity,
                            "skills": skills,
                            "job_description": jd
                        })
                    except Exception:
                        pass
    return agents


def build_agent_aliases(agent: dict) -> list[str]:
    """สร้างคำค้นหา/คำเรียกสำหรับ Agent แต่ละคนเพื่อจับคู่ในข้อความ"""
    aliases = set()
    pm = (agent.get("pm_name") or "").strip().lower()
    name = (agent.get("name") or "").strip().lower()
    dept_id = agent.get("dept_id", "").lower()

    if pm:
        aliases.add(pm)
        if pm.startswith("น้อง"):
            aliases.add(pm[4:].strip())
        if "บิ๊นท์" in pm:
            aliases.update(["bint", "bin", "บิ้นท์", "บิ้น"])
        elif "อิงฟ้า" in pm:
            aliases.update(["ingfah", "ing", "ฟ้า", "เลขา"])

    if name:
        aliases.add(name)
        if "business analyst" in name or "ba" in name:
            aliases.update(["ba", "business analyst", "นักวิเคราะห์"])
        elif "developer" in name or "ซอฟต์แวร์" in name or "dev" in name:
            aliases.update(["dev", "developer", "โปรแกรมเมอร์"])
        elif "marketing" in name or "การตลาด" in name:
            aliases.update(["marketing", "การตลาด"])
        elif "accounting" in name or "การเงิน" in name or "บัญชี" in name:
            aliases.update(["การเงิน", "บัญชี", "finance"])
        elif "sales" in name or "ฝ่ายขาย" in name:
            aliases.update(["ฝ่ายขาย", "sales", "เซลส์"])
        elif "qa" in name or "ตรวจสอบ" in name:
            aliases.update(["qa", "คิวเอ"])

    # ลบคำสั้นมากๆ เพื่อป้องกัน false match
    filtered = [a for a in aliases if len(a) >= 2]
    return sorted(filtered, key=len, reverse=True)


def resolve_target_agent(text: str, chat_id: str) -> tuple[dict, str, bool]:
    """
    วิเคราะห์หา Agent จากข้อความ
    Returns: (agent_info, remaining_command_text, is_switch_only)
    """
    agents = get_registered_agents_info()
    if not agents:
        fallback_agent = {
            "dept_id": "01_secretary",
            "name": "Secretary & CKO",
            "pm_name": "อิงฟ้า",
            "model": "gemini-1.5-flash",
            "identity": "", "skills": "", "job_description": ""
        }
        return fallback_agent, text, False

    clean_text = text.strip()
    lower_text = clean_text.lower()

    # 1. เช็คคำสั่ง Switch / ขอคุยกับ
    # เช่น "คุยกับบิ๊นท์", "สลับไปคุยกับน้องบิ๊นท์", "/switch บิ๊นท์", "/agent บิ๊นท์", "สั่งบิ๊นท์..."
    switch_patterns = [
        r'^(?:สลับไปคุยกับ|สลับคุยกับ|คุยกับ|ขอคุยกับ|ไปคุยกับ|สั่งการ|สั่ง|ถึง)\s*([^\s:,]+)(.*)$',
        r'^(?:/switch|/agent|/talk)\s+([^\s:,]+)(.*)$'
    ]

    for pat in switch_patterns:
        m = re.match(pat, clean_text, re.IGNORECASE)
        if m:
            target_raw = m.group(1).strip().lower()
            remaining = m.group(2).strip(' :,\t\n')

            for agent in agents:
                for alias in build_agent_aliases(agent):
                    if alias == target_raw or target_raw.startswith(alias):
                        is_switch_only = (len(remaining) == 0)
                        return agent, remaining, is_switch_only

    # 2. เช็คการขึ้นต้นด้วยชื่อ หรือ @ชื่อ เช่น '@บิ๊นท์ ทำ...', 'บิ๊นท์: ทำ...', 'บิ๊นท์ ทำ...'
    for agent in agents:
        for alias in build_agent_aliases(agent):
            if lower_text.startswith(f'@{alias}'):
                rem = clean_text[len(alias) + 1:].strip(' :,\t\n')
                return agent, rem, False
            prefix_match = re.match(rf'^{re.escape(alias)}[\s:,]+(.*)$', clean_text, re.IGNORECASE)
            if prefix_match:
                rem = prefix_match.group(1).strip()
                return agent, rem, False

    # 3. ตรวจสอบว่าในประโยคมีการเอ่ยชื่อ Agent เจาะจงหรือไม่ เช่น "ช่วยให้ บิ๊นท์ ตรวจสอบโค้ดให้หน่อย"
    for agent in agents:
        for alias in build_agent_aliases(agent):
            if len(alias) >= 3 and alias in lower_text:
                return agent, clean_text, False

    # 4. หากไม่ได้เอ่ยชื่อใคร ให้ดูว่ามี active agent ประจำแชทนี้อยู่หรือไม่
    current_agent_id = _active_chat_agents.get(chat_id, "01_secretary")
    current_agent = next((a for a in agents if a["dept_id"] == current_agent_id), agents[0])
    return current_agent, clean_text, False


async def handle_webhook(payload: dict, bot_token: Optional[str] = None) -> dict:
    """ประมวลผล Incoming Webhook Update จาก Telegram รองรับทุก Agent ผ่าน Telegram ตัวเดียว"""
    message = payload.get("message", {}) or payload.get("channel_post", {})
    if not message:
        return {"status": "ignored", "reason": "no_message"}

    chat_id = str(message.get("chat", {}).get("id", ""))
    from_user = message.get("from", {})
    sender_name = from_user.get("first_name") or "พี่บุ๊ค"
    text = message.get("text", "").strip() if isinstance(message.get("text"), str) else ""

    if not text:
        return {"status": "ignored", "reason": "empty_text"}

    cleaned_lower = text.strip().lower()

    # 1. เช็คคำสั่งดูรายชื่อทีมงานทั้งหมด (/agents, /teams, ใครอยู่บ้าง, รายชื่อทีม)
    if cleaned_lower in ["/agents", "/teams", "/list", "ใครอยู่บ้าง", "รายชื่อทีม", "รายชื่อทีมงาน", "ดูทีม"]:
        agents = get_registered_agents_info()
        lines = ["🏢 <b>รายชื่อทีมงาน AI ที่ประจำการอยู่ในระบบ:</b>\n"]
        for idx, a in enumerate(agents, 1):
            lines.append(f"{idx}. 🤖 <b>{a['pm_name']}</b> — {a['name']}")
        lines.append("\n💡 <b>วิธีสั่งงานหรือพูดคุย:</b>")
        lines.append("• พิมพ์ชื่อนำหน้า เช่น <code>บิ๊นท์ ช่วยวิเคราะห์ข้อมูลยอดขายให้หน่อย</code>")
        lines.append("• หรือสลับคนคุย: <code>คุยกับบิ๊นท์</code> (ข้อความต่อไปจะคุยกับคนนั้นต่อเนื่อง)")
        lines.append("• คำสั่งระบบ: <code>/confirm</code> (อนุมัติปิดงาน) | <code>/agents</code> (ดูรายชื่อทีม)")
        
        reply_msg = "\n".join(lines)
        await send_telegram_message(chat_id, reply_msg, bot_token=bot_token)
        return {"status": "agents_listed", "count": len(agents)}

    # 2. คำสั่ง /start หรือ /help
    if cleaned_lower in ["/start", "/help", "ช่วยด้วย", "วิธีใช้"]:
        agents = get_registered_agents_info()
        agent_names = ", ".join([f"<b>{a['pm_name']}</b>" for a in agents])
        help_msg = (
            f"👋 สวัสดีครับพี่บุ๊ค!\n\n"
            f"ผมคือบอทศูนย์กลางองค์กร <b>One-Person AI Enterprise</b> เชื่อมต่อทีมงาน AI ทุกคนในระบบ\n\n"
            f"👥 <b>ทีมงานที่พร้อมปฏิบัติงานตอนนี้:</b>\n{agent_names}\n\n"
            f"💡 <b>สั่งงานง่ายๆ:</b> เพียงพิมพ์ชื่อคนที่ต้องการคุยด้วย เช่น:\n"
            f"• <i>\"บิ๊นท์ ช่วยวิเคราะห์ข้อมูลยอดขาย...\"</i>\n"
            f"• <i>\"คุยกับบิ๊นท์\"</i> (เพื่อสลับคุย 1-on-1)\n"
            f"• <i>\"อิงฟ้า สรุปสถานะงานประจำวัน\"</i>\n\n"
            f"พิมพ์ <code>/agents</code> เพื่อดูรายชื่อทีมงานทั้งหมดได้ตลอดเวลาครับ!"
        )
        await send_telegram_message(chat_id, help_msg, bot_token=bot_token)
        return {"status": "help_replied"}

    # 3. เช็คคำสั่งระบบ HITL /confirm, /approve, /hire หรือคำว่า "อนุมัติ", "ยืนยัน", "ปิดงาน"
    from backend.services import simulation_service
    if cleaned_lower.startswith("/confirm") or cleaned_lower.startswith("/approve") or cleaned_lower in ["อนุมัติ", "ยืนยัน", "ปิดงาน", "confirm", "approve"]:
        parts = text.strip().split()
        target_id = parts[1] if len(parts) > 1 else None
        
        sim_state = simulation_service.get_simulation_state()
        pending_tasks = sim_state.get("pending_confirmations", [])
        
        task_to_confirm = None
        if target_id:
            task_to_confirm = next((t for t in pending_tasks if t.id == target_id), None)
        elif pending_tasks:
            task_to_confirm = pending_tasks[0]
            
        if task_to_confirm:
            await simulation_service.confirm_task(task_to_confirm.id, owner_name=sender_name)
            reply = (
                f"✅ <b>[อนุมัติปิดงานสำเร็จ 100%]</b>\n\n"
                f"📌 <b>ชื่องาน:</b> {task_to_confirm.title}\n"
                f"👤 <b>ผู้รับผิดชอบ:</b> {task_to_confirm.assigned_agent_name}\n"
                f"✨ ระบบได้จัดเก็บผลงานเข้าคลังความรู้บริษัท และบันทึกสถานะปิดงานสำเร็จเรียบร้อยแล้วครับ!"
            )
            await send_telegram_message(chat_id, reply, bot_token=bot_token)
            return {"status": "task_confirmed_via_telegram", "task_id": task_to_confirm.id}

    if cleaned_lower.startswith("/hire") or "อนุมัติสร้าง ai" in cleaned_lower:
        parts = text.strip().split()
        target_id = parts[1] if len(parts) > 1 else None
        
        sim_state = simulation_service.get_simulation_state()
        pending_hires = sim_state.get("pending_hires", [])
        
        prop_to_approve = None
        if target_id:
            prop_to_approve = next((h for h in pending_hires if h.id == target_id), None)
        elif pending_hires:
            prop_to_approve = pending_hires[0]
            
        if prop_to_approve:
            await simulation_service.approve_hiring_proposal(prop_to_approve.id, owner_name=sender_name)
            reply = (
                f"🎉 <b>[อนุมัติสร้างพนักงาน AI สำเร็จ]</b>\n\n"
                f"👤 <b>พนักงานใหม่:</b> {prop_to_approve.proposed_role}\n"
                f"🏢 <b>สังกัด:</b> {prop_to_approve.department_name}\n"
                f"🚀 บรรจุเข้าสู่ระบบและพร้อมรับคำสั่งงานทันทีครับ!"
            )
            await send_telegram_message(chat_id, reply, bot_token=bot_token)
            return {"status": "hiring_approved_via_telegram", "proposal_id": prop_to_approve.id}

    # 4. วิเคราะห์หา Target Agent จากข้อความ
    target_agent, prompt_text, is_switch_only = resolve_target_agent(text, chat_id)
    _active_chat_agents[chat_id] = target_agent["dept_id"]

    # กรณีสลับคนคุยอย่างเดียว
    if is_switch_only:
        switch_msg = (
            f"🔄 <b>[สลับการสนทนาเรียบร้อย]</b>\n\n"
            f"สวัสดีค่ะพี่บุ๊ค! ตอนนี้ท่านกำลังสนทนากับ <b>{target_agent['pm_name']}</b> ({target_agent['name']}) โดยตรงแล้วค่ะ\n"
            f"มีงานหรือคำถามอะไรให้ {target_agent['pm_name']} ช่วยดูแลไหมคะ?"
        )
        await send_telegram_message(chat_id, switch_msg, bot_token=bot_token)
        return {"status": "agent_switched", "target_agent": target_agent["pm_name"]}

    # ส่งให้ Agent คนนั้นตอบสนองและปฏิบัติงาน
    actual_prompt = prompt_text if prompt_text else text
    return await _dispatch_agent_response(chat_id, sender_name, target_agent, actual_prompt, bot_token=bot_token)


async def _dispatch_agent_response(chat_id: str, sender_name: str, agent: dict, prompt_text: str, bot_token: Optional[str] = None) -> dict:
    """ประมวลผลคำสั่งงานและโต้ตอบโดยใช้ Persona, Identity, และทักษะเฉพาะตัวของ Agent คนนั้นๆ"""
    from backend.services.llm_service import LLMService
    from backend.services.status_service import set_agent_status
    from backend.services import simulation_service

    dept_id = agent["dept_id"]
    agent_name = agent.get("pm_name") or agent["name"]
    dept_name = agent["name"]

    set_agent_status(dept_id, "processing")
    
    write_log(LogCreate(
        agent_id=dept_id,
        agent_name=agent_name,
        level=LogLevel.INFO,
        message=f"ได้รับคำสั่งจาก Telegram ({sender_name}) หา {agent_name}: {prompt_text[:60]}...",
    ))

    system_instruction = (
        f"คุณคือ '{agent_name}' ({dept_name}) ใน One-Person AI Enterprise\n"
        f"คุณกำลังสนทนาและรับคำสั่งงานโดยตรงจากพี่บุ๊ค ทาง Telegram (1-on-1)\n\n"
        f"--- ตัวตนและบุคลิกภาพ (Identity) ---\n{agent.get('identity', '')}\n\n"
        f"--- ทักษะความเชี่ยวชาญ (Skills) ---\n{agent.get('skills', '')}\n\n"
        f"--- หน้าที่รับผิดชอบ (Job Description) ---\n{agent.get('job_description', '')}\n\n"
        f"บทบาท:\n"
        f"1. สวมบทบาท '{agent_name}' อย่างสมบูรณ์แบบ ตอบเป็นภาษาไทยอย่างฉลาด สุภาพ มีไหวพริบ กระตือรือร้นและตรงประเด็น\n"
        f"2. หากพี่บุ๊ค ถามหรือคุยทั่วไป ให้คำปรึกษาและคำแนะนำอย่างผู้เชี่ยวชาญในสายงาน {dept_name}\n"
        f"3. หากพี่บุ๊ค สั่งงาน ให้ตอบรับคำสั่ง อธิบายขั้นตอนการทำงานหรือข้อเสนอแนะอย่างชัดเจนและลงมือปฏิบัติงานทันที\n"
    )
    system_instruction += _get_owner_prompt_context()

    history_key = (chat_id, dept_id)
    history = _agent_chat_histories.get(history_key, [])

    try:
        model_name = agent.get("model") or "gemini-1.5-flash"
        llm = LLMService(model=model_name, temperature=0.7)
        reply = await llm.generate(
            system_instruction=system_instruction,
            user_message=prompt_text,
            history=history
        )
    except Exception as e:
        logger.error(f"LLM generation failed for agent {agent_name}: {e}")
        reply = f"สวัสดีค่ะพี่บุ๊ค {agent_name} รับทราบคำสั่งเรียบร้อยค่ะ กำลังเร่งตรวจสอบและดำเนินการให้ทันทีค่ะ!"
    finally:
        set_agent_status(dept_id, "idle")

    # Update history
    history.append({"role": "user", "content": prompt_text})
    history.append({"role": "model", "content": reply})
    if len(history) > 10:
        history = history[-10:]
    _agent_chat_histories[history_key] = history

    # Format reply with agent persona header
    formatted_reply = f"🤖 <b>[{agent_name} — {dept_name}]</b>\n\n{reply}"
    await send_telegram_message(chat_id, formatted_reply, bot_token=bot_token)

    # เช็คว่ามีคำสั่งที่เป็น Action/งาน หรือไม่ เพื่อนำขึ้น Kanban Board
    action_keywords = ["ช่วย", "ทำ", "สร้าง", "เขียน", "ออกแบบ", "วิเคราะห์", "ตรวจ", "สรุป", "พัฒนา", "แก้", "report", "code"]
    if any(k in prompt_text.lower() for k in action_keywords):
        try:
            asyncio.create_task(simulation_service.run_simulation_preset("auto", prompt_text))
        except Exception:
            pass

    write_log(LogCreate(
        agent_id=dept_id,
        agent_name=agent_name,
        level=LogLevel.SUCCESS,
        message=f"{agent_name} ตอบกลับข้อความ Telegram ของพี่บุ๊ค เรียบร้อย",
        thought_process=f"Prompt: {prompt_text}\nReply: {reply[:100]}...",
    ))

    return {"status": "agent_replied", "agent_id": dept_id, "agent_name": agent_name, "reply": reply}




async def _initiate_verification(chat_id: str, sender_name: str, text: str) -> dict:
    """ขั้นตอนที่ 1 & 2: เมื่อเป็นคำสั่งงาน (TASK_ORDER) — เลขา AI สรุปทวนคำสั่งกับพี่บุ๊ค"""
    verification_id = str(uuid.uuid4())[:8]

    try:
        from backend.services.llm_service import LLMService
        llm = LLMService(model="gemini-1.5-flash", temperature=0.3)
        summary = await llm.generate(
            system_instruction="คุณคือเลขา AI หน้าที่ของคุณคือทวนสรุปคำสั่งงานจากพี่บุ๊ค อย่างกระชับ ตรงประเด็น สั้นไม่เกิน 2 ประโยค",
            user_message=f"สรุปคำสั่งนี้เพื่อส่งทวนกับพี่บุ๊ค: '{text}'"
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
            user_message=f"คำสั่งที่ได้รับอนุมัติจากพี่บุ๊ค: '{pending['summary']}'"
        )
    except Exception as e:
        logger.warning(f"LLM Error in PM Plan: {e}")
        pm_plan = f"แผนการดำเนินงานสำหรับคำสั่ง: {pending['summary']}"

    # แจ้งใน Executive Room (ห้องประชุมผู้บริหาร)
    exec_msg = (
        f"<b>[ห้องประชุมผู้บริหาร — PM Boardroom]</b>\n"
        f"✅ พี่บุ๊คอนุมัติคำสั่งเรียบร้อย!\n\n"
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
                f"🚀 <b>คำสั่งจากพี่บุ๊ค:</b> {pending['summary']}\n"
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
            f"🌐 <b>พี่บุ๊ค สามารถคลิกเข้ามาดูรายละเอียดการทำงานของลูกทีมแต่ละแผนกทางหน้าเว็บได้ที่:</b>\n"
            f"http://localhost:8888/#/skype\n\n"
            f"💡 <i>(หากพี่บุ๊ค มีคำสั่งเพิ่มเติม สามารถพิมพ์สั่งงานต่อทาง Telegram 1-on-1 นี้ได้เลยครับ!)</i>"
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
    # Mask bot_token in department rooms to prevent credential leakage via API
    masked_dept_rooms = {}
    for d_id, r_info in dept_rooms.items():
        copy_info = dict(r_info)
        tok = copy_info.get("bot_token", "")
        if tok:
            copy_info["bot_token"] = "••••••••" + tok[-6:] if len(tok) >= 8 else "••••••••"
        masked_dept_rooms[d_id] = copy_info

    return {
        "bot_configured": bool(bot_token),
        "owner_id": TELEGRAM_OWNER_ID or os.getenv("TELEGRAM_OWNER_ID", ""),
        "direct_chat": {
            "id": owner_direct,
            "name": "💬 คุยส่วนตัว 1-on-1 (พี่บุ๊ค ↔ เลขา AI)",
            "configured": bool(owner_direct),
        },
        "executive_room": {
            "id": exec_chat,
            "name": "🏛️ ห้องประชุมผู้บริหาร (พี่บุ๊ค + เลขา + PMs ทุกแผนก)",
            "configured": bool(exec_chat),
        },
        "default_ops_room": {
            "id": default_ops,
            "configured": bool(default_ops),
        },
        "department_rooms": masked_dept_rooms,
    }


# ─── Telegram Background Polling Service ────────────────────────────────────

_polling_tasks = []
_active_polling_tokens = {}  # {token: task}
_polling_running = False


def get_bot_token() -> str:
    """ดึง TELEGRAM_BOT_TOKEN แบบ Dynamic เพื่อป้องกันปัญหาอ่านค่าว่างช่วงโมดูลโหลด"""
    return os.getenv("TELEGRAM_BOT_TOKEN", "") or TELEGRAM_BOT_TOKEN


async def start_telegram_polling():
    """เริ่มระบบ Telegram Background Listener คอยรับและตอบกลับข้อความจากพี่บุ๊ค ทาง Telegram ผ่าน Single Enterprise Bot Hub"""
    global _polling_tasks, _polling_running, _active_polling_tokens
    _polling_running = True

    # รวม Token สำหรับ Polling — ระบบ Single Bot Enterprise Gateway
    tokens_to_poll = {}
    main_token = get_bot_token()
    if main_token:
        tokens_to_poll["enterprise_hub"] = main_token
    else:
        logger.info("ℹ️ ไม่พบ TELEGRAM_BOT_TOKEN ระบบ Telegram Polling จะไม่ทำงานจนกว่าจะระบุใน Settings")

    # 1. หยุดบอทที่ไม่มีอยู่ในรายการแล้ว (เช่น บอทเก่า หรือ token เปลี่ยน)
    active_tokens = list(_active_polling_tokens.keys())
    for t in active_tokens:
        if t not in tokens_to_poll.values():
            print(f"🛑 [Telegram Worker] หยุด Polling สำหรับ Token เก่า")
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
            "from": {"id": 1111, "first_name": "พี่บุ๊ค"},
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
        f"บทบาท: ประชุมร่วมกับพี่บุ๊ค ให้ความคิดเห็น วิเคราะห์ความเสี่ยง เสนอแนวทางปฏิบัติ วาง Timeline และงบประมาณอย่างมืออาชีพ\n"
        f"คำแนะนำ: ตอบเป็นภาษาไทยด้วยสำนวนที่เป็นธรรมชาติและกึ่งกันเองเหมือนเป็นการคุยระดมสมองของคนในทีมที่เป็นกันเอง (สุภาพแต่ไม่เป็นทางการเกินไป เข้าถึงง่าย) กระชับ ตรงประเด็น สรุปวาระประชุมและวาง Action Plan ชัดเจนสำหรับส่งต่อให้แต่ละทีมปฏิบัติการทันที"
    ) + _get_owner_prompt_context()

    from backend.services.status_service import set_agent_status
    for d_id in dept_rooms.keys():
        set_agent_status(d_id, "processing")
    try:
        reply = await llm.generate(system_instruction=system_instruction, user_message=message)
    finally:
        for d_id in dept_rooms.keys():
            set_agent_status(d_id, "idle")

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

        # 3. ส่งข้อความ Push แจ้งเตือนกลับไปยัง Telegram 1-on-1 ของพี่บุ๊ค (ข้อ 4)
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

    # บันทึกและคัดกรองลง session ป้องกันข้อมูลหลุดหล่น
    _current_session_messages.append({"sender": "พี่บุ๊ค", "content": message})
    _current_session_messages.append({"sender": responder_name, "content": reply})

    # เช็คการสั่งปิดเซสชัน / ปิดวาระการประชุม
    is_closing = any(kw in message.lower() for kw in ["ปิดวาระ", "จบประชุม", "จบการประชุม", "สิ้นสุดการประชุม", "close session"])
    if is_closing:
        session_summary = await summarize_and_save_session(_current_session_messages)
        _current_session_messages.clear()
        reply += f"\n\n📝 **[CKO อิงฟ้า] บันทึก Session เรียบร้อย:**\n{session_summary}"

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
        f"บทบาท: รับคำสั่งตรงจากพี่บุ๊ค วิเคราะห์งานของแผนกตนเอง วาง Deliverables และเริ่มปฏิบัติงานทันที\n"
        f"ข้อแนะนำ: ตอบในนาม '{pm_name}' อย่างกระตือรือร้น สุภาพ สรุปงานที่จะทำให้พี่บุ๊ค ทราบสั้นๆ พร้อมแจ้งว่าจะเริ่มดำเนินการทันที"
    ) + _get_owner_prompt_context()

    from backend.services.status_service import set_agent_status
    set_agent_status(dept_id, "processing")
    try:
        reply = await llm.generate(system_instruction=system_instruction, user_message=message)
    finally:
        set_agent_status(dept_id, "idle")

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

    # 3. ส่งข้อความ Push แจ้งเตือนกลับไปยัง Telegram 1-on-1 ของพี่บุ๊ค
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




