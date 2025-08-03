# backend/routers/auth.py
import sys
import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.schemas.user import UserCreate, UserLogin, UserResponse, AuthResponse
from pydantic import BaseModel
from backend.services.auth_service import get_auth_service, get_current_user, AuthService

# 라우터 초기화
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# 보안 스키마
security = HTTPBearer()

# OTP 관련 스키마
class SendOTPRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    email: str
    code: str

@auth_router.post("/signup", response_model=AuthResponse)
async def signup(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    회원가입 - Supabase Auth 이메일 인증 사용
    
    이메일 인증이 필요하며, 사용자는 이메일을 확인한 후 인증을 완료해야 합니다.
    """
    try:
        result = await auth_service.signup(user_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원가입 처리 중 오류가 발생했습니다: {str(e)}")

@auth_router.post("/login", response_model=AuthResponse)
async def login(
    user_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    로그인 - Supabase Auth 사용
    
    이메일 인증이 완료된 사용자만 로그인 가능합니다.
    """
    try:
        result = await auth_service.login(user_data)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그인 처리 중 오류가 발생했습니다: {str(e)}")

@auth_router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    로그아웃 - Supabase Auth 세션 종료
    """
    try:
        token = credentials.credentials
        result = await auth_service.logout(token)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그아웃 처리 중 오류가 발생했습니다: {str(e)}")

@auth_router.get("/user", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    현재 인증된 사용자 정보 조회
    
    JWT 토큰이 필요합니다.
    """
    return current_user

@auth_router.get("/verify")
async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    토큰 유효성 검증
    """
    try:
        token = credentials.credentials
        result = auth_service.verify_token(token)
        return {"valid": True, "user": result}
    except HTTPException:
        return {"valid": False, "error": "Invalid token"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

@auth_router.post("/send-otp")
async def send_otp(
    request: SendOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    이메일로 OTP 코드 발송
    """
    try:
        result = await auth_service.send_email_otp(request.email)
        return {"success": True, "message": "인증번호가 이메일로 발송되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP 발송 중 오류가 발생했습니다: {str(e)}")

@auth_router.post("/verify-otp")
async def verify_otp(
    request: VerifyOTPRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    이메일 OTP 코드 검증
    """
    try:
        result = await auth_service.verify_email_otp(request.email, request.code)
        return {"success": True, "verified": True, "message": "이메일 인증이 완료되었습니다."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OTP 검증 중 오류가 발생했습니다: {str(e)}")