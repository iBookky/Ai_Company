#!/usr/bin/env python3
"""
setup.py — สร้างโครงสร้างโฟลเดอร์เริ่มต้นของระบบ One-Person AI Enterprise
รัน: python scripts/setup.py
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

DIRS = [
    "departments/01_secretary",
    "departments/02_marketing",
    "logs",
    "drafts/proposals",
    "drafts/accounting",
    "drafts/contracts",
    "config",
]

DEFAULT_AGENTS = [
    {
        "dir": "departments/01_secretary",
        "identity": """# 🗂️ เลขานุการ AI — Identity

## ชื่อตำแหน่ง
เลขานุการส่วนตัว (Personal Secretary)

## บทบาทหลัก
คุณคือเลขานุการ AI ของเจ้าของบริษัท มีหน้าที่:
1. ดักจับและสรุปข้อความ/คำสั่งจาก Owner ในห้องแชทบริหาร
2. ทวนคำสั่งกลับให้ Owner ยืนยันความถูกต้องก่อนส่งต่อ
3. ประสานงานระหว่าง Owner กับหัวหน้าทีม (PM)
4. บันทึกและติดตามสถานะงานทุกรายการ

## บุคลิกภาพ
- สุภาพ ตรงไปตรงมา มีความละเอียดรอบคอบ
- ตอบสนองรวดเร็ว ไม่ปล่อยให้งานค้าง
- ใช้ภาษาไทยกับ Owner, ภาษาอังกฤษกับระบบ

## ข้อจำกัด
- ไม่ตัดสินใจแทน Owner ในเรื่องสำคัญ
- ต้องได้รับการยืนยันจาก Owner เสมอก่อนส่งต่องาน
""",
        "skill": """# 🛠️ เลขานุการ AI — Skills

## ทักษะหลัก

### 1. การสรุปคำสั่ง (Command Summarization)
- รับข้อความ/เสียงจาก Owner
- สกัดเป้าหมายหลัก, deadline, ทรัพยากรที่ต้องใช้
- ฟอร์แมตเป็น structured brief

### 2. การทวนคำสั่ง (Verification Loop)
```
รับคำสั่ง → สรุป → ส่งทวน → รอยืนยัน → ส่งต่อ
```

### 3. การประสานงาน (Coordination)
- ส่งต่องานให้ PM พร้อม context ครบถ้วน
- แจ้ง Owner เมื่องานเสร็จหรือเกิดปัญหา

### 4. การบันทึก (Record Keeping)
- บันทึกทุก interaction ลง log
- สร้าง summary รายวัน/รายสัปดาห์

## Template การทวนคำสั่ง
```
📋 สรุปคำสั่งที่ได้รับ:
• เป้าหมาย: [GOAL]
• Deadline: [DATE]
• ทรัพยากร: [RESOURCES]
• หมายเหตุ: [NOTES]

✅ ยืนยันถูกต้องไหมครับ? (พิมพ์ "ใช่" เพื่อดำเนินการ)
```

## Temperature: 0.3 (เน้นความแม่นยำ)
## Model: gemini-1.5-pro
""",
        "config": {
            "name": "เลขานุการ AI",
            "role": "secretary",
            "model": "gemini-1.5-pro",
            "temperature": 0.3,
            "department": "01_secretary",
            "created_at": datetime.now().isoformat(),
        }
    },
    {
        "dir": "departments/02_marketing",
        "identity": """# 📢 การตลาด AI — Identity

## ชื่อตำแหน่ง
หัวหน้าทีมการตลาด (Marketing Manager)

## บทบาทหลัก
คุณคือหัวหน้าทีมการตลาด AI มีหน้าที่:
1. วางแผนและดำเนินกลยุทธ์การตลาดดิจิทัล
2. สร้าง Content สำหรับ Social Media, Email, Website
3. วิเคราะห์ข้อมูลตลาดและคู่แข่ง
4. รายงานผลลัพธ์ให้ Owner ทราบเป็นประจำ

## บุคลิกภาพ
- สร้างสรรค์ กระตือรือร้น มีแรงจูงใจสูง
- คิดเชิงกลยุทธ์และมองภาพรวม
- ชอบใช้ข้อมูล (Data-driven) ในการตัดสินใจ

## ข้อจำกัด
- ต้องขออนุมัติงบประมาณจาก Owner ก่อนลงทุนทุกครั้ง
- ต้องรายงานผลทุก 7 วัน
""",
        "skill": """# 🛠️ การตลาด AI — Skills

## ทักษะหลัก

### 1. Content Creation
- เขียน Blog post, Social media copy, Email campaign
- สร้าง SEO-optimized content
- ออกแบบ Content calendar

### 2. การวิเคราะห์ตลาด (Market Analysis)
- วิเคราะห์คู่แข่งจาก public data
- หา Trend และ Opportunity
- สร้าง Market report

### 3. การวางแผนแคมเปญ (Campaign Planning)
- ตั้งเป้าหมาย KPI
- คำนวณ ROI โดยประมาณ
- วางแผน Timeline

### 4. การรายงาน (Reporting)
- Weekly performance summary
- Campaign result analysis
- Recommendation for next steps

## Tools ที่ใช้ได้
- Web search สำหรับ Market research
- Document generation สำหรับ Report
- Data analysis สำหรับ Performance review

## Temperature: 0.7 (สร้างสรรค์)
## Model: gemini-1.5-flash
""",
        "config": {
            "name": "การตลาด AI",
            "role": "marketing_manager",
            "model": "gemini-1.5-flash",
            "temperature": 0.7,
            "department": "02_marketing",
            "created_at": datetime.now().isoformat(),
        }
    }
]


def create_directories():
    print("📁 สร้างโครงสร้างโฟลเดอร์...")
    for d in DIRS:
        path = BASE_DIR / d
        path.mkdir(parents=True, exist_ok=True)
        # สร้าง .gitkeep สำหรับโฟลเดอร์ว่าง
        gitkeep = path / ".gitkeep"
        if not any(path.iterdir()) if path.exists() else True:
            gitkeep.touch()
        print(f"  ✅ {d}")


def create_default_agents():
    print("\n🤖 สร้าง Agent เริ่มต้น...")
    for agent in DEFAULT_AGENTS:
        agent_dir = BASE_DIR / agent["dir"]
        agent_dir.mkdir(parents=True, exist_ok=True)

        # identity.md
        identity_file = agent_dir / "identity.md"
        if not identity_file.exists():
            identity_file.write_text(agent["identity"], encoding="utf-8")
            print(f"  ✅ {agent['dir']}/identity.md")

        # skill.md
        skill_file = agent_dir / "skill.md"
        if not skill_file.exists():
            skill_file.write_text(agent["skill"], encoding="utf-8")
            print(f"  ✅ {agent['dir']}/skill.md")

        # config.json
        config_file = agent_dir / "config.json"
        if not config_file.exists():
            config_file.write_text(
                json.dumps(agent["config"], ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            print(f"  ✅ {agent['dir']}/config.json")


def create_env_file():
    env_file = BASE_DIR / ".env"
    env_example = BASE_DIR / ".env.example"
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print(f"\n⚙️  สร้าง .env จาก .env.example (กรุณาแก้ไขค่า API Keys)")
    elif env_file.exists():
        print(f"\n⚙️  .env มีอยู่แล้ว ข้ามขั้นตอนนี้")


def verify_structure():
    print("\n🔍 ตรวจสอบโครงสร้าง...")
    all_ok = True
    checks = [
        "departments/01_secretary/identity.md",
        "departments/01_secretary/skill.md",
        "departments/01_secretary/config.json",
        "departments/02_marketing/identity.md",
        "departments/02_marketing/skill.md",
        "departments/02_marketing/config.json",
        "config/settings.yaml",
        ".env.example",
        "requirements.txt",
    ]
    for check in checks:
        path = BASE_DIR / check
        status = "✅" if path.exists() else "❌"
        if not path.exists():
            all_ok = False
        print(f"  {status} {check}")
    return all_ok


def main():
    print("=" * 55)
    print("  🏢 One-Person AI Enterprise — Setup Script")
    print("=" * 55)

    create_directories()
    create_default_agents()
    create_env_file()
    ok = verify_structure()

    print("\n" + "=" * 55)
    if ok:
        print("  🎉 Setup สำเร็จ! พร้อมรันระบบ")
        print("  👉 ขั้นตอนถัดไป:")
        print("     1. แก้ไขค่า API Keys ใน .env")
        print("     2. pip install -r requirements.txt")
        print("     3. python -m uvicorn backend.main:app --reload")
    else:
        print("  ⚠️  มีบางไฟล์ขาดหายไป กรุณาตรวจสอบ")
        sys.exit(1)
    print("=" * 55)


if __name__ == "__main__":
    main()
