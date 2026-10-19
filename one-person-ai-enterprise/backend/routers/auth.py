"""
auth.py — Authentication & Security Router for One-Person AI Enterprise
Owner access control, session tokens, and password protection
"""

import os
import time
import hmac
import hashlib
import json
from pathlib import Path
from dotenv import load_dotenv, set_key
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def _get_secret_key() -> str:
    load_dotenv(ENV_FILE, override=False)
    secret = os.getenv("SECRET_KEY", "")
    if not secret:
        secret = "enterprise_secret_salt_2026_one_person_ai"
    return secret

def _get_owner_credentials() -> dict:
    load_dotenv(ENV_FILE, override=True)
    username = os.getenv("ENTERPRISE_USERNAME", "admin").strip()
    password = os.getenv("ENTERPRISE_PASSWORD", "admin1234").strip()
    owner_name = os.getenv("OWNER_NAME", "พี่บุ๊ค").strip()
    return {
        "username": username,
        "password": password,
        "owner_name": owner_name
    }

def create_session_token(username: str) -> str:
    secret = _get_secret_key()
    timestamp = int(time.time())
    payload = f"{username}:{timestamp}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"

def verify_session_token(token: str) -> bool:
    if not token:
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    username, ts_str, signature = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    # Check expiry (7 days)
    if time.time() - ts > 7 * 86400:
        return False
    secret = _get_secret_key()
    expected_sig = hmac.new(secret.encode(), f"{username}:{ts}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected_sig)

class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

@router.post("/login")
async def login(req: LoginRequest):
    creds = _get_owner_credentials()
    # Accept default admin, ibook, or telegram_owner_id
    valid_usernames = [
        creds["username"].lower(),
        "admin",
        "ibook",
        "ibookky",
        os.getenv("TELEGRAM_OWNER_ID", "").lower().replace("@", "")
    ]
    user_input = req.username.strip().lower()
    pass_input = req.password.strip()

    if user_input in valid_usernames and pass_input == creds["password"]:
        token = create_session_token(user_input)
        return {
            "status": "success",
            "token": token,
            "owner_name": creds["owner_name"],
            "username": user_input,
            "message": f"ยินดีต้อนรับคุณ {creds['owner_name']} เข้าสู่ระบบ AI Enterprise"
        }
    
    raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

@router.get("/verify")
async def verify(authorization: Optional[str] = Header(None)):
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
    elif authorization:
        token = authorization.strip()

    if not verify_session_token(token):
        raise HTTPException(status_code=401, detail="Session หมดอายุหรือไม่ถูกต้อง กรุณาเข้าสู่ระบบใหม่")
    
    creds = _get_owner_credentials()
    return {
        "status": "authenticated",
        "owner_name": creds["owner_name"],
        "username": creds["username"]
    }

@router.post("/change-password")
async def change_password(req: ChangePasswordRequest, authorization: Optional[str] = Header(None)):
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
    elif authorization:
        token = authorization.strip()

    if not verify_session_token(token):
        raise HTTPException(status_code=401, detail="ต้องเข้าสู่ระบบก่อนเปลี่ยนรหัสผ่าน")

    creds = _get_owner_credentials()
    if req.current_password.strip() != creds["password"]:
        raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")

    new_pass = req.new_password.strip()
    if len(new_pass) < 4:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 4 ตัวอักษร")

    set_key(str(ENV_FILE), "ENTERPRISE_PASSWORD", new_pass)
    return {
        "status": "success",
        "message": "เปลี่ยนรหัสผ่านเข้าสู่ระบบเรียบร้อยแล้ว"
    }
