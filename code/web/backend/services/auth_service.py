# backend/services/auth_service.py
import sys
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.services.supabase_client import get_supabase_client
from backend.schemas.user import UserCreate, UserLogin, UserResponse, AuthResponse
import re

# JWT 토큰 검증을 위한 보안 스키마
security = HTTPBearer()

def validate_password(password: str) -> tuple[bool, str]:
    """
    비밀번호 유효성 검사
    - 8글자 이상
    - 대문자 1개 이상
    - 소문자 1개 이상
    - 특수문자 1개 이상
    """
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."
    
    if not re.search(r'[A-Z]', password):
        return False, "비밀번호에 대문자가 포함되어야 합니다."
        
    if not re.search(r'[a-z]', password):
        return False, "비밀번호에 소문자가 포함되어야 합니다."
        
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        return False, "비밀번호에 특수문자가 포함되어야 합니다."
        
    return True, "유효한 비밀번호입니다."

class AuthService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def signup(self, user_data: UserCreate) -> AuthResponse:
        """OTP 검증 완료된 사용자의 회원가입 처리"""
        try:
            # 1. 비밀번호 유효성 검사
            is_valid, error_message = validate_password(user_data.pw)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)
            
            # 2. User 테이블 중복 확인
            existing_users = self.supabase.from_("User").select("*").eq("email", user_data.email).execute()
            if existing_users.data:
                raise HTTPException(status_code=400, detail="이미 등록된 사용자입니다.")
            
            # 3. User 테이블에 사용자 정보 저장
            user_insert = self.supabase.from_("User").insert({
                "auth_id": None,  # 임시로 null, 아래에서 업데이트
                "name": user_data.name,
                "email": user_data.email,
                "pw": ""  # Supabase Auth에서 관리
            }).execute()
            
            if not user_insert.data:
                raise HTTPException(status_code=500, detail="사용자 정보 저장에 실패했습니다.")
            
            user_info = user_insert.data[0]
            
            # 4. Admin API로 임시 비밀번호를 실제 비밀번호로 업데이트
            try:
                import os
                from supabase import create_client
                
                # Service Role 키로 Admin 클라이언트 생성
                supabase_url = os.getenv('SUPABASE_URL', 'https://neephzhkioahjrjmawlp.supabase.co')
                service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
                
                if service_role_key:
                    admin_client = create_client(supabase_url, service_role_key)
                    
                    # Admin API로 사용자 목록에서 이메일로 검색
                    users_response = admin_client.auth.admin.list_users()
                    
                    target_user = None
                    # Supabase Admin API 응답 구조에 따라 처리
                    users_list = users_response if isinstance(users_response, list) else getattr(users_response, 'users', [])
                    
                    for user in users_list:
                        if hasattr(user, 'email') and user.email == user_data.email:
                            target_user = user
                            break
                    
                    if target_user:
                        # 바로 비밀번호 업데이트
                        admin_client.auth.admin.update_user_by_id(
                            target_user.id,
                            {"password": user_data.pw}
                        )
                        
                        # 실제 비밀번호로 로그인 시도
                        login_response = self.supabase.auth.sign_in_with_password({
                            "email": user_data.email,
                            "password": user_data.pw
                        })
                        
                        if login_response.user and login_response.session:
                            # auth_id 업데이트
                            auth_user_id = login_response.user.id
                            self.supabase.from_("User").update({
                                "auth_id": auth_user_id
                            }).eq("user_id", user_info["user_id"]).execute()
                            
                            return AuthResponse(
                                access_token=login_response.session.access_token,
                                refresh_token=login_response.session.refresh_token,
                                token_type="bearer",
                                user=UserResponse(
                                    user_id=user_info["user_id"],
                                    name=user_info["name"],
                                    email=user_info["email"]
                                )
                            )
                
            except Exception as admin_error:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Admin API 오류: {str(admin_error)}")
                pass
            
            # 5. 임시 응답 (비밀번호 업데이트 실패한 경우)
            return {
                "access_token": "",
                "refresh_token": None,
                "token_type": "bearer",
                "user": {
                    "user_id": user_info["user_id"],
                    "name": user_info["name"],
                    "email": user_info["email"]
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"회원가입 오류: {str(e)}")
    
    async def login(self, user_data: UserLogin) -> AuthResponse:
        """Supabase Auth를 이용한 로그인"""
        try:
            # Supabase Auth 로그인
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.pw
            })
            
            if auth_response.user is None or auth_response.session is None:
                raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
            
            # User 테이블에서 auth_id로 사용자 정보 조회
            auth_user_id = auth_response.user.id
            user_query = self.supabase.from_("User").select("*").eq("auth_id", auth_user_id).single().execute()
            
            if user_query.data:
                user_info = user_query.data
            else:
                # User 테이블에 정보가 없으면 생성 (이메일 인증 완료된 사용자)
                user_insert = self.supabase.from_("User").insert({
                    "auth_id": auth_user_id,
                    "name": auth_response.user.user_metadata.get("name", "사용자"),
                    "email": auth_response.user.email,
                    "pw": ""  # Supabase Auth에서 관리하므로 빈 값
                }).execute()
                
                if user_insert.data:
                    user_info = user_insert.data[0]
                else:
                    raise HTTPException(status_code=500, detail="사용자 정보 생성에 실패했습니다.")
            
            return AuthResponse(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token,
                token_type="bearer",
                user=UserResponse(
                    user_id=user_info["user_id"],
                    name=user_info["name"],
                    email=user_info["email"]
                )
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"로그인 오류: {str(e)}")
    
    async def logout(self, token: str) -> Dict[str, str]:
        """Supabase Auth 로그아웃"""
        try:
            # Supabase Auth 로그아웃
            self.supabase.auth.sign_out()
            return {"message": "로그아웃되었습니다."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"로그아웃 오류: {str(e)}")
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Supabase JWT 토큰 검증"""
        try:
            # Supabase JWT 토큰 검증
            user_response = self.supabase.auth.get_user(token)
            
            if user_response.user is None:
                raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
            
            return {
                "user_id": user_response.user.id,
                "email": user_response.user.email,
                "name": user_response.user.user_metadata.get("name", "사용자")
            }
            
        except Exception as e:
            raise HTTPException(status_code=401, detail="토큰 검증에 실패했습니다.")
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
        """현재 인증된 사용자 정보 반환 (Depends로 사용)"""
        try:
            token = credentials.credentials
            print(f"🔍 Received token: {token[:50]}...") # 토큰 앞부분만 로깅

            # Supabase JWT 토큰 검증
            print("🔍 Calling supabase.auth.get_user...")
            user_response = self.supabase.auth.get_user(token)
            print(f"🔍 Supabase response: {user_response}")
            
            if user_response.user is None:
                print("❌ user_response.user is None")
                raise HTTPException(status_code=401, detail="인증이 필요합니다.")
            
            # User 테이블에서 auth_id로 상세 정보 조회
            auth_user_id = user_response.user.id
            user_query = self.supabase.from_("User").select("*").eq("auth_id", auth_user_id).single().execute()
            
            if not user_query.data:
                raise HTTPException(status_code=404, detail="사용자 정보를 찾을 수 없습니다.")
            
            user_info = user_query.data
            return UserResponse(
                user_id=user_info["user_id"],
                name=user_info["name"],
                email=user_info["email"]
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ Auth error: {str(e)}")
            print(f"❌ Auth error type: {type(e)}")
            raise HTTPException(status_code=401, detail=f"사용자 인증에 실패했습니다: {str(e)}")
    
    async def send_email_otp(self, email: str) -> Dict[str, Any]:
        """회원가입용 이메일 OTP 코드 발송"""
        try:
            # 먼저 이메일 중복 확인
            existing_users = self.supabase.from_("User").select("*").eq("email", email).execute()
            if existing_users.data:
                raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
            
            import uuid
            import string
            import random
            
            # Supabase 비밀번호 정책에 맞는 임시 비밀번호 생성
            def generate_secure_password():
                # 각 카테고리에서 최소 1개씩 보장
                lowercase = random.choice(string.ascii_lowercase)
                uppercase = random.choice(string.ascii_uppercase)
                digit = random.choice(string.digits)
                special = random.choice('!@#$%^&*')
                
                # 나머지 12자리 랜덤 생성
                remaining_chars = string.ascii_letters + string.digits + '!@#$%^&*'
                remaining = ''.join(random.choices(remaining_chars, k=12))
                
                # 모든 문자 합치기
                password = lowercase + uppercase + digit + special + remaining
                
                # 문자 순서 랜덤하게 섞기
                password_list = list(password)
                random.shuffle(password_list)
                return ''.join(password_list)
            
            temp_password = generate_secure_password()
            
            # Supabase Auth 회원가입 (이메일 인증 필요 상태로 생성)
            signup_response = self.supabase.auth.sign_up({
                "email": email,
                "password": temp_password,
                "options": {
                    "email_redirect_to": None,  # 리다이렉트 없음
                    "data": {
                        "temp_signup": True  # 임시 회원가입 표시
                    }
                }
            })
            
            if signup_response.user is None:
                raise HTTPException(status_code=400, detail="이미 등록된 이메일이거나 회원가입에 실패했습니다.")
            
            return {"success": True, "message": "인증번호가 이메일로 발송되었습니다."}
            
        except HTTPException:
            # HTTPException은 그대로 재발생
            raise
        except Exception as e:
            print(f"❌ OTP 발송 중 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OTP 발송 실패: {str(e)}")
    
    async def verify_email_otp(self, email: str, code: str) -> Dict[str, Any]:
        """회원가입용 이메일 OTP 코드 검증"""
        try:
            # Supabase Auth OTP 검증 (회원가입 타입)
            verify_response = self.supabase.auth.verify_otp({
                "email": email,
                "token": code,
                "type": "signup"  # 회원가입 타입으로 변경
            })
            
            if verify_response.user is None or verify_response.session is None:
                raise HTTPException(status_code=400, detail="잘못된 인증번호입니다.")
            
            # 인증 성공 - 이제 이메일이 확인되었으므로 실제 회원가입 가능
            return {"success": True, "verified": True}
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"OTP 검증 실패: {str(e)}")
    
    
    
    async def sync_oauth_user(self, access_token: str) -> AuthResponse:
        """OAuth 로그인 후 사용자 정보 동기화 - 기존 사용자 확인/업데이트 로직 재사용"""
        try:
            print(f"🔄 OAuth 사용자 동기화 시작")
            
            # 1. Supabase 토큰으로 사용자 정보 조회
            user_response = self.supabase.auth.get_user(access_token)
            
            if not user_response.user:
                raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
            
            oauth_user = user_response.user
            print(f"✅ OAuth 사용자 정보 확인: {oauth_user.email}")
            
            # 2. 기존 사용자 확인 (이메일로 조회) - 기존 로직과 동일
            existing_user = self.supabase.from_("User").select("*").eq("email", oauth_user.email).execute()
            
            if existing_user.data:  # 기존 사용자 발견
                user_info = existing_user.data[0]
                print(f"🔄 기존 사용자 발견: {user_info['email']}")
                
                # OAuth 연동 정보가 없으면 추가 (기존 로직과 동일)
                if not user_info.get("oauth_provider"):
                    provider = self._detect_oauth_provider(oauth_user)
                    print(f"🔄 기존 사용자에 {provider} 연동 추가")
                    self.supabase.from_("User").update({
                        "oauth_provider": provider,
                        "auth_id": oauth_user.id
                    }).eq("user_id", user_info["user_id"]).execute()
                
                user_response_obj = UserResponse(
                    user_id=user_info["user_id"],
                    name=user_info["name"],
                    email=user_info["email"]
                )
            else:
                # 새로운 OAuth 사용자 생성 (기존 로직과 동일)
                print("🆕 새 OAuth 사용자 생성 시작")
                provider = self._detect_oauth_provider(oauth_user)
                user_name = (
                    oauth_user.user_metadata.get("full_name") or 
                    oauth_user.user_metadata.get("name") or 
                    f"{provider.title()} 사용자"
                )
                
                new_user_data = {
                    "auth_id": oauth_user.id,
                    "name": user_name,
                    "email": oauth_user.email,
                    "pw": "",  # OAuth 사용자는 빈 문자열 (NOT NULL 제약조건)
                    "oauth_provider": provider
                }
                print(f"🔍 새 사용자 데이터: {new_user_data}")
                
                user_insert = self.supabase.from_("User").insert(new_user_data).execute()
                
                if not user_insert.data:
                    raise HTTPException(status_code=500, detail="사용자 정보 저장에 실패했습니다.")
                
                user_info = user_insert.data[0]
                print(f"✅ 새 사용자 생성 완료: {user_info}")
                user_response_obj = UserResponse(
                    user_id=user_info["user_id"],
                    name=user_info["name"],
                    email=user_info["email"]
                )
            
            # 3. 응답 반환 (Supabase 토큰 그대로 사용)
            return AuthResponse(
                access_token=access_token,
                refresh_token=None,  # 프론트엔드에서 Supabase 세션으로 관리
                token_type="bearer",
                user=user_response_obj
            )
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"❌ OAuth 사용자 동기화 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"OAuth 사용자 동기화 실패: {str(e)}")
    
    def _detect_oauth_provider(self, oauth_user) -> str:
        """OAuth 사용자 정보에서 제공자 감지 (단순화)"""
        # Supabase app_metadata에서 provider 정보 확인
        if hasattr(oauth_user, 'app_metadata') and oauth_user.app_metadata:
            # Supabase는 app_metadata에 provider 정보를 포함
            provider_info = oauth_user.app_metadata.get('provider')
            if provider_info:
                return provider_info.lower()
        
        # 기본값 (fallback)
        return "google"
    

# 전역 서비스 인스턴스
auth_service = AuthService()

# 의존성 주입용 함수들
def get_auth_service() -> AuthService:
    return auth_service

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """현재 인증된 사용자 정보 반환 (FastAPI Depends용)"""
    return auth_service.get_current_user(credentials)