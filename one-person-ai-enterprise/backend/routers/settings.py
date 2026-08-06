"""
settings.py — Router สำหรับอ่าน บันทึก และทดสอบการตั้งค่าระบบอย่างปลอดภัย
"""

import os
import json
import httpx
from pathlib import Path
from dotenv import load_dotenv, set_key
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.models.schemas import AppSettings, SettingsUpdate, ApiResponse, ModelChoice

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
DEPARTMENTS_DIR = BASE_DIR / "departments"

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class TestMessageRequest(BaseModel):
    chat_id: str
    message: str = "<b>[ทดสอบระบบ]</b> 🚀 ข้อความจาก One-Person AI Enterprise บอทเชื่อมต่อสำเร็จเรียบร้อย!"


def _load_settings() -> AppSettings:
    """โหลดการตั้งค่าจาก .env และ department config.json files"""
    load_dotenv(ENV_FILE, override=True)

    ops_json = os.getenv("TELEGRAM_OPS_CHAT_IDS", "")
    ops_chat_ids = {}
    if ops_json:
        try:
            ops_chat_ids = json.loads(ops_json)
        except Exception:
            pass

    # อ่าน ops_chat_id จากโฟลเดอร์ departments/ เสริม
    if DEPARTMENTS_DIR.exists():
        for dept_dir in DEPARTMENTS_DIR.iterdir():
            if dept_dir.is_dir() and not dept_dir.name.startswith("."):
                config_file = dept_dir / "config.json"
                if config_file.exists():
                    try:
                        cfg = json.loads(config_file.read_text(encoding="utf-8"))
                        if cfg.get("ops_chat_id"):
                            ops_chat_ids[dept_dir.name] = cfg["ops_chat_id"]
                    except Exception:
                        pass

    return AppSettings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_owner_id=os.getenv("TELEGRAM_OWNER_ID", ""),
        telegram_owner_direct_chat_id=os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", ""),
        telegram_exec_chat_id=os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", ""),
        telegram_admin_chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID", ""),
        telegram_ops_chat_id=os.getenv("TELEGRAM_OPS_CHAT_ID", ""),
        telegram_ops_chat_ids=ops_chat_ids,
        default_model=os.getenv("DEFAULT_MODEL", "gemini-1.5-flash"),
        gemini_fallback_models=os.getenv("GEMINI_FALLBACK_MODELS", ""),
        available_models=os.getenv("AVAILABLE_MODELS", ""),
        gemini_configured=bool(os.getenv("GEMINI_API_KEY")),
        anthropic_configured=bool(os.getenv("ANTHROPIC_API_KEY")),
        telegram_configured=bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    )


def _mask_key(key: str) -> str:
    """ซ่อนค่า API key หรือ Token เหลือแค่ 6 ตัวหลัง"""
    if not key or len(key) < 8:
        return "••••••••" if key else ""
    return "••••••••" + key[-6:]


@router.get("")
async def get_settings():
    """ดึงการตั้งค่าปัจจุบัน (ซ่อน API keys)"""
    settings = _load_settings()
    return {
        "gemini_api_key": _mask_key(settings.gemini_api_key),
        "gemini_configured": settings.gemini_configured,
        "anthropic_api_key": _mask_key(settings.anthropic_api_key),
        "anthropic_configured": settings.anthropic_configured,
        "telegram_bot_token": _mask_key(settings.telegram_bot_token),
        "telegram_owner_id": settings.telegram_owner_id,
        "telegram_owner_direct_chat_id": settings.telegram_owner_direct_chat_id,
        "telegram_exec_chat_id": settings.telegram_exec_chat_id,
        "telegram_admin_chat_id": settings.telegram_admin_chat_id,
        "telegram_ops_chat_id": settings.telegram_ops_chat_id,
        "telegram_ops_chat_ids": settings.telegram_ops_chat_ids,
        "telegram_configured": settings.telegram_configured,
        "default_model": settings.default_model,
        "gemini_fallback_models": settings.gemini_fallback_models,
        "available_models": settings.available_models,
    }


@router.put("", response_model=ApiResponse)
async def update_settings(data: SettingsUpdate):
    """บันทึกการตั้งค่าใหม่ลง .env และ sync กับ config.json ใน departments/"""
    if not ENV_FILE.exists():
        ENV_FILE.touch()
        os.chmod(ENV_FILE, 0o600)

    field_map = {
        "gemini_api_key": "GEMINI_API_KEY",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_owner_id": "TELEGRAM_OWNER_ID",
        "telegram_owner_direct_chat_id": "TELEGRAM_OWNER_DIRECT_CHAT_ID",
        "telegram_exec_chat_id": "TELEGRAM_EXEC_CHAT_ID",
        "telegram_admin_chat_id": "TELEGRAM_ADMIN_CHAT_ID",
        "telegram_ops_chat_id": "TELEGRAM_OPS_CHAT_ID",
        "default_model": "DEFAULT_MODEL",
        "gemini_fallback_models": "GEMINI_FALLBACK_MODELS",
        "available_models": "AVAILABLE_MODELS",
    }

    updated = []
    for field, env_key in field_map.items():
        value = getattr(data, field, None)
        # ป้องกันการบันทึกค่าที่ถูก mask (••••••••) กลับลง .env
        if value is not None and not str(value).startswith("••••••••"):
            env_value = value.value if hasattr(value, "value") else str(value)
            set_key(str(ENV_FILE), env_key, env_value)
            updated.append(field)

    # อัปเดต telegram_ops_chat_ids (Multi-Room Operations)
    if data.telegram_ops_chat_ids is not None:
        set_key(str(ENV_FILE), "TELEGRAM_OPS_CHAT_IDS", json.dumps(data.telegram_ops_chat_ids, ensure_ascii=False))
        updated.append("telegram_ops_chat_ids")

        # Sync ops_chat_id ลงในแต่ละแผนก departments/{dept_id}/config.json
        DEPARTMENTS_DIR.mkdir(parents=True, exist_ok=True)
        for dept_id, chat_id in data.telegram_ops_chat_ids.items():
            dept_dir = DEPARTMENTS_DIR / dept_id
            if dept_dir.exists():
                config_file = dept_dir / "config.json"
                cfg = {}
                if config_file.exists():
                    try:
                        cfg = json.loads(config_file.read_text(encoding="utf-8"))
                    except Exception:
                        pass
                cfg["ops_chat_id"] = chat_id
                config_file.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    # บังคับใช้สิทธิ์แบบปลอดภัย (0600 — อ่าน/เขียนได้เฉพาะ owner)
    try:
        os.chmod(ENV_FILE, 0o600)
    except Exception:
        pass

    # Reload env vars
    load_dotenv(ENV_FILE, override=True)

    # อัปเดต telegram service credentials
    import backend.services.telegram_service as tg_svc
    tg_svc.TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    tg_svc.TELEGRAM_OWNER_DIRECT_CHAT_ID = os.getenv("TELEGRAM_OWNER_DIRECT_CHAT_ID", "")
    tg_svc.TELEGRAM_EXEC_CHAT_ID = os.getenv("TELEGRAM_EXEC_CHAT_ID", "") or os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    tg_svc.TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
    tg_svc.TELEGRAM_OPS_CHAT_ID = os.getenv("TELEGRAM_OPS_CHAT_ID", "")
    tg_svc.TELEGRAM_OWNER_ID = os.getenv("TELEGRAM_OWNER_ID", "")
    if data.telegram_ops_chat_ids is not None:
        tg_svc.TELEGRAM_OPS_CHAT_IDS = data.telegram_ops_chat_ids

    # สั่งอัปเดต / เพิ่ม Polling สำหรับบอทที่เพิ่งตั้งค่าใหม่โดยอัตโนมัติ
    await tg_svc.start_telegram_polling()

    return ApiResponse(
        success=True,
        message=f"บันทึกการตั้งค่าสำเร็จ ({len(updated)} รายการ)",
        data={"updated_fields": updated}
    )


@router.post("/test")
async def test_credentials():
    """ทดสอบการเชื่อมต่อจริงสำหรับ Telegram Bot Token และ LLM API Keys"""
    results = {}

    # 1. ทดสอบ Telegram Bot Token
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if token:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                if resp.status_code == 200:
                    bot_data = resp.json().get("result", {})
                    results["telegram"] = {
                        "ok": True,
                        "bot_name": bot_data.get("first_name", ""),
                        "bot_username": f"@{bot_data.get('username', '')}",
                        "message": f"เชื่อมต่อสำเร็จ! บอทชื่อ: {bot_data.get('first_name')} (@{bot_data.get('username')})"
                    }
                else:
                    results["telegram"] = {
                        "ok": False,
                        "message": f"Telegram API คืนค่ารหัสผิดพลาด ({resp.status_code}): Token ไม่ถูกต้อง"
                    }
        except Exception as e:
            results["telegram"] = {"ok": False, "message": f"ไม่สามารถเชื่อมต่อ Telegram API: {str(e)}"}
    else:
        results["telegram"] = {"ok": False, "message": "ยังไม่ได้กรอก Telegram Bot Token"}

    # 2. สถานะ Gemini Key
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    results["gemini"] = {
        "ok": bool(gemini_key),
        "message": "ตั้งค่า Gemini API Key เรียบร้อยแล้ว" if gemini_key else "ยังไม่ได้ตั้งค่า Gemini Key"
    }

    # 3. สถานะ Anthropic Key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    results["anthropic"] = {
        "ok": bool(anthropic_key),
        "message": "ตั้งค่า Anthropic API Key เรียบร้อยแล้ว" if anthropic_key else "ยังไม่ได้ตั้งค่า Claude Key"
    }

    return {"status": "ok", "results": results}


@router.post("/test-message")
async def test_send_message(req: TestMessageRequest):
    """ส่งข้อความทดสอบไปยัง Telegram Chat ID ที่ระบุจริง"""
    if not req.chat_id.strip():
        raise HTTPException(status_code=400, detail="กรุณาระบุ Telegram Chat ID ที่ต้องการทดสอบส่ง")

    import backend.services.telegram_service as tg_svc
    success = await tg_svc.send_telegram_message(req.chat_id.strip(), req.message)

    if success:
        return {"status": "success", "message": f"ส่งข้อความทดสอบไปยัง Chat ID ({req.chat_id}) สำเร็จ! กรุณาเช็คในแอป Telegram"}
    else:
        raise HTTPException(status_code=400, detail="ส่งข้อความไม่สำเร็จ กรุณาตรวจสอบ Chat ID หรือตรวจสอบว่าได้ดึงบอทเข้าแชท/กด /start แล้วหรือยัง")


@router.get("/models")
async def get_available_models():
    """ดึงรายชื่อโมเดลที่รองรับทั้งหมด"""
    return [
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Google", "context": "1M tokens", "tier": "premium"},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "Google", "context": "1M tokens", "tier": "fast"},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "Anthropic", "context": "200K tokens", "tier": "premium"},
        {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "Anthropic", "context": "200K tokens", "tier": "fast"},
    ]
