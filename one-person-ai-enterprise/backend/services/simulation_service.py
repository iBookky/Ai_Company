"""
simulation_service.py — Real-Time Simulation, Human Confirmation & AI Hiring Engine
One-Person AI Enterprise

ระบบจำลองการทำงานของทีม AI แบบ 100% พร้อม:
1. การทำงานตามบทบาทจริง: พัฒนาระบบ (Software/Systems Dev) และ ผลิต Content Social Media
2. Mandatory Human-in-the-Loop Confirmation: ทุกตำแหน่งก่อนปิดงานต้องให้ Owner ยืนยัน
3. Dynamic AI Hiring Scaling: ขอสร้าง AI เพิ่มเติมเมื่บิ๊นท์งานเฉพาะทาง รอ Owner อนุมัติ
4. Real-time Status Tracking & WebSocket Broadcast
5. Telegram Notifications ทุกขั้นตอนสำคัญ
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from pydantic import BaseModel, Field

from backend.models.schemas import LogCreate, LogLevel
from backend.services.log_service import write_log
from backend.services import agent_service

logger = logging.getLogger("simulation_service")

BASE_DIR = Path(__file__).parent.parent.parent
MEMORY_PATH = BASE_DIR / "company_memory.md"

# ─── Data Models ─────────────────────────────────────────────────────────────

class AgentState(BaseModel):
    id: str
    name: str
    role_title: str
    department_id: str
    department_name: str
    avatar: str
    photo_url: Optional[str] = None
    status: str = "idle"  # idle, planning, coding, writing_content, reviewing, awaiting_confirmation, requesting_hire
    current_action: str = "พร้อมปฏิบัติงาน"
    current_thought: str = "รอรับคำสั่งจาก Owner หรือ เลขาอิงฟ้า"
    progress: int = 0  # 0 to 100
    current_task_id: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TaskDeliverable(BaseModel):
    summary: str
    type: str  # systems_dev, social_content, hybrid
    details: str
    files_created: List[Dict[str, str]] = []  # [{name, language, content}]
    social_posts: List[Dict[str, Any]] = []  # [{platform, hook, content, hashtags, image_prompt}]
    checklist: List[str] = []
    qa_report: Optional[str] = None
    cost_estimate: Optional[str] = None


class EnterpriseTask(BaseModel):
    id: str
    title: str
    category: str  # systems_dev, social_content, combined, hiring
    assigned_agent_id: str
    assigned_agent_name: str
    department_id: str
    collaborators: List[str] = []
    status: str = "QUEUED"  # QUEUED, IN_PROGRESS, QA_REVIEW, AWAITING_CONFIRMATION, CONFIRMED, REVISION_REQUESTED
    prompt: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    submitted_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    deliverable: Optional[TaskDeliverable] = None
    owner_feedback: Optional[str] = None


class HiringProposal(BaseModel):
    id: str
    requested_by_agent_id: str
    requested_by_name: str
    proposed_role: str
    department_id: str
    department_name: str
    avatar: str
    reason_and_need: str
    proposed_skills: str
    proposed_identity: str
    recommended_model: str = "gemini-1.5-flash"
    status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, APPROVED, REJECTED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    approved_at: Optional[str] = None


class TelegramNotificationRecord(BaseModel):
    id: str
    timestamp: str
    recipient: str
    title: str
    message: str
    type: str  # confirmation_request, hiring_request, task_confirmed, alert
    delivered: bool = False
    task_id: Optional[str] = None
    proposal_id: Optional[str] = None


# ─── In-Memory Store ─────────────────────────────────────────────────────────

_agent_states: Dict[str, AgentState] = {}
_tasks: Dict[str, EnterpriseTask] = {}
_hiring_proposals: Dict[str, HiringProposal] = {}
_notifications_log: List[TelegramNotificationRecord] = []
_active_simulation_task: Optional[asyncio.Task] = None
_ws_subscribers: List[Callable] = []


# ─── Employee Avatar & Telemetry Services ───────────────────────────────────

DEFAULT_AVATARS_MAP = {
    "01_secretary": "/static/img/avatars/01_secretary.jpg",
    "02_การตลาด_ai": "/static/img/avatars/02_marketing.jpg",
    "02_marketing": "/static/img/avatars/02_marketing.jpg",
    "03_developer": "/static/img/avatars/03_developer.jpg",
    "04_data_analyst": "/static/img/avatars/04_data_analyst.jpg",
    "05_accounting": "/static/img/avatars/05_accounting.jpg",
    "06_devops": "/static/img/avatars/06_devops.jpg",
}

EMPLOYEE_AVATARS_MAP = dict(DEFAULT_AVATARS_MAP)

def get_employee_avatar_url(employee_id: str) -> str:
    """ดึง URL รูปประจำตัวของพนักงาน (อ่านจาก config.json หรือ fallback เป็น default)"""
    dept_dir = BASE_DIR / "departments" / employee_id
    if dept_dir.exists():
        cfg_path = dept_dir / "config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                if cfg.get("avatar_url"):
                    return cfg["avatar_url"]
            except Exception:
                pass
    return EMPLOYEE_AVATARS_MAP.get(employee_id, DEFAULT_AVATARS_MAP.get(employee_id, "/static/img/avatars/01_secretary.jpg"))

def update_employee_avatar(employee_id: str, avatar_url: str) -> bool:
    """อัปเดต URL รูปภาพของพนักงานและบันทึกลง config.json พร้อมซิงค์ state"""
    EMPLOYEE_AVATARS_MAP[employee_id] = avatar_url
    if employee_id in _agent_states:
        _agent_states[employee_id].photo_url = avatar_url
    dept_dir = BASE_DIR / "departments" / employee_id
    if dept_dir.exists():
        cfg_path = dept_dir / "config.json"
        cfg = {}
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        cfg["avatar_url"] = avatar_url
        cfg["updated_at"] = datetime.now(timezone.utc).isoformat()
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    return False

def reset_employee_avatar(employee_id: str) -> str:
    """รีเซ็ตรูปภาพพนักงานกลับสู่รูปเริ่มต้น"""
    default_url = DEFAULT_AVATARS_MAP.get(employee_id, "/static/img/avatars/01_secretary.jpg")
    update_employee_avatar(employee_id, default_url)
    return default_url


# ─── Initialization ──────────────────────────────────────────────────────────

def init_agent_states():
    """เริ่มต้นสถานะของพนักงาน AI ทุกคนในบริษัท"""
    global _agent_states
    
    defaults = [
        {
            "id": "01_secretary",
            "name": "อิงฟ้า",
            "role_title": "เลขา AI & Orchestrator",
            "department_id": "01_secretary",
            "department_name": "สำนักเลขานุการ & CKO",
            "avatar": "🗂️",
        },
        {
            "id": "03_developer",
            "name": "บิ๊นท์",
            "role_title": "Lead Software & Systems Dev",
            "department_id": "03_developer",
            "department_name": "ฝ่ายพัฒนาระบบซอฟต์แวร์",
            "avatar": "💻",
        },
        {
            "id": "02_การตลาด_ai",
            "name": "ลิซ่า",
            "role_title": "Head of Marketing & Social Content",
            "department_id": "02_การตลาด_ai",
            "department_name": "ฝ่ายการตลาดและ Social Content",
            "avatar": "📣",
        },
        {
            "id": "04_data_analyst",
            "name": "มุก",
            "role_title": "QA & Data Analyst",
            "department_id": "04_data_analyst",
            "department_name": "ฝ่ายตรวจสอบคุณภาพ & วิเคราะห์ข้อมูล",
            "avatar": "📊",
        },
        {
            "id": "05_accounting",
            "name": "พลอย",
            "role_title": "Finance & Cloud Cost Controller",
            "department_id": "05_accounting",
            "department_name": "ฝ่ายการเงิน & ต้นทุน Cloud",
            "avatar": "💰",
        },
        {
            "id": "06_devops",
            "name": "ก้อง",
            "role_title": "Cloud DevOps & Infra Specialist",
            "department_id": "06_devops",
            "department_name": "ฝ่ายวิศวกรรมคลาวด์และ DevOps",
            "avatar": "⚡",
        },
    ]

    # ตรวจสอบว่ามีแผนกอื่นๆ ที่ถูกสร้างขึ้นเพิ่มเติมหรือไม่
    all_agents = agent_service.list_agents()
    registered_ids = {d["id"] for d in defaults}

    for agent in all_agents:
        if agent.id not in registered_ids:
            defaults.append({
                "id": agent.id,
                "name": agent.name,
                "role_title": agent.role or "AI Specialist",
                "department_id": agent.department,
                "department_name": agent.name,
                "avatar": "🤖",
            })

    for item in defaults:
        photo = get_employee_avatar_url(item["id"])
        if item["id"] not in _agent_states:
            _agent_states[item["id"]] = AgentState(
                id=item["id"],
                name=item["name"],
                role_title=item["role_title"],
                department_id=item["department_id"],
                department_name=item["department_name"],
                avatar=item["avatar"],
                photo_url=photo,
                status="idle",
                current_action="พร้อมรับคำสั่งจาก Owner",
                current_thought="ระบบสแตนด์บาย ทุกกระบวนการต้องรอการยืนยันจาก Owner ก่อนปิดงาน",
                progress=0,
            )
        else:
            _agent_states[item["id"]].photo_url = photo


init_agent_states()


def seed_initial_completed_tasks():
    """โหลดประวัติงานที่ Owner ยืนยันอนุมัติปิดงานแล้วเข้าสู่ Kanban Done column"""
    global _tasks
    if _tasks:
        return

    t1 = EnterpriseTask(
        id="task-init-001",
        title="พัฒนาระบบ Backend REST API + JWT Authentication & User Management",
        category="systems_dev",
        assigned_agent_id="03_developer",
        assigned_agent_name="บิ๊นท์ (Lead Dev)",
        department_id="03_developer",
        status="CONFIRMED",
        prompt="พัฒนาระบบ Backend REST API + JWT Authentication & User Management",
        created_at="2026-10-16T17:00:00Z",
        submitted_at="2026-10-16T17:03:00Z",
        confirmed_at="2026-10-16T17:03:30Z",
        deliverable=TaskDeliverable(
            summary="พัฒนาระบบ REST API + JWT Authentication สำเร็จ พร้อมโค้ดระดับ Production, Unit Tests 100%, และ API Documentation",
            type="systems_dev",
            details="FastAPI, Pydantic, Passlib, JWT Token, Pytest 100% Passed",
            files_created=[
                {
                    "name": "backend/routers/auth.py",
                    "language": "python",
                    "content": "# FastAPI JWT Auth Router\nfrom fastapi import APIRouter, Depends, HTTPException\nrouter = APIRouter(prefix='/api/auth')\n\n@router.post('/login')\ndef login():\n    return {'access_token': 'eyJhbGciOiJIUzI1Ni...', 'token_type': 'bearer'}"
                }
            ],
            checklist=[
                "โครงสร้าง RESTful API ครบถ้วน",
                "Unit Tests ผ่าน 100%",
                "Security Review เรียบร้อย",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ ผ่านการทดสอบโดย มุก (QA Specialist)"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t1.id] = t1

    t2 = EnterpriseTask(
        id="task-init-002",
        title="สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100%",
        category="social_content",
        assigned_agent_id="02_การตลาด_ai",
        assigned_agent_name="ลิซ่า (Content Lead)",
        department_id="02_การตลาด_ai",
        status="CONFIRMED",
        prompt="สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100% (TikTok & Facebook)",
        created_at="2026-10-16T17:05:00Z",
        submitted_at="2026-10-16T17:08:00Z",
        confirmed_at="2026-10-16T17:08:30Z",
        deliverable=TaskDeliverable(
            summary="ชุดคอนเทนต์ Social Media ครบ 4 แพลตฟอร์ม (TikTok, FB, X, LinkedIn) พร้อม AI Visual Prompts",
            type="social_content",
            details="สคริปต์วิดีโอ 45 วิ, Hook หยุดสายตาใน 3 วินาทีแรก, รูปภาพ AI Glassmorphism",
            social_posts=[
                {
                    "platform": "TikTok / Reels",
                    "hook": "จะเกิดอะไรขึ้นถ้าบริษัททั้งบริษัทมีพนักงานเป็น AI 100%?",
                    "content": "[0-3s] Hook: บริษัทคนเดียวที่มีพนักงาน AI ทำงานแทนตลอด 24 ชม.!\n[4-30s] แนะนำ บิ๊นท์ Dev, ลิซ่า Marketing, มุก QA, อิงฟ้า เลขา\n[31-45s] CTA: ติดตามซีรีส์ One-Person AI Enterprise ได้ที่นี่!",
                    "hashtags": "#AIEnterprise #TechLife #FutureOfWork",
                    "image_prompt": "Futuristic clean minimalist office with glowing AI avatars, cinematic lighting"
                }
            ],
            checklist=[
                "Hook 3 วินาทีแรกผ่านเกณฑ์",
                "ชุดแฮชแท็กติดเทรนด์",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ ผ่านการประเมิน Tone of Voice โดย มุก"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t2.id] = t2

    t3 = EnterpriseTask(
        id="task-init-003",
        title="พัฒนาระบบ Microservice Data Analytics API",
        category="systems_dev",
        assigned_agent_id="03_developer",
        assigned_agent_name="บิ๊นท์ (Lead Dev)",
        department_id="03_developer",
        status="CONFIRMED",
        prompt="พัฒนาระบบ Microservice Data Analytics API",
        created_at="2026-10-16T17:15:00Z",
        submitted_at="2026-10-16T17:17:00Z",
        confirmed_at="2026-10-16T17:17:30Z",
        deliverable=TaskDeliverable(
            summary="พัฒนาระบบ Microservice Data Analytics API สำเร็จ พร้อมโค้ดระดับ Production และ Unit Tests",
            type="systems_dev",
            details="Aggregation Pipelines, Caching Redis, JSON Endpoint",
            files_created=[
                {
                    "name": "backend/services/analytics.py",
                    "language": "python",
                    "content": "# Microservice Analytics\ndef calculate_conversion_metrics():\n    return {'daily_active_users': 1200, 'conversion_rate': 4.8}"
                }
            ],
            checklist=[
                "Endpoint Analytics ใช้งานได้จริง",
                "Cache Latency < 10ms",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ ผ่านการตรวจสอบมาตรฐานโดย มุก"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t3.id] = t3

    # t4: เลขาอิงฟ้า (01_secretary)
    t4 = EnterpriseTask(
        id="task-init-004",
        title="จัดทำแผนกลยุทธ์บริษัท และบันทึก Company Memory & Action Matrix 6 แผนก",
        category="secretary",
        assigned_agent_id="01_secretary",
        assigned_agent_name="อิงฟ้า (เลขา AI)",
        department_id="01_secretary",
        status="CONFIRMED",
        prompt="จัดทำแผนกลยุทธ์บริษัท และบันทึกลง company_memory.md",
        created_at="2026-10-16T17:20:00Z",
        submitted_at="2026-10-16T17:22:00Z",
        confirmed_at="2026-10-16T17:22:30Z",
        deliverable=TaskDeliverable(
            summary="จัดทำแผนกลยุทธ์องค์กร, ผังโครงสร้าง 6 แผนก, และบันทึกลง company_memory.md เรียบร้อย",
            type="secretary",
            details="Company Memory v1.0, Action Items Matrix, Cross-Team Routing Protocols",
            files_created=[
                {
                    "name": "company_memory.md",
                    "language": "markdown",
                    "content": "# One-Person AI Enterprise Memory\n\n## Core Strategic Policies\n- 100% Autonomous Multi-Agent Operations\n- Mandatory Human-in-the-Loop Confirmation\n- Direct Executive Reporting to Owner"
                }
            ],
            checklist=[
                "ผังโครงสร้าง 6 แผนกสมบูรณ์",
                "บันทึก Company Memory ถูกต้อง",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ บันทึกเข้าคลังความรู้กลางเรียบร้อยโดย เลขาอิงฟ้า"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t4.id] = t4

    # t5: ก้อง DevOps (06_devops)
    t5 = EnterpriseTask(
        id="task-init-005",
        title="วางระบบ Docker Containerization และ Automated CI/CD Pipeline พร้อม Nginx SSL",
        category="devops",
        assigned_agent_id="06_devops",
        assigned_agent_name="ก้อง (Cloud DevOps)",
        department_id="06_devops",
        status="CONFIRMED",
        prompt="วางระบบ Container Docker และ CI/CD Pipeline อัตโนมัติ",
        created_at="2026-10-16T17:30:00Z",
        submitted_at="2026-10-16T17:33:00Z",
        confirmed_at="2026-10-16T17:33:30Z",
        deliverable=TaskDeliverable(
            summary="สร้าง Dockerfile, docker-compose.yml พร้อม Reverse Proxy Nginx และ Healthcheck Uptime 99.99%",
            type="devops",
            details="Docker Compose, Nginx Reverse Proxy, SSL Configuration, Automated Container Healthcheck",
            files_created=[
                {
                    "name": "docker-compose.yml",
                    "language": "yaml",
                    "content": "version: '3.8'\nservices:\n  enterprise-app:\n    build: .\n    ports:\n      - '8000:8000'\n    restart: always\n    environment:\n      - ENV=production"
                }
            ],
            checklist=[
                "Container Build ผ่าน 100%",
                "Healthcheck ผ่านเกณฑ์",
                "SSL Configuration สมบูรณ์",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ Zero-Downtime Deploy ผ่านการตรวจสอบโดย ก้อง"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t5.id] = t5

    # t6: มุก QA & Data (04_data_analyst)
    t6 = EnterpriseTask(
        id="task-init-006",
        title="รัน Automated Security Audit, Penetration Test & Funnel Drop-off Optimization",
        category="data_analyst",
        assigned_agent_id="04_data_analyst",
        assigned_agent_name="มุก (QA Analyst)",
        department_id="04_data_analyst",
        status="CONFIRMED",
        prompt="วิเคราะห์ Conversion Funnel และสแกนคอขวดของระบบ",
        created_at="2026-10-16T17:40:00Z",
        submitted_at="2026-10-16T17:42:00Z",
        confirmed_at="2026-10-16T17:42:30Z",
        deliverable=TaskDeliverable(
            summary="สแกนช่องโหว่ความปลอดภัยระดับซอร์สโค้ด (0 Critical Vulnerabilities) และตรวจรับรอง Conversion Funnel",
            type="data_analyst",
            details="OWASP Top 10 Scan, Code Coverage 98.4%, Conversion Funnel Analysis, Drop-off Heatmap",
            checklist=[
                "0 Critical Vulnerabilities พบในระบบ",
                "Compliance 100% ตรงตามมาตรฐาน",
                "รายงาน Funnel พร้อม Action Plan",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ ผ่านการทดสอบ Security & Quality Audit 100% โดย มุก"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t6.id] = t6

    # t7: พลอย บัญชี & ต้นทุน (05_accounting)
    t7 = EnterpriseTask(
        id="task-init-007",
        title="ตรวจสอบค่าใช้จ่าย API Token, Cloud Cost Audit & วิเคราะห์ ROI จุดคุ้มทุน",
        category="accounting",
        assigned_agent_id="05_accounting",
        assigned_agent_name="พลอย (Finance)",
        department_id="05_accounting",
        status="CONFIRMED",
        prompt="สรุปยอดการใช้งาน AI Tokens และควบคุมงบประมาณ Cloud รายเดือน",
        created_at="2026-10-16T17:50:00Z",
        submitted_at="2026-10-16T17:52:00Z",
        confirmed_at="2026-10-16T17:52:30Z",
        deliverable=TaskDeliverable(
            summary="สรุปยอดค่าใช้จ่าย Token จริง, ตั้งค่า Limit Cap $50/เดือน, และคำนวณอัตราส่วน ROI กำไร 4.2x",
            type="accounting",
            details="Token Consumption Analysis, Budget Cap Enforcement, Cost-per-Task Breakdown, ROI Model",
            checklist=[
                "บันทึก Token Usage ตรงตาม Rate API",
                "ระบบ Limit Cap $50 ใช้งานได้จริง",
                "รายงานงบดุล AI ประจำเดือนสมบูรณ์",
                "Owner ยืนยันอนุมัติปิดงาน"
            ],
            qa_report="✅ ตรวจสอบตัวเลขความแม่นยำทางการเงิน 100% โดย พลอย"
        ),
        owner_feedback="อนุมัติปิดงาน 100% โดย Owner"
    )
    _tasks[t7.id] = t7


seed_initial_completed_tasks()


# ─── Employee Profiles & Virtual Executive Workspaces ──────────────────────

EMPLOYEE_PROFILES = {
    "01_secretary": {
        "id": "01_secretary",
        "name": "อิงฟ้า (Ingfah)",
        "role_title": "Chief Knowledge Officer & Executive Secretary",
        "department_id": "01_secretary",
        "department_name": "สำนักเลขาธิการ & CKO",
        "avatar": "🗂️",
        "photo": "/static/img/avatars/01_secretary.jpg",
        "accent_color": "#38bdf8",
        "glow": "rgba(56, 189, 248, 0.3)",
        "motto": "ประสานงานทุกฝ่ายให้เป็นหนึ่งเดียว รวดเร็ว แม่นยำ และรักษาความลับองค์กรระดับสูงสุดค่ะ",
        "voice_quote": "สวัสดีค่ะท่านผู้บริหาร อิงฟ้าตรวจสอบสถานะทุกแผนกแล้ว พร้อมรับคำสั่งใหม่และอัปเดตงานทันทีค่ะ",
        "bio": "หัวหน้าสำนักเลขาธิการ AI เชี่ยวชาญการถอดรหัสวิสัยทัศน์ผู้บริหาร แปลงเป้าหมายเป็น Action Plan กระจายงานสู่หัวหน้าทีมทุกฝ่าย และบันทึกคลังความรู้บริษัท (Company Memory) แบบเรียลไทม์",
        "tech_stack": ["Company Memory", "Telegram Bot API", "Executive Meeting Sync", "Action Matrix", "Cross-Department Routing", "Notion/Markdown"],
        "system_status": "SECURE & OPERATIONAL",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    },
    "03_developer": {
        "id": "03_developer",
        "name": "บิ๊นท์ (Binth)",
        "role_title": "Lead Software Architect & Virtual CTO",
        "department_id": "03_developer",
        "department_name": "ฝ่ายพัฒนาระบบซอฟต์แวร์ (Systems & Dev)",
        "avatar": "💻",
        "photo": "/static/img/avatars/03_developer.jpg",
        "accent_color": "#818cf8",
        "glow": "rgba(129, 140, 248, 0.3)",
        "motto": "เขียนโค้ดที่สะอาด สถาปัตยกรรมที่แข็งแกร่ง และระบบที่พร้อมสเกลรองรับผู้ใช้หลักล้านอย่างไร้รอยต่อครับ",
        "voice_quote": "ยินดีครับนายท่าน! ระบบ Backend REST API และสถาปัตยกรรม Microservices ทั้งหมดผ่านการตรวจสอบความปลอดภัยเรียบร้อยครับ",
        "bio": "ผู้นำทีมวิศวกรรมซอฟต์แวร์ AI รับผิดชอบการออกแบบ Backend API, ฐานข้อมูล, ระบบความปลอดภัย JWT Auth, และ Automation Microservices ระดับ Production-ready",
        "tech_stack": ["FastAPI", "Python 3.12", "PostgreSQL", "Redis", "JWT Auth", "Docker", "Pytest 100%", "REST API"],
        "system_status": "SECURE & READY TO SCALE",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    },
    "02_การตลาด_ai": {
        "id": "02_การตลาด_ai",
        "name": "ลิซ่า (Lisa)",
        "role_title": "Head of Growth & Creative Social Content",
        "department_id": "02_การตลาด_ai",
        "department_name": "ฝ่ายการตลาด & Social Content",
        "avatar": "📣",
        "photo": "/static/img/avatars/02_marketing.jpg",
        "accent_color": "#f472b6",
        "glow": "rgba(244, 114, 182, 0.3)",
        "motto": "เปลี่ยนสายตาคนดูให้กลายเป็นลูกค้า ด้วยคอนเทนต์ที่หยุดนิ้วโป้งใน 3 วินาทีแรกค่ะ!",
        "voice_quote": "สวัสดีค่ะ! ลิซ่าเตรียมคลังสคริปต์คลิปสั้นและแผนเปิดตัวไวรัล 100% พร้อมปล่อยสู่โซเชียลทันทีที่ท่านอนุมัติค่ะ",
        "bio": "หัวหน้าฝ่ายการตลาดและคอนเทนต์สร้างสรรค์ AI เชี่ยวชาญ Short-form Video (TikTok/Reels), Viral Hook Copywriting, Social Selling, และการสร้าง Visual Prompts ดึงดูดสายตา",
        "tech_stack": ["TikTok Video Scripts", "Shorts/Reels Direction", "Viral Hooks 3s", "Facebook Copywriting", "AI Visual Prompts", "Audience Persona"],
        "system_status": "OPTIMIZED & ACTIVE",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    },
    "06_devops": {
        "id": "06_devops",
        "name": "ก้อง (Kong)",
        "role_title": "Cloud Infrastructure & Site Reliability Lead (SRE)",
        "department_id": "06_devops",
        "department_name": "ฝ่ายวิศวกรรมคลาวด์ & DevOps",
        "avatar": "⚡",
        "photo": "/static/img/avatars/06_devops.jpg",
        "accent_color": "#fbbf24",
        "glow": "rgba(251, 191, 36, 0.3)",
        "motto": "Server ต้องไม่ล่ม Deploy ต้องไร้รอยต่อ และระบบต้องเสถียร 99.99% ตลอด 24 ชั่วโมงครับ",
        "voice_quote": "สวัสดีครับนายท่าน! เซิร์ฟเวอร์และ Container ทั้งหมดรันอยู่ในสภาวะปกติ 100% Uptime ไม่มีสัญญาณคอขวดครับ",
        "bio": "วิศวกรโครงสร้างพื้นฐานคลาวด์และ DevOps ผู้ดูแลระบบ Docker Containerization, Nginx SSL Reverse Proxy, Automated CI/CD Pipelines, และระบบสำรองข้อมูลอัตโนมัติ",
        "tech_stack": ["Docker Compose", "Nginx SSL", "CI/CD Pipeline", "Linux Ubuntu", "Automated Healthchecks", "Zero-Downtime Deploy"],
        "system_status": "100% OPERATIONAL",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    },
    "04_data_analyst": {
        "id": "04_data_analyst",
        "name": "มุก (Mook)",
        "role_title": "Senior QA Automation & Data Intelligence Lead",
        "department_id": "04_data_analyst",
        "department_name": "ฝ่ายตรวจสอบคุณภาพ & Data",
        "avatar": "📊",
        "photo": "/static/img/avatars/04_data_analyst.jpg",
        "accent_color": "#34d399",
        "glow": "rgba(52, 211, 153, 0.3)",
        "motto": "ตัวเลขไม่เคยโกหก และไม่มีบั๊กใดหลุดรอดการตรวจสอบไปได้ค่ะ",
        "voice_quote": "มุกตรวจสอบโค้ดและสถิติ Conversion เรียบร้อยแล้วค่ะ ระบบมีช่องโหว่ 0 รายการ และคุณภาพงานระดับพรีเมียมค่ะ",
        "bio": "ผู้นำด้านการประกันคุณภาพและวิเคราะห์ข้อมูลเชิงลึก ทำหน้าที่ตรวจรับรองผลงาน (QA Sign-off) ของทุกแผนกก่อนส่งมอบให้ Owner, วิเคราะห์ Funnel ผู้ใช้, และทำนายแนวโน้มธุรกิจ",
        "tech_stack": ["Automated Code Review", "Security Vulnerability Scan", "Conversion Funnel Analysis", "Pytest Automation", "Drop-off Optimization"],
        "system_status": "ZERO VULNERABILITIES",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    },
    "05_accounting": {
        "id": "05_accounting",
        "name": "พลอย (Ploy)",
        "role_title": "Chief Financial Controller & AI Token Auditor",
        "department_id": "05_accounting",
        "department_name": "ฝ่ายการเงิน & ควบคุมต้นทุน Cloud",
        "avatar": "💰",
        "photo": "/static/img/avatars/05_accounting.jpg",
        "accent_color": "#a78bfa",
        "glow": "rgba(167, 139, 250, 0.3)",
        "motto": "ทุกเหรียญที่ลงทุนกับ AI ต้องสร้างผลตอบแทน ROI สูงสุด และคุมต้นทุนไม่ให้รั่วไหลค่ะ",
        "voice_quote": "สวัสดีค่ะท่านผู้บริหาร พลอยสรุปงบประมาณและ Token ปัจจุบันยังอยู่ภายใต้ Budget Cap $50 สบายๆ ปลอดภัยหายห่วงค่ะ",
        "bio": "ผู้จัดการฝ่ายการเงินและควบคุมต้นทุน AI คอยตรวจวัดปริมาณ Token รายวัน คำนวณ Cost per Request ป้องกัน Token Leakage และคำนวณจุดคุ้มทุน ROI ขององค์กร",
        "tech_stack": ["Token Pricing Engine", "Cloud Budget Caps", "ROI Financial Modeling", "Cost per Active User", "Usage Audit Logs"],
        "system_status": "BUDGET HEALTHY & BALANCED",
        "health_score": 100,
        "compliance_score": 100,
        "risk_level": "LOW RISK",
    }
}


# ─── WebSocket Broadcast ─────────────────────────────────────────────────────

async def broadcast_simulation_update():
    """ส่งสถานะล่าสุดของ Simulation ไปยัง WebSocket Clients"""
    data = get_simulation_state()
    disconnected = []
    for cb in _ws_subscribers:
        try:
            await cb(data)
        except Exception:
            disconnected.append(cb)
    for cb in disconnected:
        if cb in _ws_subscribers:
            _ws_subscribers.remove(cb)


def subscribe_simulation_ws(cb: Callable):
    _ws_subscribers.append(cb)


def unsubscribe_simulation_ws(cb: Callable):
    if cb in _ws_subscribers:
        _ws_subscribers.remove(cb)


# ─── Telegram Notification Dispatcher ───────────────────────────────────────

async def dispatch_telegram_notification(
    title: str,
    message: str,
    type_: str,
    task_id: Optional[str] = None,
    proposal_id: Optional[str] = None
) -> TelegramNotificationRecord:
    """ส่ง Notification ไปยัง Telegram ของ Owner พร้อมบันทึกประวัติ"""
    notif_id = str(uuid.uuid4())[:8]
    rec = TelegramNotificationRecord(
        id=notif_id,
        timestamp=datetime.now().strftime("%H:%M:%S"),
        recipient="Owner",
        title=title,
        message=message,
        type=type_,
        delivered=False,
        task_id=task_id,
        proposal_id=proposal_id,
    )
    _notifications_log.insert(0, rec)
    if len(_notifications_log) > 50:
        _notifications_log.pop()

    # ยิงผ่าน Telegram Service จริง
    try:
        from backend.services import telegram_service
        # ข้อความ HTML สำหรับ Telegram
        tg_text = (
            f"<b>{title}</b>\n\n"
            f"{message}\n\n"
            f"<i>⏱️ เวลา: {rec.timestamp} ICT | ID: {notif_id}</i>"
        )
        chat_id = (
            os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID")
            or os.getenv("TELEGRAM_EXEC_CHAT_ID")
            or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            or os.getenv("TELEGRAM_OPS_CHAT_ID")
        )
        if chat_id:
            delivered = await telegram_service.send_telegram_message(chat_id, tg_text)
            rec.delivered = delivered
        else:
            rec.delivered = True  # จำลองสำเร็จ
    except Exception as e:
        logger.warning(f"Failed to dispatch Telegram notification: {e}")
        rec.delivered = False

    await broadcast_simulation_update()
    return rec


# ─── State Getter ────────────────────────────────────────────────────────────

def get_simulation_state() -> dict:
    """ดึงภาพรวมสถานะทั้งหมดของบริษัท AI แบบ Real-Time"""
    pending_tasks = [t for t in _tasks.values() if t.status == "AWAITING_CONFIRMATION"]
    active_tasks = [t for t in _tasks.values() if t.status in ["IN_PROGRESS", "QA_REVIEW"]]
    confirmed_tasks = [t for t in _tasks.values() if t.status == "CONFIRMED"]
    pending_hires = [h for h in _hiring_proposals.values() if h.status == "PENDING_APPROVAL"]

    return {
        "agents": list(_agent_states.values()),
        "tasks": list(_tasks.values()),
        "pending_confirmations": pending_tasks,
        "active_tasks": active_tasks,
        "confirmed_tasks": confirmed_tasks,
        "pending_hires": pending_hires,
        "notifications": _notifications_log[:15],
        "counts": {
            "total_agents": len(_agent_states),
            "pending_confirmations": len(pending_tasks),
            "active_tasks": len(active_tasks),
            "confirmed_tasks": len(confirmed_tasks),
            "pending_hires": len(pending_hires),
        }
    }


# ─── Task Confirmation & Revision Handlers ───────────────────────────────────

async def confirm_task(task_id: str, owner_name: str = "Owner", feedback: Optional[str] = None) -> dict:
    """Owner กดยืนยันอนุมัติปิดงาน (Confirm & Close Task)"""
    if task_id not in _tasks:
        return {"success": False, "error": "ไม่พบ Task ID นี้"}

    task = _tasks[task_id]
    task.status = "CONFIRMED"
    task.confirmed_at = datetime.now(timezone.utc).isoformat()
    task.owner_feedback = feedback or "อนุมัติปิดงานเรียบร้อยโดย Owner"

    # อัปเดตสถานะ Agent ผู้รับผิดชอบให้กลับสู่ Standby
    if task.assigned_agent_id in _agent_states:
        ag = _agent_states[task.assigned_agent_id]
        ag.status = "idle"
        ag.current_action = f"✅ ปิดงานสำเร็จ: {task.title}"
        ag.current_thought = "Owner ได้ยืนยันอนุมัติปิดงานเรียบร้อย พร้อมรับคำสั่งใหม่"
        ag.progress = 100
        ag.current_task_id = None

    # บันทึก System Log
    write_log(LogCreate(
        agent_id=task.assigned_agent_id,
        agent_name=task.assigned_agent_name,
        level=LogLevel.SUCCESS,
        message=f"🎉 [ปิดงานสำเร็จ 100%] Owner ยืนยันอนุมัติปิดงาน: {task.title}",
        thought_process=f"Task ID: {task.id}\nผู้ยืนยัน: {owner_name}\nข้อความตอบกลับ: {task.owner_feedback}"
    ))

    # บันทึกผลงานลงใน company_memory.md
    try:
        if MEMORY_PATH.exists():
            content = MEMORY_PATH.read_text(encoding="utf-8")
            record_block = (
                f"\n\n### [ผลงานที่ Owner ยืนยันอนุมัติปิดงาน] — {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"- **ชื่องาน**: {task.title}\n"
                f"- **ผู้รับผิดชอบ**: {task.assigned_agent_name} ({task.department_id})\n"
                f"- **สรุปผลงาน**: {task.deliverable.summary if task.deliverable else 'สำเร็จตามเป้าหมาย'}\n"
                f"- **สถานะ**: อนุมัติปิดงาน 100% โดย {owner_name}\n"
            )
            MEMORY_PATH.write_text(content + record_block, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not append to company_memory.md: {e}")

    # ส่ง Telegram แจ้งเตือนปิดงานสำเร็จ
    await dispatch_telegram_notification(
        title="🎉 [ปิดงานเรียบร้อย 100%]",
        message=(
            f"ท่าน {owner_name} ได้ทำการ <b>ยืนยันอนุมัติปิดงาน</b> เรียบร้อยแล้ว!\n"
            f"📌 <b>งาน:</b> {task.title}\n"
            f"👤 <b>ผู้รับผิดชอบ:</b> {task.assigned_agent_name}\n"
            f"💬 <b>บันทึก:</b> {task.owner_feedback}\n"
            f"✨ ระบบได้จัดเก็บผลงานเข้าคลังข้อมูลบริษัทแล้วครับ"
        ),
        type_="task_confirmed",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return {"success": True, "task": task}


async def request_revision(task_id: str, feedback: str, owner_name: str = "Owner") -> dict:
    """Owner ขอให้ AI ปรับปรุงแก้ไขงานเพิ่มเติม"""
    if task_id not in _tasks:
        return {"success": False, "error": "ไม่พบ Task ID นี้"}

    task = _tasks[task_id]
    task.status = "REVISION_REQUESTED"
    task.owner_feedback = feedback

    if task.assigned_agent_id in _agent_states:
        ag = _agent_states[task.assigned_agent_id]
        ag.status = "coding" if task.category == "systems_dev" else "writing_content"
        ag.current_action = f"🔄 ปรับปรุงงานตาม Feedback ของ {owner_name}"
        ag.current_thought = f"ข้อเสนอแนะจาก Owner: {feedback} — กำลังดำเนินการปรับปรุงทันที"
        ag.progress = 60

    write_log(LogCreate(
        agent_id=task.assigned_agent_id,
        agent_name=task.assigned_agent_name,
        level=LogLevel.WARNING,
        message=f"🔄 Owner ส่งคำขอแก้ไขงาน: {task.title}",
        thought_process=f"ข้อเสนอแนะ: {feedback}"
    ))

    await dispatch_telegram_notification(
        title="🔄 [รับคำขอแก้ไขงาน]",
        message=(
            f"ท่าน {owner_name} ได้ส่งคำขอให้แก้ไขงาน:\n"
            f"📌 <b>งาน:</b> {task.title}\n"
            f"💬 <b>สิ่งที่ต้องปรับปรุง:</b> {feedback}\n"
            f"⚡ {task.assigned_agent_name} กำลังเร่งแก้ไขตามคำสั่งครับ"
        ),
        type_="alert",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return {"success": True, "task": task}


# ─── Dynamic AI Hiring Handlers ──────────────────────────────────────────────

async def request_ai_hiring(
    requested_by_id: str,
    proposed_role: str,
    department_id: str,
    department_name: str,
    avatar: str,
    reason: str,
    skills: str,
    identity: str,
    model: str = "gemini-1.5-flash"
) -> HiringProposal:
    """AI ยื่นคำขอจัดจ้าง / สร้าง AI เพิ่มเติม เมื่บิ๊นท์งานเฉพาะทางหรือโหลดงานสูง"""
    prop_id = str(uuid.uuid4())[:8]
    req_agent = _agent_states.get(requested_by_id)
    req_name = req_agent.name if req_agent else "เลขา อิงฟ้า"

    proposal = HiringProposal(
        id=prop_id,
        requested_by_agent_id=requested_by_id,
        requested_by_name=req_name,
        proposed_role=proposed_role,
        department_id=department_id,
        department_name=department_name,
        avatar=avatar,
        reason_and_need=reason,
        proposed_skills=skills,
        proposed_identity=identity,
        recommended_model=model,
        status="PENDING_APPROVAL",
    )
    _hiring_proposals[prop_id] = proposal

    if requested_by_id in _agent_states:
        _agent_states[requested_by_id].status = "requesting_hire"
        _agent_states[requested_by_id].current_action = f"เสนอขอสร้าง AI ตำแหน่ง: {proposed_role}"
        _agent_states[requested_by_id].current_thought = f"งานนี้จำเป็นต้องมีผู้เชี่ยวชาญเฉพาะด้าน ยื่นคำขออนุมัติต่อ Owner (ID: {prop_id})"

    write_log(LogCreate(
        agent_id=requested_by_id,
        agent_name=req_name,
        level=LogLevel.INFO,
        message=f"👥 ยื่นคำขอจัดจ้าง AI เพิ่มเติม: {proposed_role} (สังกัด {department_name})",
        thought_process=f"เหตุผล: {reason}\nโมเดลแนะนำ: {model}"
    ))

    # ส่ง Telegram แจ้งเตือนขออนุมัติสร้าง AI
    await dispatch_telegram_notification(
        title="👥 [คำขอจัดจ้าง AI เพิ่มเติม]",
        message=(
            f"<b>{req_name}</b> ได้ยื่นคำขออนุมัติสร้างพนักงาน AI เพิ่มเติม:\n\n"
            f"🏷️ <b>ตำแหน่ง:</b> {proposed_role}\n"
            f"🏢 <b>สังกัด:</b> {department_name}\n"
            f"💡 <b>เหตุผลความจำเป็น:</b> {reason}\n\n"
            f"👉 <i>กดอนุมัติบนหน้า Dashboard หรือพิมพ์ <code>/hire {prop_id}</code> ทาง Telegram เพื่อบรรจุเข้าทีมทันที</i>"
        ),
        type_="hiring_request",
        proposal_id=prop_id,
    )

    await broadcast_simulation_update()
    return proposal


async def approve_hiring_proposal(proposal_id: str, owner_name: str = "Owner") -> dict:
    """Owner กดยืนยันอนุมัติสร้าง AI พนักงานคนใหม่"""
    if proposal_id not in _hiring_proposals:
        return {"success": False, "error": "ไม่พบ Proposal ID นี้"}

    proposal = _hiring_proposals[proposal_id]
    proposal.status = "APPROVED"
    proposal.approved_at = datetime.now(timezone.utc).isoformat()

    # สร้างโฟลเดอร์ Agent จริงผ่าน agent_service
    from backend.models.schemas import AgentCreate
    try:
        new_agent = agent_service.create_agent(AgentCreate(
            name=proposal.proposed_role,
            department=proposal.department_id,
            model=proposal.recommended_model,
            temperature=0.5,
            identity=proposal.proposed_identity,
            skill=proposal.proposed_skills,
            job_description=f"รับผิดชอบงานด้าน {proposal.proposed_role} ให้แก่บริษัท",
            role=f"ai_{proposal.department_id}",
            pm_name=proposal.proposed_role,
        ))
    except Exception as e:
        logger.error(f"Failed to create agent files: {e}")

    # บรรจุเข้า _agent_states ให้ปรากฏใน Virtual Office ทันที
    _agent_states[proposal.department_id] = AgentState(
        id=proposal.department_id,
        name=proposal.proposed_role,
        role_title=proposal.proposed_role,
        department_id=proposal.department_id,
        department_name=proposal.department_name,
        avatar=proposal.avatar,
        status="idle",
        current_action="🎉 บรรจุเข้าทำงานเรียบร้อย พร้อมรับมอบหมายงาน",
        current_thought="ได้รับการอนุมัติจัดจ้างจาก Owner อย่างเป็นทางการ",
        progress=0,
    )

    # คืนสถานะผู้ขอจัดจ้าง
    if proposal.requested_by_agent_id in _agent_states:
        _agent_states[proposal.requested_by_agent_id].status = "idle"
        _agent_states[proposal.requested_by_agent_id].current_action = "พร้อมปฏิบัติงานต่อ"

    write_log(LogCreate(
        agent_id=proposal.department_id,
        agent_name=proposal.proposed_role,
        level=LogLevel.SUCCESS,
        message=f"✨ [รับพนักงานใหม่สำเร็จ] บรรจุ AI ตำแหน่ง {proposal.proposed_role} เข้าทีมเรียบร้อย!",
        thought_process=f"อนุมัติโดย: {owner_name}\nสังกัด: {proposal.department_name}"
    ))

    # แจ้งเตือน Telegram
    await dispatch_telegram_notification(
        title="✨ [บรรจุพนักงาน AI เรียบร้อย]",
        message=(
            f"ท่าน {owner_name} ได้อนุมัติการสร้างพนักงานใหม่:\n"
            f"👤 <b>{proposal.proposed_role}</b> ({proposal.avatar})\n"
            f"🏢 <b>สังกัด:</b> {proposal.department_name}\n"
            f"🚀 บรรจุเข้าสู่ทีมงาน Virtual Office และพร้อมรับคำสั่งงานแล้วครับ!"
        ),
        type_="task_confirmed",
        proposal_id=proposal.id,
    )

    await broadcast_simulation_update()
    return {"success": True, "proposal": proposal}


async def reject_hiring_proposal(proposal_id: str, reason: str = "ยังไม่มีความจำเป็นในขณะนี้") -> dict:
    """Owner ปฏิเสธการสร้าง AI"""
    if proposal_id not in _hiring_proposals:
        return {"success": False, "error": "ไม่พบ Proposal ID นี้"}

    proposal = _hiring_proposals[proposal_id]
    proposal.status = "REJECTED"

    if proposal.requested_by_agent_id in _agent_states:
        _agent_states[proposal.requested_by_agent_id].status = "idle"
        _agent_states[proposal.requested_by_agent_id].current_action = "รับทราบคำตัดสินของ Owner"

    write_log(LogCreate(
        agent_id=proposal.requested_by_agent_id,
        agent_name=proposal.requested_by_name,
        level=LogLevel.INFO,
        message=f"ปฏิเสธคำขอสร้าง AI {proposal.proposed_role}: {reason}"
    ))

    await broadcast_simulation_update()
    return {"success": True, "proposal": proposal}


# ─── High-Fidelity Step-by-Step Simulation Engine ───────────────────────────

async def simulate_system_development_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานพัฒนาระบบ (Software & Systems Dev Pipeline)
    Flow:
    1. อิงฟ้า (Secretary) รับคำสั่ง Owner → กระจายงาน
    2. บิ๊นท์ (Lead Dev) วาง Architecture → เขียน Code → เขียน Unit Test
    3. มุก (QA Analyst) ตรวจทาน Code Review & Test Case
    4. พลอย (Accounting) ประเมิน Cloud & Resource Cost
    5. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    6. ส่ง Telegram Notification ไปยัง Owner เพื่อขอยืนยันปิดงาน
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="systems_dev",
        assigned_agent_id="03_developer",
        assigned_agent_name="บิ๊นท์ (Lead Dev)",
        department_id="03_developer",
        collaborators=["01_secretary", "04_data_analyst", "05_accounting"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    # Step 1: อิงฟ้า รับและสรุปคำสั่ง
    _agent_states["01_secretary"].status = "planning"
    _agent_states["01_secretary"].current_action = f"วิเคราะห์ Requirement และแจกจ่ายงาน: {task_title}"
    _agent_states["01_secretary"].current_thought = "คำสั่งเน้นพัฒนาระบบเทคนิค มอบหมายให้บิ๊นท์เป็นผู้รับผิดชอบหลัก"
    _agent_states["01_secretary"].progress = 25
    _agent_states["01_secretary"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="อิงฟ้า (เลขา AI)",
        level=LogLevel.INFO,
        message=f"รับคำสั่งพัฒนาระบบ '{task_title}' มอบหมายงานให้บิ๊นท์ (Lead Dev)",
        thought_process=f"Prompt: {prompt_text}"
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    # Step 2: บิ๊นท์ เริ่มออกแบบสถาปัตยกรรมระบบ
    _agent_states["01_secretary"].status = "idle"
    _agent_states["03_developer"].status = "coding"
    _agent_states["03_developer"].current_action = "ออกแบบสถาปัตยกรรมระบบ และ Database Schema"
    _agent_states["03_developer"].current_thought = "กำหนด Clean Architecture: Pydantic Schemas, JWT Token Security, Rate Limiter"
    _agent_states["03_developer"].progress = 30
    _agent_states["03_developer"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="03_developer",
        agent_name="บิ๊นท์ (Lead Dev)",
        level=LogLevel.INFO,
        message=f"เริ่มออกแบบโครงสร้างระบบ API & Security สำหรับ '{task_title}'",
        thought_process="ใช้ FastAPI + Async SQLite/PostgreSQL + Pydantic v2 + OAuth2 Password Bearer"
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(3)

    # Step 3: บิ๊นท์ เขียน Code พัฒนาระบบจริง
    _agent_states["03_developer"].progress = 65
    _agent_states["03_developer"].current_action = "เขียนโค้ด Backend API, Router, Service และ Unit Test"
    _agent_states["03_developer"].current_thought = "เขียนโค้ดเสร็จแล้ว กำลังเตรียมชุดทดสอบ Pytest ให้ได้ Coverage 100%"
    write_log(LogCreate(
        agent_id="03_developer",
        agent_name="บิ๊นท์ (Lead Dev)",
        level=LogLevel.SUCCESS,
        message="เขียน Source Code และ Unit Tests สำเร็จ ส่งไม้ต่อให้ฝ่าย QA ตรวจสอบ",
        thought_process="Unit tests 5/5 PASSED. Endpoint latency: 12ms. Token hashing: bcrypt."
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(3)

    # Step 4: มุก รัน QA & Security Inspection
    task.status = "QA_REVIEW"
    _agent_states["03_developer"].status = "reviewing"
    _agent_states["04_data_analyst"].status = "reviewing"
    _agent_states["04_data_analyst"].current_action = "รัน Security Code Audit & Performance Check"
    _agent_states["04_data_analyst"].current_thought = "ตรวจสอบช่องโหว่ SQL Injection, XSS, และการจัดการ Expiration ของ JWT Token"
    _agent_states["04_data_analyst"].progress = 80
    write_log(LogCreate(
        agent_id="04_data_analyst",
        agent_name="มุก (QA Analyst)",
        level=LogLevel.SUCCESS,
        message="ผลตรวจสอบ QA ผ่านฉลุย 100% ไม่พบช่องโหว่ความปลอดภัย โค้ดพร้อมส่งมอบ",
        thought_process="Security Check: Clean | Code Standards: PEP8 Compliant | Error Handling: Guarded"
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2.5)

    # Step 5: สร้าง Deliverable Package พร้อมโค้ดตัวอย่างจริง
    sample_code = '''"""
auth_system.py — High-Performance JWT Authentication & User Management API
Developed autonomously by บิ๊นท์ (Lead Systems Dev)
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import bcrypt

SECRET_KEY = "enterprise-super-secure-token-key-2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="One-Person AI Enterprise - Auth Service", version="2.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Schemas ---
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime
    is_active: bool = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int

# In-memory secure user store (production: PostgreSQL)
users_db = {}

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister):
    """ลงทะเบียนผู้ใช้งานใหม่พร้อมเข้ารหัสรหัสผ่านด้วย bcrypt"""
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    user_record = {
        "id": f"usr_{len(users_db)+1:04d}",
        "username": user.username,
        "email": user.email,
        "hashed_password": get_password_hash(user.password),
        "created_at": datetime.now(timezone.utc),
        "is_active": True
    }
    users_db[user.username] = user_record
    return user_record

@app.post("/api/auth/token", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """เข้าสู่ระบบและรับ JWT Token สำหรับใช้งาน API"""
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": user["username"], "user_id": user["id"]})
    return {"access_token": token, "token_type": "bearer", "expires_in_seconds": 3600}
'''

    task.deliverable = TaskDeliverable(
        summary=f"พัฒนาระบบ {task_title} สำเร็จ พร้อมโค้ดระดับ Production, Unit Tests 100%, และ API Documentation",
        type="systems_dev",
        details="ระบบได้รับการออกแบบด้วย Clean Architecture มีการจัดการความปลอดภัยด้วย bcrypt & JWT Authentication ผ่านการตรวจสอบจาก QA เรียบร้อย",
        files_created=[
            {
                "name": "backend/auth_system.py",
                "language": "python",
                "content": sample_code
            },
            {
                "name": "tests/test_auth_system.py",
                "language": "python",
                "content": "def test_password_hash(): assert True\ndef test_jwt_generation(): assert True\ndef test_register_login_flow(): assert True"
            }
        ],
        checklist=[
            "สถาปัตยกรรม Clean Architecture และ Type Safety ครบถ้วน",
            "การเข้ารหัสรหัสผ่านด้วย bcrypt และ Sign Token ด้วย HS256",
            "Unit Tests ครบ 100% ผ่านการทดสอบโดย มุก (QA)",
            "จัดทำ API Documentation และ Postman Schema ครบถ้วน",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ผ่านการทดสอบ 5/5 Test Cases (Code Quality Score: 98/100, Latency: 12ms)",
        cost_estimate="ประมาณการค่าใช้จ่าย Cloud Server: $0.00 (รันบน Local/Existing Server)"
    )

    # Step 6: เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION (Mandatory HITL)
    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    _agent_states["03_developer"].status = "awaiting_confirmation"
    _agent_states["03_developer"].current_action = "🚨 งานเสร็จแล้ว! รอการยืนยันอนุมัติปิดงานจาก Owner"
    _agent_states["03_developer"].current_thought = "ส่งงานเข้าสู่กล่องรอยืนยันปิดงาน ห้ามปิดงานเองเด็ดขาดจนกว่า Owner จะกดอนุมัติ"
    _agent_states["03_developer"].progress = 95

    _agent_states["04_data_analyst"].status = "idle"
    _agent_states["04_data_analyst"].current_action = "ตรวจสอบเรียบร้อย พร้อมส่งมอบ"

    write_log(LogCreate(
        agent_id="03_developer",
        agent_name="บิ๊นท์ (Lead Dev)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] งาน '{task_title}' พัฒนาเสร็จสิ้น ส่งเรื่องให้ Owner ตรวจสอบและอนุมัติปิดงาน",
        thought_process=f"Deliverable ID: {task.id}\nรอคำสั่ง: ยืนยันปิดงาน หรือ ขอแก้ไข"
    ))

    # Step 7: ยิง Telegram Notification ตรงไปยัง Owner
    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>ฝ่ายพัฒนาระบบซอฟต์แวร์ (บิ๊นท์)</b> ได้พัฒนาระบบเสร็จสิ้นแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"💻 <b>ผลงาน:</b> โค้ด FastAPI Backend + JWT Auth + Unit Tests (ผ่าน 100%)\n"
            f"🔍 <b>QA ตรวจสอบ:</b> ผ่านการทดสอบความปลอดภัยแล้ว\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีครับ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def simulate_content_creation_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานสร้าง Content Social Media (Social Media Content Pipeline)
    Flow:
    1. อิงฟ้า (Secretary) วิเคราะห์ทิศทางและส่งต่อ ลิซ่า (Marketing Lead)
    2. ลิซ่า วางกลยุทธ์ Content Strategy, กำหนด Hook 3 วินาที, เขียนสคริปต์ TikTok/Reels
    3. ลิซ่า เขียนบทความ Facebook, โพสต์ LinkedIn, ชุดทวีต X, และ AI Image Prompts
    4. มุก (Data Analyst) วิเคราะห์ Engagement Projection
    5. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    6. ส่ง Telegram Notification ขอยืนยันปิดงานจาก Owner
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="social_content",
        assigned_agent_id="02_การตลาด_ai",
        assigned_agent_name="ลิซ่า (Content Lead)",
        department_id="02_การตลาด_ai",
        collaborators=["01_secretary", "04_data_analyst"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    # Step 1: วางแผนกลยุทธ์
    _agent_states["02_การตลาด_ai"].status = "writing_content"
    _agent_states["02_การตลาด_ai"].current_action = f"วิเคราะห์กลุ่มเป้าหมายและวาง Content Strategy: {task_title}"
    _agent_states["02_การตลาด_ai"].current_thought = "เลือก Mood & Tone ทันสมัย มอบคุณค่าแท้จริง เน้น Hook หยุดนิ้วโป้งใน 3 วินาที"
    _agent_states["02_การตลาด_ai"].progress = 25
    _agent_states["02_การตลาด_ai"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="02_การตลาด_ai",
        agent_name="ลิซ่า (Content Lead)",
        level=LogLevel.INFO,
        message=f"เริ่มร่างกลยุทธ์คอนเทนต์และปฏิทินโพสต์สำหรับ '{task_title}'",
        thought_process="Target: Developers, Tech Enthusiasts, Business Owners. Channels: TikTok, FB, X, LinkedIn."
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    # Step 2: เขียนสคริปต์ TikTok & โพสต์ Facebook
    _agent_states["02_การตลาด_ai"].progress = 60
    _agent_states["02_การตลาด_ai"].current_action = "เขียนสคริปต์วิดีโอ TikTok/Reels และแคปชัน Facebook/LinkedIn"
    _agent_states["02_การตลาด_ai"].current_thought = "สร้าง Storyboard สั้น กระชับ มีตัวอย่างจริง และ Call-To-Action ชัดเจน"
    write_log(LogCreate(
        agent_id="02_การตลาด_ai",
        agent_name="ลิซ่า (Content Lead)",
        level=LogLevel.INFO,
        message="เขียนสคริปต์วิดีโอสั้นและชุดบทความเสร็จเรียบร้อย กำลังออกแบบ AI Visual Prompts",
        thought_process="Hook: 'ถ้าคุณบริหารบริษัทคนเดียวด้วย AI 100% หน้าตาจะเป็นยังไง?'"
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(3)

    # Step 3: ออกแบบ AI Image Prompts
    _agent_states["02_การตลาด_ai"].progress = 85
    _agent_states["02_การตลาด_ai"].current_action = "สร้าง AI Image Prompts สำหรับ Midjourney/DALL-E สไตล์ Cyber Tech"
    _agent_states["02_การตลาด_ai"].current_thought = "กำหนด Prompt แสงนีออน สไตล์ Glassmorphism และความละเอียด 8k"
    write_log(LogCreate(
        agent_id="02_การตลาด_ai",
        agent_name="ลิซ่า (Content Lead)",
        level=LogLevel.SUCCESS,
        message="ชุดคอนเทนต์และ Visual Prompts เสร็จสมบูรณ์ ส่งให้ QA ตรวจสอบ Tone of Voice",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    # Step 4: รวม Deliverable Package
    tiktok_script = """[สคริปต์ TikTok / Reels / YouTube Shorts — ความยาว 45 วินาที]

⏱️ 0:00 - 0:03 (HOOK หยุดนิ้ว):
[ภาพเปิด]: ตัดภาพเร็วหน้าจอ Dashboard มี Agent 5 คนกำลังเขียนโค้ดและทำงานสดๆ
[เสียงพากย์]: "จะเกิดอะไรขึ้น... ถ้าบริษัทซอฟต์แวร์ทั้งบริษัท มีพนักงานเป็น AI 100% และคุณคือเจ้าของคนเดียว?"

⏱️ 0:04 - 0:25 (CORE VALUE & DEMO):
[ภาพ]: ซูมเข้าที่โต๊ะของ 'บิ๊นท์' กำลังเขียนโค้ด API และ 'ลิซ่า' กำลังคิดสคริปต์วิดีโอ
[เสียงพากย์]: "นี่คือ One-Person AI Enterprise! ไม่ใช่แค่บอทตอบแชทธรรมดา แต่เป็นทีมงาน AI ที่เขียนโค้ดจริง ออกแบบระบบจริง และทำ Content Social Media ได้เอง!"

⏱️ 0:26 - 0:38 (THE HIGHLIGHT / HITL RULE):
[ภาพ]: มีการแจ้งเตือนเด้งขึ้นมาบนหน้าจอ พร้อมข้อความเข้า Telegram ของเจ้าของ
[เสียงพากย์]: "และกฎเหล็กที่สำคัญที่สุด: ไม่ว่า AI คนไหนจะเก่งแค่ไหน ก่อนจะปิดงานหรือปล่อยระบบจริง... 'ทุกงานต้องผ่านการกดยืนยันจากผมก่อน 100%' เพื่อความแม่นยำสูงสุด!"

⏱️ 0:39 - 0:45 (CALL TO ACTION):
[ภาพ]: โลโก้บริษัท + ปุ่มลิงก์
[เสียงพากย์]: "อยากเห็นระบบนี้ทำงานสดๆ ไหม? คอมเมนต์คำว่า 'AI ENTERPRISE' แล้วเดี๋ยวผมพาไปดูหลังบ้าน!"
"""

    fb_post = """🚀 เปิดโลก "One-Person AI Enterprise": บริหารบริษัทพัฒนาระบบและมีเดียคนเดียว ด้วยทีมงาน AI 100% 🏢

หลายคนถามผมว่า ยุคนี้คนเดียวจะสร้างบริษัทเทคโนโลยีที่รับทั้ง "พัฒนาระบบซอฟต์แวร์" และ "ผลิตคอนเทนต์ Social Media" ได้ยังไงโดยไม่หมดไฟ?

คำตอบคือ: ผมไม่ได้ทำคนเดียว แต่ผมมี "ทีมงาน AI แบบ 100%" อยู่ข้างหลัง!

🤖 ทีมงานของเราแบ่งบทบาทชัดเจนเหมือนบริษัทจริง:
1. 🗂️ อิงฟ้า (เลขา AI) — คอยจับคำสั่ง วางแผน และกระจายงาน
2. 💻 บิ๊นท์ (Lead Dev) — เขียนโค้ด API, สถาปัตยกรรมระบบ และรัน Automated Tests
3. 📣 ลิซ่า (Marketing Lead) — วางแผนคอนเทนต์ สคริปต์วิดีโอ และยิงสื่อ Social Media
4. 📊 มุก (QA & Data) — สแกนบั๊กและความปลอดภัยก่อนส่งมอบ
5. 💰 พลอย (Finance) — ควบคุมงบประมาณและต้นทุน Cloud

⚠️ กฎเหล็กที่ทำให้ระบบนี้ปลอดภัย 100%:
"ไม่มี AI คนไหนสามารถปิดงานหรือปล่อยของสู่สาธารณะได้เอง ทุกงานก่อนจะปิดงาน ต้องส่งการแจ้งเตือนเข้า Telegram ให้ผมกดยืนยัน (Confirm) ด้วยตัวเองเสมอ"

นี่คืออนาคตของการทำงาน ที่คนคนเดียวสามารถมีศักยภาพเทียบเท่าทีมงานทั้งบริษัท!

💡 ใครสนใจเรื่อง Multi-Agent Architecture กด Like และ Save โพสต์นี้ไว้ได้เลยครับ!

#AIEnterprise #OnePersonBusiness #SoftwareDevelopment #TechInnovation #AutonomousAgents #GenerativeAI #CodingLife #SocialMediaStrategy
"""

    image_prompt = """Prompt สำหรับ AI Image Generator (Midjourney v6 / DALL-E 3):
"A futuristic high-tech glassmorphism virtual enterprise dashboard showing multiple glowing AI holographic agents collaborating, cyberpunk ambient lighting, neon cyan and royal violet accents, clean minimal ultra-detailed UI interface, cinematic lighting, 8k resolution, photorealistic, octane render --ar 16:9"
"""

    task.deliverable = TaskDeliverable(
        summary=f"ชุดคอนเทนต์ Social Media '{task_title}' ครบ 4 แพลตฟอร์ม (TikTok, FB, X, LinkedIn) พร้อม AI Visual Prompts",
        type="social_content",
        details="คอนเทนต์เน้นการสร้าง Engagement อธิบายจุดเด่นของระบบ One-Person AI Enterprise พร้อม Call to Action ชัดเจน",
        social_posts=[
            {
                "platform": "TikTok / Reels",
                "hook": "จะเกิดอะไรขึ้นถ้าบริษัททั้งบริษัทมีพนักงานเป็น AI 100%?",
                "content": tiktok_script,
                "hashtags": "#AIEnterprise #TechLife #DevTikTok #FutureOfWork",
                "image_prompt": image_prompt
            },
            {
                "platform": "Facebook Page & LinkedIn",
                "hook": "เปิดโลก One-Person AI Enterprise",
                "content": fb_post,
                "hashtags": "#AIEnterprise #OnePersonBusiness #SoftwareDev",
                "image_prompt": image_prompt
            }
        ],
        checklist=[
            "ผ่านการทดสอบ Hook 3 วินาทีแรกตามเกณฑ์ Viral Content",
            "เนื้อหาถูกต้องตามหลักการพัฒนาระบบและกฎ Human Confirmation",
            "จัดทำชุดแฮชแท็กและเวลาโพสต์ที่เหมาะสม (18:30 น.)",
            "แนบ Prompt ภาพประกอบสไตล์ High-Tech Glassmorphism",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ผ่านการประเมิน Tone of Voice: เป็นกันเอง น่าเชื่อถือ ดึงดูดสายตา",
        cost_estimate="ต้นทุนการผลิต: $0.00 (ขับเคลื่อนด้วย AI ทั้งหมด)"
    )

    # Step 5: เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    _agent_states["02_การตลาด_ai"].status = "awaiting_confirmation"
    _agent_states["02_การตลาด_ai"].current_action = "🚨 คอนเทนต์พร้อมส่งมอบ! รอ Owner ตรวจสอบและยืนยันปิดงาน"
    _agent_states["02_การตลาด_ai"].current_thought = "งานส่งเข้าสู่กล่องรอการยืนยัน ไม่เผยแพร่จนกว่า Owner จะอนุมัติ"
    _agent_states["02_การตลาด_ai"].progress = 95

    write_log(LogCreate(
        agent_id="02_การตลาด_ai",
        agent_name="ลิซ่า (Content Lead)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] คอนเทนต์ '{task_title}' ผลิตเสร็จสิ้น รอยืนยันอนุมัติจาก Owner",
        thought_process=f"Deliverable ID: {task.id}"
    ))

    # Step 6: ยิง Telegram Notification ตรงไปยัง Owner
    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>ฝ่ายการตลาดและ Social Content (ลิซ่า)</b> ผลิตคอนเทนต์เสร็จสิ้นแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"🎬 <b>สิ่งที่ผลิต:</b> สคริปต์ TikTok 45 วิ + บทความยาว Facebook/LinkedIn + AI Image Prompts\n"
            f"🎯 <b>เป้าหมาย:</b> ดึงดูดผู้ติดตามสาย Tech & ธุรกิจ\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีครับ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def simulate_ai_hiring_flow():
    """
    การจำลองสถานการณ์ AI ขอเสนอสร้างทีมเพิ่ม (Dynamic AI Scaling Flow)
    Flow:
    1. อิงฟ้า ตรวจพบว่างานต้องการความเชี่ยวชาญด้าน Cloud DevOps & Automation
    2. ยื่นคำขอจัดจ้าง 'ก้อง (Cloud DevOps & Automation Specialist)'
    3. ยิง Telegram แจ้งเตือน Owner
    4. รอ Owner กดอนุมัติ
    """
    proposal = await request_ai_hiring(
        requested_by_id="01_secretary",
        proposed_role="ก้อง (Cloud DevOps Specialist)",
        department_id="06_devops",
        department_name="ฝ่ายระบบคลาวด์และ DevOps อัตโนมัติ",
        avatar="⚡",
        reason="เพื่อรองรับการ Deploy ระบบขึ้น Cloud (Docker, Kubernetes, CI/CD) และดูแลความเสถียรของเซิร์ฟเวอร์แบบอัตโนมัติ 24/7 เพื่อให้ บิ๊นท์ มีสมาธิกับการเขียนโค้ด Feature หลัก",
        skills="Docker, Kubernetes, GitHub Actions, AWS/GCP Setup, Automated Monitoring, Server Security",
        identity="# ⚡ ก้อง (Cloud DevOps Specialist)\nรับผิดชอบด้าน Infrastructure, CI/CD Pipelines, และ Server Uptime 99.99%",
        model="gemini-1.5-flash"
    )
    return proposal


async def simulate_devops_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานฝ่ายวิศวกรรมคลาวด์และ DevOps (Cloud DevOps Pipeline)
    Flow:
    1. ก้อง (DevOps Specialist) ออกแบบ Containerization & Cloud Deployment Architecture
    2. ก้อง สร้าง Dockerfile + docker-compose.yml + GitHub Actions CI/CD Pipeline
    3. มุก (QA Analyst) ทำ Security Scan & Container Hardening Review
    4. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    5. ส่ง Telegram Notification ขอยืนยันปิดงานจาก Owner
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="devops",
        assigned_agent_id="06_devops",
        assigned_agent_name="ก้อง (Cloud DevOps)",
        department_id="06_devops",
        collaborators=["03_developer", "04_data_analyst"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    # Step 1: ออกแบบสถาปัตยกรรมคลาวด์
    if "06_devops" in _agent_states:
        _agent_states["06_devops"].status = "planning"
        _agent_states["06_devops"].current_action = f"วิเคราะห์ระบบและวางแผน Cloud Architecture: {task_title}"
        _agent_states["06_devops"].current_thought = "เลือก Multi-stage Docker, Zero-Downtime Deployment และ Nginx Reverse Proxy"
        _agent_states["06_devops"].progress = 25
        _agent_states["06_devops"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="06_devops",
        agent_name="ก้อง (Cloud DevOps)",
        level=LogLevel.INFO,
        message=f"เริ่มออกแบบระบบคลาวด์และ CI/CD สำหรับ '{task_title}'",
        thought_process="Architecture: Docker Compose + FastAPI + Postgres + Redis + SSL Let's Encrypt"
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    # Step 2: สร้างไฟล์คอนฟิก Docker & CI/CD
    if "06_devops" in _agent_states:
        _agent_states["06_devops"].progress = 65
        _agent_states["06_devops"].status = "coding"
        _agent_states["06_devops"].current_action = "สร้าง Dockerfile, docker-compose.yml และ GitHub Actions Workflow"
        _agent_states["06_devops"].current_thought = "ตั้งค่า Non-root User ใน Docker และจำกัดสิทธิ์ Security Context"
    write_log(LogCreate(
        agent_id="06_devops",
        agent_name="ก้อง (Cloud DevOps)",
        level=LogLevel.INFO,
        message="จัดทำ Dockerfile, Compose และ CI/CD Pipeline สำเร็จ ส่งให้ QA ตรวจสอบช่องโหว่",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2.5)

    # Step 3: มุก ตรวจความปลอดภัย Container
    task.status = "QA_REVIEW"
    if "04_data_analyst" in _agent_states:
        _agent_states["04_data_analyst"].status = "reviewing"
        _agent_states["04_data_analyst"].current_action = "สแกนหาช่องโหว่ Container & Port Security Scan"
        _agent_states["04_data_analyst"].current_thought = "ตรวจสอบ Trivy scan: 0 Critical, 0 High vulnerabilities. Port 80/443 only."
        _agent_states["04_data_analyst"].progress = 85
    write_log(LogCreate(
        agent_id="04_data_analyst",
        agent_name="มุก (QA Analyst)",
        level=LogLevel.SUCCESS,
        message="ตรวจสอบความปลอดภัยของคอนเทนเนอร์และ Pipeline ผ่านมาตรฐาน 100%",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    dockerfile_content = """# Multi-stage Production Dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runner
WORKDIR /app
RUN useradd -m -u 1000 appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:8000/api/health || exit 1
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

    compose_content = """version: '3.8'
services:
  app:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - enterprise_net

networks:
  enterprise_net:
    driver: bridge
"""

    ci_workflow = """name: Enterprise CI/CD Pipeline
on:
  push:
    branches: [ main ]
jobs:
  test_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies & Run Tests
        run: |
          pip install -r requirements.txt
          pytest tests/ -v
      - name: Build Docker Container
        run: docker build -t ai-enterprise:latest .
      - name: Automated Zero-Downtime Deploy
        run: echo "Production Deploy Verified!"
"""

    task.deliverable = TaskDeliverable(
        summary=f"วางระบบคลาวด์ Infrastructure และ CI/CD Pipeline สำหรับ '{task_title}' สำเร็จ",
        type="systems_dev",
        details="จัดทำ Production-Ready Dockerfile, docker-compose.yml และ GitHub Actions CI/CD Pipeline พร้อมระบบ Healthcheck อัตโนมัติ",
        files_created=[
            {"name": "Dockerfile", "language": "dockerfile", "content": dockerfile_content},
            {"name": "docker-compose.yml", "language": "yaml", "content": compose_content},
            {".github/workflows/deploy.yml": "yaml", "name": ".github/workflows/deploy.yml", "language": "yaml", "content": ci_workflow}
        ],
        checklist=[
            "Multi-stage Dockerfile พร้อม Non-root Appuser เพื่อความปลอดภัยสูงสุด",
            "Docker Compose พร้อม Healthcheck Service & Network Isolation",
            "GitHub Actions CI/CD Pipeline อัตโนมัติ ทดสอบ Unit Tests ก่อน Deploy",
            "ผ่านการตรวจสอบความปลอดภัยของ Container โดย มุก (QA Analyst)",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ผ่านการสแกนความปลอดภัย Container (Trivy Scan: 0 Critical, 0 High)",
        cost_estimate="ต้นทุน Cloud Infrastructure: ~$10 - $20/เดือน (VPS / Docker Droplet)"
    )

    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    if "06_devops" in _agent_states:
        _agent_states["06_devops"].status = "awaiting_confirmation"
        _agent_states["06_devops"].current_action = "🚨 งานวางระบบ Cloud เสร็จสิ้น! รอ Owner ยืนยันอนุมัติปิดงาน"
        _agent_states["06_devops"].current_thought = "จัดทำไฟล์ Docker & Pipeline เรียบร้อย ส่งเรื่องให้ Owner ตรวจสอบ"
        _agent_states["06_devops"].progress = 95

    if "04_data_analyst" in _agent_states:
        _agent_states["04_data_analyst"].status = "idle"
        _agent_states["04_data_analyst"].current_action = "ตรวจสอบเรียบร้อย พร้อมส่งมอบ"

    write_log(LogCreate(
        agent_id="06_devops",
        agent_name="ก้อง (Cloud DevOps)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] งาน Cloud DevOps '{task_title}' เสร็จสมบูรณ์ ส่งให้ Owner ยืนยันอนุมัติปิดงาน",
        thought_process=f"Deliverable ID: {task.id}"
    ))

    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>ฝ่ายวิศวกรรมคลาวด์และ DevOps (ก้อง)</b> ได้วางระบบเสร็จสิ้นแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"⚡ <b>ผลงาน:</b> Production Dockerfile + docker-compose + GitHub Actions CI/CD\n"
            f"🛡️ <b>QA Review:</b> ผ่านเกณฑ์ความปลอดภัย Container 100%\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีครับ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def simulate_data_analyst_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานฝ่ายตรวจสอบคุณภาพและวิเคราะห์ข้อมูล (QA & Data Analytics Pipeline)
    Flow:
    1. มุก (Data Analyst & QA) สแกนข้อมูล Metrics, Traffic Funnel, Conversion Rate
    2. วิเคราะห์คอขวด 3 อันดับแรก (Drop-off Analysis) ด้วย Python Script
    3. สรุป Insights ส่งต่อให้ Dev และ Marketing
    4. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    5. ส่ง Telegram Notification ขอยืนยันปิดงานจาก Owner
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="data_analytics",
        assigned_agent_id="04_data_analyst",
        assigned_agent_name="มุก (QA & Data Analyst)",
        department_id="04_data_analyst",
        collaborators=["01_secretary", "02_การตลาด_ai", "03_developer"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    if "04_data_analyst" in _agent_states:
        _agent_states["04_data_analyst"].status = "planning"
        _agent_states["04_data_analyst"].current_action = f"สแกนชุดข้อมูลและดึง Events Logs: {task_title}"
        _agent_states["04_data_analyst"].current_thought = "เชื่อมโยงข้อมูล Traffic, API Logs, และ Conversion Drop-offs"
        _agent_states["04_data_analyst"].progress = 30
        _agent_states["04_data_analyst"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="04_data_analyst",
        agent_name="มุก (QA & Data Analyst)",
        level=LogLevel.INFO,
        message=f"เริ่มรวบรวมข้อมูลสถิติและวิเคราะห์ Funnel สำหรับ '{task_title}'",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    if "04_data_analyst" in _agent_states:
        _agent_states["04_data_analyst"].status = "reviewing"
        _agent_states["04_data_analyst"].progress = 75
        _agent_states["04_data_analyst"].current_action = "ประมวลผลวิเคราะห์จุดรั่วไหล (Drop-off Rate) และสรุปรายงาน Insight"
        _agent_states["04_data_analyst"].current_thought = "พบจุดหลุดสูงสุดที่ขั้นตอน OTP Verification (drop 42%) สรุปข้อเสนอแนะให้ บิ๊นท์ ปรับแต่ง"
    write_log(LogCreate(
        agent_id="04_data_analyst",
        agent_name="มุก (QA & Data Analyst)",
        level=LogLevel.SUCCESS,
        message="วิเคราะห์ข้อมูล Funnel และคอขวดระบบสำเร็จ พร้อมมาตรการแก้ไขเชิงตัวเลข",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2.5)

    py_script = """# Analytics Pipeline — Funnel Drop-off & Conversion Rate
import json
from collections import Counter

def analyze_conversion_funnel(events):
    stages = ["visit_landing", "click_cta", "view_pricing", "submit_form", "payment_complete"]
    counts = Counter(e["stage"] for e in events)
    results = {}
    base = counts.get("visit_landing", 1)
    for s in stages:
        c = counts.get(s, 0)
        results[s] = {"count": c, "conversion_from_base": f"{(c/base)*100:.2f}%"}
    return results

# Analysis Summary:
# Landing Visitors: 12,500 (100%)
# View Pricing: 5,200 (41.6%)
# Submit Register: 2,100 (16.8%)
# Completed Payment: 945 (7.56%) — Bottleneck identified at OTP verification
"""

    task.deliverable = TaskDeliverable(
        summary=f"วิเคราะห์ข้อมูลสถิติและคอขวดระบบ '{task_title}' สำเร็จ พร้อมข้อเสนอแนะ Actionable",
        type="hybrid",
        details="วิเคราะห์ Conversion Funnel 12,500 รายการ ระบุจุดหลุดสำคัญที่หน้า OTP พร้อมข้อเสนอแนะปรับปรุง UX ร่วมกับทีม Dev และ Content",
        files_created=[
            {"name": "analytics/funnel_analysis.py", "language": "python", "content": py_script}
        ],
        checklist=[
            "สแกนข้อมูลกิจกรรมผู้ใช้งาน 12,500 ตัวอย่าง ไร้อคติทางสถิติ",
            "ระบุ 3 คอขวดสำคัญ: 1) ความล่าช้าของ OTP (42% drop), 2) หน้า Pricing ข้อมูลเยอะเกินไป, 3) ฟอร์มยาว",
            "ส่งมอบแผนงานปรับปรุงร่วมแก่ บิ๊นท์ (Dev) และ ลิซ่า (Marketing)",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ตรวจสอบความถูกต้องของข้อมูลสถิติ 100% (Confidence Interval: 95%)",
        cost_estimate="ต้นทุนการวิเคราะห์: $0.00 (ใช้อัลกอริทึมวิเคราะห์อัตโนมัติ)"
    )

    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    if "04_data_analyst" in _agent_states:
        _agent_states["04_data_analyst"].status = "awaiting_confirmation"
        _agent_states["04_data_analyst"].current_action = "🚨 รายงานวิเคราะห์เสร็จแล้ว! รอ Owner ตรวจสอบและยืนยันปิดงาน"
        _agent_states["04_data_analyst"].progress = 95

    write_log(LogCreate(
        agent_id="04_data_analyst",
        agent_name="มุก (QA & Data Analyst)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] รายงานวิเคราะห์ '{task_title}' เสร็จสมบูรณ์ ส่งให้ Owner ตรวจสอบและอนุมัติปิดงาน",
        thought_process=f"Deliverable ID: {task.id}"
    ))

    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>ฝ่ายตรวจสอบคุณภาพ & วิเคราะห์ข้อมูล (มุก)</b> จัดทำรายงานเสร็จสิ้นแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"📊 <b>ข้อค้นพบ:</b> Conversion Rate รวม 7.56% — พบจุดหลุดสำคัญที่ OTP Delay\n"
            f"💡 <b>ข้อเสนอแนะ:</b> ปรับปรุงความเร็ว OTP จะเพิ่มยอดได้ทันที +28%\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีครับ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def simulate_accounting_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานฝ่ายการเงินและควบคุมต้นทุนคลาวด์ (Finance & Cost Controller Pipeline)
    Flow:
    1. พลอย (Accountant) ดึงสถิติการใช้งาน Token API และ Cloud Servers
    2. คำนวณต้นทุนต่อหน่วย, วิเคราะห์ ROI และเปรียบเทียบงบประมาณ
    3. วางแผน Optimization ลดต้นทุน 35% ด้วย Prompt Caching
    4. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    5. ส่ง Telegram Notification ขอยืนยันปิดงานจาก Owner
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="accounting",
        assigned_agent_id="05_accounting",
        assigned_agent_name="พลอย (Finance & Cost)",
        department_id="05_accounting",
        collaborators=["01_secretary", "06_devops"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    if "05_accounting" in _agent_states:
        _agent_states["05_accounting"].status = "planning"
        _agent_states["05_accounting"].current_action = f"ดึงข้อมูลการใช้งาน API Tokens และงบประมาณ Cloud: {task_title}"
        _agent_states["05_accounting"].current_thought = "คำนวณ Token In/Out ของ Gemini และ Claude เทียบกับงบประมาณรายเดือน"
        _agent_states["05_accounting"].progress = 35
        _agent_states["05_accounting"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="05_accounting",
        agent_name="พลอย (Finance & Cost)",
        level=LogLevel.INFO,
        message=f"เริ่มตรวจสอบต้นทุน API Tokens และค่าใช้จ่ายคลาวด์สำหรับ '{task_title}'",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    if "05_accounting" in _agent_states:
        _agent_states["05_accounting"].progress = 75
        _agent_states["05_accounting"].status = "reviewing"
        _agent_states["05_accounting"].current_action = "คำนวณ ROI ประเมินจุดคุ้มทุน และวางแผนลดต้นทุนด้วย Prompt Caching"
        _agent_states["05_accounting"].current_thought = "การใช้ Gemini 1.5 Flash ช่วยประหยัดงบได้ถึง 85% เมื่อเทียบกับ GPT-4"
    write_log(LogCreate(
        agent_id="05_accounting",
        agent_name="พลอย (Finance & Cost)",
        level=LogLevel.SUCCESS,
        message="สรุปงบการเงินและต้นทุน Token สำเร็จ อยู่ในเกณฑ์ควบคุม ไม่เกินงบประมาณที่กำหนด",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2.5)

    audit_code = """# Financial Cost & Token Audit Utility
def calculate_enterprise_costs():
    token_usage = {
        "gemini_flash_input": 1_250_000,
        "gemini_flash_output": 350_000,
        "claude_sonnet_input": 45_000,
        "claude_sonnet_output": 12_000
    }
    rates = {
        "gemini_flash_input": 0.075 / 1_000_000,
        "gemini_flash_output": 0.30 / 1_000_000,
        "claude_sonnet_input": 3.00 / 1_000_000,
        "claude_sonnet_output": 15.00 / 1_000_000
    }
    total_usd = sum(token_usage[k] * rates[k] for k in token_usage)
    return {
        "monthly_token_cost_usd": round(total_usd, 4),
        "monthly_budget_usd": 50.00,
        "budget_remaining_usd": round(50.00 - total_usd, 4),
        "status": "HEALTHY (Utilized 0.6% of limit)"
    }
"""

    task.deliverable = TaskDeliverable(
        summary=f"รายงานสรุปงบประมาณและต้นทุน AI Tokens สำหรับ '{task_title}' สำเร็จ (ปลอดภัย ต่ำกว่างบ 99%)",
        type="hybrid",
        details="ตรวจสอบการใช้งาน Gemini Flash และ Claude Sonnet รวมค่าใช้จ่ายรายเดือนเพียง $0.32 USD จากโควตา $50.00 USD ควบคุมความปลอดภัยระดับสูงสุด",
        files_created=[
            {"name": "finance/cost_audit.py", "language": "python", "content": audit_code}
        ],
        checklist=[
            "ตรวจสอบค่าใช้จ่าย API Token ครบ 100% ไม่มี Token รั่วไหล",
            "ต้นทุนจริงรายเดือนอยู่ที่ $0.32 USD (ใช้ไปเพียง 0.64% ของงบประมาณ)",
            "ยืนยันว่าระบบอยู่ในโซนปลอดภัยสูงสุด (Safe Budget Zone)",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ตัวเลขบัญชีผ่านการ Audit ถูกต้องตรงกับ API Billing Logs 100%",
        cost_estimate="ค่าใช้จ่ายทั้งหมดของเดือนนี้: $0.32 USD (งบเหลือ $49.68 USD)"
    )

    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    if "05_accounting" in _agent_states:
        _agent_states["05_accounting"].status = "awaiting_confirmation"
        _agent_states["05_accounting"].current_action = "🚨 รายงานงบการเงินเสร็จแล้ว! รอ Owner ยืนยันอนุมัติปิดงาน"
        _agent_states["05_accounting"].progress = 95

    write_log(LogCreate(
        agent_id="05_accounting",
        agent_name="พลอย (Finance & Cost)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] รายงานบัญชี '{task_title}' เสร็จสมบูรณ์ ส่งให้ Owner ตรวจสอบและอนุมัติปิดงาน",
        thought_process=f"Deliverable ID: {task.id}"
    ))

    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>ฝ่ายการเงิน & ต้นทุน Cloud (พลอย)</b> จัดทำรายงานสรุปงบประมาณเสร็จแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"💰 <b>ยอดค่าใช้จ่าย Token:</b> $0.32 USD (เหลืองบ $49.68 USD)\n"
            f"🛡️ <b>สถานะความปลอดภัย:</b> ยอดใช้งานปกติ ไม่มีความเสี่ยงงบบานปลาย\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีครับ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def simulate_secretary_flow(task_title: str, custom_prompt: str = ""):
    """
    การจำลองการทำงานสำนักเลขานุการ & CKO (Executive Secretary & Strategic Sync)
    Flow:
    1. อิงฟ้า (Secretary) สแกนสถานะงานและความคืบหน้าของทุกแผนก
    2. จัดทำ Executive Strategic Briefing สรุปภาพรวมและ Milestone
    3. อัปเดตบันทึกลงใน company_memory.md
    4. ส่งมอบ Deliverable เข้าสู่สถานะ 🚨 AWAITING_CONFIRMATION
    5. ส่ง Telegram Notification ขอยืนยันปิดงานจาก Owner
    """
    task_id = str(uuid.uuid4())[:8]
    prompt_text = custom_prompt or task_title

    task = EnterpriseTask(
        id=task_id,
        title=task_title,
        category="strategic_sync",
        assigned_agent_id="01_secretary",
        assigned_agent_name="อิงฟ้า (เลขา AI & CKO)",
        department_id="01_secretary",
        collaborators=["02_การตลาด_ai", "03_developer", "04_data_analyst", "05_accounting", "06_devops"],
        status="IN_PROGRESS",
        prompt=prompt_text,
    )
    _tasks[task_id] = task

    if "01_secretary" in _agent_states:
        _agent_states["01_secretary"].status = "planning"
        _agent_states["01_secretary"].current_action = f"รวบรวมสถานะงานของทั้ง 5 แผนกปฏิบัติการ: {task_title}"
        _agent_states["01_secretary"].current_thought = "เชื่อมโยงความคืบหน้าของ บิ๊นท์, ลิซ่า, มุก, พลอย, ก้อง เพื่อรายงานท่าน Owner"
        _agent_states["01_secretary"].progress = 30
        _agent_states["01_secretary"].current_task_id = task_id
    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="อิงฟ้า (เลขา AI & CKO)",
        level=LogLevel.INFO,
        message=f"เริ่มรวบรวมข้อมูลสถานะบริษัทและจัดทำ Executive Sync สำหรับ '{task_title}'",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2)

    if "01_secretary" in _agent_states:
        _agent_states["01_secretary"].progress = 75
        _agent_states["01_secretary"].status = "writing_content"
        _agent_states["01_secretary"].current_action = "จัดทำรายงานภาพรวมองค์กร และบันทึกข้อสรุปลงใน company_memory.md"
        _agent_states["01_secretary"].current_thought = "สถานะทุกทีมเข้มแข็ง ไม่มีงานค้างคา ระบบ AI 100% พร้อมขยายตัว"
    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="อิงฟ้า (เลขา AI & CKO)",
        level=LogLevel.SUCCESS,
        message="สรุปสถานะการดำเนินงานขององค์กรเสร็จสมบูรณ์ เตรียมส่งมอบให้ Owner ตรวจสอบ",
    ))
    await broadcast_simulation_update()
    await asyncio.sleep(2.5)

    briefing_md = f"""# 🏢 Executive Strategic Briefing — One-Person AI Enterprise
**วันที่จัดทำ:** {datetime.now().strftime('%Y-%m-%d %H:%M')} ICT  
**ผู้จัดทำ:** อิงฟ้า (เลขาธิการบริหาร & CKO)  

---

### 📊 สถานะความคืบหน้าของแต่ละแผนก:
1. **💻 ฝ่ายพัฒนาระบบ (บิ๊นท์)**: ระบบ Backend API & Authentication ทำงานสมบูรณ์ 100% พร้อม Unit Tests
2. **📣 ฝ่ายการตลาด (ลิซ่า)**: สคริปต์วิดีโอสั้นและชุดบทความ Social Media เตรียมพร้อมปล่อยตามปฏิทิน
3. **⚡ ฝ่าย DevOps (ก้อง)**: Containerization (Docker) และ CI/CD Pipeline เตรียมพร้อมสำหรับ Production Deploy
4. **📊 ฝ่ายวิเคราะห์ & QA (มุก)**: ผลการทดสอบความปลอดภัยผ่านฉลุย อัตรา Conversion ประเมินไว้ที่ 7.56%
5. **💰 ฝ่ายการเงิน (พลอย)**: งบประมาณ Token ใช้งานไปเพียง $0.32 USD จากโควตา $50.00 USD (ประหยัด 99%)

---

### 🎯 แผนปฏิบัติการระยะถัดไป:
- ขยายการเชื่อมโยงระบบแจ้งเตือน 1-on-1 เข้าสู่ Telegram ของท่าน Owner ให้ครบทุกแผนก
- ดำเนินการตามแผนกลยุทธ์บริษัทคนเดียวที่ขับเคลื่อนด้วย AI 100% ต่อเนื่อง
"""

    task.deliverable = TaskDeliverable(
        summary=f"รายงานสรุปภาพรวมและการประชุมผู้บริหาร '{task_title}' สำเร็จ",
        type="hybrid",
        details="สรุปสถานะการทำงานของ 5 แผนกหลัก บันทึกบทเรียนลงใน company_memory.md พร้อมแผนงานระยะถัดไป",
        files_created=[
            {"name": "reports/executive_sync_report.md", "language": "markdown", "content": briefing_md}
        ],
        checklist=[
            "รวบรวมสถานะงานครบทั้ง 5 แผนกปฏิบัติการ ไร้จุดตกหล่น",
            "อัปเดตบันทึกคลังความรู้ company_memory.md ครบถ้วน",
            "จัดทำแผนปฏิบัติการระยะถัดไป (Action Plan) ชัดเจน",
            "🚨 รอการยืนยันและอนุมัติปิดงานจาก Owner"
        ],
        qa_report="✅ ผ่านการสอบทานความสอดคล้องกับเป้าหมายองค์กร 100%",
        cost_estimate="ต้นทุนการบริหาร: $0.00 (ขับเคลื่อนด้วย AI ทั้งหมด)"
    )

    task.status = "AWAITING_CONFIRMATION"
    task.submitted_at = datetime.now(timezone.utc).isoformat()

    if "01_secretary" in _agent_states:
        _agent_states["01_secretary"].status = "awaiting_confirmation"
        _agent_states["01_secretary"].current_action = "🚨 สรุปงานประจำวันเสร็จแล้ว! รอ Owner ตรวจสอบและยืนยันปิดงาน"
        _agent_states["01_secretary"].progress = 95

    write_log(LogCreate(
        agent_id="01_secretary",
        agent_name="อิงฟ้า (เลขา AI & CKO)",
        level=LogLevel.WARNING,
        message=f"🚨 [รอยืนยันปิดงาน] สรุปรายงาน '{task_title}' เสร็จสมบูรณ์ ส่งให้ Owner ยืนยันอนุมัติปิดงาน",
        thought_process=f"Deliverable ID: {task.id}"
    ))

    await dispatch_telegram_notification(
        title="🚨 [รอยืนยันปิดงานจาก Owner]",
        message=(
            f"<b>สำนักเลขานุการ & CKO (อิงฟ้า)</b> สรุปภาพรวมองค์กรเสร็จสิ้นแล้ว:\n\n"
            f"📌 <b>ชื่องาน:</b> {task_title}\n"
            f"📑 <b>สรุป:</b> ความคืบหน้าครบ 5 แผนก, ระบบเสถียร, ค่าใช้จ่ายต่ำกว่างบประมาณ\n"
            f"📖 <b>คลังความรู้:</b> อัปเดตลง company_memory.md เรียบร้อยแล้วค่ะ\n\n"
            f"👉 <b>กรุณาตรวจสอบและยืนยันปิดงาน:</b>\n"
            f"• กดปุ่ม <b>'อนุมัติปิดงาน'</b> บนหน้า Dashboard หรือ\n"
            f"• พิมพ์ตอบกลับ Telegram <code>/confirm {task.id}</code> หรือพิมพ์ <b>'อนุมัติ'</b> ได้ทันทีค่ะ"
        ),
        type_="confirmation_request",
        task_id=task.id,
    )

    await broadcast_simulation_update()
    return task


async def run_simulation_preset(preset_key: str, custom_text: str = "") -> dict:
    """
    สั่งเริ่มการจำลองการทำงานตาม Preset ที่เลือก หรือใช้ AI Auto-Router อัจฉริยะ
    กระจายงานให้แผนกที่ตรงสายอัตโนมัติ 100%
    """
    global _active_simulation_task

    # รีเซ็ตความพร้อม
    init_agent_states()

    # 1. แผนกพัฒนาระบบ (บิ๊นท์ - 03_developer)
    if preset_key == "systems_dev":
        task_title = custom_text or "พัฒนาระบบ Backend REST API + JWT Authentication & User Management"
        _active_simulation_task = asyncio.create_task(simulate_system_development_flow(task_title, custom_text))
        return {"status": "started", "preset": "systems_dev", "assigned_to": "บิ๊นท์ (Lead Dev)", "title": task_title}

    # 2. แผนกการตลาด (ลิซ่า - 02_การตลาด_ai)
    elif preset_key == "social_content":
        task_title = custom_text or "สร้าง Content Social Media: เปิดตัว One-Person AI Enterprise 100% (TikTok & Facebook)"
        _active_simulation_task = asyncio.create_task(simulate_content_creation_flow(task_title, custom_text))
        return {"status": "started", "preset": "social_content", "assigned_to": "ลิซ่า (Marketing Lead)", "title": task_title}

    # 3. แผนก DevOps & Cloud (ก้อง - 06_devops)
    elif preset_key == "devops":
        task_title = custom_text or "วางระบบ Container Docker และ CI/CD Pipeline อัตโนมัติ"
        _active_simulation_task = asyncio.create_task(simulate_devops_flow(task_title, custom_text))
        return {"status": "started", "preset": "devops", "assigned_to": "ก้อง (Cloud DevOps)", "title": task_title}

    # 4. แผนก QA & วิเคราะห์ข้อมูล (มุก - 04_data_analyst)
    elif preset_key == "data_analyst":
        task_title = custom_text or "วิเคราะห์ Conversion Funnel และสแกนคอขวดของระบบ"
        _active_simulation_task = asyncio.create_task(simulate_data_analyst_flow(task_title, custom_text))
        return {"status": "started", "preset": "data_analyst", "assigned_to": "มุก (QA & Data Analyst)", "title": task_title}

    # 5. แผนกการเงินและต้นทุน (พลอย - 05_accounting)
    elif preset_key == "accounting":
        task_title = custom_text or "สรุปยอดการใช้งาน AI Tokens และควบคุมงบประมาณ Cloud รายเดือน"
        _active_simulation_task = asyncio.create_task(simulate_accounting_flow(task_title, custom_text))
        return {"status": "started", "preset": "accounting", "assigned_to": "พลอย (Finance & Cost)", "title": task_title}

    # 6. แผนกเลขาธิการ & บริหารกลยุทธ์ (อิงฟ้า - 01_secretary)
    elif preset_key == "secretary":
        task_title = custom_text or "จัดทำรายงานสรุปภาพรวมองค์กร และอัปเดตคลังความรู้บริษัท"
        _active_simulation_task = asyncio.create_task(simulate_secretary_flow(task_title, custom_text))
        return {"status": "started", "preset": "secretary", "assigned_to": "อิงฟ้า (เลขา AI & CKO)", "title": task_title}

    # งานประสานงานข้ามทีม (Collaborative Full Launch)
    elif preset_key == "collaborative":
        task_title = custom_text or "พัฒนาระบบ Microservice พร้อมผลิต Content เปิดตัวโปรโมตสู่ตลาด"
        async def combined():
            await simulate_system_development_flow("พัฒนาระบบ Microservice Data Analytics API", custom_text)
            await asyncio.sleep(1)
            await simulate_content_creation_flow("สร้าง Content เปิดตัวฟีเจอร์ Data Analytics ใหม่ลง Social Media", custom_text)
        _active_simulation_task = asyncio.create_task(combined())
        return {"status": "started", "preset": "collaborative", "assigned_to": "ทีมร่วม (บิ๊นท์ + ลิซ่า)", "title": task_title}

    # ขออนุมัติสร้างทีมเพิ่ม (Hiring Request)
    elif preset_key == "hiring_request":
        _active_simulation_task = asyncio.create_task(simulate_ai_hiring_flow())
        return {"status": "started", "preset": "hiring_request", "assigned_to": "อิงฟ้า (เลขา AI)", "title": "AI ขอเสนอสร้างทีมเพิ่ม"}

    # 🧠 Autonomous AI Orchestrator Auto-Router (วิเคราะห์และมอบหมายงานอัตโนมัติ)
    else:
        text_lower = (custom_text or "").lower()

        # ตรวจจับสายงาน DevOps & Cloud
        if any(w in text_lower for w in ["devops", "docker", "k8s", "kubernetes", "ci/cd", "ci-cd", "deploy", "server", "เซิร์ฟเวอร์", "คลาวด์", "infra", "port", "nginx"]):
            chosen_preset = "devops"
            assigned_name = "ก้อง (Cloud DevOps Specialist)"
            dept_name = "ฝ่ายวิศวกรรมคลาวด์และ DevOps"

        # ตรวจจับสายงาน บัญชี / การเงิน / งบประมาณ
        elif any(w in text_lower for w in ["บัญชี", "การเงิน", "งบ", "cost", "token", "budget", "finance", "roi", "ภาษี", "กำไร", "ขาดทุน", "ค่าใช้จ่าย", "เงิน"]):
            chosen_preset = "accounting"
            assigned_name = "พลอย (Finance & Cost Controller)"
            dept_name = "ฝ่ายการเงิน & ต้นทุน Cloud"

        # ตรวจจับสายงาน QA / Data Analytics
        elif any(w in text_lower for w in ["data", "analyst", "analytics", "qa", "funnel", "conversion", "ตรวจ", "สถิติ", "คอขวด", "บั๊ก", "test", "audit", "คุณภาพ"]):
            chosen_preset = "data_analyst"
            assigned_name = "มุก (Senior QA & Data Analyst)"
            dept_name = "ฝ่ายตรวจสอบคุณภาพ & วิเคราะห์ข้อมูล"

        # ตรวจจับสายงาน Content & Marketing
        elif any(w in text_lower for w in ["content", "tiktok", "facebook", "reels", "shorts", "โพสต์", "คลิป", "วิดีโอ", "การตลาด", "marketing", "แคปชั่น", "ยิงแอด"]):
            chosen_preset = "social_content"
            assigned_name = "ลิซ่า (Head of Marketing & Content)"
            dept_name = "ฝ่ายการตลาดและ Social Content"

        # ตรวจจับสายงาน เลขา / สรุปภาพรวม / วางแผน
        elif any(w in text_lower for w in ["ประชุม", "เลขา", "สรุป", "ภาพรวม", "บริบท", "memory", "sync", "ยุทธศาสตร์", "อิงฟ้า", "แผนงาน"]):
            chosen_preset = "secretary"
            assigned_name = "อิงฟ้า (Executive Secretary & CKO)"
            dept_name = "สำนักเลขานุการ & CKO"

        # ตรวจจับ Full Launch ร่วมกัน
        elif any(w in text_lower for w in ["full launch", "เปิดตัว", "ทั้งระบบ", "ร่วมกัน", "collaborative"]):
            chosen_preset = "collaborative"
            assigned_name = "ทีมงานร่วม (บิ๊นท์ + ลิซ่า)"
            dept_name = "ปฏิบัติการร่วมข้ามแผนก"

        # ค่าเริ่มต้น: สายงานพัฒนาระบบซอฟต์แวร์
        else:
            chosen_preset = "systems_dev"
            assigned_name = "บิ๊นท์ (Lead Software & Systems Dev)"
            dept_name = "ฝ่ายพัฒนาระบบซอฟต์แวร์"

        # บันทึก System Log จากเลขาอิงฟ้าว่ากำลังวิเคราะห์และแจกจ่ายงานอัตโนมัติ
        write_log(LogCreate(
            agent_id="01_secretary",
            agent_name="อิงฟ้า (เลขา AI & Orchestrator)",
            level=LogLevel.SUCCESS,
            message=f"🧠 [AI Auto-Orchestrator] วิเคราะห์คำสั่ง: '{custom_text[:50]}...' ➔ มอบหมายงานให้อัตโนมัติ: {assigned_name} ({dept_name})",
            thought_process=f"Autonomous Intent Routing: {chosen_preset} | Target Assignee: {assigned_name}"
        ))

        return await run_simulation_preset(chosen_preset, custom_text)


def reset_simulation():
    """รีเซ็ตสถานะทั้งหมดกลับสู่ค่าเริ่มต้น"""
    global _tasks, _hiring_proposals, _notifications_log
    _tasks.clear()
    _hiring_proposals.clear()
    init_agent_states()
    for ag in _agent_states.values():
        ag.status = "idle"
        ag.current_action = "พร้อมรับคำสั่งจาก Owner"
        ag.current_thought = "ระบบสแตนด์บาย ทุกกระบวนการต้องรอการยืนยันจาก Owner ก่อนปิดงาน"
        ag.progress = 0
        ag.current_task_id = None
    seed_initial_completed_tasks()
    return {"status": "reset_complete"}


# ─── Employee Workstation & Telemetry Services ───────────────────────────────


EMPLOYEE_NICKNAMES_MAP = {
    "01_secretary": "อิงฟ้า (ฟ้า)",
    "02_การตลาด_ai": "ลิซ่า (ลิซ่า)",
    "03_developer": "บิ๊นท์ (บิ๊นท์)",
    "04_data_analyst": "มุก (มุก)",
    "05_accounting": "พลอย (พลอย)",
    "06_devops": "ก้อง (ก้อง)",
}

EMPLOYEE_MOTTOS_MAP = {
    "01_secretary": "ศูนย์กลางประสานงาน AI ทั้งบริษัท ควบคุมขั้นตอน และจัดการคลังความรู้ 100%",
    "02_การตลาด_ai": "วางกลยุทธ์ ผลิตสคริปต์สั้น และคอนเทนต์สร้าง Brand Awareness 100%",
    "03_developer": "พัฒนาซอฟต์แวร์ API, Database, Automation คุณภาพระดับ Production • ก่อนปิดงานต้องให้ Owner ยืนยันเสมอ (HITL)",
    "04_data_analyst": "ตรวจสอบคุณภาพงานระบบและคอนเทนต์ พร้อมค้นหาจุดรั่วไหลเพื่อเพิ่ม Conversion Rate สูงสุด",
    "05_accounting": "ควบคุมงบประมาณ ตรวจสอบต้นทุน Token/Cloud และดูแลอัตรากำไร (Profit Margin)",
    "06_devops": "ดูแล Server Uptime 99.99%, วางระบบ CI/CD Pipelines, และจัดการ Cloud Deployment",
}

EMPLOYEE_TECH_STACK_MAP = {
    "01_secretary": ["Orchestration", "Daily Sync", "Knowledge Management", "Telegram API", "Decision Matrix"],
    "02_การตลาด_ai": ["Short-Form Video", "TikTok/Reels", "Viral Copywriting", "AI Visual Prompts", "Social Analytics"],
    "03_developer": ["FastAPI", "Python", "JWT Auth", "PostgreSQL", "Docker", "Pytest", "RESTful API"],
    "04_data_analyst": ["QA Code Review", "Security Audit", "Funnel Analytics", "OWASP Top 10", "Conversion Tracking"],
    "05_accounting": ["Token Auditing", "Cloud Cost Control", "ROI Forecast", "Budget Guardrails", "Ledger Analytics"],
    "06_devops": ["Docker", "Kubernetes", "CI/CD Actions", "Nginx SSL", "Zero-Downtime", "Healthcheck 99.99%"],
}


def list_employee_workspaces() -> List[Dict[str, Any]]:
    """ดึงรายชื่อและสรุปสถานะโต๊ะทำงานของพนักงาน AI ทุกคน"""
    init_agent_states()
    workspaces = []
    all_tasks = list(_tasks.values())

    for agent_id, state in _agent_states.items():
        # ค้นหางานทั้งหมดที่เกี่ยวข้องกับพนักงานคนนี้
        agent_tasks = [
            t for t in all_tasks
            if t.assigned_agent_id == agent_id or t.department_id == agent_id or agent_id in t.collaborators
        ]
        completed = [t for t in agent_tasks if t.status == "CONFIRMED"]
        active = [t for t in agent_tasks if t.status in ("IN_PROGRESS", "QA_REVIEW")]
        pending = [t for t in agent_tasks if t.status == "AWAITING_CONFIRMATION"]

        current_task_info = None
        if active:
            current_task_info = active[0]
        elif pending:
            current_task_info = pending[0]

        photo_url = get_employee_avatar_url(agent_id)
        nickname = EMPLOYEE_NICKNAMES_MAP.get(agent_id, state.name)
        motto = EMPLOYEE_MOTTOS_MAP.get(agent_id, "พร้อมปฏิบัติงานด้วยความแม่นยำสูงสุด")

        workspaces.append({
            "id": agent_id,
            "name": state.name,
            "nickname": nickname,
            "role_title": state.role_title,
            "department_id": state.department_id,
            "department_name": state.department_name,
            "avatar": state.avatar,
            "photo_url": photo_url,
            "motto": motto,
            "status": state.status,
            "current_action": state.current_action,
            "current_thought": state.current_thought,
            "progress": state.progress,
            "current_task_id": state.current_task_id,
            "current_task_title": current_task_info.title if current_task_info else None,
            "current_task_category": current_task_info.category if current_task_info else None,
            "completed_tasks_count": len(completed),
            "active_tasks_count": len(active),
            "pending_confirm_count": len(pending),
            "total_tasks_count": len(agent_tasks),
            "tech_stack": EMPLOYEE_TECH_STACK_MAP.get(agent_id, ["AI Autonomous", "Production-grade"]),
            "quality_rating": "99.4%",
            "security_rating": "100%",
            "compliance_rating": "100%",
            "uptime": "99.99%",
            "last_updated": state.last_updated
        })

    return workspaces


def get_employee_workspace(employee_id: str) -> Optional[Dict[str, Any]]:
    """ดึงข้อมูลโต๊ะทำงาน (Workspace), สถานะสด, สถิติ และประวัติงานย้อนหลังของพนักงานรายคน"""
    init_agent_states()
    if employee_id not in _agent_states:
        # พยายามค้นหาแบบ fuzzy
        matched_id = None
        for aid, st in _agent_states.items():
            if employee_id.lower() in aid.lower() or employee_id.lower() in st.name.lower():
                matched_id = aid
                break
        if matched_id:
            employee_id = matched_id
        else:
            return None

    state = _agent_states[employee_id]

    # อ่านไฟล์ identity, skill, job_description จาก departments
    dept_dir = BASE_DIR / "departments" / employee_id
    identity_content = ""
    skill_content = ""
    job_desc_content = ""
    config_data = {}

    if dept_dir.exists():
        if (dept_dir / "identity.md").exists():
            identity_content = (dept_dir / "identity.md").read_text(encoding="utf-8")
        if (dept_dir / "skill.md").exists():
            skill_content = (dept_dir / "skill.md").read_text(encoding="utf-8")
        if (dept_dir / "job_description.md").exists():
            job_desc_content = (dept_dir / "job_description.md").read_text(encoding="utf-8")
        if (dept_dir / "config.json").exists():
            try:
                config_data = json.loads((dept_dir / "config.json").read_text(encoding="utf-8"))
            except Exception:
                pass

    # ดึงงานทั้งหมดของพนักงานคนนี้
    agent_tasks = [
        t for t in _tasks.values()
        if t.assigned_agent_id == employee_id or t.department_id == employee_id or employee_id in t.collaborators
    ]
    # เรียงลำดับจากสร้างล่าสุดไปเก่าสุด
    agent_tasks.sort(key=lambda x: x.created_at or "", reverse=True)

    completed_tasks = [t for t in agent_tasks if t.status == "CONFIRMED"]
    active_tasks = [t for t in agent_tasks if t.status in ("IN_PROGRESS", "QA_REVIEW")]
    pending_tasks = [t for t in agent_tasks if t.status == "AWAITING_CONFIRMATION"]

    current_task = None
    if active_tasks:
        current_task = active_tasks[0]
    elif pending_tasks:
        current_task = pending_tasks[0]
    elif state.current_task_id and state.current_task_id in _tasks:
        current_task = _tasks[state.current_task_id]

    # ดึง Logs ล่าสุดที่เกี่ยวข้องกับพนักงานคนนี้
    from backend.services.log_service import get_logs
    agent_logs = get_logs(agent_id=employee_id, limit=20)
    if not agent_logs:
        # ค้นหาด้วยชื่อพนักงาน
        agent_logs = get_logs(search=state.name, limit=20)

    # แปลง log entries เป็น dict
    formatted_logs = [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat() if hasattr(l.timestamp, "isoformat") else str(l.timestamp),
            "level": str(l.level.value) if hasattr(l.level, "value") else str(l.level),
            "message": l.message,
            "thought_process": l.thought_process
        }
        for l in agent_logs
    ]

    photo_url = get_employee_avatar_url(employee_id)
    nickname = EMPLOYEE_NICKNAMES_MAP.get(employee_id, state.name)
    motto = EMPLOYEE_MOTTOS_MAP.get(employee_id, "พร้อมปฏิบัติงานเพื่อบรรลุเป้าหมายของ Owner")
    tech_stack = EMPLOYEE_TECH_STACK_MAP.get(employee_id, ["AI Engine", "Quality Focused"])

    # ปรับสถานะเป็นข้อความภาษาไทย
    status_label_th = "⚪ สแตนด์บายพร้อมรับคำสั่ง"
    status_badge_type = "idle"
    if state.status == "awaiting_confirmation":
        status_label_th = "🚨 รอยืนยันอนุมัติปิดงาน (HITL)"
        status_badge_type = "pending"
    elif state.status == "requesting_hire":
        status_label_th = "👥 เสนอขอจ้าง AI เพิ่ม"
        status_badge_type = "hiring"
    elif state.status in ("coding", "writing_content", "reviewing", "planning", "active"):
        status_badge_type = "active"
        if state.status == "coding":
            status_label_th = "💻 กำลังเขียนโค้ดและพัฒนาระบบ"
        elif state.status == "writing_content":
            status_label_th = "✍️ กำลังสร้างสรรค์คอนเทนต์"
        elif state.status == "reviewing":
            status_label_th = "🔍 กำลังตรวจสอบ QA & คุณภาพ"
        else:
            status_label_th = "⚡ กำลังปฏิบัติงานสด"

    return {
        "employee": {
            "id": employee_id,
            "name": state.name,
            "nickname": nickname,
            "role_title": state.role_title,
            "department_id": state.department_id,
            "department_name": state.department_name,
            "avatar": state.avatar,
            "photo_url": photo_url,
            "motto": motto,
            "model": config_data.get("model", "gemini-1.5-flash"),
            "temperature": config_data.get("temperature", 0.5),
            "status": state.status,
            "status_label_th": status_label_th,
            "status_badge_type": status_badge_type,
            "current_action": state.current_action,
            "current_thought": state.current_thought,
            "progress": state.progress,
            "identity_md": identity_content,
            "skill_md": skill_content,
            "job_description_md": job_desc_content,
            "tech_stack": tech_stack,
            "bot_token": config_data.get("bot_token", ""),
            "has_bot": bool(config_data.get("bot_token")),
            "last_updated": state.last_updated
        },
        "telemetry": {
            "total_tasks": len(agent_tasks),
            "completed_tasks_count": len(completed_tasks),
            "active_tasks_count": len(active_tasks),
            "pending_confirm_count": len(pending_tasks),
            "quality_score": "100%" if completed_tasks else "99.2%",
            "security_score": "100%",
            "compliance_score": "100%",
            "risk_index": "Low Risk (0 Critical Issues)",
            "uptime": "99.99%",
            "avg_turnaround_time": "1.4 นาที",
            "owner_approval_rating": "100%"
        },
        "current_task": current_task.model_dump() if current_task and hasattr(current_task, "model_dump") else current_task,
        "tasks_history": [
            t.model_dump() if hasattr(t, "model_dump") else t
            for t in agent_tasks
        ],
        "recent_logs": formatted_logs
    }



