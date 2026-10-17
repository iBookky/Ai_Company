import os
import re
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List

from backend.services import simulation_service

BASE_DIR = Path(__file__).parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/api/simulation", tags=["Simulation"])


class SetAvatarUrlRequest(BaseModel):
    avatar_url: str


class StartSimulationRequest(BaseModel):
    preset: str = "systems_dev"  # systems_dev, social_content, collaborative, hiring_request, custom
    prompt: Optional[str] = ""


class ConfirmTaskRequest(BaseModel):
    feedback: Optional[str] = "อนุมัติปิดงานเรียบร้อยโดย Owner"
    owner_name: Optional[str] = "Owner"


class RequestRevisionRequest(BaseModel):
    feedback: str
    owner_name: Optional[str] = "Owner"


class HiringDecisionRequest(BaseModel):
    owner_name: Optional[str] = "Owner"
    reason: Optional[str] = ""


@router.get("/state")
async def get_simulation_state():
    """ดึงภาพรวมสถานะ Agent ทุกคน, งานที่รอยืนยัน, และคำขอสร้าง AI"""
    return simulation_service.get_simulation_state()


@router.get("/employees")
async def list_employees():
    """ดึงรายชื่อและสถานะ Workspace ของพนักงาน AI ทุกคน"""
    return simulation_service.list_employee_workspaces()


@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str):
    """ดึงข้อมูลโต๊ะทำงาน (Workspace), สถานะสด, สถิติ และประวัติงานย้อนหลังของพนักงานรายคน"""
    ws = simulation_service.get_employee_workspace(employee_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"ไม่พบพนักงานรหัส {employee_id}")
    return ws


@router.post("/employees/{employee_id}/avatar")
async def upload_employee_avatar(employee_id: str, file: UploadFile = File(...)):
    """อัปโหลดรูปประจำตัวใหม่สำหรับพนักงาน AI อย่างปลอดภัย พร้อมตรวจสอบ Magic Bytes และป้องกัน Path Traversal"""
    # 1. ตรวจสอบรหัสพนักงาน
    if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", employee_id):
        raise HTTPException(status_code=400, detail="รหัสพนักงานไม่ถูกต้อง")

    # 2. ตรวจสอบนามสกุลไฟล์
    original_filename = file.filename or "avatar.jpg"
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="ประเภทไฟล์ไม่รองรับ กรุณาใช้ไฟล์รูปภาพ .jpg, .png หรือ .webp เท่านั้น"
        )

    # 3. ตรวจสอบขนาดไฟล์ (จำกัด 5 MB)
    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"ขนาดไฟล์เกินกำหนด (สูงสุด 5 MB, ขนาดที่ส่งมา: {len(content) / (1024*1024):.2f} MB)"
        )

    # 4. ตรวจสอบ Magic Bytes เพื่อป้องกันการปลอมแปลงนามสกุล
    is_valid = False
    if ext in (".jpg", ".jpeg") and content[:3] == b"\xff\xd8\xff":
        is_valid = True
    elif ext == ".png" and content[:8] == b"\x89PNG\r\n\x1a\n":
        is_valid = True
    elif ext == ".webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        is_valid = True

    if not is_valid:
        raise HTTPException(status_code=400, detail="โครงสร้างไฟล์รูปภาพไม่ถูกต้อง หรือถูกแก้ไขเนื้อหา")

    # 5. เขียนไฟล์ลงในไดเรกทอรี avatars ป้องกัน Directory Traversal
    avatars_dir = FRONTEND_DIR / "img" / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)

    # ลบไฟล์นามสกุลอื่นของ employee นี้เพื่อไม่ให้มีไฟล์ขยะค้าง
    for old_ext in ALLOWED_AVATAR_EXTENSIONS:
        if old_ext != ext:
            old_file = avatars_dir / f"{employee_id}{old_ext}"
            if old_file.exists() and old_file.is_file():
                try:
                    old_file.unlink()
                except Exception:
                    pass

    safe_filename = f"{employee_id}{ext}"
    dest_path = (avatars_dir / safe_filename).resolve()

    if not dest_path.is_relative_to(avatars_dir.resolve()):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เขียนไฟล์นอกไดเรกทอรีที่กำหนด")

    dest_path.write_bytes(content)

    # 6. อัปเดต state และ config
    timestamp = int(datetime.now(timezone.utc).timestamp())
    avatar_url = f"/static/img/avatars/{safe_filename}?v={timestamp}"
    simulation_service.update_employee_avatar(employee_id, avatar_url)

    return {
        "status": "success",
        "message": f"เปลี่ยนรูปภาพพนักงาน {employee_id} เรียบร้อยแล้ว",
        "avatar_url": avatar_url,
    }


@router.post("/employees/{employee_id}/avatar-url")
async def set_employee_avatar_url(employee_id: str, req: SetAvatarUrlRequest):
    """กำหนด URL รูปภาพประจำตัว หรือเลือกจากรูป Preset ของระบบอย่างปลอดภัย"""
    if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", employee_id):
        raise HTTPException(status_code=400, detail="รหัสพนักงานไม่ถูกต้อง")

    url = req.avatar_url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="กรุณาระบุ URL รูปภาพ")

    # ป้องกัน XSS & SSRF: อนุญาตเฉพาะ http, https, /static/, data:image/
    is_safe = (
        url.startswith("/static/") or
        url.startswith("http://") or
        url.startswith("https://") or
        url.startswith("data:image/")
    )
    if not is_safe or "javascript:" in url.lower():
        raise HTTPException(status_code=400, detail="URL รูปภาพไม่ปลอดภัยหรือไม่รองรับ")

    simulation_service.update_employee_avatar(employee_id, url)
    return {
        "status": "success",
        "message": f"เปลี่ยนรูปภาพพนักงาน {employee_id} เรียบร้อยแล้ว",
        "avatar_url": url,
    }


@router.post("/employees/{employee_id}/avatar/reset")
async def reset_employee_avatar(employee_id: str):
    """รีเซ็ตรูปภาพพนักงาน AI กลับเป็นรูปมาตรฐานของระบบ"""
    if not re.match(r"^[a-zA-Z0-9_\-\u0E00-\u0E7F]+$", employee_id):
        raise HTTPException(status_code=400, detail="รหัสพนักงานไม่ถูกต้อง")

    default_url = simulation_service.reset_employee_avatar(employee_id)
    return {
        "status": "success",
        "message": "รีเซ็ตรูปภาพกลับเป็นค่าเริ่มต้นเรียบร้อยแล้ว",
        "avatar_url": default_url,
    }


@router.post("/start")
async def start_simulation(req: StartSimulationRequest):
    """สั่งเริ่มการจำลองการทำงานของทีม AI ตาม Preset หรือ Custom Prompt"""
    result = await simulation_service.run_simulation_preset(req.preset, req.prompt or "")
    return {"status": "success", "detail": result}


@router.post("/tasks/{task_id}/confirm")
async def confirm_task(task_id: str, req: ConfirmTaskRequest):
    """Owner กดยืนยันอนุมัติปิดงาน (Confirm & Close Task)"""
    result = await simulation_service.confirm_task(
        task_id=task_id,
        owner_name=req.owner_name or "Owner",
        feedback=req.feedback
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to confirm task"))
    return {"status": "confirmed", "task": result["task"]}


@router.post("/tasks/{task_id}/revise")
async def revise_task(task_id: str, req: RequestRevisionRequest):
    """Owner ส่งคำขอแก้ไขงานกลับไปยังทีม AI"""
    if not req.feedback.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุข้อเสนอแนะที่ต้องการให้แก้ไข")
    result = await simulation_service.request_revision(
        task_id=task_id,
        feedback=req.feedback.strip(),
        owner_name=req.owner_name or "Owner"
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to request revision"))
    return {"status": "revision_requested", "task": result["task"]}


@router.post("/hire/{proposal_id}/approve")
async def approve_hiring(proposal_id: str, req: HiringDecisionRequest):
    """Owner อนุมัติการสร้าง AI พนักงานใหม่เข้าสู่บริษัท"""
    result = await simulation_service.approve_hiring_proposal(
        proposal_id=proposal_id,
        owner_name=req.owner_name or "Owner"
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to approve hiring"))
    return {"status": "approved", "proposal": result["proposal"]}


@router.post("/hire/{proposal_id}/reject")
async def reject_hiring(proposal_id: str, req: HiringDecisionRequest):
    """Owner ปฏิเสธคำขอสร้าง AI"""
    result = await simulation_service.reject_hiring_proposal(
        proposal_id=proposal_id,
        reason=req.reason or "ยังไม่มีความจำเป็นในขณะนี้"
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to reject hiring"))
    return {"status": "rejected", "proposal": result["proposal"]}


@router.post("/reset")
async def reset_simulation():
    """รีเซ็ตสถานะทั้งหมดกลับสู่ค่าเริ่มต้น (Standby)"""
    return simulation_service.reset_simulation()


@router.get("/notifications")
async def get_notifications():
    """ดึงประวัติการส่ง Telegram Notifications ล่าสุด"""
    state = simulation_service.get_simulation_state()
    return state.get("notifications", [])


@router.websocket("/ws")
async def simulation_websocket(websocket: WebSocket):
    """WebSocket สำหรับรับการอัปเดตสถานะ Simulation แบบ Real-Time"""
    await websocket.accept()

    # ส่งสถานะเริ่มต้น
    initial_data = simulation_service.get_simulation_state()
    await websocket.send_text(initial_data.__str__() if isinstance(initial_data, str) else str(initial_data))

    async def send_update(data):
        try:
            import json
            payload = json.dumps(data, default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o), ensure_ascii=False)
            await websocket.send_text(payload)
        except Exception:
            pass

    simulation_service.subscribe_simulation_ws(send_update)

    try:
        while True:
            # รับคำสั่ง ping หรือ message จาก client
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_state":
                await send_update(simulation_service.get_simulation_state())
    except WebSocketDisconnect:
        simulation_service.unsubscribe_simulation_ws(send_update)
    except Exception:
        simulation_service.unsubscribe_simulation_ws(send_update)
