# 🏢 One-Person AI Enterprise

ระบบบริหารทีม AI สำหรับเจ้าของธุรกิจคนเดียว — สร้าง, จัดการ, และควบคุม AI Agents ทั้งหมดผ่านหน้าเว็บ Dashboard เดียว

---

## 🚀 วิธีเริ่มต้นใช้งาน

### ขั้นตอนที่ 1: Setup โครงสร้างโฟลเดอร์
```bash
cd one-person-ai-enterprise
python3 scripts/setup.py
```

### ขั้นตอนที่ 2: ติดตั้ง Dependencies
```bash
pip3 install -r requirements.txt
```

### ขั้นตอนที่ 3: ตั้งค่า API Keys
แก้ไขไฟล์ `.env` (สร้างอัตโนมัติจาก setup.py):
```bash
nano .env
```
ใส่ค่าต่อไปนี้:
```
GEMINI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
SKYPE_APP_ID=your_app_id
SKYPE_APP_PASSWORD=your_password
SKYPE_ADMIN_ROOM_ID=19:xxxxxxxx@thread.skype
SKYPE_OPS_ROOM_ID=19:xxxxxxxx@thread.skype
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNO...
TELEGRAM_ADMIN_CHAT_ID=-100123456789
TELEGRAM_OPS_CHAT_ID=-100987654321
TELEGRAM_OWNER_ID=@myusername
```
> 💡 ใส่ผ่านหน้า **Settings** บน Dashboard ได้ง่ายๆ ใน 1 นาที

### ขั้นตอนที่ 4: รัน Backend Server
```bash
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### ขั้นตอนที่ 5: เปิด Dashboard
เปิดเบราว์เซอร์ไปที่: **http://localhost:8000**

---

## 📁 โครงสร้างโปรเจกต์

```
one-person-ai-enterprise/
├── backend/
│   ├── main.py                 ← FastAPI App Entry Point
│   ├── models/
│   │   └── schemas.py          ← Pydantic Data Models
│   ├── routers/
│   │   ├── agents.py           ← Agent CRUD API
│   │   ├── logs.py             ← Logging API + WebSocket
│   │   ├── drafts.py           ← Draft Repository API
│   │   ├── telegram.py         ← Telegram Webhook + Simulator
│   │   └── settings.py         ← Settings API (อ่าน/เขียน .env)
│   └── services/
│       ├── agent_service.py    ← Business Logic สำหรับ Agent
│       ├── llm_service.py      ← Wrapper Gemini + Claude
│       ├── log_service.py      ← Central Logging + WS Broadcast
│       └── telegram_service.py ← Dual-Verification Loop Logic (Telegram)
├── frontend/
│   ├── index.html              ← SPA Main Page
│   ├── css/style.css           ← Design System (Dark Mode)
│   └── js/
│       ├── app.js              ← Router + WebSocket + Utilities
│       ├── agents.js           ← Agent Builder UI
│       ├── logs.js             ← Log Viewer (Real-time)
│       ├── drafts.js           ← Draft Repository UI
│       ├── telegram.js         ← Telegram Room Monitor
│       └── settings.js         ← Settings Form
├── departments/
│   ├── 01_secretary/
│   │   ├── identity.md         ← บุคลิกภาพ/บทบาท
│   │   ├── skill.md            ← ทักษะและคำสั่ง
│   │   └── config.json         ← Model, Temperature
│   └── 02_marketing/
│       ├── identity.md
│       ├── skill.md
│       └── config.json
├── logs/
│   └── system.jsonl            ← Central Log File
├── drafts/
│   ├── proposals/              ← ใบเสนอราคา
│   ├── accounting/             ← เอกสารบัญชี
│   └── contracts/              ← สัญญา
├── config/
│   └── settings.yaml           ← App Configuration
├── scripts/
│   ├── setup.py                ← สร้างโครงสร้างเริ่มต้น
│   └── scan_agents.py          ← สแกน Agent ทั้งหมด
├── .env                        ← API Keys (ไม่ commit)
├── .env.example                ← Template
└── requirements.txt
```

---

## 🤖 วิธีสร้าง Agent ใหม่

1. เปิด Dashboard → คลิก **"จัดการ Agents"**
2. กดปุ่ม **"＋ สร้าง Agent ใหม่"**
3. กรอกข้อมูล:
   - **ชื่อตำแหน่ง**: เช่น "นักเขียน Content"
   - **โมเดลสมอง**: เลือก Gemini / Claude
   - **Temperature**: ปรับ slider (0.0 = แม่นยำ, 1.0 = สร้างสรรค์)
   - **Identity**: บอก AI ว่าตัวเองเป็นใคร มีหน้าที่อะไร
   - **Skills**: บอก AI ว่าทำได้อะไร ทำอย่างไร
4. กด **"บันทึก Agent"**

ระบบจะสร้างโฟลเดอร์ `departments/XX_name/` พร้อม `identity.md`, `skill.md`, `config.json` โดยอัตโนมัติ

---

## ✈️ ระบบ Telegram Dual-Verification Loop

### การสร้าง Telegram Bot ใน 1 นาที (ฟรี 100%)
1. เปิดแอป Telegram แล้วค้นหาบอท `@BotFather`
2. พิมพ์คำสั่ง `/newbot` ตั้งชื่อบอท → ได้รับ **HTTP API Token** ทันที
3. นำ Token มาใส่ในหน้า **Settings** บน Dashboard

### การทำงาน
```
Owner ส่งคำสั่งในกลุ่ม Telegram (Admin Chat)
  ↓
เลขา AI ดักจับ → สรุป → ทวนกลับ
  ↓
Owner พิมพ์ "ใช่" หรือ "อนุมัติ" เพื่อยืนยัน
  ↓
PM AI คำนวณ Timeline + Budget → ส่งแผนลงกลุ่ม Admin
  ↓
PM กระจายงานลงกลุ่มปฏิบัติการ (Ops Chat) ให้ AI ลูกน้อง
```

### ทดสอบโดยไม่ต้องตั้งค่า Telegram จริง
ใช้ **Simulator** ในหน้า "Telegram Rooms":
- พิมพ์คำสั่งในช่อง → กด "ส่งคำสั่งจำลอง"
- ดูผลการยืนยันและการกระจายงานได้ทันที


---

## 📋 API Endpoints

| Method | URL | คำอธิบาย |
|--------|-----|----------|
| GET | `/api/agents` | รายชื่อ Agent ทั้งหมด |
| POST | `/api/agents` | สร้าง Agent ใหม่ |
| PUT | `/api/agents/{id}` | แก้ไข Agent |
| DELETE | `/api/agents/{id}` | ลบ Agent |
| GET | `/api/logs` | ดึง Logs |
| POST | `/api/logs` | บันทึก Log |
| WS | `/api/logs/ws` | Real-time Logs |
| GET | `/api/drafts` | รายการเอกสารร่าง |
| POST | `/api/drafts/upload` | อัปโหลดเอกสาร |
| POST | `/api/skype/webhook` | Skype Bot Webhook |
| POST | `/api/skype/simulate` | ทดสอบ Skype |
| GET/PUT | `/api/settings` | อ่าน/บันทึก Settings |

**Swagger UI**: http://localhost:8000/docs

---

## 🔧 การขยายระบบ

### เพิ่มแผนกใหม่
```bash
mkdir departments/03_sales
# สร้างไฟล์ identity.md, skill.md
# หรือผ่านหน้า Dashboard
```

### เพิ่ม LLM Model ใหม่
แก้ไข `backend/models/schemas.py`:
```python
class ModelChoice(str, Enum):
    # เพิ่ม model ใหม่ที่นี่
    MY_MODEL = "my-model-name"
```

### บันทึก Log จาก Agent ภายนอก
```python
import httpx
httpx.post("http://localhost:8000/api/logs", json={
    "agent_id": "my_agent",
    "agent_name": "My Agent",
    "level": "ERROR",
    "message": "เกิดข้อผิดพลาด: ...",
    "thought_process": "ขั้นตอน 1: ...",
})
```
