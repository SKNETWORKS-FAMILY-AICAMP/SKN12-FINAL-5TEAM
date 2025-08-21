from fastapi import APIRouter, HTTPException
from typing import List
from backend.services.supabase_client import supabase_client
from backend.schemas.position import PositionResponse

position_router = APIRouter(prefix="/position", tags=["Position"])

# 🟢 GET /position – 전체 직군 목록 조회
@position_router.get("", response_model=List[PositionResponse])
def get_positions():
    """
    모든 직군(position) 목록을 조회합니다.
    인증이 필요하지 않은 공개 API입니다.
    """
    res = supabase_client.client.from_("position").select("*").order("position_id").execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No positions found")
    return res.data