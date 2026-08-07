"""
scheduler_service.py — Automatic Daily Scheduler Service (Asia/Bangkok ICT GMT+7)
One-Person AI Enterprise

Triggers:
1. 08:30 AM ICT Daily: Morning Briefing — Pending tasks & priority task list sent by Secretary Engfa.
2. 18:00 PM ICT Daily: Evening Summary — EOD Work summary & bottleneck report sent by Secretary Engfa.
"""

import asyncio
import logging
from datetime import datetime
import pytz
import httpx
import os

from backend.services import telegram_service
from backend.models.schemas import LogCreate, LogLevel
from backend.services.log_service import write_log

logger = logging.getLogger(__name__)

TIMEZONE_ICT = pytz.timezone("Asia/Bangkok")
_scheduler_running = False
_scheduler_task = None


def get_ict_now() -> datetime:
    return datetime.now(TIMEZONE_ICT)


async def generate_morning_briefing() -> str:
    """สร้างรายงานสรุปงานค้างและวาระสำคัญประจำเช้า 08:30 น."""
    dept_rooms = telegram_service.get_all_department_rooms()
    dept_summary_list = []

    for dept_id, info in dept_rooms.items():
        dept_name = info.get("name", dept_id)
        pm_name = info.get("pm_name", f"PM {dept_name}")
        dept_summary_list.append(f"• <b>{dept_name}</b> ({pm_name}): พร้อมรับคำสั่งเร่งด่วนประจำวัน")

    summary_str = "\n".join(dept_summary_list) if dept_summary_list else "• ยังไม่มีทีมปฏิบัติการที่ถูกสร้าง"

    owner_name = os.getenv("OWNER_NAME", "Owner")
    prompt = (
        f"รายงานประจำเช้า เวลา 08:30 น.\n"
        f"กรุณาสวมบทบาท 'อิงฟ้า' เลขา AI ส่วนตัวและเพื่อนคู่คิด ทักทายคุณ {owner_name} ในยามเช้าอย่างอบอุ่น สดใส และมืออาชีพ\n"
        f"สรุปวาระงานและรายการที่ต้องเร่งดำเนินการในวันนี้ให้คุณ {owner_name} ทราบสั้นๆ กระชับ เพื่อให้คุณ {owner_name} เริ่มต้นสั่งงานแต่ละทีมได้ทันที\n\n"
        f"ข้อมูลทีมปฏิบัติการในองค์กรขณะนี้:\n{summary_str}"
    )

    try:
        from backend.services.llm_service import LLMService
        from backend.services.telegram_service import _get_owner_prompt_context
        llm = LLMService(model="gemini-1.5-flash", temperature=0.7)
        briefing_text = await llm.generate(
            system_instruction=(
                f"คุณคือ 'อิงฟ้า' เลขา AI และเพื่อนคู่คิดบริหาร สรุปรายงานยามเช้า 08:30 น. ให้แก่คุณ {owner_name} "
                "เน้นความสุภาพ อบอุ่น กระชับ จัดรูปแบบด้วยสัญลักษณ์ข้อความอ่านง่าย"
            ) + _get_owner_prompt_context(),
            user_message=prompt,
        )
    except Exception as e:
        briefing_text = f"สวัสดีค่ะคุณ {owner_name} อิงฟ้าสรุปวาระงานประจำเช้า 08:30 น. ค่ะ\n\n{summary_str}"

    return briefing_text


async def generate_evening_summary() -> str:
    """สร้างรายงานสรุปผลงานประจำวันและจุดติดขัด 18:00 น."""
    dept_rooms = telegram_service.get_all_department_rooms()
    dept_summary_list = []

    for dept_id, info in dept_rooms.items():
        dept_name = info.get("name", dept_id)
        pm_name = info.get("pm_name", f"PM {dept_name}")
        dept_summary_list.append(f"• <b>{dept_name}</b> ({pm_name}): สรุปการปฏิบัติงานเสร็จสมบูรณ์เรียบร้อยแล้ว")

    summary_str = "\n".join(dept_summary_list) if dept_summary_list else "• ยังไม่มีทีมงานปฏิบัติการ"

    owner_name = os.getenv("OWNER_NAME", "Owner")
    prompt = (
        f"รายงานประจำเย็น เวลา 18:00 น. (End-of-Day Summary)\n"
        f"กรุณาสวมบทบาท 'อิงฟ้า' เลขา AI และเพื่อนคู่คิด สรุปภาพรวมการทำงานของทุกทีมประจำวันนี้ให้คุณ {owner_name} ทราบ\n"
        f"ระบุสิ่งที่สำเร็จ ความคืบหน้า จุดติดขัด (Bottleneck) ถ้ามี และให้คำแนะนำเชิงกลยุทธ์สำหรับวันพรุ่งนี้\n\n"
        f"ข้อมูลทีมปฏิบัติการ:\n{summary_str}"
    )

    try:
        from backend.services.llm_service import LLMService
        from backend.services.telegram_service import _get_owner_prompt_context
        llm = LLMService(model="gemini-1.5-flash", temperature=0.6)
        summary_text = await llm.generate(
            system_instruction=(
                f"คุณคือ 'อิงฟ้า' เลขา AI สรุปรายงานการทำงานประจำวัน 18:00 น. (EOD Summary) แก่คุณ {owner_name} "
                "สุภาพ มืออาชีพ จริงใจ ให้คำแนะนำประเสริฐแก่องค์กร"
            ) + _get_owner_prompt_context(),
            user_message=prompt,
        )
    except Exception as e:
        summary_text = f"เรียนคุณ {owner_name} อิงฟ้าสรุปภาพรวมการทำงานของทุกทีมประจำวันนี้ 18:00 น. ค่ะ\n\n{summary_str}"

    return summary_text


async def send_briefing_to_owner(title: str, content: str):
    """ส่งข้อความรายงาน 1-on-1 จากเลขาอิงฟ้าตรงเข้า Telegram ของ Owner"""
    owner_chat = os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "") or telegram_service.TELEGRAM_OWNER_DIRECT_CHAT_ID
    bot_token = telegram_service.get_bot_token()

    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="เลขา AI (อิงฟ้า)",
        level=LogLevel.SUCCESS,
        message=f"ส่งรายงานอัตโนมัติประจำวัน: {title}",
        thought_process=content,
    ))

    if not owner_chat or not bot_token:
        logger.warning("Telegram owner chat ID or bot token missing for scheduled briefing.")
        return

    msg = (
        f"<b>[🔔 {title}]</b>\n"
        f"<i>รายงานอัตโนมัติจากเลขา AI (อิงฟ้า)</i>\n\n"
        f"{content}\n\n"
        f"🌐 <i>สามารถเข้าชมกระดานติดตามงานฉบับเต็มได้ที่หน้าเว็บครับ</i>"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json={"chat_id": owner_chat, "text": telegram_service.clean_telegram_html(msg), "parse_mode": "HTML"})
            logger.info(f"✅ Scheduled briefing '{title}' sent successfully to Owner Telegram!")
    except Exception as e:
        logger.error(f"Failed to send scheduled briefing to Owner Telegram: {e}")


async def _scheduler_loop():
    """Background Loop ตรวจสอบเวลา 08:30 น. และ 18:00 น. เวลาไทย (ICT GMT+7)"""
    global _scheduler_running
    last_morning_sent_date = ""
    last_evening_sent_date = ""

    logger.info("⏰ [Daily Scheduler] เริ่มทำงานระบบตั้งเวลาส่งรายงานอัตโนมัติ (08:30 น. & 18:00 น. ICT)")

    while _scheduler_running:
        try:
            now = get_ict_now()
            today_str = now.strftime("%Y-%m-%d")
            hour = now.hour
            minute = now.minute

            # 1. 08:30 AM ICT — Morning Briefing (08:30 - 08:31)
            if hour == 8 and minute == 30 and last_morning_sent_date != today_str:
                logger.info("🌅 Triggers Morning Briefing (08:30 AM ICT)...")
                briefing_text = await generate_morning_briefing()
                await send_briefing_to_owner("สรุปรายการงานค้าง & วาระเร่งด่วนประจำเช้า (08:30 น.)", briefing_text)
                last_morning_sent_date = today_str

            # 2. 18:00 PM ICT — Evening Summary (18:00 - 18:01)
            if hour == 18 and minute == 0 and last_evening_sent_date != today_str:
                logger.info("🌇 Triggers Evening EOD Summary (18:00 PM ICT)...")
                summary_text = await generate_evening_summary()
                await send_briefing_to_owner("สรุปผลการทำงานประจำวัน & จุดติดขัด (18:00 น.)", summary_text)
                last_evening_sent_date = today_str

        except Exception as e:
            logger.error(f"Error in daily scheduler loop: {e}")

        await asyncio.sleep(25)  # Check every 25 seconds


def start_scheduler():
    global _scheduler_running, _scheduler_task
    if not _scheduler_running:
        _scheduler_running = True
        _scheduler_task = asyncio.create_task(_scheduler_loop())


def stop_scheduler():
    global _scheduler_running, _scheduler_task
    _scheduler_running = False
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None
