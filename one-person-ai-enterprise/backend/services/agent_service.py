"""
agent_service.py — Business logic สำหรับ Agent CRUD operations
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from backend.models.schemas import AgentCreate, AgentRead, AgentUpdate, AgentDetail

BASE_DIR = Path(__file__).parent.parent.parent
DEPARTMENTS_DIR = BASE_DIR / "departments"


def _sanitize_dir_name(name: str) -> str:
    """แปลงชื่อเป็น folder-safe string"""
    name = re.sub(r"[^\w\s-]", "", name, flags=re.UNICODE)
    name = re.sub(r"\s+", "_", name.strip())
    return name.lower()


def _get_next_dept_index() -> str:
    """หาเลขลำดับถัดไปสำหรับโฟลเดอร์แผนก"""
    DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)
    existing = [
        d.name for d in DEPARTMENTS_DIR.iterdir()
        if d.is_dir() and re.match(r"^\d+_", d.name)
    ]
    if not existing:
        return "03"
    indices = [int(d.split("_")[0]) for d in existing if d.split("_")[0].isdigit()]
    return str(max(indices) + 1).zfill(2)


def _read_agent_dir(dept_dir: Path) -> Optional[AgentRead]:
    """อ่านข้อมูล Agent จากโฟลเดอร์"""
    if not dept_dir.is_dir():
        return None

    config_file = dept_dir / "config.json"
    identity_file = dept_dir / "identity.md"
    skill_file = dept_dir / "skill.md"
    job_description_file = dept_dir / "job_description.md"
    memory_file = dept_dir / "memory.md"

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # Avatar URL
    avatar_url = config.get("avatar_url", "")
    if not avatar_url:
        default_avatars = {
            "01_secretary": "/static/img/avatars/01_secretary.jpg",
            "02_การตลาด_ai": "/static/img/avatars/02_marketing.jpg",
            "02_marketing": "/static/img/avatars/02_marketing.jpg",
            "03_developer": "/static/img/avatars/03_developer.jpg",
            "04_data_analyst": "/static/img/avatars/04_data_analyst.jpg",
            "05_accounting": "/static/img/avatars/05_accounting.jpg",
            "06_sales": "/static/img/avatars/06_sales.jpg",
        }
        avatar_url = default_avatars.get(dept_dir.name, "/static/img/avatars/01_secretary.jpg")

    return AgentRead(
        id=dept_dir.name,
        name=config.get("name", dept_dir.name),
        role=config.get("role", "agent"),
        model=config.get("model", "gemini-1.5-flash"),
        temperature=config.get("temperature", 0.5),
        department=dept_dir.name,
        ops_chat_id=config.get("ops_chat_id", ""),
        pm_name=config.get("pm_name", ""),
        avatar_url=avatar_url,
        has_identity=identity_file.exists(),
        has_skill=skill_file.exists(),
        has_job_description=job_description_file.exists(),
        has_memory=memory_file.exists(),
        identity_preview=(
            identity_file.read_text(encoding="utf-8")[:300]
            if identity_file.exists() else ""
        ),
        skill_preview=(
            skill_file.read_text(encoding="utf-8")[:300]
            if skill_file.exists() else ""
        ),
        job_description_preview=(
            job_description_file.read_text(encoding="utf-8")[:300]
            if job_description_file.exists() else ""
        ),
        memory_preview=(
            memory_file.read_text(encoding="utf-8")[:350]
            if memory_file.exists() else ""
        ),
        created_at=config.get("created_at", ""),
        path=str(dept_dir),
    )


def list_agents() -> list[AgentRead]:
    """ดึงรายชื่อ Agent ทั้งหมด"""
    DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)
    agents = []
    for dept_dir in sorted(DEPARTMENTS_DIR.iterdir()):
        if dept_dir.is_dir() and not dept_dir.name.startswith("."):
            agent = _read_agent_dir(dept_dir)
            if agent:
                agents.append(agent)
    return agents


def get_agent(agent_id: str) -> Optional[AgentDetail]:
    """ดึงข้อมูล Agent พร้อม identity, skill และ job_description เต็ม"""
    if not agent_id or ".." in agent_id or "/" in agent_id or "\\" in agent_id:
        return None
    dept_dir = (DEPARTMENTS_DIR / agent_id).resolve()
    if not dept_dir.is_relative_to(DEPARTMENTS_DIR) or not dept_dir.exists():
        return None

    base = _read_agent_dir(dept_dir)
    if not base:
        return None

    identity_file = dept_dir / "identity.md"
    skill_file = dept_dir / "skill.md"
    job_description_file = dept_dir / "job_description.md"

    return AgentDetail(
        **base.model_dump(),
        identity=identity_file.read_text(encoding="utf-8") if identity_file.exists() else "",
        skill=skill_file.read_text(encoding="utf-8") if skill_file.exists() else "",
        job_description=job_description_file.read_text(encoding="utf-8") if job_description_file.exists() else "",
    )


def create_agent(data: AgentCreate) -> AgentRead:
    """สร้าง Agent ใหม่พร้อมโฟลเดอร์และไฟล์อย่างปลอดภัย"""
    # สร้างชื่อโฟลเดอร์
    dept_id = data.department.strip()
    if not re.match(r"^\d+_", dept_id):
        idx = _get_next_dept_index()
        safe_name = _sanitize_dir_name(data.name)
        dept_id = f"{idx}_{safe_name}"
    else:
        # Enforce safe directory name chars ป้องกัน Path Traversal
        if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", dept_id):
            raise ValueError("รหัสแผนกไม่ถูกต้อง มีอักขระที่ไม่ปลอดภัย")

    dept_dir = (DEPARTMENTS_DIR / dept_id).resolve()
    if not dept_dir.is_relative_to(DEPARTMENTS_DIR):
        raise ValueError("Invalid department path")
    dept_dir.mkdir(parents=True, exist_ok=True)

    # เขียนไฟล์
    (dept_dir / "identity.md").write_text(data.identity, encoding="utf-8")
    (dept_dir / "skill.md").write_text(data.skill, encoding="utf-8")
    (dept_dir / "job_description.md").write_text(data.job_description, encoding="utf-8")

    config = {
        "name": data.name,
        "role": data.role or "agent",
        "pm_name": data.pm_name or f"PM {data.name}",
        "model": data.model,
        "temperature": data.temperature,
        "department": dept_id,
        "parent_department": data.parent_department,
        "ops_chat_id": data.ops_chat_id or "",
        "avatar_url": data.avatar_url or "",
        "created_at": datetime.now().isoformat(),
    }
    (dept_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return _read_agent_dir(dept_dir)


def update_agent(agent_id: str, data: AgentUpdate) -> Optional[AgentRead]:
    """อัปเดตข้อมูล Agent"""
    if not agent_id or not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", agent_id):
        return None
    dept_dir = (DEPARTMENTS_DIR / agent_id).resolve()
    if not dept_dir.is_relative_to(DEPARTMENTS_DIR) or not dept_dir.exists():
        return None

    config_file = dept_dir / "config.json"
    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    if data.name is not None:
        config["name"] = data.name
    if data.model is not None:
        config["model"] = data.model
    if data.temperature is not None:
        config["temperature"] = data.temperature
    if data.ops_chat_id is not None:
        config["ops_chat_id"] = data.ops_chat_id
    if data.pm_name is not None:
        config["pm_name"] = data.pm_name
    if data.avatar_url is not None:
        config["avatar_url"] = data.avatar_url
        try:
            from backend.services import simulation_service
            simulation_service.EMPLOYEE_AVATARS_MAP[agent_id] = data.avatar_url
        except Exception:
            pass

    config["updated_at"] = datetime.now().isoformat()
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    if data.identity is not None:
        (dept_dir / "identity.md").write_text(data.identity, encoding="utf-8")
    if data.skill is not None:
        (dept_dir / "skill.md").write_text(data.skill, encoding="utf-8")
    if data.job_description is not None:
        (dept_dir / "job_description.md").write_text(data.job_description, encoding="utf-8")

    return _read_agent_dir(dept_dir)


def delete_agent(agent_id: str) -> bool:
    """ลบ Agent และโฟลเดอร์อย่างปลอดภัย (ป้องกันการลบแผนกหลักและ Path Traversal)"""
    # ป้องกันการลบแผนกหลัก 6 แผนก
    CORE_DEPTS = {"01_secretary", "02_การตลาด_ai", "03_developer", "04_data_analyst", "05_accounting", "06_sales"}
    if agent_id in CORE_DEPTS:
        return False

    if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", agent_id):
        return False

    dept_dir = (DEPARTMENTS_DIR / agent_id).resolve()
    if not dept_dir.is_relative_to(DEPARTMENTS_DIR.resolve()) or not dept_dir.exists():
        return False

    try:
        shutil.rmtree(dept_dir)
        return True
    except Exception:
        return False


def rename_department_id(old_id: str, new_id: str) -> bool:
    """เปลี่ยนชื่อโฟลเดอร์ ID ของแผนก/ทีมบนดิสก์อย่างปลอดภัย"""
    if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", old_id) or not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", new_id):
        return False

    old_dir = (DEPARTMENTS_DIR / old_id).resolve()
    new_dir = (DEPARTMENTS_DIR / new_id).resolve()

    if not old_dir.is_relative_to(DEPARTMENTS_DIR.resolve()) or not new_dir.is_relative_to(DEPARTMENTS_DIR.resolve()):
        return False

    if not old_dir.exists() or new_dir.exists():
        return False

    try:
        old_dir.rename(new_dir)
        config_file = new_dir / "config.json"
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8"))
            config["department"] = new_id
            config["updated_at"] = datetime.now().isoformat()
            config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False
