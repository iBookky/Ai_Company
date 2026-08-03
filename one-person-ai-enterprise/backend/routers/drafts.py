"""
drafts.py — Router สำหรับ Draft Repository (อัปโหลด, ดู, พิมพ์)
"""

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
DRAFTS_DIR = BASE_DIR / "drafts"

ALLOWED_TYPES = {
    "application/pdf", "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain", "image/png", "image/jpeg",
}

router = APIRouter(prefix="/api/drafts", tags=["Drafts"])


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

    categories = [category] if category else ["proposals", "accounting", "contracts"]
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
    """อัปโหลดเอกสารร่างใหม่"""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"ประเภทไฟล์ไม่รองรับ: {file.content_type}"
        )

    cat_dir = DRAFTS_DIR / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    # สร้างชื่อไฟล์ unique
    suffix = Path(file.filename).suffix
    unique_name = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = cat_dir / unique_name

    async with aiofiles.open(file_path, "wb") as out:
        content = await file.read()
        await out.write(content)

    return _read_draft_meta(file_path, category)


@router.get("/{category}/{file_id}/download")
async def download_draft(category: str, file_id: str):
    """ดาวน์โหลดไฟล์"""
    cat_dir = DRAFTS_DIR / category
    matches = list(cat_dir.glob(f"{file_id}*"))
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
    """ดูไฟล์ในเบราว์เซอร์ (inline)"""
    cat_dir = DRAFTS_DIR / category
    matches = list(cat_dir.glob(f"{file_id}*"))
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
    """ลบเอกสารร่าง"""
    cat_dir = DRAFTS_DIR / category
    matches = list(cat_dir.glob(f"{file_id}*"))
    if not matches:
        raise HTTPException(status_code=404, detail="ไม่พบไฟล์")

    matches[0].unlink()
    return ApiResponse(success=True, message=f"ลบไฟล์เรียบร้อยแล้ว")
