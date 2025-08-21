"""
Supabase 클라이언트 설정 및 관리
"""

import os
from supabase import create_client, Client
from typing import Optional
import logging
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)

class SupabaseClient:
    """Supabase 클라이언트 싱글톤"""
    
    _instance: Optional['SupabaseClient'] = None
    _client: Optional[Client] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._initialize_client()
    
    def _initialize_client(self):
        """Supabase 클라이언트 초기화"""
        try:
            # 환경변수에서 설정 로드
            supabase_url = os.getenv('SUPABASE_URL', 'https://neephzhkioahjrjmawlp.supabase.co')
            supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
            
            if not supabase_url or not supabase_key:
                raise ValueError("Supabase URL 또는 SERVICE_ROLE_KEY가 설정되지 않았습니다.")
            
            self._client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase 클라이언트 초기화 완료 (service_role_key 사용)")
            
        except Exception as e:
            logger.error(f"❌ Supabase 클라이언트 초기화 실패: {str(e)}")
            raise
    
    @property
    def client(self) -> Client:
        """Supabase 클라이언트 반환"""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def get_user_client(self, user_token: str) -> Client:
        """사용자 JWT 토큰을 사용하는 Supabase 클라이언트 반환"""
        supabase_url = os.getenv('SUPABASE_URL', 'https://neephzhkioahjrjmawlp.supabase.co')
        supabase_key = os.getenv(
            'SUPABASE_ANON_KEY', 
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5lZXBoemhraW9haGpyam1hd2xwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTIyMTIwODcsImV4cCI6MjA2Nzc4ODA4N30.o4uLLdGxFclnRi-FEBeaEVCUklstLPIF6JRVM1pNLBc'
        )
        
        # 사용자 토큰으로 클라이언트 생성
        user_client = create_client(supabase_url, supabase_key)
        
        # 방법 1: set_session으로 사용자 토큰 설정
        try:
            user_client.auth.set_session(
                access_token=user_token,
                refresh_token=""
            )
            print(f"✅ set_session 성공")
        except Exception as e:
            print(f"❌ set_session 실패: {e}")
            # 방법 2: postgrest.auth로 설정
            try:
                user_client.postgrest.auth(user_token)
                print(f"✅ postgrest.auth 성공")
            except Exception as e2:
                print(f"❌ postgrest.auth 실패: {e2}")
                # 방법 3: 헤더 직접 설정 (백업)
                user_client.auth._headers = {"Authorization": f"Bearer {user_token}"}
                print(f"⚠️ 헤더 직접 설정 사용")
        
        return user_client

    def health_check(self) -> bool:
        """Supabase 연결 상태 확인"""
        try:
            # 간단한 쿼리로 연결 테스트
            result = self.client.table('interviews').select('count').limit(1).execute()
            logger.info("✅ Supabase 연결 상태 양호")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {str(e)}")
            return False

# 전역 클라이언트 인스턴스
supabase_client = SupabaseClient()

def get_supabase_client() -> Client:
    """Supabase 클라이언트 의존성 주입용 함수"""
    return supabase_client.client

def get_user_supabase_client(user_token: str) -> Client:
    """사용자 JWT 토큰을 사용하는 Supabase 클라이언트"""
    return supabase_client.get_user_client(user_token)