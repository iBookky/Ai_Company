"""
agents.py — Router สำหรับ Agent CRUD API
"""

from fastapi import APIRouter, HTTPException, status
from backend.models.schemas import AgentCreate, AgentRead, AgentUpdate, AgentDetail, ApiResponse
from backend.services import agent_service
from backend.services.log_service import write_log
from backend.models.schemas import LogCreate, LogLevel

router = APIRouter(prefix="/api/agents", tags=["Agents"])


@router.get("", response_model=list[AgentRead])
async def list_agents():
    """ดึงรายชื่อ Agent ทั้งหมด"""
    return agent_service.list_agents()


@router.get("/{agent_id}", response_model=AgentDetail)
async def get_agent(agent_id: str):
    """ดึงข้อมูล Agent พร้อม identity + skill เต็ม"""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"ไม่พบ Agent: {agent_id}")
    return agent


@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
async def create_agent(data: AgentCreate):
    """สร้าง Agent ใหม่"""
    try:
        agent = agent_service.create_agent(data)
        write_log(LogCreate(
            agent_id=agent.id,
            agent_name=agent.name,
            level=LogLevel.SUCCESS,
            message=f"สร้าง Agent ใหม่สำเร็จ: {agent.name} (Model: {agent.model})",
        ))
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"สร้าง Agent ไม่สำเร็จ: {str(e)}")


@router.put("/{agent_id}", response_model=AgentRead)
async def update_agent(agent_id: str, data: AgentUpdate):
    """อัปเดตข้อมูล Agent"""
    agent = agent_service.update_agent(agent_id, data)
    if not agent:
        raise HTTPException(status_code=404, detail=f"ไม่พบ Agent: {agent_id}")
    write_log(LogCreate(
        agent_id=agent.id,
        agent_name=agent.name,
        level=LogLevel.INFO,
        message=f"อัปเดต Agent สำเร็จ: {agent.name}",
    ))
    return agent


@router.delete("/{agent_id}", response_model=ApiResponse)
async def delete_agent(agent_id: str):
    """ลบ Agent"""
    success = agent_service.delete_agent(agent_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"ไม่พบ Agent: {agent_id}")
    write_log(LogCreate(
        agent_id=agent_id,
        agent_name=agent_id,
        level=LogLevel.WARNING,
        message=f"ลบ Agent: {agent_id}",
    ))
    return ApiResponse(success=True, message=f"ลบ Agent {agent_id} เรียบร้อยแล้ว")
