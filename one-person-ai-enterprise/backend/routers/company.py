"""
company.py — Company Operating Model, Working Hours, Policies & Directives Router
Manages company operational blueprint, hours, policies, and strategic direction.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.parent.parent
POLICY_FILE = BASE_DIR / "company_policy.json"
COMPANY_MEMORY_FILE = BASE_DIR / "company_memory.md"

router = APIRouter(prefix="/api/company", tags=["Company Directives & Policy"])

DEFAULT_DIRECTIVES = {
    "working_hours": {
        "mode": "autonomous_24_7",
        "mode_label": "24/7 Autonomous (AI สแตนด์บายและทำงานตลอด 24 ชั่วโมง)",
        "start_time": "08:30",
        "end_time": "18:00",
        "work_days": "ทุกวัน (จันทร์ - อาทิตย์)",
        "morning_briefing_time": "08:30",
        "evening_summary_time": "18:00",
        "off_hours_behavior": "AI ปฏิบัติงานเบื้องหลัง สรุปข้อมูล และสแตนด์บายรับคำสั่งด่วน 24/7",
        "timezone": "Asia/Bangkok (ICT GMT+7)"
    },
    "strategic_direction": {
        "vision": "สร้างและบริหารองค์กรเทคโนโลยีและคอนเทนต์ระดับสากลด้วยพลังของ One-Person Multi-Agent AI Enterprise 100%",
        "primary_focus": "1. พัฒนาระบบซอฟต์แวร์และ Automation 2. ธุรกิจร้านอะไหล่รถยนต์ 3. ผลิตคอนเทนต์โซเชียลมีเดียคุณภาพสูง",
        "quarterly_goals": "พัฒนาระบบอัตโนมัติให้เสร็จสมบูรณ์, ดำเนินงานแบบ Zero-Token ประหยัดงบประมาณ, เพิ่มการเข้าถึงของแบรนด์",
        "target_audience": "ผู้ประกอบการ, เจ้าของธุรกิจ, ลูกค้าทั่วไป และผู้ติดตามสื่อดิจิทัลสายเทคโนโลยี",
        "brand_tone": "มืออาชีพ นวัตกรรมสูง จริงใจ เข้าถึงง่าย และสร้างสรรค์"
    },
    "policies": {
        "hitl_rule": "กฎเหล็ก Human-in-the-Loop: ทุกการส่งมอบงานสำคัญ (การเงิน, โพสต์คอนเทนต์จริง, Deploy ระบบ) ต้องผ่านการยืนยัน (Confirm) จาก Owner เสมอ",
        "token_cost_policy": "นโยบาย Zero-Token Priority: ให้ความสำคัญกับโมเดลในเครื่อง (Local LLM / Ollama) และสมองกลอัจฉริยะเป็นอันดับแรกเพื่อประหยัดต้นทุน 0 บาท",
        "quality_assurance": "มาตรฐาน Zero-Defect: ซอฟต์แวร์ต้องผ่านการทดสอบครอบคลุม 100% คอนเทนต์ต้อง Hook 3 วินาทีแรกและตรงกลุ่มเป้าหมาย",
        "security_privacy": "รักษาความลับทางการค้าและข้อมูลลูกค้า 100%: ห้าม Hardcode Secrets และปกป้อง API Keys ทุกระดับ"
    },
    "company_model": {
        "model_type": "One-Person AI Enterprise (Solopreneur + Multi-Agent Workforce)",
        "supreme_leader": "พี่บุ๊ค (Owner & Supreme Decision Maker)",
        "core_departments": [
            "01_secretary: สำนักเลขาและ CKO (อิงฟ้า)",
            "02_marketing: ฝ่ายการตลาดและ Social Media (ลิซ่า)",
            "03_developer: ฝ่ายพัฒนาระบบซอฟต์แวร์ (บิ๊นท์)",
            "04_data_analyst: ฝ่ายวิเคราะห์ข้อมูลและ QA (มุก)",
            "05_accounting: ฝ่ายบัญชีและการเงิน (พลอย)",
            "06_sales: ฝ่ายขายและบริการลูกค้าสัมพันธ์ (พิมพ์)"
        ],
        "workforce_scaling": "หากมีภาระงานเกินขีดจำกัด AI แต่ละแผนกสามารถยื่นคำขอจ้างงาน AI (Hiring Proposal) ให้ Owner พิจารณาอนุมัติได้"
    }
}

def load_directives() -> dict:
    if POLICY_FILE.exists():
        try:
            data = json.loads(POLICY_FILE.read_text(encoding="utf-8"))
            # Merge with defaults to ensure all keys present
            merged = DEFAULT_DIRECTIVES.copy()
            for k, v in data.items():
                if isinstance(v, dict) and k in merged:
                    merged[k].update(v)
                else:
                    merged[k] = v
            return merged
        except Exception:
            pass
    return DEFAULT_DIRECTIVES

def save_directives(data: dict):
    POLICY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # Sync to company_memory.md for all agents to read
    sync_to_company_memory(data)

def sync_to_company_memory(data: dict):
    wh = data.get("working_hours", {})
    sd = data.get("strategic_direction", {})
    pol = data.get("policies", {})
    cm = data.get("company_model", {})

    content = f"""# Company Memory (คลังปัญญาของบริษัท)

ไฟล์บันทึกความรู้ บริบทองค์กร เวลาทำงาน นโยบาย และทิศทางกลยุทธ์ของบริษัท AI แบบ 100%

---

## [ข้อมูลโปรไฟล์ธุรกิจและเป้าหมายองค์กร]
- **ชื่อองค์กร**: One-Person AI Enterprise
- **รูปแบบบริษัท**: {cm.get('model_type', 'One-Person AI Enterprise')}
- **ผู้มีอำนาจตัดสินใจสูงสุด (Supreme Owner)**: {cm.get('supreme_leader', 'พี่บุ๊ค')}
- **วิสัยทัศน์**: {sd.get('vision', '')}
- **ทิศทางและภารกิจหลัก**: {sd.get('primary_focus', '')}
- **เป้าหมายประจำไตรมาส/ปี**: {sd.get('quarterly_goals', '')}
- **กลุ่มเป้าหมาย**: {sd.get('target_audience', '')}
- **โทนของแบรนด์**: {sd.get('brand_tone', '')}

---

## [เวลาทำงานและตารางปฏิบัติการ (Company Operating Schedule)]
- **โหมดการทำงาน**: {wh.get('mode_label', wh.get('mode', '24/7 Autonomous'))}
- **เวลาทำการหลัก**: {wh.get('start_time', '08:30')} - {wh.get('end_time', '18:00')} น. ({wh.get('timezone', 'Asia/Bangkok')})
- **วันปฏิบัติงาน**: {wh.get('work_days', 'ทุกวัน')}
- **รอบรายงานยามเช้า (Morning Briefing)**: เวลา {wh.get('morning_briefing_time', '08:30')} น. โดยเลขาอิงฟ้า
- **รอบรายงานปิดวัน (Evening EOD Summary)**: เวลา {wh.get('evening_summary_time', '18:00')} น. โดยเลขาอิงฟ้า
- **นโยบายการทำงานนอกเวลา**: {wh.get('off_hours_behavior', '')}

---

## [นโยบายและกฎเหล็กของบริษัท (Corporate Policies & Safeguards)]
- **กฎเหล็กที่ 1 (Human-in-the-Loop Mandatory)**: {pol.get('hitl_rule', '')}
- **กฎเหล็กที่ 2 (Zero-Token Priority)**: {pol.get('token_cost_policy', '')}
- **กฎเหล็กที่ 3 (Zero-Defect Quality)**: {pol.get('quality_assurance', '')}
- **กฎเหล็กที่ 4 (Security & Privacy)**: {pol.get('security_privacy', '')}
- **กฎเหล็กที่ 5 (Workforce Scaling)**: {cm.get('workforce_scaling', '')}

---

## [โครงสร้างองค์กร 6 แผนกหลัก]
1. สำนักเลขาและ CKO (อิงฟ้า)
2. ฝ่ายการตลาดและ Social Media Content (ลิซ่า)
3. ฝ่ายพัฒนาระบบซอฟต์แวร์ (บิ๊นท์)
4. ฝ่ายวิเคราะห์ข้อมูลและ QA (มุก)
5. ฝ่ายบัญชีและการเงิน (พลอย)
6. ฝ่ายขายและบริการลูกค้าสัมพันธ์ (พิมพ์)

---
*บันทึกข้อมูลล่าสุด: ปรับปรุงตามการกำหนดทิศทางของ Owner*
"""
    COMPANY_MEMORY_FILE.write_text(content, encoding="utf-8")


class DirectivesUpdateRequest(BaseModel):
    working_hours: Optional[Dict[str, Any]] = None
    strategic_direction: Optional[Dict[str, Any]] = None
    policies: Optional[Dict[str, Any]] = None
    company_model: Optional[Dict[str, Any]] = None


@router.get("/directives")
async def get_directives():
    return load_directives()


@router.post("/directives")
async def update_directives(req: DirectivesUpdateRequest):
    current = load_directives()
    if req.working_hours:
        current["working_hours"].update(req.working_hours)
    if req.strategic_direction:
        current["strategic_direction"].update(req.strategic_direction)
    if req.policies:
        current["policies"].update(req.policies)
    if req.company_model:
        current["company_model"].update(req.company_model)

    save_directives(current)
    return {
        "status": "success",
        "message": "บันทึกเวลาทำงาน ทิศทาง นโยบาย และรูปแบบบริษัทเรียบร้อยแล้ว",
        "directives": current
    }


# ─── Company Shift Control (Start / End Work) ─────────────────
from datetime import datetime, timezone
import asyncio
from backend.services.log_service import write_log
from backend.models.schemas import LogCreate, LogLevel
from backend.services import simulation_service, scheduler_service


@router.get("/shift")
async def get_shift_status():
    data = load_directives()
    shift = data.get("shift", {
        "status": "active",
        "status_label": "เปิดทำการ (On Shift)",
        "last_started_at": datetime.now(timezone.utc).isoformat(),
        "last_ended_at": None,
    })
    return shift


@router.post("/shift/start")
async def start_shift():
    data = load_directives()
    now_iso = datetime.now(timezone.utc).isoformat()
    shift = {
        "status": "active",
        "status_label": "เปิดทำการ (On Shift)",
        "last_started_at": now_iso,
        "last_ended_at": data.get("shift", {}).get("last_ended_at")
    }
    data["shift"] = shift
    save_directives(data)

    # Wake up agents to idle
    for agent_id, state in simulation_service._agent_states.items():
        if state.status in ["standby", "off_duty"]:
            state.status = "idle"
            state.current_action = "พร้อมรับคำสั่งจาก Owner ประจำวัน"
            state.current_thought = "เปิดกะการทำงาน เริ่มต้นวันใหม่พร้อมลุยทุกโปรเจกต์"

    # Write log
    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="เลขา AI (อิงฟ้า)",
        level=LogLevel.SUCCESS,
        message="🚀 [เริ่มงาน] เปิดกะทำงานประจำวัน — ทีมงาน AI ทั้ง 6 แผนกพร้อมปฏิบัติการ",
        thought_process="Owner เริ่มงานประจำวัน รวบรวมงานค้างและแจ้งเตือนวาระสำคัญ"
    ))

    # Send briefing in background
    async def _send_morning():
        try:
            briefing = await scheduler_service.generate_morning_briefing()
            await scheduler_service.send_briefing_to_owner("เปิดกะทำงานประจำวัน — สรุปวาระงานยามเช้า", briefing)
        except Exception:
            pass

    asyncio.create_task(_send_morning())

    return {
        "status": "active",
        "message": "🏢 เริ่มกะทำงานประจำวันเรียบร้อยแล้ว ทีมงาน AI ทั้ง 6 แผนกพร้อมปฏิบัติงานครับ!",
        "shift": shift
    }


@router.post("/shift/end")
async def end_shift():
    data = load_directives()
    now_iso = datetime.now(timezone.utc).isoformat()
    shift = {
        "status": "off_duty",
        "status_label": "เลิกงาน / พักผ่อน (Off Duty)",
        "last_started_at": data.get("shift", {}).get("last_started_at"),
        "last_ended_at": now_iso
    }
    data["shift"] = shift
    save_directives(data)

    # Set agents to standby
    for agent_id, state in simulation_service._agent_states.items():
        if state.status == "idle":
            state.status = "standby"
            state.current_action = "พักผ่อนนอกเวลางาน (สแตนด์บายรับคำสั่งด่วน)"
            state.current_thought = "บันทึกข้อมูลและสรุปผลงานปิดวันเรียบร้อย พร้อมพักผ่อน"

    # Write log
    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="เลขา AI (อิงฟ้า)",
        level=LogLevel.INFO,
        message="🌇 [เลิกงาน] ปิดกะทำงานประจำวัน — เลขาอิงฟ้ารวบรวมผลงานปิดวันเรียบร้อย",
        thought_process="Owner กดเลิกงาน ปิดกะการทำงานประจำวัน และสรุปผลส่ง Telegram"
    ))

    # Send summary in background
    async def _send_evening():
        try:
            summary = await scheduler_service.generate_evening_summary()
            await scheduler_service.send_briefing_to_owner("ปิดกะทำงานประจำวัน — สรุปผลงานปิดวัน (EOD Summary)", summary)
        except Exception:
            pass

    asyncio.create_task(_send_evening())

    return {
        "status": "off_duty",
        "message": "🌙 ปิดกะทำงานประจำวันเรียบร้อยแล้ว เลขาอิงฟ้ารวบรวมสรุปผลงานส่งเข้า Telegram เรียบร้อยครับ!",
        "shift": shift
    }

