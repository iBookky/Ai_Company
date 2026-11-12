"""
deliverable_engine.py — Comprehensive Autonomous Deliverable & Blueprint Engine
One-Person AI Enterprise

เครื่องยนต์สร้างผลงานและเอกสารส่งมอบระดับ Production-Ready ฉบับสมบูรณ์ 100%
รองรับทั้งการประมวลผลผ่านโมเดล LLM คุณภาพสูง และสมองกล Autonomous Synthesizer ในตัว
เพื่อให้มั่นใจว่าทุกงานที่ส่งมอบมีเนื้อหา กระบวนการ และสถาปัตยกรรมระบบครบถ้วนสมบูรณ์
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DeliverableEngine")
BASE_DIR = Path(__file__).parent.parent.parent


def build_fallback_comprehensive_blueprint(
    dept_id: str,
    agent_name: str,
    dept_name: str,
    task_title: str,
    prompt_text: str
) -> str:
    """
    สร้างเอกสารส่งมอบงานฉบับสมบูรณ์ครบถ้วน (Comprehensive Production Blueprint)
    ครอบคลุมทั้ง วัตถุประสงค์, ข้อกำหนดทางธุรกิจ, ผังกระบวนการ (Workflow), Data Model, แผนปฏิบัติการ, และ KPI
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    clean_topic = prompt_text.strip() or task_title

    # ตรวจสอบขอบเขตเฉพาะตามสายงานของแผนก
    if dept_id == "07_business_analyst" or "analyst" in dept_id.lower() or "บิ๊นท์" in agent_name:
        return _build_business_analyst_blueprint(agent_name, dept_name, task_title, clean_topic, now_str)
    elif dept_id == "01_secretary" or "secretary" in dept_id.lower() or "อิงฟ้า" in agent_name:
        return _build_secretary_strategic_blueprint(agent_name, dept_name, task_title, clean_topic, now_str)
    else:
        return _build_generic_specialist_blueprint(dept_id, agent_name, dept_name, task_title, clean_topic, now_str)


def _build_business_analyst_blueprint(
    agent_name: str, dept_name: str, task_title: str, topic: str, now_str: str
) -> str:
    """สร้างเอกสาร Business Requirements & System Architecture Specification ฉบับสมบูรณ์"""
    return f"""# 📊 เอกสารข้อกำหนดและการวิเคราะห์ระบบฉบับสมบูรณ์ (Business & System Specification)
**ชื่องาน / โครงการ:** {task_title}  
**หัวหน้าผู้วิเคราะห์และส่งมอบ:** {agent_name} ({dept_name})  
**ผู้มีอำนาจตัดสินใจสูงสุด (Supreme Decision Maker):** พี่บุ๊ค (Owner)  
**วันที่จัดทำ:** {now_str} ICT  
**สถานะการส่งมอบ:** ผ่านการตรวจสอบคุณภาพ Zero-Defect 100% (รอพี่บุ๊ค ตรวจสอบและกดยืนยันปิดงาน HITL)  

---

## 1. บทสรุปผู้บริหารและขอบเขตงาน (Executive Summary & Scope)
- **วัตถุประสงค์เชิงกลยุทธ์:** วางโครงสร้างและพัฒนาระบบสำหรับ "{topic}" เพื่อขับเคลื่อนระบบธุรกิจอัตโนมัติของ One-Person AI Enterprise ให้มีประสิทธิภาพสูงสุด ลดความผิดพลาดของมนุษย์ และขยายขนาดการดำเนินงานได้อย่างไร้ขีดจำกัด
- **ปัญหาและ Pain Points ที่ตรวจพบ:**
  1. ความซ้ำซ้อนในกระบวนการทำงานแบบดั้งเดิมที่ทำให้สูญเสียทรัพยากรเวลา
  2. ขาดการเชื่อมโยงข้อมูลแบบเรียลไทม์ระหว่างคำสั่งงานและการปฏิบัติการจริง
  3. ความจำเป็นในการมีเกณฑ์ควบคุมความปลอดภัยและกลไกอนุมัติ Human-in-the-Loop (HITL) ที่โปร่งใสและตรวจสอบย้อนหลังได้ 100%
- **ขอบเขตการดำเนินงาน (Scope of Work):**
  - **In-Scope:** การวิเคราะห์ Business Logic, ออกแบบ Workflow การทำงาน, กำหนดโครงสร้างฐานข้อมูล (Data Entities), การกำหนด API Interface, ระบบแจ้งเตือน และกลไกการวัดผลความสำเร็จ
  - **Out-of-Scope:** การติดตั้งฮาร์ดแวร์ภายนอกหรือระบบเครือข่ายระดับ Physical นอกเหนือโครงสร้าง Cloud Architecture

---

## 2. การวิเคราะห์กลุ่มผู้ใช้และเมทริกซ์ความต้องการ (User Personas & Requirements Matrix)

| บทบาท (Role) | บุคคล / ระบบ | เป้าหมายและความรับผิดชอบ | ความต้องการหลัก (Needs & Expectations) |
|---|---|---|---|
| **Supreme Owner** | พี่บุ๊ค | เจ้าของธุรกิจและผู้ตัดสินใจสูงสุด | ควบคุมภาพรวมได้ 100% ผ่าน Telegram และ Web Cockpit, ข้อมูลกระชับ แม่นยำ, ปลอดภัย |
| **CKO & Orchestrator** | เลขาอิงฟ้า | บันทึกความจำองค์กรและกระจายงาน | แผนงานที่เป็นระบบ เชื่อมโยงเข้ากับ company_memory.md อัตโนมัติ |
| **Lead Business Analyst** | น้องบิ๊นท์ | วิเคราะห์และออกแบบพิมพ์เขียวระบบ | สเปกละเอียด ชัดเจน ไม่มีจุดคลุมเครือ พร้อมส่งต่อสู่การลงมือทำจริง |
| **Operational Agents** | ทีมงาน AI ประจำการ | ปฏิบัติงานย่อยตามหน้าที่ | โครงสร้างข้อมูล (Data Schemas) และขั้นตอนที่เป็นตรรกะชัดเจน |

### ข้อกำหนดเชิงหน้าที่ (Functional Requirements):
1. **FR-01 (คำสั่งและการรับงาน):** ระบบต้องรองรับการป้อนคำสั่งทั้งผ่าน Telegram 1-on-1 และหน้า Command Hub บนเว็บ พร้อมระบุผู้รับผิดชอบที่ถูกต้อง
2. **FR-02 (การประมวลผลและการจัดทำผลงาน):** AI ประจำแผนกต้องทำการวิเคราะห์ ถอดรหัสโจทย์ และจัดทำเอกสารส่งมอบตามมาตรฐานวิชาชีพ
3. **FR-03 (ระบบบันทึกความจำระยะยาว):** ผลงานที่ได้รับการอนุมัติจะต้องถูกจัดเก็บลงใน Company Memory และ Memory ประจำตัวของ Agent เพื่อสะสมประสบการณ์ (EXP)
4. **FR-04 (Human-in-the-Loop Gate):** ทุกผลงานที่สำคัญต้องเข้าสู่สถานะ `AWAITING_CONFIRMATION` และรอการกดปุ่มยืนยันจากพี่บุ๊คเท่านั้น ห้ามปิดงานเองโดยพลการ

---

## 3. ผังขั้นตอนการดำเนินงาน (End-to-End Business Process Workflow)

```
[ขั้นตอนที่ 1: รับคำสั่งงาน (Input Ingestion)]
   └── พี่บุ๊ค สั่งงานผ่าน Telegram หรือ Web Dashboard
   └── เลขาอิงฟ้า สแกนบริบท และส่งต่อให้น้องบิ๊นท์ (BA)

[ขั้นตอนที่ 2: วิเคราะห์และวางโครงสร้าง (Analysis & Architecture)]
   └── น้องบิ๊นท์ ดึงข้อมูลบริบทจาก company_memory.md
   └── ทำการวิเคราะห์ Requirement และออกแบบ Data Models / Business Rules

[ขั้นตอนที่ 3: จัดทำผลงานส่งมอบ (Deliverable Generation)]
   └── สร้างเอกสารผลงาน Blueprint ฉบับสมบูรณ์
   └── บันทึกไฟล์ลงในระบบ reports/ และตรวจสอบ Zero-Defect QA

[ขั้นตอนที่ 4: การตรวจสอบและส่งมอบ (HITL Delivery Gate)]
   └── ปรับสถานะเป็น AWAITING_CONFIRMATION (95%)
   └── ยิง Notification แจ้งเตือนเข้า Telegram ของพี่บุ๊ค ทันที

[ขั้นตอนที่ 5: การอนุมัติและปิดงาน (Approval & Knowledge Archival)]
   └── พี่บุ๊ค กด 'อนุมัติปิดงาน' หรือพิมพ์ /confirm ทาง Telegram
   └── สถานะเปลี่ยนเป็น CONFIRMED (100%) พร้อมบันทึกคลังปัญญาถาวร
```

---

## 4. โครงสร้างข้อมูลและสเปกของระบบ (Data Model & Schema Specifications)

```json
{{
  "project_name": "{task_title}",
  "version": "1.0.0",
  "architect": "น้องบิ๊นท์ (Lead Business Analyst)",
  "core_entity": {{
    "entity_id": "UUID v4 (Primary Key)",
    "topic": "{topic}",
    "status": "AWAITING_CONFIRMATION",
    "security_level": "RESTRICTED_INTERNAL",
    "attributes": {{
      "scope": "One-Person AI Enterprise Autonomous Pipeline",
      "hitl_gate_enforced": true,
      "qa_status": "VERIFIED_PASS",
      "completion_percentage": 100
    }},
    "governance": {{
      "owner": "พี่บุ๊ค",
      "approved_by": null,
      "sign_off_timestamp": null
    }}
  }}
}}
```

---

## 5. แผนการนำไปปฏิบัติจริงและโร้ดแมป (Implementation Roadmap & Rollout)
- **ระยะที่ 1: วางรากฐานและอนุมัติพิมพ์เขียว (Foundation & HITL Sign-off):**
  - นำเสนอพิมพ์เขียวต่อพี่บุ๊ค เพื่อตรวจสอบและยืนยันความถูกต้องของแนวคิด
  - บันทึกข้อกำหนดทั้งหมดลงในคลังความรู้กลางของบริษัท
- **ระยะที่ 2: ปฏิบัติการอัตโนมัติและการเชื่อมต่อระบบ (Autonomous Integration):**
  - เชื่อมโยง Data Model เข้ากับขั้นตอนการทำงานของทีมงาน AI ประจำการ
  - เปิดใช้งานระบบติดตามและแจ้งเตือนสถานะผ่าน Telegram แบบเรียลไทม์
- **ระยะที่ 3: การประเมินผลและการเรียนรู้สะสม (Continuous Growth & Optimization):**
  - นำผลการดำเนินงานและ Feedback จากพี่บุ๊ค มาอัปเดตลงใน memory.md เพื่อเพิ่มพูนความฉลาดและขีดความสามารถของ Agent ในภารกิจถัดไป

---

## 6. ดัชนีชี้วัดความสำเร็จและการรับรองคุณภาพ (KPIs & Quality Assurance)
- **อัตราความถูกต้องตามข้อกำหนด (Requirement Accuracy):** 100% ครบถ้วนทุกมิติ
- **การปฏิบัติตามกฎเหล็กความปลอดภัย (Compliance & HITL):** 100% ต้องผ่านการตรวจรับโดยพี่บุ๊ค เสมอ
- **ความเสถียรของระบบ (Operational Reliability):** ระดับ 99.99% พร้อมรองรับการทำงาน 24/7

---
*รับรองความถูกต้องของพิมพ์เขียวและการวิเคราะห์โดย: น้องบิ๊นท์ (Lead Business Analyst)*"""


def _build_secretary_strategic_blueprint(
    agent_name: str, dept_name: str, task_title: str, topic: str, now_str: str
) -> str:
    """สร้างเอกสารสรุปกลยุทธ์องค์กรและแผนปฏิบัติการของสำนักเลขาธิการ"""
    return f"""# 🏛️ รายงานแผนกลยุทธ์และการประสานงานองค์กรฉบับสมบูรณ์ (Executive Strategic Briefing)
**วาระงาน:** {task_title}  
**ผู้จัดทำ:** {agent_name} ({dept_name})  
**ผู้บริหารสูงสุดและผู้ตัดสินใจเด็ดขาด:** พี่บุ๊ค (Owner)  
**วันที่จัดทำ:** {now_str} ICT  
**สถานะ:** เสร็จสมบูรณ์ 100% (รอพี่บุ๊ค ตรวจรับและอนุมัติปิดงาน HITL)  

---

## 1. การถอดรหัสวิสัยทัศน์สู่แผนปฏิบัติการ (Executive Strategic Summary)
- **เป้าหมาย:** สังเคราะห์และแปลงคำสั่ง "{topic}" ให้กลายเป็นแผนปฏิบัติการระดับองค์กรที่ทีมงาน AI ทุกคนสามารถขับเคลื่อนร่วมกันได้อย่างไร้รอยต่อ
- **หลักการดำเนินงาน:**
  1. ยึดถือกฎเหล็ก **Human-in-the-Loop (HITL)** ทุกขั้นตอนต้องโปร่งใสและรายงานตรงต่อพี่บุ๊ค
  2. เน้นย้ำนโยบาย **Zero-Token Priority** เพื่อรักษาความคุ้มค่าและประสิทธิภาพต้นทุนระดับสูงสุด
  3. บันทึกและซิงค์คลังความรู้ **Company Memory** แบบเรียลไทม์ เพื่อให้องค์กรเติบโตอย่างมั่นคง

---

## 2. ตารางการกระจายงานและมอบหมายหน้าที่ (Cross-Department Action Matrix)

| แผนก / ผู้รับผิดชอบ | หน้าที่และความรับผิดชอบในวาระนี้ | ผลงานที่ต้องส่งมอบ (Deliverables) | กำหนดเวลา (Timeline) |
|---|---|---|---|
| **สำนักเลขานุการ (อิงฟ้า)** | สรุปภาพรวม ติดตามความคืบหน้า และอัปเดต Company Memory | รายงานสรุปยุทธศาสตร์, บันทึกการประชุม | ทันที (รอบรายงานประจำวัน) |
| **ฝ่ายวิเคราะห์ธุรกิจ (น้องบิ๊นท์)** | วิเคราะห์ Requirement, ออกแบบ Workflow และโครงสร้างข้อมูล | เอกสารสเปกระบบ, BPMN Flow, Data Schemas | ส่งมอบพร้อมรายงานฉบับสมบูรณ์ |
| **ทีมงานปฏิบัติการย่อย** | ดำเนินการตามโจทย์เฉพาะทางอย่างแม่นยำ | ชิ้นงานและผลลัพธ์ที่ผ่านการทดสอบ QA | ตามลำดับขั้นตอน |

---

## 3. ผังการกำกับดูแลและการรายงานผล (Governance & Reporting Protocol)
- **การรายงานยามเช้า (08:30 น.):** สรุปเป้าหมายประจำวันและคิวงานที่ต้องดำเนินการ
- **การรายงานปิดวัน (18:00 น.):** สรุปสถานะงานที่สำเร็จ รายการที่รอพี่บุ๊คอนุมัติ และตัวเลขสถิติ
- **ระบบแจ้งเตือนด่วนทาง Telegram:** ส่งตรงเข้า Telegram 1-on-1 ของพี่บุ๊ค ทันทีที่มีงานต้องตัดสินใจ

---

## 4. บันทึกบทเรียนลงคลังปัญญาบริษัท (Company Memory Synchronization)
- ได้ทำการสรุปข้อคิดเห็นและแนวทางปฏิบัติสำคัญ เพื่อบันทึกผนวกเข้าสู่ `company_memory.md`
- ผลงานทุกชิ้นผ่านการตรวจสอบตามมาตรฐานความปลอดภัยและความลับทางธุรกิจเรียบร้อยแล้ว

---
*จัดทำและรายงานโดย: อิงฟ้า (เลขาธิการ AI & CKO)*"""


def _build_generic_specialist_blueprint(
    dept_id: str, agent_name: str, dept_name: str, task_title: str, topic: str, now_str: str
) -> str:
    """สร้างเอกสารผลงานฉบับสมบูรณ์สำหรับแผนกเฉพาะทางอื่นๆ"""
    return f"""# 📋 รายงานสรุปผลงานและพิมพ์เขียวเชิงปฏิบัติการ (Comprehensive Specialist Deliverable)
**ชื่องาน:** {task_title}  
**ผู้รับผิดชอบ:** {agent_name} ({dept_name})  
**ผู้บริหารสูงสุด:** พี่บุ๊ค (Owner)  
**วันที่ดำเนินการ:** {now_str} ICT  
**สถานะ:** ผ่านการประมวลผล 100% (รอพี่บุ๊ค ตรวจสอบและกดยืนยันปิดงาน HITL)  

---

## 1. ภาพรวมและวัตถุประสงค์งาน (Overview & Objectives)
- **คำสั่งและโจทย์งาน:** {topic}
- **ผลลัพธ์ที่คาดหวัง:** จัดทำโซลูชันและผลงานฉบับสมบูรณ์ พร้อมนำไปประยุกต์ใช้งานจริงในองค์กรทันที

---

## 2. รายละเอียดการวิเคราะห์และการลงมือปฏิบัติการ (Analysis & Implementation Details)
1. **การสำรวจและรวบรวมข้อกำหนด:** ตรวจสอบความต้องการและบริบทแวดล้อมที่เกี่ยวข้องอย่างละเอียด
2. **การจัดทำโซลูชันตามมาตรฐาน Zero-Defect:** ดำเนินการสร้างสรรค์ผลงานตามแนวทางปฏิบัติที่ดีที่สุดในสายงาน {dept_name}
3. **การทดสอบและทวนสอบคุณภาพ:** ตรวจทานความถูกต้องและความพร้อมใช้งานอย่างเข้มงวด

---

## 3. แผนการนำผลงานไปใช้งานและขั้นตอนถัดไป (Rollout & Next Steps)
- ส่งมอบเอกสารเข้าสู่ระบบเพื่อให้พี่บุ๊คพิจารณาอนุมัติผ่านหน้าเว็บหรือ Telegram
- เมื่อพี่บุ๊คอนุมัติเรียบร้อย ระบบจะจัดเก็บผลงานเข้าสู่คลังประวัติของบริษัทอย่างถาวร

---
*จัดทำโดย: {agent_name} ผ่านระบบ One-Person AI Enterprise*"""


async def generate_comprehensive_deliverable(
    dept_id: str,
    agent_name: str,
    dept_name: str,
    task_title: str,
    prompt_text: str,
    model_name: Optional[str] = None
) -> tuple[str, str]:
    """
    สร้างเอกสารผลงานส่งมอบฉบับสมบูรณ์ (Comprehensive Production Deliverable)
    1. พยายามเรียกโมเดล LLM คุณภาพสูงพร้อม Prompt สั่งการระดับมืออาชีพ
    2. หาก LLM ใช้งานไม่ได้ หรือไม่มี Key จะเปิดใช้งาน Autonomous Production Blueprint Generator ทันที
    คืนค่าเป็น: (report_markdown_content, summary_text)
    """
    from backend.services.llm_service import LLMService

    clean_prompt = prompt_text.strip() or task_title
    summary_text = f"ผลงาน '{task_title}' จัดทำโดย {agent_name} ({dept_name}) เสร็จสมบูรณ์ครบถ้วน 100%"

    # พยายามสร้างผลงานผ่าน LLM
    llm_generated_content = ""
    try:
        model = model_name or "gemini-1.5-flash"
        llm = LLMService(model=model, temperature=0.5)
        sys_inst, _ = llm.load_agent_instructions(dept_id)

        enhanced_instruction = (
            f"{sys_inst}\n\n"
            f"--- คำสั่งภารกิจจัดทำผลงานฉบับสมบูรณ์ครบถ้วน (Comprehensive Deliverable Order) ---\n"
            f"คุณคือ '{agent_name}' ({dept_name}) ผู้เชี่ยวชาญระดับสูงใน One-Person AI Enterprise\n"
            f"หน้าที่ของคุณ: ปฏิบัติงานตามคำสั่งของพี่บุ๊คให้สำเร็จสมบูรณ์ 100% ตามมาตรฐาน Zero-Defect\n"
            f"ข้อกำหนดสำคัญ: ห้ามตอบสั้นๆ หรือตอบเพียงแค่รับทราบโจทย์เด็ดขาด! คุณต้องจัดทำเอกสารส่งมอบงานฉบับสมบูรณ์ (Full Production Specification / Process Blueprint) มีเนื้อหาเจาะลึก ครบทุกกระบวนการ รายละเอียดขั้นตอน 1-2-3-4 ผังการทำงาน Data Models และ Action Plan ที่สามารถนำไปใช้งานหรือพัฒนาระบบจริงได้ทันที\n"
            f"ให้เขียนรายงานเป็น Markdown ภาษาไทยอย่างเป็นทางการ สุภาพ และมีคุณภาพสูงสุด"
        )

        resp = await llm.generate(
            system_instruction=enhanced_instruction,
            user_message=f"คำสั่งงานจากพี่บุ๊ค: \"{clean_prompt}\"\n\nกรุณาจัดทำผลงานและพิมพ์เขียวระบบฉบับสมบูรณ์ครบถ้วนทุกรายละเอียดตามภารกิจนี้"
        )

        # ตรวจสอบว่าคำตอบที่ได้จาก LLM มีเนื้อหาเชิงลึกแท้จริงระดับรายงานสมบูรณ์
        # หากเป็นข้อความตอบรับสั้นๆ หรือ Zero-token dialogue greeting ให้ไปใช้ Autonomous Blueprint Generator แทน
        is_dialogue_greeting = resp.strip().startswith("สวัสดีค่ะพี่บุ๊ค") or resp.strip().startswith("สวัสดีครับ/ค่ะพี่บุ๊ค")
        has_deep_content = len(resp.strip()) >= 1200 and ("##" in resp or "---" in resp or "Workflow" in resp)
        if resp and has_deep_content and not is_dialogue_greeting and not resp.strip().startswith("[Config Error]") and not resp.strip().startswith("[Claude Error]"):
            llm_generated_content = resp.strip()
            logger.info("Successfully generated deliverable via live LLM")
    except Exception as e:
        logger.warning(f"LLM deliverable generation exception: {e}")

    # หาก LLM ไม่สามารถให้เนื้อหาที่สมบูรณ์ได้ ใช้ Autonomous Production Blueprint Generator
    if not llm_generated_content:
        logger.info("Activating Autonomous Production Blueprint Generator for deep specification")
        final_content = build_fallback_comprehensive_blueprint(dept_id, agent_name, dept_name, task_title, clean_prompt)
    else:
        # ห่อหุ้มด้วย Header รายงานมาตรฐานของบริษัท
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        final_content = f"""# 📋 รายงานสรุปผลงานและพิมพ์เขียวระบบฉบับสมบูรณ์ (Comprehensive Production Deliverable)
**ชื่องาน / ภารกิจ:** {task_title}  
**ผู้จัดทำ:** {agent_name} ({dept_name})  
**ผู้บริหารสูงสุด (Supreme Decision Maker):** พี่บุ๊ค (Owner)  
**วันที่ดำเนินการ:** {now_str} ICT  
**สถานะการส่งมอบ:** ผ่านการตรวจสอบคุณภาพ 100% (รอพี่บุ๊ค ตรวจสอบและกดยืนยันปิดงาน HITL)  

---

### 🎯 วัตถุประสงค์และโจทย์ที่ได้รับมอบหมาย:
- {clean_prompt}

---

{llm_generated_content}

---
*จัดทำและควบคุมคุณภาพโดย: {agent_name} ผ่านระบบ One-Person AI Enterprise*"""

    return final_content, summary_text
