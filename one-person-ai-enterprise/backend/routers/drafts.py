import re
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import aiofiles

from backend.models.schemas import DraftFile, ApiResponse

BASE_DIR = Path(__file__).parent.parent.parent
DRAFTS_DIR = (BASE_DIR / "drafts").resolve()

ALLOWED_CATEGORIES = {"proposals", "accounting", "contracts"}
ALLOWED_TYPES = {
    "application/pdf", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "image/png", "image/jpeg",
}
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB

router = APIRouter(prefix="/api/drafts", tags=["Drafts"])


def _check_category(category: str) -> str:
    cat = category.strip().lower()
    if cat not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"หมวดหมู่ไม่ถูกต้อง รองรับเฉพาะ: {', '.join(ALLOWED_CATEGORIES)}")
    return cat


def _check_file_id(file_id: str) -> str:
    fid = file_id.strip()
    if not re.match(r"^[a-zA-Z0-9_\-]+$", fid):
        raise HTTPException(status_code=400, detail="รหัสไฟล์ไม่ถูกต้อง")
    return fid


def _read_draft_meta(file_path: Path, category: str) -> DraftFile:
    stat = file_path.stat()
    content_type, _ = mimetypes.guess_type(str(file_path))
    return DraftFile(
        id=file_path.stem,
        name=file_path.name,
        category=category,
        size_bytes=stat.st_size,
        content_type=content_type or "application/octet-stream",
        uploaded_at=datetime.fromtimestamp(stat.st_mtime),
        path=str(file_path),
    )


@router.get("", response_model=list[DraftFile])
async def list_drafts(category: Optional[str] = None):
    """ดึงรายการเอกสารร่างทั้งหมด แยกตามหมวดหมู่"""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    drafts = []

    if category:
        categories = [_check_category(category)]
    else:
        categories = list(ALLOWED_CATEGORIES)

    for cat in categories:
        cat_dir = DRAFTS_DIR / cat
        if cat_dir.exists():
            for f in sorted(cat_dir.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        drafts.append(_read_draft_meta(f, cat))
                    except Exception:
                        pass
    return drafts


@router.post("/upload", response_model=DraftFile, status_code=201)
async def upload_draft(
    file: UploadFile = File(...),
    category: str = Form("proposals"),
    description: Optional[str] = Form(None),
):
    """อัปโหลดเอกสารร่างใหม่ พร้อมการตรวจสอบความปลอดภัยอย่างรัดกุม"""
    valid_cat = _check_category(category)

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"ประเภทไฟล์ไม่รองรับ: {file.content_type}"
        )

    cat_dir = (DRAFTS_DIR / valid_cat).resolve()
    cat_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize original filename ป้องกัน Directory Traversal
    raw_filename = Path(file.filename or "upload").name
    safe_name = re.sub(r"[^\w\.\-]", "_", raw_filename)
    unique_name = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    file_path = (cat_dir / unique_name).resolve()

    if not file_path.is_relative_to(DRAFTS_DIR):
        raise HTTPException(status_code=403, detail="ไม่อนุญาตให้เขียนไฟล์นอกไดเรกทอรีที่กำหนด")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="ขนาดไฟล์เกินขีดจำกัด (สูงสุด 15 MB)")

    async with aiofiles.open(file_path, "wb") as out:
        await out.write(content)

    return _read_draft_meta(file_path, valid_cat)


@router.get("/{category}/{file_id}/download")
async def download_draft(category: str, file_id: str):
    """ดาวน์โหลดไฟล์อย่างปลอดภัย"""
    valid_cat = _check_category(category)
    valid_id = _check_file_id(file_id)

    cat_dir = (DRAFTS_DIR / valid_cat).resolve()
    matches = [f for f in cat_dir.glob(f"{valid_id}*") if f.is_file() and f.resolve().is_relative_to(DRAFTS_DIR)]
    if not matches:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")

    file_path = matches[0]
    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type=mimetypes.guess_type(str(file_path))[0] or "application/octet-stream",
    )


@router.get("/{category}/{file_id}/view")
async def view_draft(category: str, file_id: str):
    """ดูไฟล์ในเบราว์เซอร์ (inline) อย่างปลอดภัย"""
    valid_cat = _check_category(category)
    valid_id = _check_file_id(file_id)

    cat_dir = (DRAFTS_DIR / valid_cat).resolve()
    matches = [f for f in cat_dir.glob(f"{valid_id}*") if f.is_file() and f.resolve().is_relative_to(DRAFTS_DIR)]
    if not matches:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")

    file_path = matches[0]
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        headers={"Content-Disposition": "inline"},
    )


@router.delete("/{category}/{file_id}", response_model=ApiResponse)
async def delete_draft(category: str, file_id: str):
    """ลบเอกสารร่างอย่างปลอดภัย"""
    valid_cat = _check_category(category)
    valid_id = _check_file_id(file_id)

    cat_dir = (DRAFTS_DIR / valid_cat).resolve()
    matches = [f for f in cat_dir.glob(f"{valid_id}*") if f.is_file() and f.resolve().is_relative_to(DRAFTS_DIR)]
    if not matches:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")

    matches[0].unlink()
    return ApiResponse(success=True, message="ลบไฟล์เรียบร้อยแล้ว")
