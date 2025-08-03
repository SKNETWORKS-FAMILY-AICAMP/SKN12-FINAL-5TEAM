from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.services.supabase_client import supabase_client
from backend.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse
from backend.schemas.user import UserResponse
from backend.services.auth_service import AuthService

# AuthService 인스턴스 생성
auth_service = AuthService()

resume_router = APIRouter(prefix="/resume", tags=["Resume"])

# 소유권 검증 헬퍼 함수
def verify_resume_ownership(resume_id: int, user_id: int) -> dict:
    """이력서 소유권을 검증하고 이력서 데이터를 반환합니다."""
    res = supabase_client.client.from_("user_resume").select("*").eq("user_resume_id", resume_id).single().execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail="Resume not found")
    
    resume_data = res.data
    if resume_data["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You don't have permission to access this resume")
    
    return resume_data

# 🟢 GET /resume – 내 이력서 목록 조회
@resume_router.get("/", response_model=List[ResumeResponse])
async def get_resumes(current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 이력서 목록을 조회합니다."""
    res = supabase_client.client.from_("user_resume").select("*").eq("user_id", current_user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No resumes found")
    return res.data
    
# 🟡 POST /resume – 이력서 생성
@resume_router.post("/", response_model=ResumeResponse)
async def create_resume(resume: ResumeCreate, current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 새 이력서를 생성합니다."""
    data = {**resume.dict(), "user_id": current_user.user_id}
    res = supabase_client.client.from_("user_resume").insert(data).execute()
    
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create resume")
    return res.data[0]  

# 🟢 GET /resume/{resume_id} – 이력서 상세 조회
@resume_router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(resume_id: int, current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 특정 이력서를 조회합니다."""
    resume_data = verify_resume_ownership(resume_id, current_user.user_id)
    return resume_data

# 🔵 PUT /resume/{resume_id} – 이력서 수정
@resume_router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(resume_id: int, resume: ResumeUpdate, current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 이력서를 수정합니다."""
    # 소유권 검증
    verify_resume_ownership(resume_id, current_user.user_id)
    
    # 이력서 수정
    res = supabase_client.client.from_("user_resume").update(resume.dict()).eq("user_resume_id", resume_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to update resume")
    return res.data[0]

# 🔴 DELETE /resume/{resume_id} – 이력서 삭제
@resume_router.delete("/{resume_id}")
async def delete_resume(resume_id: int, current_user: UserResponse = Depends(auth_service.get_current_user)):
    """현재 인증된 사용자의 이력서를 삭제합니다."""
    # 소유권 검증
    verify_resume_ownership(resume_id, current_user.user_id)
    
    # 이력서 삭제
    res = supabase_client.client.from_("user_resume").delete().eq("user_resume_id", resume_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to delete resume")
    return {"message": "Resume deleted successfully"}
