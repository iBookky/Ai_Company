#!/usr/bin/env python3
"""
scan_agents.py — สแกนโฟลเดอร์ departments/ และส่งคืนรายชื่อ Agent ทั้งหมด
รัน: python scripts/scan_agents.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
DEPARTMENTS_DIR = BASE_DIR / "departments"


def scan_agents() -> list[dict]:
    agents = []
    if not DEPARTMENTS_DIR.exists():
        return agents

    for dept_dir in sorted(DEPARTMENTS_DIR.iterdir()):
        if not dept_dir.is_dir() or dept_dir.name.startswith("."):
            continue

        config_file = dept_dir / "config.json"
        identity_file = dept_dir / "identity.md"
        skill_file = dept_dir / "skill.md"

        config = {}
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                config = {}

        agent = {
            "id": dept_dir.name,
            "name": config.get("name", dept_dir.name),
            "role": config.get("role", "unknown"),
            "model": config.get("model", "gemini-1.5-flash"),
            "temperature": config.get("temperature", 0.5),
            "department": dept_dir.name,
            "has_identity": identity_file.exists(),
            "has_skill": skill_file.exists(),
            "identity_preview": (
                identity_file.read_text(encoding="utf-8")[:200]
                if identity_file.exists() else ""
            ),
            "skill_preview": (
                skill_file.read_text(encoding="utf-8")[:200]
                if skill_file.exists() else ""
            ),
            "created_at": config.get("created_at", ""),
            "path": str(dept_dir),
        }
        agents.append(agent)

    return agents


def main():
    agents = scan_agents()
    result = {
        "total": len(agents),
        "scanned_at": datetime.now().isoformat(),
        "agents": agents
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
