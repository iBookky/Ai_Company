from typing import Dict

# Dictionary to keep track of active statuses: agent_id -> state ("idle" or "processing")
_active_statuses: Dict[str, str] = {}


def set_agent_status(agent_id: str, status: str):
    """กำหนดสถานะของ Agent ('idle', 'processing')"""
    _active_statuses[agent_id] = status


def get_agent_status(agent_id: str) -> str:
    """ดึงสถานะปัจจุบันของ Agent"""
    return _active_statuses.get(agent_id, "idle")


def get_all_statuses() -> Dict[str, str]:
    """ดึงสถานะของ Agent ทั้งหมด"""
    return _active_statuses
