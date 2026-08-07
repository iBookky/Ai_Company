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

    config = {}
    if config_file.exists():
        try:
            config = json.loads(config_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    return AgentRead(
        id=dept_dir.name,
        name=config.get("name", dept_dir.name),
        role=config.get("role", "agent"),
        model=config.get("model", "gemini-1.5-flash"),
        temperature=config.get("temperature", 0.5),
        department=dept_dir.name,
        ops_chat_id=config.get("ops_chat_id", ""),
        pm_name=config.get("pm_name", ""),
        has_identity=identity_file.exists(),
        has_skill=skill_file.exists(),
        identity_preview=(
            identity_file.read_text(encoding="utf-8")[:300]
            if identity_file.exists() else ""
        ),
        skill_preview=(
            skill_file.read_text(encoding="utf-8")[:300]
            if skill_file.exists() else ""
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
    """ดึงข้อมูล Agent พร้อม identity และ skill เต็ม"""
    dept_dir = DEPARTMENTS_DIR / agent_id
    if not dept_dir.exists():
        return None

    base = _read_agent_dir(dept_dir)
    if not base:
        return None

    identity_file = dept_dir / "identity.md"
    skill_file = dept_dir / "skill.md"

    return AgentDetail(
        **base.model_dump(),
        identity=identity_file.read_text(encoding="utf-8") if identity_file.exists() else "",
        skill=skill_file.read_text(encoding="utf-8") if skill_file.exists() else "",
    )


def create_agent(data: AgentCreate) -> AgentRead:
    """สร้าง Agent ใหม่พร้อมโฟลเดอร์และไฟล์"""
    # สร้างชื่อโฟลเดอร์
    dept_id = data.department.strip()
    if not re.match(r"^\d+_", dept_id):
        idx = _get_next_dept_index()
        safe_name = _sanitize_dir_name(data.name)
        dept_id = f"{idx}_{safe_name}"

    dept_dir = DEPARTMENTS_DIR / dept_id
    dept_dir.mkdir(parents=True, exist_ok=True)

    # เขียนไฟล์
    (dept_dir / "identity.md").write_text(data.identity, encoding="utf-8")
    (dept_dir / "skill.md").write_text(data.skill, encoding="utf-8")

    config = {
        "name": data.name,
        "role": data.role or "agent",
        "pm_name": data.pm_name or f"PM {data.name}",
        "model": data.model,
        "temperature": data.temperature,
        "department": dept_id,
        "parent_department": data.parent_department,
        "ops_chat_id": data.ops_chat_id or "",
        "created_at": datetime.now().isoformat(),
    }
    (dept_dir / "config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return _read_agent_dir(dept_dir)


def update_agent(agent_id: str, data: AgentUpdate) -> Optional[AgentRead]:
    """อัปเดตข้อมูล Agent"""
    dept_dir = DEPARTMENTS_DIR / agent_id
    if not dept_dir.exists():
        return None

    config_file = dept_dir / "config.json"
    config = {}
    if config_file.exists():
        config = json.loads(config_file.read_text(encoding="utf-8"))

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

    config["updated_at"] = datetime.now().isoformat()
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


    if data.identity is not None:
        (dept_dir / "identity.md").write_text(data.identity, encoding="utf-8")
    if data.skill is not None:
        (dept_dir / "skill.md").write_text(data.skill, encoding="utf-8")

    return _read_agent_dir(dept_dir)


def delete_agent(agent_id: str) -> bool:
    """ลบ Agent และโฟลเดอร์ทั้งหมด"""
    dept_dir = DEPARTMENTS_DIR / agent_id
    if not dept_dir.exists():
        return False
    shutil.rmtree(dept_dir)
    return True
