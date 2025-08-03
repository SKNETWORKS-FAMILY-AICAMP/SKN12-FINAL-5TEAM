from backend.services.existing_tables_service import existing_tables_service
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from backend.services.supabase_client import supabase_client
from backend.schemas.user import UserCreate, UserResponse, UserNameUpdate
from backend.services.auth_service import get_current_user

user_router = APIRouter(prefix="/user", tags=["User"])

# 🟢 GET /user/me – 내 프로필 조회
@user_router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: UserResponse = Depends(get_current_user)):
    """인증된 사용자의 프로필 정보 조회"""
    return current_user

# 🔵 PUT /user/me – 내 프로필 수정
@user_router.put("/me", response_model=UserResponse)
def update_my_profile(
    user_update: UserNameUpdate, 
    current_user: UserResponse = Depends(get_current_user)
):
    """인증된 사용자의 프로필 정보 수정"""
    res = supabase_client.client.from_("User").update(user_update.dict()).eq("user_id", current_user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="User not found")
    return res.data[0]