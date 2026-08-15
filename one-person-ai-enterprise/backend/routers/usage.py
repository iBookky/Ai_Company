from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services import usage_service
from backend.models.schemas import ApiResponse

router = APIRouter(prefix="/api/usage", tags=["Usage"])


class UpdateLimitsRequest(BaseModel):
    monthly_token_limit: int
    monthly_cost_limit: float


@router.get("")
async def get_usage_summary():
    """ดึงข้อมูลการใช้งานและลิมิต AI ทั้งหมด"""
    try:
        return usage_service.get_usage_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/limits")
async def update_usage_limits(req: UpdateLimitsRequest):
    """อัปเดตลิมิตการใช้โมเดลรายเดือน"""
    try:
        limits = {
            "monthly_token_limit": req.monthly_token_limit,
            "monthly_cost_limit": req.monthly_cost_limit
        }
        usage_service.save_limits(limits)
        return ApiResponse(success=True, message="อัปเดตลิมิตความปลอดภัยโมเดล AI เรียบร้อยแล้ว")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
